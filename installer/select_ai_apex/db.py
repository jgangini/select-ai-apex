from __future__ import annotations

from pathlib import Path


def split_sql_script(text: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    in_plsql = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        lowered = stripped.lower()
        if not stripped:
            if buffer:
                buffer.append(line)
            continue
        if lowered.startswith(("prompt ", "set ", "whenever ")):
            continue
        if stripped == "/":
            statement = "\n".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
            in_plsql = False
            continue
        if not buffer and lowered.startswith(("begin", "declare", "create or replace")):
            in_plsql = True
        buffer.append(line)
        if not in_plsql and stripped.endswith(";"):
            statement = "\n".join(buffer).strip()
            statements.append(statement[:-1].strip())
            buffer = []

    tail = "\n".join(buffer).strip()
    if tail:
        statements.append(tail[:-1].strip() if tail.endswith(";") else tail)
    return [statement for statement in statements if statement]


def execute_sql_text(connection, text: str) -> int:
    count = 0
    cursor = connection.cursor()
    try:
        for statement in split_sql_script(text):
            cursor.execute(statement)
            count += 1
        connection.commit()
    finally:
        cursor.close()
    return count


def connect_with_wallet(
    *,
    user: str,
    password: str,
    dsn: str,
    wallet_dir: Path,
    wallet_password: str,
):
    import oracledb

    return oracledb.connect(
        user=user,
        password=password,
        dsn=dsn,
        config_dir=str(wallet_dir),
        wallet_location=str(wallet_dir),
        wallet_password=wallet_password,
    )
