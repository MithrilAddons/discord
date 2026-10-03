import json
from pathlib import Path

from mithril_discord.messages import release_message, status_message


def test_backend_foundation_fixture_has_expected_shapes_and_renders():
    value = json.loads(
        (Path(__file__).parents[1] / "contracts" / "discord-foundation-v1.json").read_text()
    )
    summary = value["summary"]
    assert set(summary) == {
        "version",
        "status",
        "checked_at",
        "floors",
        "hypixel",
        "latest_version",
    }
    assert summary["version"] == 1
    assert "M7" in status_message(summary, "synthetic-time")
    catalog = value["releases"]
    assert set(catalog) == {"version", "status", "updated_at", "releases"}
    assert catalog["version"] == 1
    embed, view = release_message(catalog["releases"][0], 1)
    assert "b" * 64 in embed.fields[0].value
    assert len(view.children) == 2
