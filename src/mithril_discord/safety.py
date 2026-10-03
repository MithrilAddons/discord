"""Deterministic community message checks; never fetch attachments or links."""

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

EXECUTABLES = {
    ".jar",
    ".exe",
    ".zip",
    ".rar",
    ".7z",
    ".bat",
    ".cmd",
    ".ps1",
    ".scr",
    ".msi",
    ".com",
}
URLS = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
CONTEXT = re.compile(r"\b(?:mithrilpf|mods?|downloads?)\b", re.IGNORECASE)
SECRET_REQUEST = re.compile(r"\b(?:session[\s_-]*id|ssid|tokens?)\b", re.IGNORECASE)
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "shorturl.at"}


@dataclass(frozen=True)
class Decision:
    delete: bool = False
    rule: str | None = None
    file_hashes: tuple[str, ...] = ()
    warn: bool = False
    review: bool = False


def official_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or parts.username
            or parts.password
            or parts.port not in (None, 443)
        ):
            return False
        host = (parts.hostname or "").lower()
        path = unquote(parts.path).rstrip("/")
        if any(part in (".", "..") for part in path.split("/")):
            return False
        if host == "mithril.foo":
            return True
        if host == "github.com":
            prefix = "/MithrilAddons/mithrilpf/releases"
            return path == prefix or path.startswith(prefix + "/")
        if host == "modrinth.com":
            return path == "/mod/mithrilpf" or path.startswith("/mod/mithrilpf/")
    except ValueError:
        return False
    return False


def assess(text: str, filenames=(), *, staff=False, young=False) -> Decision:
    if staff:
        return Decision()
    normalized = unicodedata.normalize("NFKC", text)
    urls = [match.rstrip(".,!)]}") for match in URLS.findall(normalized)]
    warn = bool(SECRET_REQUEST.search(normalized))
    hashes = tuple(
        hashlib.sha256(name.encode()).hexdigest()
        for name in filenames
        if any(
            unicodedata.normalize("NFKC", name).casefold().rstrip(" .").endswith(ext)
            for ext in EXECUTABLES
        )
    )
    if hashes:
        return Decision(True, "executable_attachment", hashes, warn)
    if young and (urls or filenames):
        return Decision(True, "new_account_links", (), warn)
    if CONTEXT.search(normalized) and any(not official_url(url) for url in urls):
        return Decision(True, "unofficial_download", (), warn)
    review = False
    for url in urls:
        try:
            host = (urlsplit(url).hostname or "").casefold()
        except ValueError:
            continue
        review |= host in SHORTENERS or ("mithril" in host and not official_url(url))
    return Decision(warn=warn, review=review)
