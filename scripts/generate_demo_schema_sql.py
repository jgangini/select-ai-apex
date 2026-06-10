from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = REPO_ROOT / "data" / "demo"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
NUMBER_RE = re.compile(r"^[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?$")
IDENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]*$")


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_identifier(value: str) -> str:
    value = value.strip().upper()
    if not IDENT_RE.match(value):
        raise ValueError(f"Unsupported Oracle identifier: {value!r}")
    return '"' + value.replace('"', '""') + '"'


def constraint_name(prefix: str, table_name: str, suffix: str = "") -> str:
    raw = f"{prefix}_{table_name}{suffix}".upper()
    if len(raw) <= 128:
        return raw
    return raw[:120]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def table_metadata(demo: dict[str, Any]) -> list[tuple[Path, dict[str, Any]]]:
    folder = str(demo["folder"])
    schema = str(demo["schema"]).upper()
    demo_dir = DEMO_ROOT / folder
    metadata_path = demo_dir / str(demo.get("metadata_path") or "data")
    table_names = [str(table).upper() for table in demo.get("tables", [])]
    if not table_names:
        table_names = sorted(path.stem.upper() for path in metadata_path.glob("*.json"))
    metadata: list[tuple[Path, dict[str, Any]]] = []
    for table_name in table_names:
        path = metadata_path / f"{table_name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Missing metadata file: {path}")
        item = load_json(path)
        owner_name = str(item.get("owner_name", "")).upper()
        declared_table = str(item.get("table_name", "")).upper()
        if owner_name != schema:
            raise ValueError(f"{path}: owner_name {owner_name!r} must be {schema!r}")
        if declared_table != table_name:
            raise ValueError(f"{path}: table_name {declared_table!r} must be {table_name!r}")
        metadata.append((path, item))
    return metadata


def render_value(raw_value: str, data_type: str) -> str:
    value = raw_value.strip()
    if value == "":
        return "NULL"
    normalized_type = data_type.upper()
    if normalized_type.startswith(("NUMBER", "FLOAT", "BINARY_FLOAT", "BINARY_DOUBLE")):
        if not NUMBER_RE.match(value):
            raise ValueError(f"Invalid numeric value {value!r} for {data_type}")
        return value
    if normalized_type.startswith("DATE"):
        if DATE_RE.match(value):
            return f"DATE {sql_string(value)}"
        if DATETIME_RE.match(value):
            return f"TO_DATE({sql_string(value)}, 'YYYY-MM-DD HH24:MI:SS')"
        raise ValueError(f"Invalid date value {value!r} for {data_type}")
    if normalized_type.startswith("TIMESTAMP"):
        if DATE_RE.match(value):
            return f"TO_TIMESTAMP({sql_string(value + ' 00:00:00')}, 'YYYY-MM-DD HH24:MI:SS')"
        if DATETIME_RE.match(value):
            return f"TO_TIMESTAMP({sql_string(value)}, 'YYYY-MM-DD HH24:MI:SS')"
        raise ValueError(f"Invalid timestamp value {value!r} for {data_type}")
    return sql_string(value)


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
            f"  CONSTRAINT {sql_identifier(fk_name)} FOREIGN KEY ({columns}) REFERENCES {sql_identifier(schema)}.{target_table} ({target_columns})"
        )
    body = ",\n".join(definitions)
    return f"CREATE TABLE {sql_identifier(schema)}.{sql_identifier(table_name)} (\n{body}\n);"


def render_comments(schema: str, table: dict[str, Any]) -> list[str]:
    table_name = str(table["table_name"]).upper()
    statements = [
        f"COMMENT ON TABLE {sql_identifier(schema)}.{sql_identifier(table_name)} IS {sql_string(str(table.get('table_comment') or table_name))};"
    ]
    for column in sorted(table["columns"], key=lambda item: int(item.get("ordinal_position", 0))):
        column_name = str(column["column_name"]).upper()
        comment = str(column.get("comment") or column.get("ui_display") or column_name)
        statements.append(
            f"COMMENT ON COLUMN {sql_identifier(schema)}.{sql_identifier(table_name)}.{sql_identifier(column_name)} IS {sql_string(comment)};"
        )
    return statements


def render_inserts(schema: str, metadata_path: Path, table: dict[str, Any]) -> list[str]:
    table_name = str(table["table_name"]).upper()
    csv_path = metadata_path.with_suffix(".csv")
    if not csv_path.exists():
        return []
    columns = [str(column["column_name"]).upper() for column in sorted(table["columns"], key=lambda item: int(item.get("ordinal_position", 0)))]
    types = {str(column["column_name"]).upper(): str(column["data_type"]) for column in table["columns"]}
    sql_columns = ", ".join(sql_identifier(column) for column in columns)
    statements: list[str] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = [str(column).upper() for column in (reader.fieldnames or [])]
        if header != columns:
            raise ValueError(f"{csv_path}: CSV header does not match metadata columns")
        for row in reader:
            values = ", ".join(render_value(row[column], types[column]) for column in columns)
            statements.append(f"INSERT INTO {sql_identifier(schema)}.{sql_identifier(table_name)} ({sql_columns}) VALUES ({values});")
    return statements


def render_install_sql(demo: dict[str, Any]) -> str:
    schema = str(demo["schema"]).upper()
    metadata = table_metadata(demo)
    table_names = [str(table["table_name"]).upper() for _, table in metadata]
    lines: list[str] = [
        "SET DEFINE OFF",
        "SET SERVEROUTPUT ON",
        "WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK",
        "",
        f"PROMPT === ADMIN: install bundled {schema} schema for Select AI Apex ===",
        "",
        "DECLARE",
        "  l_count NUMBER;",
        "BEGIN",
        f"  SELECT COUNT(*) INTO l_count FROM dba_users WHERE username = {sql_string(schema)};",
        "  IF l_count = 0 THEN",
        f"    EXECUTE IMMEDIATE 'CREATE USER {schema} IDENTIFIED BY \"__DEMO_SCHEMA_PASSWORD__\" ACCOUNT UNLOCK';",
        "  ELSE",
        f"    EXECUTE IMMEDIATE 'ALTER USER {schema} IDENTIFIED BY \"__DEMO_SCHEMA_PASSWORD__\" ACCOUNT UNLOCK';",
        "  END IF;",
        "END;",
        "/",
        "",
        f"GRANT CREATE SESSION TO {sql_identifier(schema)};",
        f"GRANT CREATE TABLE TO {sql_identifier(schema)};",
        f"GRANT CREATE VIEW TO {sql_identifier(schema)};",
        f"GRANT CREATE SYNONYM TO {sql_identifier(schema)};",
        f"GRANT UNLIMITED TABLESPACE TO {sql_identifier(schema)};",
        "",
        "BEGIN",
        f"  FOR t IN (SELECT table_name FROM all_tables WHERE owner = {sql_string(schema)}) LOOP",
        "    BEGIN",
        f"      EXECUTE IMMEDIATE 'DROP TABLE {sql_identifier(schema)}.\"' || REPLACE(t.table_name, '\"', '\"\"') || '\" CASCADE CONSTRAINTS PURGE';",
        "    EXCEPTION",
        "      WHEN OTHERS THEN",
        "        IF SQLCODE != -942 THEN",
        "          RAISE;",
        "        END IF;",
        "    END;",
        "  END LOOP;",
        "END;",
        "/",
        "",
    ]
    for path, table in metadata:
        lines.append(render_create_table(schema, table))
        lines.extend(render_comments(schema, table))
        inserts = render_inserts(schema, path, table)
        if inserts:
            lines.append("")
            lines.append(f"PROMPT Loading {schema}.{table['table_name']} from {path.with_suffix('.csv').name}")
            lines.extend(inserts)
        lines.append("")
    grants_list = ", ".join(sql_string(table_name) for table_name in table_names)
    lines.extend([
        "BEGIN",
        f"  FOR t IN (SELECT column_value AS table_name FROM sys.odcivarchar2list({grants_list})) LOOP",
        f"    EXECUTE IMMEDIATE 'GRANT SELECT ON {sql_identifier(schema)}.\"' || REPLACE(t.table_name, '\"', '\"\"') || '\" TO __APP_SCHEMA__';",
        "  END LOOP;",
        "END;",
        "/",
        "",
        "COMMIT;",
        "",
    ])
    return "\n".join(lines)


def load_catalog() -> dict[str, Any]:
    return load_json(DEMO_ROOT / "manifest.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate demo install.sql files from data/demo metadata and CSV files.")
    parser.add_argument("--write", action="store_true", help="Write install.sql files in each demo folder.")
    args = parser.parse_args()
    catalog = load_catalog()
    for demo in catalog.get("demos", []):
        sql = render_install_sql(demo)
        target = DEMO_ROOT / str(demo["folder"]) / str(demo.get("install") or "install.sql")
        if args.write:
            target.write_text(sql, encoding="utf-8", newline="\n")
            print(f"wrote {target.relative_to(REPO_ROOT).as_posix()} ({len(sql.splitlines())} lines)")
        else:
            print(f"would write {target.relative_to(REPO_ROOT).as_posix()} ({len(sql.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
