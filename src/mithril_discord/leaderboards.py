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


def validate_name(name):
    if name is not None and (
        not isinstance(name, str) or not re.fullmatch(r"\w{1,16}", name, flags=re.ASCII)
    ):
        raise ValueError("Invalid Minecraft name")


def validate_map_id(map_id):
    if map_id is not None and (
        not isinstance(map_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", map_id)
    ):
        raise ValueError("Invalid map reference")


def validate(rows):
    if not isinstance(rows, list) or len(rows) > 1000:
        raise ValueError("Invalid leaderboard size")
    seen = set()
    for row in rows:
        uuid = row["uuid"]
        if not isinstance(uuid, str) or not re.fullmatch(r"[0-9a-f]{32}", uuid) or uuid in seen:
            raise ValueError("Invalid leaderboard identity")
        seen.add(uuid)
        validate_name(row["name"])
        validate_map_id(row.get("map_id"))
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
        pages = paginate(category_lines(rows, terminal))
        for number, description in enumerate(pages, 1):
            suffix = f" ({number}/{len(pages)})" if len(pages) > 1 else ""
            embed = info_embed(title + suffix, description.rstrip())
            embed.timestamp = updated
            embeds.append(embed)
    return embeds


def displayed_time(row, terminal):
    timing = duration(row["real_ms"] if terminal else row["ticks"] * 50)
    if not terminal and row.get("map_id"):
        return f"[{timing}](https://mithril.foo/runs/{row['map_id']})"
    return timing


def category_lines(rows, terminal):
    lines = []
    for rank, entries in groupby(rows, key=lambda row: row["rank"]):
        tied = list(entries)
        first = tied[0]
        timing = displayed_time(first, terminal)
        prefix = f"**{rank}. {timing}** — "
        line = prefix
        for row in tied:
            name = plain(row["name"] or row["uuid"])
            if len(line) + len(name) + 2 > 3500:
                lines.append(line)
                line = prefix
            line += (", " if line != prefix else "") + name
        lines.append(line)
    if not rows:
        lines.append("No eligible times yet. Record a qualifying run with MithrilPF linked.")
    return lines


def paginate(lines):
    # A group remains one rank even when its names need a continuation card.
    pages = [""]
    for line in lines:
        if pages[-1] and len(pages[-1]) + len(line) + 1 > 3500:
            pages.append("")
        pages[-1] += line + "\n"
    return pages
