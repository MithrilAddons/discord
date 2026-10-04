"""Phase-one guild bot. Discord failures do not run inside the Finder process."""

import asyncio
import contextlib
import datetime as dt
import http.client
import time

import discord
from discord import app_commands

from . import backend
from .config import read_secret
from .leaderboards import cards
from .messages import (
    WARNING,
    info_embed,
    release_message,
    release_metrics,
    status_message,
    support_reply,
)
from .safety import assess
from .state import State


class CommunityBot(discord.Client):
    def __init__(self, config):
        intents = discord.Intents.none()
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = True
        # Phase 1 does not yet need member or voice-state subscriptions.
        super().__init__(
            intents=intents, max_messages=None, allowed_mentions=discord.AllowedMentions.none()
        )
        self.config = config
        self.secret = read_secret(config.secret_file)
        self.state = State(config.state_file)
        self.tree = app_commands.CommandTree(self)
        self.worker = None
        self.summary = None
        self.last_success = None
        self.failures = 0
        self.command_release = None
        self.last_warning = {}
        guild = discord.Object(id=config.guild_id)

        @self.tree.command(name="status", description="Show MithrilPF service status", guild=guild)
        async def status(interaction: discord.Interaction):
            await interaction.response.send_message(
                embed=info_embed("Service status", status_message(self.summary, self.last_success)),
                ephemeral=True,
            )

        @self.tree.command(
            name="release", description="Show the latest verified release metadata", guild=guild
        )
        async def release(interaction: discord.Interaction):
            if self.command_release is None:
                await interaction.response.send_message(
                    embed=info_embed(
                        "Release information",
                        "Release metadata is unavailable. Please try again later.",
                    ),
                    ephemeral=True,
                )
                return
            embed, view = release_message(self.command_release, config.channels["how-to"])
            await interaction.response.send_message(
                embeds=[embed, *release_metrics(self.command_release)], view=view, ephemeral=True
            )

    async def setup_hook(self):
        await self.tree.sync(guild=discord.Object(id=self.config.guild_id))
        self.worker = asyncio.create_task(self.poll())

    async def close(self):
        if self.worker:
            self.worker.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.worker
        await super().close()

    async def on_error(self, event_method, *args, **kwargs):
        # Never log event payloads, exception messages, tokens, or user content.
        print(f"Discord event failed: {event_method}", flush=True)

    async def channel(self, name):
        channel = self.get_channel(self.config.channels[name]) or await self.fetch_channel(
            self.config.channels[name]
        )
        if channel.guild.id != self.config.guild_id:
            raise ValueError("Configured channel belongs to another guild")
        return channel

    async def saved_message(self, key, channel, *, mentions=None, **kwargs):
        """Edit tracked posts; scan deterministic markers after an interrupted send/save."""
        message_id = await asyncio.to_thread(self.state.get, key)
        if message_id:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(**kwargs, allowed_mentions=discord.AllowedMentions.none())
                return message
            except discord.NotFound:
                await asyncio.to_thread(self.state.remove, key)
        marker = f"MithrilPF: {key}"
        async for message in channel.history(limit=100):
            if message.author.id == self.user.id and any(
                e.footer.text == marker for e in message.embeds
            ):
                await asyncio.to_thread(self.state.put, key, message.id)
                await message.edit(**kwargs, allowed_mentions=discord.AllowedMentions.none())
                return message
        message = await channel.send(
            **kwargs, allowed_mentions=mentions or discord.AllowedMentions.none()
        )
        await asyncio.to_thread(self.state.put, key, message.id)
        return message

    async def tick(self):
        try:
            self.summary = await asyncio.to_thread(backend.fetch, "summary", self.secret)
            checked = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%S")
            status_message(self.summary, checked)  # Validate before publishing.
            self.last_success = checked
            recovered = self.failures >= 3
            self.failures = 0
        except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
            self.summary = None
            recovered = False
            self.failures += 1
        channel = await self.channel("status")
        embed = info_embed(
            title="Service status", description=status_message(self.summary, self.last_success)
        )
        embed.set_footer(text="MithrilPF: status")
        await self.saved_message("status", channel, embed=embed)
        if self.failures >= 3 or recovered:
            text = (
                "Service restored."
                if recovered
                else "The backend has failed three consecutive checks."
            )
            incident = info_embed(title="Service incident", description=text)
            incident.set_footer(text="MithrilPF: incident")
            await self.saved_message("incident", channel, embed=incident)

    async def releases(self):
        payload = await asyncio.to_thread(backend.fetch, "releases", self.secret)
        if payload["status"] != "ready":
            return  # Never announce an old cached release as newly published during an outage.
        releases = payload["releases"]
        if not isinstance(releases, list) or len(releases) > 10:
            raise ValueError("Invalid release catalogue")
        for release in releases:
            release_message(release, self.config.channels["how-to"])
        self.command_release = releases[0] if releases else None
        for release in reversed(releases):
            targets = ("releases", "beta") if release["prerelease"] else ("releases",)
            for target in targets:
                await self.publish_release(release, target)

    async def publish_release(self, release, target):
        embed, view = release_message(release, self.config.channels["how-to"])
        key = f"release:{target}:{release['version']}"
        if await asyncio.to_thread(self.state.get, key):
            return
        embed.set_footer(text=f"MithrilPF: {key}")
        content = f"<@&{self.config.beta_role}>" if target == "beta" else None
        mentions = discord.AllowedMentions(
            roles=[discord.Object(id=self.config.beta_role)],
            everyone=False,
            users=False,
            replied_user=False,
        )
        await self.saved_message(
            key,
            await self.channel(target),
            embeds=[embed, *release_metrics(release)],
            view=view,
            content=content,
            mentions=mentions,
        )

    async def poll(self):
        await self.wait_until_ready()
        turns = 0
        while not self.is_closed():
            try:
                await self.leaderboards()
            except (OSError, ValueError, KeyError, TypeError, discord.HTTPException):
                print("Discord leaderboard publication failed; retrying.", flush=True)
            try:
                await self.tick()
                if turns % 5 == 0:
                    await self.releases()
            except (
                OSError,
                ValueError,
                KeyError,
                TypeError,
                http.client.HTTPException,
                discord.HTTPException,
            ):
                print(
                    "Discord publication cycle failed; retrying without logging payloads.",
                    flush=True,
                )
            turns += 1
            await asyncio.sleep(60)

    async def leaderboards(self):
        if "leaderboards" not in self.config.channels:
            return
        channel = await self.channel("leaderboards")
        try:
            payload = await asyncio.to_thread(backend.fetch, "leaderboards", self.secret)
            embeds = cards(payload)
        except (OSError, ValueError, KeyError, TypeError, OverflowError, http.client.HTTPException):
            # Replace stale rankings: deleted or moderated records must not remain
            # presented as current when the authoritative service is unavailable.
            embeds = [
                info_embed(
                    "Leaderboards unavailable",
                    "Rankings could not be refreshed. Retrying every minute.",
                )
            ]
        prefix = f"leaderboards:{channel.id}:"
        active = set()
        for index, embed in enumerate(embeds):
            key = f"{prefix}{index}"
            active.add(key)
            embed.set_footer(text=f"MithrilPF: {key}")
            await self.saved_message(key, channel, embed=embed)
        for key in await asyncio.to_thread(self.state.keys, prefix):
            if key not in active:
                message_id = await asyncio.to_thread(self.state.get, key)
                with contextlib.suppress(discord.NotFound):
                    await (await channel.fetch_message(message_id)).delete()
                await asyncio.to_thread(self.state.remove, key)

    async def on_message(self, message):
        if (
            message.guild is None
            or message.guild.id != self.config.guild_id
            or message.author.id == self.user.id
        ):
            return
        author = message.author
        roles = getattr(author, "roles", ())
        staff = author.id == message.guild.owner_id or any(
            r.id == self.config.staff_role for r in roles
        )
        now = dt.datetime.now(dt.UTC)
        joined = getattr(author, "joined_at", None)
        linked = any(r.id == self.config.linked_role for r in roles)
        young = (
            not linked
            and (now - author.created_at).days < 7
            and (joined is None or now - joined < dt.timedelta(hours=24))
        )
        decision = assess(
            message.content, [a.filename for a in message.attachments], staff=staff, young=young
        )
        if decision.delete:
            await message.delete()
        if decision.delete or decision.review:
            # Only identifiers, rule, and filename hashes; no original content or attachments.
            audit = (
                f"Author ID: {author.id}\nRule: {decision.rule or 'suspicious_domain'}"
                f"\nMessage ID: {message.id}"
            )
            if decision.file_hashes:
                audit += "\nFilename SHA-256: " + ", ".join(decision.file_hashes)
            await (await self.channel("audit-log")).send(
                embed=info_embed("Message safety review", audit[:1900])
            )
        if decision.delete and self.warning_allowed(("dm", author.id)):
            with contextlib.suppress(discord.Forbidden):
                await author.send(
                    embed=info_embed(
                        "Message removed",
                        "Your message was removed by the server's download-safety rules.\n\n"
                        f"Use <#{self.config.channels['releases']}> for MithrilPF downloads.\n\n"
                        + WARNING,
                    ),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
        elif decision.warn and self.warning_allowed(message.channel.id):
            await message.channel.send(embed=info_embed("Keep your account safe", WARNING))

    def warning_allowed(self, channel_id):
        now = time.monotonic()
        self.last_warning = {key: at for key, at in self.last_warning.items() if at > now - 300}
        if channel_id in self.last_warning or len(self.last_warning) >= 500:
            return False
        self.last_warning[channel_id] = now
        return True

    async def on_raw_message_edit(self, payload):
        if payload.guild_id != self.config.guild_id:
            return
        channel = self.get_channel(payload.channel_id)
        if channel:
            with contextlib.suppress(discord.NotFound):
                await self.on_message(await channel.fetch_message(payload.message_id))

    async def on_thread_create(self, thread):
        if (
            thread.guild.id != self.config.guild_id
            or thread.parent_id != self.config.channels["support"]
        ):
            return
        # The create event is only handled for newly created threads, not cached joins.
        await thread.send(
            embed=info_embed(
                "Support checklist",
                support_reply(getattr(thread, "name", ""), self.config.channels["how-to"]),
            )
        )
