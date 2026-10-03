# Contributing

Use a focused `feat/`, `fix/`, `chore/`, `refactor/` or `docs/` branch with a
lowercase kebab-case name, signed commits and pull requests. Describe resulting
behavior, validation and deployment dependencies. Contributions use the MIT license.
Do not copy implementation from the AGPL backend into this repository.

Run Ruff formatting followed by `python tools/check.py`. Tests must use synthetic
identities and temporary storage, never real Discord/Hypixel accounts or credentials.
Preserve versioned contracts and test both sides of any protocol change. Dependencies
are exact-pinned with a committed uv lockfile. Review checksum/dependency changes.

No credentials, account data, logs or runtime databases belong in Git. API tests are
offline; distinguish them from actual Discord permission/rendering checks. Keep the bot
independent from the Finder process and its databases. Changes to permissions,
identity verification, erasure or public API behavior need explicit review.
