# Development

Use Python 3.12-3.14 and uv 0.12.19, matching the backend's supported Python range.

```text
uv sync --locked
uv run --locked ruff format .
python tools/check.py
```

If uv is not on PATH, set `UV_EXECUTABLE` to its executable path for the check script.
Run the package from source with `PYTHONPATH=src` and `uv run --locked python -m
mithril_discord`. No development install modifies another repository's environment.

Code is in `src/mithril_discord`; tests are in `tests`; operational state belongs
under ignored `.local/`, outside source. Tests block outbound HTTP and never read
the local bot token. The standard check includes lockfile validation, Ruff lint and
format verification, pytest and branch coverage (minimum 80%). Reports are under
`build/reports`. Tests do not prove real Discord permissions or rendering.

CI runs `Verify (ubuntu-24.04)` with Python 3.12 and `Verify (windows-2025)` with
Python 3.14. Actions are pinned; checkout credentials are not retained; default
permissions are read-only. CI does not deploy. Fork and Dependabot PRs run all
offline checks without receiving the Sonar token.

SonarQube project key: `MithrilAddons_discord`, organization `mithriladdons`.
Import the GitHub repository, turn automatic analysis off, set `SONAR_TOKEN` as
a repository Actions secret, then run the first main analysis. Linux CI waits for
the quality gate and fails when analysis/gate fails; it does not silently skip
missing configuration. Configure the two verification jobs as required checks once
they exist. Sonar initialization and actual CI require published source and must
be verified separately from local tests.
