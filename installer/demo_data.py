from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from .validators import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = REPO_ROOT / "data"
IDENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]*$")


@dataclass(frozen=True)
class DemoSchemaEntry:
    schema: str
    folder: str
    aliases: tuple[str, ...]
    metadata_path: str
    row_source: str
    tables: tuple[str, ...]
    label: str = ""
    use_case: str = ""

    @property
    def root(self) -> Path:
        return DEMO_ROOT / self.folder

    @property
    def data_dir(self) -> Path:
        return self.root / self.metadata_path


@dataclass(frozen=True)
class DemoLoadTableResult:
    table: str
    rows: int


def sql_identifier(value: str) -> str:
    cleaned = value.strip().upper()
    if not IDENT_RE.match(cleaned):
        raise ValidationError(f"Unsupported Oracle identifier: {value!r}")
    return '"' + cleaned.replace('"', '""') + '"'


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def constraint_name(prefix: str, table_name: str, suffix: str = "") -> str:
    raw = f"{prefix}_{table_name}{suffix}".upper()
    return raw if len(raw) <= 128 else raw[:120]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def demo_catalog() -> list[dict[str, Any]]:
    manifest_path = DEMO_ROOT / "manifest.json"
    if not manifest_path.exists():
        return []
    manifest = _load_json(manifest_path)
    demos = manifest.get("demos", [])
    if not isinstance(demos, list):
        raise ValidationError("data/manifest.json must contain a demos array")
    return [demo for demo in demos if isinstance(demo, dict)]


def demo_entries() -> dict[str, DemoSchemaEntry]:
    entries: dict[str, DemoSchemaEntry] = {}
    for demo in demo_catalog():
        schema = str(demo.get("schema", "")).strip().upper()
        folder = str(demo.get("folder", "")).strip()
        if not schema or not folder:
            continue
        entry = DemoSchemaEntry(
            schema=schema,
            folder=folder,
            aliases=tuple(str(alias).strip().upper() for alias in demo.get("aliases", []) if str(alias).strip()),
            metadata_path=str(demo.get("metadata_path") or "data").strip() or "data",
            row_source=str(demo.get("row_source") or "data/*.csv").strip() or "data/*.csv",
            tables=tuple(str(table).strip().upper() for table in demo.get("tables", []) if str(table).strip()),
            label=str(demo.get("label", "")).strip(),
            use_case=str(demo.get("use_case") or demo.get("domain") or "").strip(),
        )
        entries[entry.schema] = entry
        for alias in entry.aliases:
            entries[alias] = entry
    return entries


def demo_entry_for_schema(schema: str) -> DemoSchemaEntry | None:
    return demo_entries().get(schema.strip().upper())


def table_metadata(entry: DemoSchemaEntry) -> list[tuple[Path, dict[str, Any]]]:
    if not entry.root.exists():
        raise FileNotFoundError(f"Missing demo folder: {entry.root}")
    table_names = list(entry.tables) or sorted(path.stem.upper() for path in entry.data_dir.glob("*.json"))
    metadata: list[tuple[Path, dict[str, Any]]] = []
    for table_name in table_names:
        path = entry.data_dir / f"{table_name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Missing metadata file: {path}")
        item = _load_json(path)
        owner_name = str(item.get("owner_name", "")).upper()
        declared_table = str(item.get("table_name", "")).upper()
        if owner_name != entry.schema:
            raise ValidationError(f"{path}: owner_name {owner_name!r} must be {entry.schema!r}")
        if declared_table != table_name:
            raise ValidationError(f"{path}: table_name {declared_table!r} must be {table_name!r}")
        csv_path = path.with_suffix(".csv")
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing CSV file: {csv_path}")
        metadata.append((path, item))
    return metadata


def render_create_table(schema: str, table: dict[str, Any]) -> str:
    table_name = str(table["table_name"]).upper()
    definitions: list[str] = []
    pk_columns: list[str] = []
    for column in sorted(table["columns"], key=lambda item: int(item.get("ordinal_position", 0))):
        column_name = str(column["column_name"]).upper()
        data_type = str(column["data_type"]).upper()
        nullable = str(column.get("nullable", "Y")).upper()
        not_null = " NOT NULL" if nullable == "N" else ""
        definitions.append(f"  {sql_identifier(column_name)} {data_type}{not_null}")
        if column.get("primary_key") is True:
            pk_columns.append(column_name)
    if pk_columns:
        pk_name = constraint_name("PK", table_name)
        pk_list = ", ".join(sql_identifier(column) for column in pk_columns)
        definitions.append(f"  CONSTRAINT {sql_identifier(pk_name)} PRIMARY KEY ({pk_list})")
    for foreign_key in table.get("foreign_keys", []):
        fk_name = str(foreign_key["name"]).upper()
        columns = ", ".join(sql_identifier(str(column).upper()) for column in foreign_key["columns"])
        target = foreign_key["references"]
        target_table = sql_identifier(str(target["table"]).upper())
        target_columns = ", ".join(sql_identifier(str(column).upper()) for column in target["columns"])
        definitions.append(
            f"  CONSTRAINT {sql_identifier(fk_name)} FOREIGN KEY ({columns}) "
            f"REFERENCES {sql_identifier(schema)}.{target_table} ({target_columns})"
        )
    body = ",\n".join(definitions)
    return f"CREATE TABLE {sql_identifier(schema)}.{sql_identifier(table_name)} (\n{body}\n);"


def render_comments(schema: str, table: dict[str, Any]) -> list[str]:
    table_name = str(table["table_name"]).upper()
    statements = [
        f"COMMENT ON TABLE {sql_identifier(schema)}.{sql_identifier(table_name)} "
        f"IS {sql_string(str(table.get('table_comment') or table_name))};"
    ]
    for column in sorted(table["columns"], key=lambda item: int(item.get("ordinal_position", 0))):
        column_name = str(column["column_name"]).upper()
        comment = str(column.get("comment") or column.get("ui_display") or column_name)
        statements.append(
            f"COMMENT ON COLUMN {sql_identifier(schema)}.{sql_identifier(table_name)}.{sql_identifier(column_name)} "
            f"IS {sql_string(comment)};"
        )
    return statements


def render_demo_schema_ddl(entry: DemoSchemaEntry, *, app_schema: str, demo_password: str) -> str:
    metadata = table_metadata(entry)
    table_names = [str(table["table_name"]).upper() for _, table in metadata]
    lines: list[str] = [
        f"-- Demo schema {entry.schema} is created from data/{entry.folder}/manifest.json and data/*.csv.",
        f"-- CSV rows are loaded by the Select AI Apex loader, not by static INSERT statements.",
        "DECLARE",
        "  l_count NUMBER;",
        "BEGIN",
        f"  SELECT COUNT(*) INTO l_count FROM dba_users WHERE username = {sql_string(entry.schema)};",
        "  IF l_count = 0 THEN",
        f"    EXECUTE IMMEDIATE 'CREATE USER {entry.schema} IDENTIFIED BY \"{demo_password}\" ACCOUNT UNLOCK';",
        "  ELSE",
        f"    EXECUTE IMMEDIATE 'ALTER USER {entry.schema} IDENTIFIED BY \"{demo_password}\" ACCOUNT UNLOCK';",
        "  END IF;",
        "END;",
        "/",
        "",
        f"GRANT CREATE SESSION TO {sql_identifier(entry.schema)};",
        f"GRANT CREATE TABLE TO {sql_identifier(entry.schema)};",
        f"GRANT CREATE VIEW TO {sql_identifier(entry.schema)};",
        f"GRANT CREATE SYNONYM TO {sql_identifier(entry.schema)};",
        f"GRANT UNLIMITED TABLESPACE TO {sql_identifier(entry.schema)};",
        "",
        "BEGIN",
        f"  FOR t IN (SELECT table_name FROM all_tables WHERE owner = {sql_string(entry.schema)}) LOOP",
        "    EXECUTE IMMEDIATE 'DROP TABLE " + sql_identifier(entry.schema) + ".\"' || REPLACE(t.table_name, '\"', '\"\"') || '\" CASCADE CONSTRAINTS PURGE';",
        "  END LOOP;",
        "END;",
        "/",
        "",
    ]
    for _, table in metadata:
        lines.append(render_create_table(entry.schema, table))
        lines.extend(render_comments(entry.schema, table))
        lines.append("")
    grants_list = ", ".join(sql_string(table_name) for table_name in table_names)
    lines.extend(
        [
            "BEGIN",
            f"  FOR t IN (SELECT column_value AS table_name FROM sys.odcivarchar2list({grants_list})) LOOP",
            f"    EXECUTE IMMEDIATE 'GRANT SELECT ON {sql_identifier(entry.schema)}.\"' || REPLACE(t.table_name, '\"', '\"\"') || '\" TO {sql_identifier(app_schema)}';",
            "  END LOOP;",
            "END;",
            "/",
        ]
    )
    return "\n".join(lines)


def parse_csv_value(raw_value: str, data_type: str) -> object:
    value = raw_value.strip()
    if value == "":
        return None
    normalized_type = data_type.upper()
    if normalized_type.startswith(("NUMBER", "FLOAT", "BINARY_FLOAT", "BINARY_DOUBLE")):
        return Decimal(value)
    if normalized_type.startswith("DATE"):
        if len(value) == 10:
            return date.fromisoformat(value)
        return datetime.fromisoformat(value.replace(" ", "T"))
    if normalized_type.startswith("TIMESTAMP"):
        if len(value) == 10:
            value = value + " 00:00:00"
        return datetime.fromisoformat(value.replace(" ", "T"))
    return value


def _insert_sql(schema: str, table: dict[str, Any], columns: list[str]) -> str:
    table_name = str(table["table_name"]).upper()
    column_list = ", ".join(sql_identifier(column) for column in columns)
    bind_list = ", ".join(f":{index + 1}" for index, _ in enumerate(columns))
    return f"INSERT INTO {sql_identifier(schema)}.{sql_identifier(table_name)} ({column_list}) VALUES ({bind_list})"


def load_demo_schema_rows(connection: Any, entry: DemoSchemaEntry, *, batch_size: int = 1000) -> list[DemoLoadTableResult]:
    results: list[DemoLoadTableResult] = []
    cursor = connection.cursor()
    try:
        for metadata_path, table in table_metadata(entry):
            columns = [
                str(column["column_name"]).upper()
                for column in sorted(table["columns"], key=lambda item: int(item.get("ordinal_position", 0)))
            ]
            types = {str(column["column_name"]).upper(): str(column["data_type"]) for column in table["columns"]}
            sql = _insert_sql(entry.schema, table, columns)
            total_rows = 0
            batch: list[list[object]] = []
            with metadata_path.with_suffix(".csv").open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                header = [str(column).upper() for column in (reader.fieldnames or [])]
                if header != columns:
                    raise ValidationError(f"{metadata_path.with_suffix('.csv')}: CSV header does not match metadata columns")
                for row in reader:
                    batch.append([parse_csv_value(row[column], types[column]) for column in columns])
                    if len(batch) >= batch_size:
                        cursor.executemany(sql, batch)
                        total_rows += len(batch)
                        batch = []
                if batch:
                    cursor.executemany(sql, batch)
                    total_rows += len(batch)
            results.append(DemoLoadTableResult(table=str(table["table_name"]).upper(), rows=total_rows))
        connection.commit()
    finally:
        cursor.close()
    return results


def validate_demo_catalog() -> list[str]:
    messages: list[str] = []
    for entry in {item.schema: item for item in demo_entries().values()}.values():
        row_total = 0
        for metadata_path, _table in table_metadata(entry):
            with metadata_path.with_suffix(".csv").open("r", encoding="utf-8-sig", newline="") as handle:
                row_total += max(sum(1 for _ in handle) - 1, 0)
        messages.append(f"{entry.schema}: {len(entry.tables)} tables, {row_total} rows")
    return messages
