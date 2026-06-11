from __future__ import annotations

import re
import zipfile
from pathlib import Path

from .validators import ValidationError

TNS_ALIAS_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_.-]*)\s*=")


def list_wallet_dsn_aliases(wallet_zip: Path) -> list[str]:
    if not wallet_zip.exists():
        raise ValidationError(f"wallet zip does not exist: {wallet_zip}")
    try:
        with zipfile.ZipFile(wallet_zip, "r") as archive:
            names = set(archive.namelist())
            if "tnsnames.ora" not in names:
                raise ValidationError("wallet zip must contain tnsnames.ora")
            text = archive.read("tnsnames.ora").decode("utf-8", errors="replace")
    except zipfile.BadZipFile as exc:
        raise ValidationError("wallet must be a valid zip file") from exc

    aliases: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("("):
            continue
        match = TNS_ALIAS_RE.match(line)
        if match:
            aliases.append(match.group(1))
    return sorted(dict.fromkeys(aliases))


def extract_wallet(wallet_zip: Path, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wallet_zip, "r") as archive:
        archive.extractall(target_dir)
    return target_dir
