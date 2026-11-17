from __future__ import annotations

import re
from dataclasses import dataclass

ORACLE_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]{0,127}$")
OCI_OCID_RE = re.compile(r"^ocid1\.[a-z0-9]+\.")


class ValidationError(ValueError):
    """Raised when deployment input cannot be safely rendered."""


@dataclass(frozen=True, order=True)
class DbObject:
    owner: str
    name: str

    @property
    def qualified_name(self) -> str:
        return f"{self.owner}.{self.name}"


def normalize_identifier(value: str, label: str = "identifier") -> str:
    cleaned = value.strip().upper()
    if not ORACLE_IDENTIFIER_RE.fullmatch(cleaned):
        raise ValidationError(
            f"{label} must be an unquoted Oracle identifier using letters, numbers, _, $, or #: {value!r}"
        )
    return cleaned


def normalize_csv_identifiers(raw: str | None, label: str) -> list[str]:
    if not raw:
        return []
    values = [normalize_identifier(part, label) for part in raw.split(",") if part.strip()]
    return sorted(dict.fromkeys(values))


def normalize_db_objects(raw: str | None) -> list[DbObject]:
    if not raw:
        return []
    objects: list[DbObject] = []
    for part in raw.split(","):
        value = part.strip()
        if not value:
            continue
        pieces = value.split(".")
        if len(pieces) != 2:
            raise ValidationError(f"table entries must use OWNER.TABLE format: {value!r}")
        owner = normalize_identifier(pieces[0], "table owner")
        name = normalize_identifier(pieces[1], "table name")
        objects.append(DbObject(owner=owner, name=name))
    return sorted(dict.fromkeys(objects))


def validate_ocid(value: str | None, label: str) -> str | None:
    if value is None or value == "":
        return None
    cleaned = value.strip()
    if not OCI_OCID_RE.match(cleaned):
        raise ValidationError(f"{label} must look like an OCI OCID: {value!r}")
    return cleaned


def csv_quote(values: list[str]) -> str:
    return ", ".join(sql_string(value) for value in values)


def sql_identifier(value: str) -> str:
    return normalize_identifier(value)


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def q_quote(value: str, delimiter: str = "~") -> str:
    marker = f"{delimiter}'"
    if marker in value:
        raise ValidationError(f"Cannot q-quote value containing {marker!r}")
    return f"q'{delimiter}{value}{delimiter}'"


def redact_secret(value: str, keep: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= keep:
        return "***"
    return f"{value[:keep]}***REDACTED***"
