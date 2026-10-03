import json

import pytest

from mithril_discord.config import Config, read_secret
from mithril_discord.state import State


def test_state_survives_restart_and_uses_no_message_content(tmp_path):
    path = tmp_path / "new" / "state.sqlite3"
    state = State(path)
    assert state.get("status") is None
    state.put("status", 100)
    assert State(path).get("status") == 100
    state.put("status", 101)
    assert state.get("status") == 101
    state.remove("status")
    assert State(path).get("status") is None


def test_config_paths_and_secret_handling(tmp_path):
    value = {
        "guild_id": 1,
        "staff_role": 2,
        "beta_role": 3,
        "linked_role": 4,
        "token_file": "token.txt",
        "secret_file": "secret.txt",
        "state_file": "state.sqlite3",
        "channels": dict.fromkeys(
            ("releases", "status", "audit-log", "how-to", "support", "beta"), 10
        ),
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(value))
    config = Config.load(path)
    config.token_file.write_text("synthetic-token\n")
    assert read_secret(config.token_file) == "synthetic-token"
    assert "synthetic-token" not in repr(config)
    for bad in ("", "a b", "a\nb"):
        config.token_file.write_text(bad)
        with pytest.raises(ValueError):
            read_secret(config.token_file)
    value["guild_id"] = True
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        Config.load(path)
    value["guild_id"] = 1
    value["channels"].pop("beta")
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        Config.load(path)
