import copy
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from test_bot import bot as bot
from test_bot import channel, run

from mithril_discord.leaderboards import cards, duration


def fixture():
    return json.loads(
        (Path(__file__).parents[1] / "contracts/discord-leaderboards-v1.json").read_text()
    )


def test_cards_use_ranked_clock_and_compact_tied_player_lines():
    embeds = cards(fixture())
    assert len(embeds) == 3
    assert embeds[0].description == "**1. 1:30.000** — SyntheticOne"
    terminal = embeds[2].description
    assert terminal.count("**1.") == 1
    assert terminal == "**1. 1:40.000** — SyntheticOne, SyntheticTwo"
    assert all("tick time" not in e.description for e in embeds)
    assert all("real" not in e.description for e in embeds)
    assert duration(60005) == "1:00.005"


def test_each_separate_pb_occupies_one_line():
    data = fixture()
    first = data["boards"]["f7_solo"][0]
    data["boards"]["f7_solo"].append(
        dict(first, rank=2, uuid="2" * 32, name="SyntheticTwo", ticks=1820)
    )
    assert cards(data)[0].description.splitlines() == [
        "**1. 1:30.000** — SyntheticOne",
        "**2. 1:31.000** — SyntheticTwo",
    ]


def test_empty_unknown_name_and_large_tie_group_fit_discord_limits():
    data = fixture()
    data["boards"]["f7_solo"] = []
    first = data["boards"]["m7_terminals"][0]
    data["boards"]["m7_terminals"] = [dict(first, uuid=f"{n:032x}", name=None) for n in range(400)]
    embeds = cards(data)
    assert "No eligible times" in embeds[0].description
    assert len(embeds) > 3
    assert all(len(embed.description) <= 4096 and len(embed) <= 6000 for embed in embeds)
    assert all(e.description.startswith("**1. 1:40.000** — ") for e in embeds[2:])
    combined = "\n".join(e.description for e in embeds)
    for n in range(400):
        assert f"{n:032x}" in combined


@pytest.mark.parametrize(
    "field,value",
    [
        ("uuid", "bad"),
        ("name", "@everyone"),
        ("name", "Synthetíc"),
        ("name", 42),
        ("ticks", True),
        ("ticks", 0),
        ("rank", 11),
        ("real_ms", -1),
    ],
)
def test_bad_records_rejected(field, value):
    data = fixture()
    data["boards"]["f7_solo"][0][field] = value
    with pytest.raises(ValueError):
        cards(data)


def test_bad_contract_duplicate_and_capacity_rejected():
    data = fixture()
    for change in (dict(version=2), dict(boards={})):
        with pytest.raises(ValueError):
            cards({**data, **change})
    for rows in (None, data["boards"]["f7_solo"] * 2, data["boards"]["f7_solo"] * 1001):
        changed = copy.deepcopy(data)
        changed["boards"]["f7_solo"] = rows
        with pytest.raises(ValueError):
            cards(changed)


def test_refresh_edits_saved_posts_and_clears_stale_pages_on_outage(bot, monkeypatch):
    data = fixture()
    bot.config.channels["leaderboards"] = 10
    target = channel()
    bot.channel = AsyncMock(return_value=target)
    bot.saved_message = AsyncMock()
    monkeypatch.setattr("mithril_discord.bot.backend.fetch", lambda *args: data)
    bot.state.put("leaderboards:10:3", 503)
    bot.state.put("status", 600)
    run(bot.leaderboards())
    assert bot.saved_message.await_count == 3
    target.fetch_message.return_value.delete.assert_awaited_once()
    assert bot.state.get("leaderboards:10:3") is None
    assert bot.state.get("status") == 600
    for index in range(3):
        bot.state.put(f"leaderboards:10:{index}", 500 + index)

    def fail(*args):
        raise OSError("private error content")

    monkeypatch.setattr("mithril_discord.bot.backend.fetch", fail)
    run(bot.leaderboards())
    assert bot.saved_message.call_args.kwargs["embed"].title == "Leaderboards unavailable"
    assert bot.state.keys("leaderboards:") == ["leaderboards:10:0"]
    monkeypatch.setattr("mithril_discord.bot.backend.fetch", lambda *args: data)
    run(bot.leaderboards())
    assert bot.saved_message.call_args.kwargs["embed"].title == "M7 terminals"


def test_unconfigured_leaderboard_makes_no_requests(bot, monkeypatch):
    def fail(*args):
        raise AssertionError("Not configured")

    monkeypatch.setattr("mithril_discord.bot.backend.fetch", fail)
    run(bot.leaderboards())


def test_leaderboard_failure_does_not_stop_status_or_releases(bot, monkeypatch, capsys):
    bot.wait_until_ready = AsyncMock()
    bot.is_closed = Mock(side_effect=[False, True])
    bot.leaderboards = AsyncMock(side_effect=ValueError("private payload"))
    bot.tick = AsyncMock()
    bot.releases = AsyncMock()
    monkeypatch.setattr("mithril_discord.bot.asyncio.sleep", AsyncMock())
    run(bot.poll())
    bot.tick.assert_awaited_once()
    bot.releases.assert_awaited_once()
    assert "private payload" not in capsys.readouterr().out
