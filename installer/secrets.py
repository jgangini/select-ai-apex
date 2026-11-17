from __future__ import annotations

from random import SystemRandom
import string


SYSTEM_RANDOM = SystemRandom()


def generate_oracle_password(length: int = 18) -> str:
    alphabet = string.ascii_letters + string.digits + "_#"
    while True:
        password = "".join(SYSTEM_RANDOM.choice(alphabet) for _ in range(length))
        if (
            any(ch.islower() for ch in password)
            and any(ch.isupper() for ch in password)
            and any(ch.isdigit() for ch in password)
            and "admin" not in password.lower()
        ):
            return password
