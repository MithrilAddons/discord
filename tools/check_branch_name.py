"""Enforce the shared contribution branch naming convention."""

import os
import re


def valid_branch(name: str, author: str = "") -> bool:
    if author == "dependabot[bot]" and name.startswith("dependabot/"):
        return True
    return (
        re.fullmatch(r"(?:feat|fix|chore|refactor|docs)/[a-z0-9]+(?:-[a-z0-9]+)*", name) is not None
    )


def main() -> None:
    if not valid_branch(os.environ.get("PR_HEAD_REF", ""), os.environ.get("PR_AUTHOR", "")):
        raise SystemExit("Use feat/, fix/, chore/, refactor/, or docs/ and a kebab-case name.")


if __name__ == "__main__":
    main()
