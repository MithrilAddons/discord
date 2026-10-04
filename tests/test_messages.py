import pytest

from mithril_discord.messages import (
    ACCENT_COLOR,
    release_message,
    release_metrics,
    server_information,
    status_message,
    support_reply,
)


def test_server_information_fits_discord_limits_and_links_configured_channels():
    channels = {"how-to": 10, "releases": 11, "status": 12, "support": 13}
    cards = server_information(channels)
    for embeds in cards.values():
        assert len(embeds) <= 10
        assert sum(len(embed) for embed in embeds) <= 6000
        for embed in embeds:
            assert embed.colour.value == ACCENT_COLOR
            assert embed.author.name == "MithrilPF"
            assert embed.footer.text.startswith("MithrilPF")
            assert len(embed.title) <= 256
            assert len(embed.description) <= 4096
            assert len(embed.fields) <= 25
            assert all(len(f.name) <= 256 and len(f.value) <= 1024 for f in embed.fields)
    welcome_text = "\n".join(f.value for f in cards["welcome"][0].fields)
    assert all(f"<#{channel}>" in welcome_text for channel in channels.values())
    assert "not enabled yet" in welcome_text


def release():
    return {
        "version": "1.2.3",
        "sha256": "a" * 64,
        "prerelease": False,
        "url": "https://github.com/MithrilAddons/mithrilpf/releases/download/v1.2.3/mithrilpf-1.2.3.jar",
        "page": "https://github.com/MithrilAddons/mithrilpf/releases/tag/v1.2.3",
        "notes": "@everyone ``` [bad](https://evil.invalid)",
    }


@pytest.mark.parametrize(
    "key,bad",
    [
        ("version", "../x"),
        ("sha256", "bad"),
        ("page", "https://evil.invalid"),
        ("url", "https://evil.invalid/mod.jar"),
    ],
)
def test_releases_reject_untrusted_fields(key, bad):
    value = release()
    value[key] = bad
    with pytest.raises(ValueError):
        release_message(value, 10)


def test_release_templates_escape_mentions_and_only_use_official_buttons():
    embed, view = release_message(release(), 10)
    assert embed.colour.value == ACCENT_COLOR
    assert "@everyone" not in embed.description
    assert embed.description == "@\u200beveryone ``` [bad](https://evil.invalid)"
    assert len(view.children) == 2
    assert "No detached" in embed.fields[1].value
    assert "a" * 64 in embed.fields[0].value


def test_release_notes_preserve_markdown_and_code_without_an_outer_code_block():
    value = release()
    value["notes"] = (
        "## Updating\n\nUse **Check now** in `/mpf`.\n"
        "- Keep your settings.\n\n"
        "[Fix PR](https://github.com/MithrilAddons/mithrilpf/pull/21)\n\n"
        "```text\nExample command\n```"
    )
    embed, _ = release_message(value, 10)
    assert embed.description == value["notes"]
    assert embed.fields[0].value == f"```\n{'a' * 64}\n```"


def test_release_notes_keep_length_limit_and_empty_fallback():
    value = release()
    value["notes"] = "x" * 3000
    assert len(release_message(value, 10)[0].description) == 2600
    value["notes"] = ""
    assert release_message(value, 10)[0].description == "See the release notes on GitHub."


def test_status_only_aggregate_data_and_outages():
    value = {
        "floors": {f: {"open_parties": 1, "looking": 2} for f in ("F7", "M7")},
        "hypixel": "unknown",
        "latest_version": None,
    }
    assert "1 open parties" in status_message(value, "2026-01-01")
    assert "unreachable" in status_message(None, None)
    value["hypixel"] = "arbitrary text"
    with pytest.raises(ValueError):
        status_message(value, None)
    value["hypixel"] = "ok"
    value["floors"]["M7"]["looking"] = -1
    with pytest.raises(ValueError):
        status_message(value, None)


def test_support_hints_use_fixed_text_and_releases_reject_wrong_channel_marker():
    reply = support_reply("LINK and INVITE @everyone", 10)
    assert "confirm the correct account" in reply
    assert "conflicting game party" in reply
    assert "@everyone" not in reply
    value = release()
    value["prerelease"] = True
    with pytest.raises(ValueError, match="prerelease"):
        release_message(value, 10)


def checks():
    return {
        "tests": 283,
        "line_coverage": 82.5,
        "branch_coverage": 78.4,
        "run_url": "https://github.com/MithrilAddons/mithrilpf/actions/runs/123",
    }


def test_native_release_embeds_fit_discord_limits_together():
    value = {**release(), "checks": checks(), "notes": "x" * 2600}
    primary, _ = release_message(value, 123456789012345678)
    embeds = [primary, *release_metrics(value)]
    assert len(embeds) == 2
    assert sum(len(e) for e in embeds) <= 6000
    for embed in embeds:
        assert len(embed.title) <= 256
        assert len(embed.description) <= 4096
        assert len(embed.fields) <= 25
        assert len(embed.footer.text) <= 2048
        assert all(len(f.name) <= 256 and len(f.value) <= 1024 for f in embed.fields)
        assert embed.to_dict()["type"] == "rich"
    assert embeds[1].fields[0].value == "283 passed"
    assert embeds[1].fields[1].value == "82.5%"
    assert release_metrics(release()) == []


@pytest.mark.parametrize(
    "key,value",
    [
        ("tests", True),
        ("tests", 0),
        ("run_url", "https://evil.invalid"),
        ("line_coverage", float("nan")),
        ("branch_coverage", 101),
        ("line_coverage", "80"),
    ],
)
def test_metrics_reject_invalid_numbers_and_external_links(key, value):
    metrics = checks()
    metrics[key] = value
    with pytest.raises(ValueError):
        release_metrics({**release(), "checks": metrics})
