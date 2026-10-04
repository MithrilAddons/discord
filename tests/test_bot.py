import asyncio
import datetime as dt
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from mithril_discord.bot import CommunityBot
from mithril_discord.config import Config
from mithril_discord.messages import WARNING


@pytest.fixture
def bot(tmp_path):
    secret = tmp_path / "secret"
    secret.write_text("a" * 64)
    channels = {
        name: i + 10
        for i, name in enumerate(("status", "releases", "beta", "audit-log", "support", "how-to"))
    }
    instance = CommunityBot(
        Config(1, tmp_path / "token", secret, tmp_path / "state.db", 2, 3, 4, channels)
    )
    instance._connection.user = SimpleNamespace(id=5)
    return instance


def run(coroutine):
    return asyncio.run(coroutine)


async def history(messages=()):
    for message in messages:
        yield message


def channel():
    value = SimpleNamespace(
        id=10,
        guild=SimpleNamespace(id=1),
        send=AsyncMock(return_value=SimpleNamespace(id=500)),
        fetch_message=AsyncMock(),
        history=lambda **kw: history(),
    )
    return value


def message(*, roles=(), text="", filename=None):
    now = dt.datetime.now(dt.UTC)
    return SimpleNamespace(
        id=100,
        guild=SimpleNamespace(id=1, owner_id=9),
        author=SimpleNamespace(
            id=8,
            roles=roles,
            created_at=now - dt.timedelta(days=30),
            joined_at=now - dt.timedelta(days=2),
            send=AsyncMock(),
        ),
        channel=channel(),
        content=text,
        attachments=[SimpleNamespace(filename=filename)] if filename else [],
        delete=AsyncMock(),
    )


def test_filter_deletes_logs_no_content_and_private_notice(bot):
    audit = channel()
    bot.channel = AsyncMock(return_value=audit)
    msg = message(text="SECRET-CONTENT", filename="private.jar")
    run(bot.on_message(msg))
    msg.delete.assert_awaited_once()
    msg.author.send.assert_awaited_once()
    log = audit.send.call_args.kwargs["embed"].description
    assert "SECRET-CONTENT" not in log
    assert "private.jar" not in log
    assert "executable_attachment" in log


def test_staff_own_messages_and_other_guilds_are_ignored(bot):
    for msg in (
        message(roles=[SimpleNamespace(id=2)], filename="test.jar"),
        message(filename="test.jar"),
    ):
        if not msg.author.roles:
            msg.guild.id = 99
        run(bot.on_message(msg))
        msg.delete.assert_not_awaited()
    msg = message(filename="test.jar")
    msg.author.id = bot.user.id
    run(bot.on_message(msg))
    msg.delete.assert_not_awaited()
    msg.guild = None
    run(bot.on_message(msg))


def test_warnings_are_fixed_and_rate_limited(bot):
    msg = message(text="send token")
    run(bot.on_message(msg))
    run(bot.on_message(msg))
    msg.channel.send.assert_awaited_once()
    assert msg.channel.send.call_args.kwargs["embed"].description == WARNING
    bot.last_warning = {i: float("inf") for i in range(500)}
    assert not bot.warning_allowed(999)


def test_linked_member_exempt_from_new_account_gate(bot):
    msg = message(roles=[SimpleNamespace(id=4)], text="https://example.invalid")
    msg.author.created_at = msg.author.joined_at = dt.datetime.now(dt.UTC)
    run(bot.on_message(msg))
    msg.delete.assert_not_awaited()
    msg.author.roles = []
    bot.channel = AsyncMock(return_value=channel())
    run(bot.on_message(msg))
    msg.delete.assert_awaited_once()


def test_edited_messages_rechecked_and_support_forum_reply(bot):
    msg = message()
    target = channel()
    target.fetch_message = AsyncMock(return_value=msg)
    bot.get_channel = Mock(return_value=target)
    bot.on_message = AsyncMock()
    run(bot.on_raw_message_edit(SimpleNamespace(guild_id=1, channel_id=10, message_id=100)))
    bot.on_message.assert_awaited_once_with(msg)
    run(bot.on_raw_message_edit(SimpleNamespace(guild_id=2)))
    thread = SimpleNamespace(
        guild=SimpleNamespace(id=1), parent_id=bot.config.channels["support"], send=AsyncMock()
    )
    run(bot.on_thread_create(thread))
    assert "/mithrilpfstatus" in thread.send.call_args.kwargs["embed"].description
    thread.parent_id = 999
    run(bot.on_thread_create(thread))
    thread.send.assert_awaited_once()


def test_saved_posts_edit_after_restart_and_recover_send_save_gap(bot):
    target = channel()
    embed = discord.Embed(title="Status")
    embed.set_footer(text="MithrilPF: status")
    run(bot.saved_message("status", target, embed=embed))
    assert bot.state.get("status") == 500
    prior = SimpleNamespace(id=500, edit=AsyncMock())
    target.fetch_message.return_value = prior
    run(bot.saved_message("status", target, embed=embed))
    prior.edit.assert_awaited_once()
    target.send.assert_awaited_once()
    bot.state.remove("status")
    prior.author, prior.embeds = SimpleNamespace(id=5), [embed]
    target.history = lambda **kw: history([prior])
    run(bot.saved_message("status", target, embed=embed))
    assert bot.state.get("status") == 500
    target.send.assert_awaited_once()


def test_only_one_incident_then_recovery_update(bot, monkeypatch):
    summary = {
        "version": 1,
        "floors": {f: {"open_parties": 0, "looking": 0} for f in ("F7", "M7")},
        "hypixel": "unknown",
        "latest_version": None,
    }
    fetch = Mock(side_effect=[OSError(), OSError(), OSError(), OSError(), summary])
    monkeypatch.setattr("mithril_discord.bot.backend.fetch", fetch)
    bot.channel = AsyncMock(return_value=channel())
    bot.saved_message = AsyncMock()
    for _ in range(5):
        run(bot.tick())
    incidents = [call for call in bot.saved_message.call_args_list if call.args[0] == "incident"]
    assert len(incidents) == 3
    assert "restored" in incidents[-1].kwargs["embed"].description
    assert bot.failures == 0


def test_releases_once_per_channel_and_opted_beta_role_only(bot, monkeypatch):
    from test_messages import release

    value = release()
    value["prerelease"] = True
    value["version"] = "1.2.3-rc.1"
    value["page"] = value["page"].replace("1.2.3", "1.2.3-rc.1")
    value["url"] = value["url"].replace("1.2.3", "1.2.3-rc.1")
    monkeypatch.setattr(
        "mithril_discord.bot.backend.fetch",
        lambda *args: {"version": 1, "status": "ready", "releases": [value]},
    )
    target = channel()
    bot.channel = AsyncMock(return_value=target)
    run(bot.releases())
    run(bot.releases())
    assert target.send.await_count == 2
    beta = target.send.call_args_list[1].kwargs
    assert beta["content"] == "<@&3>"
    assert not beta["allowed_mentions"].everyone
    assert len(beta["allowed_mentions"].roles) == 1
    assert len(beta["embeds"]) == 1
    assert bot.command_release == value


def test_cached_commands_are_ephemeral(bot):
    from test_messages import release

    async def check():
        interaction = SimpleNamespace(response=SimpleNamespace(send_message=AsyncMock()))
        commands = {c.name: c for c in bot.tree.get_commands(guild=discord.Object(id=1))}
        await commands["status"].callback(interaction)
        await commands["release"].callback(interaction)
        bot.command_release = release()
        await commands["release"].callback(interaction)
        assert all(c.kwargs["ephemeral"] for c in interaction.response.send_message.call_args_list)
        assert all(
            all(
                isinstance(e, discord.Embed)
                for e in c.kwargs.get("embeds", [c.kwargs.get("embed")])
            )
            for c in interaction.response.send_message.call_args_list
        )

    run(check())


def test_channel_must_belong_to_selected_guild(bot):
    target = channel()
    bot.get_channel = Mock(return_value=None)
    bot.fetch_channel = AsyncMock(return_value=target)
    assert run(bot.channel("status")) is target
    target.guild.id = 999
    request = bot.channel("status")
    with pytest.raises(ValueError):
        run(request)


def test_connection_hooks_and_sanitized_errors(bot, capsys):
    async def check():
        bot.tree.sync = AsyncMock()
        bot.poll = AsyncMock()
        await bot.setup_hook()
        bot.tree.sync.assert_awaited_once()
        await bot.close()
        await bot.on_error("on_message", "sensitive-content")

    run(check())
    assert "sensitive-content" not in capsys.readouterr().out


def test_release_posts_include_separate_metrics_without_extra_messages(bot):
    from test_messages import checks, release

    value = {**release(), "checks": checks()}
    target = channel()
    bot.channel = AsyncMock(return_value=target)
    run(bot.publish_release(value, "releases"))
    run(bot.publish_release(value, "releases"))
    target.send.assert_awaited_once()
    embeds = target.send.call_args.kwargs["embeds"]
    assert len(embeds) == 2
    assert embeds[1].title == "Automated checks"
    assert embeds[0].footer.text == "MithrilPF: release:releases:1.2.3"
