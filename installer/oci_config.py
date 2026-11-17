from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .validators import ValidationError


@dataclass(frozen=True)
class OciConfig:
    tenancy: str
    user: str
    fingerprint: str
    region: str


def parse_oci_config_text(text: str, profile: str = "DEFAULT") -> OciConfig:
    current_profile: str | None = None
    values: dict[str, str] = {}
    wanted = profile.strip() or "DEFAULT"

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_profile = line[1:-1].strip()
            continue
        if current_profile is None:
            current_profile = "DEFAULT"
        if current_profile != wanted or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

    missing = [key for key in ("tenancy", "user", "fingerprint", "region") if not values.get(key)]
    if missing:
        raise ValidationError(f"OCI config profile {wanted!r} is missing: {', '.join(missing)}")
    return OciConfig(
        tenancy=values["tenancy"],
        user=values["user"],
        fingerprint=values["fingerprint"],
        region=values["region"],
    )


def read_oci_config(path: Path, profile: str = "DEFAULT") -> OciConfig:
    return parse_oci_config_text(path.read_text(encoding="utf-8"), profile=profile)
