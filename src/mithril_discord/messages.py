"""Fixed templates and official download buttons with Markdown release notes."""

import math
import re

import discord

from .safety import official_url

ACCENT_COLOR = 0xB4B8FF


def info_embed(title: str, description: str = "", *, url=None):
    """Shared visual structure for server information and bot notices."""
    embed = discord.Embed(title=title, description=description, colour=ACCENT_COLOR, url=url)
    embed.set_author(name="MithrilPF", url="https://mithril.foo")
    embed.set_footer(text="MithrilPF • Community")
    return embed


WARNING = "MithrilPF and its staff never ask for your Minecraft session ID, token, or SSID."
SUPPORT_TEMPLATE = (
    "Please include your MithrilPF, Minecraft and Fabric versions, what happened, "
    "and the output of `/mithrilpfstatus`. Remove personal details before posting logs. " + WARNING
)
SUPPORT_HINTS = (
    (
        "link",
        "For browser linking, confirm the correct account on mithril.foo "
        "and keep the mod's link screen open.",
    ),
    (
        "invite",
        "For invites, check all members are on Hypixel and there is no conflicting game party.",
    ),
    (
        "update",
        "Automatic updates require an official release build; local builds do not self-update.",
    ),
    (
        "not on hypixel",
        "Presence requires being connected to Hypixel, not the title screen or another server.",
    ),
)


def support_reply(title: str, how_to: int):
    hints = [text for keyword, text in SUPPORT_HINTS if keyword in title.casefold()]
    return "\n\n".join(
        [SUPPORT_TEMPLATE, *hints, f"Installation and troubleshooting: <#{how_to}>."]
    )


def server_information(channels):
    welcome = info_embed(
        "Welcome to MithrilPF",
        "Find Hypixel SkyBlock dungeon parties through the Minecraft mod and website.\n\n"
        "**Discord is optional.** You can chat and ask for support without linking.",
    )
    welcome.add_field(
        name="Start here",
        value=f"**Install and get help** · <#{channels['how-to']}>\n"
        f"**Official downloads** · <#{channels['releases']}>\n"
        f"**Service updates** · <#{channels['status']}>\n"
        f"**Ask for support** · <#{channels['support']}>",
        inline=False,
    )
    welcome.add_field(
        name="Keep your account safe",
        value=f"{WARNING}\n\nGet the mod only from official release links. "
        "Never install a JAR sent by a stranger.",
        inline=False,
    )
    welcome.add_field(
        name="Coming later",
        value="Discord account verification and party voice are not enabled yet.",
        inline=False,
    )
    installation = info_embed(
        "Installation & download verification",
        "Use the installation requirements published with the release on "
        "[GitHub](https://github.com/MithrilAddons/mithrilpf/releases) or "
        "[Modrinth](https://modrinth.com/mod/mithrilpf).\n\n"
        "Install the **gameplay JAR**, not the sources JAR. "
        "Our website is [mithril.foo](https://mithril.foo).",
    )
    installation.add_field(
        name="1 · Calculate the SHA-256 checksum",
        value="**Windows · PowerShell**\n"
        "```powershell\nGet-FileHash -Algorithm SHA256 -LiteralPath 'path-to-downloaded.jar'\n```"
        "\n**Linux**\n```sh\nsha256sum path-to-downloaded.jar\n```"
        "\n**macOS**\n```sh\nshasum -a 256 path-to-downloaded.jar\n```",
        inline=False,
    )
    installation.add_field(
        name="2 · Compare before installing",
        value="Compare all **64 hexadecimal characters** with the release post or official "
        "`SHA256SUMS` file. **If they differ, do not install the file.**\n\n"
        "A checksum detects changed bytes; it does not independently authenticate a publisher. "
        "The current release pipeline does not publish a detached JAR signature.",
        inline=False,
    )
    help_card = info_embed(
        "Linking & troubleshooting",
        "Start with `/mpf` in Minecraft. Discord linking is not part of the initial bot release.",
    )
    help_card.add_field(
        name="Link your browser safely",
        value="Minecraft authentication happens through the mod and Mojang; only Mojang receives "
        "the Minecraft access token. Browser linking requires confirming the correct account "
        "on **mithril.foo**. Do not share screenshots of link codes or QR codes.",
        inline=False,
    )
    help_card.add_field(
        name="When asking for support",
        value=f"Post in <#{channels['support']}> and include:\n"
        "• MithrilPF, Minecraft and Fabric versions\n"
        "• What you expected and what happened\n"
        "• `/mithrilpfstatus` output\n\nRemove account details and credentials from logs.",
        inline=False,
    )
    help_card.add_field(
        name="Common checks",
        value="**Invites** · Check all members are on Hypixel and whether another game party "
        "conflicts.\n**Updates** · Automatic updates require an official release build "
        "and a restart.",
        inline=False,
    )
    return {"welcome": [welcome], "how-to": [installation, help_card]}


def plain(text: str) -> str:
    return discord.utils.escape_markdown(discord.utils.escape_mentions(text))


def release_message(release, how_to: int):
    version = release["version"]
    if (
        not isinstance(version, str)
        or len(version) > 80
        or not re.fullmatch(r"\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+)?", version)
    ):
        raise ValueError("Invalid version")
    checksum = release["sha256"]
    if not isinstance(checksum, str) or not re.fullmatch(r"[a-f0-9]{64}", checksum):
        raise ValueError("Missing SHA-256")
    expected = f"https://github.com/MithrilAddons/mithrilpf/releases/tag/v{version}"
    download = (
        "https://github.com/MithrilAddons/mithrilpf/releases/download/"
        f"v{version}/mithrilpf-{version}.jar"
    )
    if (
        release["page"] != expected
        or release["url"] != download
        or not official_url(release["url"])
    ):
        raise ValueError("Invalid release destination")
    if type(release["prerelease"]) is not bool or release["prerelease"] != ("-" in version):
        raise ValueError("Invalid prerelease marker")
    notes = discord.utils.escape_mentions(str(release["notes"])[:2600])
    channel = "Prerelease" if release["prerelease"] else "Stable"
    embed = info_embed(title=f"MithrilPF {version} ({channel})", url=expected)
    embed.description = notes or "See the release notes on GitHub."
    embed.add_field(name="SHA-256", value=f"```\n{checksum}\n```", inline=False)
    embed.add_field(
        name="Verify your download",
        value=f"Instructions: <#{how_to}>. No detached JAR signature is currently published.",
        inline=False,
    )
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="GitHub download", url=release["url"]))
    view.add_item(discord.ui.Button(label="Modrinth", url="https://modrinth.com/mod/mithrilpf"))
    return embed, view


def release_metrics(release):
    metrics = release.get("checks")
    if metrics is None:
        return []
    tests = metrics["tests"]
    url = metrics["run_url"]
    if (
        type(tests) is not int
        or not 0 < tests <= 1_000_000
        or not re.fullmatch(
            r"https://github\.com/MithrilAddons/mithrilpf/actions/runs/[1-9][0-9]{0,14}", url
        )
    ):
        raise ValueError("Invalid release check metadata")
    for key in ("line_coverage", "branch_coverage"):
        value = metrics[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError("Invalid coverage percentage")
    embed = info_embed("Automated checks", "Release builds passed on Linux and Windows.", url=url)
    embed.add_field(name="JVM tests", value=f"{tests:,} passed", inline=True)
    embed.add_field(name="Line coverage", value=f"{metrics['line_coverage']:.1f}%", inline=True)
    embed.add_field(name="Branch coverage", value=f"{metrics['branch_coverage']:.1f}%", inline=True)
    embed.add_field(name="Report", value=f"[View release workflow]({url})", inline=False)
    embed.set_footer(
        text="MithrilPF • JVM test counts and JaCoCo coverage from the Linux release build"
    )
    return [embed]


def status_message(summary, last_success):
    if summary is None:
        return (
            "MithrilPF backend is unreachable. "
            f"Last successful check: {last_success or 'not yet'} UTC."
        )
    lines = ["**MithrilPF status: online**", f"Last successful check: {last_success} UTC"]
    for floor in ("F7", "M7"):
        counts = summary["floors"][floor]
        if any(type(counts[k]) is not int or counts[k] < 0 for k in ("open_parties", "looking")):
            raise ValueError("Invalid aggregate counts")
        lines.append(
            f"{floor}: {counts['open_parties']} open parties; {counts['looking']} players looking"
        )
    hypixel = summary["hypixel"]
    if hypixel not in ("ok", "slow", "failing", "unknown"):
        raise ValueError("Invalid Hypixel status")
    lines.append(f"Hypixel finder lookups: {hypixel}")
    lines.append(f"Latest mod: {plain(summary.get('latest_version') or 'unknown')}")
    return "\n".join(lines)
