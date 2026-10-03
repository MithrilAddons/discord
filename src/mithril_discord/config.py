"""Explicit local configuration; tokens are read separately and never represented."""

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    guild_id: int
    token_file: Path
    secret_file: Path
    state_file: Path
    staff_role: int
    beta_role: int
    linked_role: int
    channels: dict[str, int]

    @classmethod
    def load(cls, path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        ids = [
            data["guild_id"],
            data["staff_role"],
            data["beta_role"],
            data["linked_role"],
            *data["channels"].values(),
        ]
        if not all(type(value) is int and 0 < value < 2**64 for value in ids):
            raise ValueError("Discord IDs must be positive integers")
        required = {"releases", "status", "audit-log", "how-to", "support", "beta"}
        if not required <= data["channels"].keys():
            raise ValueError("Missing foundation channels")
        secrets = Path(os.environ.get("CREDENTIALS_DIRECTORY", path.parent))
        return cls(
            data["guild_id"],
            secrets / data["token_file"],
            secrets / data["secret_file"],
            path.parent / data["state_file"],
            data["staff_role"],
            data["beta_role"],
            data["linked_role"],
            data["channels"],
        )


def read_secret(path: Path) -> str:
    value = path.read_text(encoding="utf-8-sig").strip()
    if not value or any(char.isspace() for char in value):
        raise ValueError("Secret file must contain one non-empty token")
    return value
