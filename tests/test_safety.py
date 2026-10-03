import hashlib

import pytest

from mithril_discord.safety import assess, official_url


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/MithrilAddons/mithrilpf/releases",
        "https://github.com/MithrilAddons/mithrilpf/releases/download/v1.2.3/mod.jar",
        "https://modrinth.com/mod/mithrilpf",
        "https://mithril.foo/party-finder",
    ],
)
def test_exact_official_hosts(url):
    assert official_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://mithril.foo",
        "https://mithril.foo.evil.invalid/a.jar",
        "https://github.com/attacker/mithrilpf/releases",
        "https://github.com/MithrilAddons/mithrilpf/releases-malware",
        "https://modrinth.com/mod/mithrilpf-fake",
        "https://mithril.foo@evil.invalid",
        "https://evil.invalid@mithril.foo",
        "https://mithril.foo:444/a.jar",
        "https://[broken",
        "https://mithril.foo:bad",
        "https://github.com/MithrilAddons/mithrilpf/releases/%2e%2e/evil",
        "ftp://mithril.foo",
    ],
)
def test_lookalikes_and_alternate_origins_never_official(url):
    assert not official_url(url)


@pytest.mark.parametrize(
    "filename", ["mod.jar", "MOD.JAR", "mod.jar. ", "thing.EXE", "mod.ｊａｒ", "a.ps1", "a.zip"]
)
def test_attachment_rules_keep_only_filename_hash(filename):
    result = assess("", [filename])
    assert result.delete
    assert result.file_hashes == (hashlib.sha256(filename.encode()).hexdigest(),)
    assert filename not in repr(result)


def test_community_and_new_member_rules():
    assert not assess("a screenshot", ["image.png"]).delete
    assert assess("a screenshot", ["image.png"], young=True).delete
    assert assess("hi https://example.invalid", young=True).delete
    assert assess("download the mod https://evil.invalid/a").delete
    assert not assess("download https://mithril.foo").delete
    assert assess("see https://bit.ly/example").review
    assert assess("see https://mithril-foo.invalid").review
    assert assess("send me your session ID").warn
    assert not assess("mod https://evil.invalid", ["bad.jar"], staff=True).delete
