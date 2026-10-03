"""Run the community bot; no credentials in CLI arguments."""

import argparse
from pathlib import Path

import discord

from .bot import CommunityBot
from .config import Config, read_secret


def main():
    parser = argparse.ArgumentParser(description="MithrilPF Discord bot")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    try:
        config = Config.load(args.config)
        CommunityBot(config).run(read_secret(config.token_file), log_handler=None)
    except (OSError, ValueError, KeyError, discord.DiscordException) as error:
        raise SystemExit(
            f"Startup failed ({type(error).__name__}); check local configuration and access."
        ) from None


if __name__ == "__main__":
    main()
