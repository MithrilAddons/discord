"""Uniform leaderboard cards, with exact clock comparisons and overflow pages."""

import datetime as dt
import re
from itertools import groupby

from .messages import info_embed, plain

CATEGORIES = {
    "f7_solo": "F7 solo clear",
    "m7_solo": "M7 solo clear",
    "m7_terminals": "M7 terminals",
}


def duration(milliseconds):
    minutes, remainder = divmod(milliseconds, 60000)
    seconds, millis = divmod(remainder, 1000)
    return f"{minutes}:{seconds:02}.{millis:03}"


def validate(rows):
    if not isinstance(rows, list) or len(rows) > 1000:
        raise ValueError("Invalid leaderboard size")
    seen = set()
    for row in rows:
        uuid = row["uuid"]
        if not isinstance(uuid, str) or not re.fullmatch(r"[0-9a-f]{32}", uuid) or uuid in seen:
            raise ValueError("Invalid leaderboard identity")
        seen.add(uuid)
        if row["name"] is not None and (
            not isinstance(row["name"], str) or not re.fullmatch(r"[A-Za-z0-9_]{1,16}", row["name"])
        ):
            raise ValueError("Invalid Minecraft name")
        for key, maximum in (("rank", 10), ("real_ms", 7200000), ("ticks", 144000)):
            if type(row[key]) is not int or not 1 <= row[key] <= maximum:
                raise ValueError("Invalid leaderboard timing")


def cards(payload):
    if payload["version"] != 1 or set(payload["boards"]) != set(CATEGORIES):
        raise ValueError("Unsupported leaderboards")
    updated = dt.datetime.fromtimestamp(payload["updated_at"], dt.UTC)
    embeds = []
    for key, title in CATEGORIES.items():
        rows = payload["boards"][key]
        validate(rows)
        terminal = key == "m7_terminals"
        rule = (
            "Top 10 time slots · Real time, then tick time · One PB per player"
            if terminal
            else "Top 10 players · Tick time · Solo 300 score · One PB per player"
        )
        pages = paginate(category_lines(rows, terminal, rule), rule, title)
        for number, description in enumerate(pages, 1):
            suffix = f" ({number}/{len(pages)})" if len(pages) > 1 else ""
            embed = info_embed(title + suffix, description.rstrip())
            embed.timestamp = updated
            embeds.append(embed)
    return embeds


def category_lines(rows, terminal, rule):
    lines = [rule, ""]
    for rank, entries in groupby(rows, key=lambda row: row["rank"]):
        tied = list(entries)
        first = tied[0]
        timing = f"{duration(first['ticks'] * 50)} tick time"
        if terminal:
            timing = f"{duration(first['real_ms'])} real · {timing}"
        lines.append(f"**{rank}. {timing}**")
        lines.extend(plain(row["name"] or row["uuid"]) for row in tied)
        lines.append("")
    if not rows:
        lines.append("No eligible times yet. Record a qualifying run with MithrilPF linked.")
    return lines


def paginate(lines, rule, title):
    # A group remains one rank even when its names need a continuation card.
    pages = [""]
    heading = ""
    for line in lines:
        if len(pages[-1]) + len(line) + 1 > 3500:
            pages.append(f"{rule}\n\n{title} — continued\n{heading}\n")
        if line.startswith("**"):
            heading = line
        pages[-1] += line + "\n"
    return pages
