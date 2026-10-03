import sys
from unittest.mock import Mock

import pytest

from mithril_discord.__main__ import main
from tools import check, check_branch_name


@pytest.mark.parametrize(
    "branch", ["feat/bot", "fix/discord-api", "chore/tooling", "docs/runtime", "refactor/polls"]
)
def test_allowed_branches(branch):
    assert check_branch_name.valid_branch(branch)


def test_reject_bad_branches_and_impersonated_dependabot(monkeypatch):
    assert not check_branch_name.valid_branch("feat/../../main")
    assert not check_branch_name.valid_branch("dependabot/pip/x", "somebody")
    assert check_branch_name.valid_branch("dependabot/pip/x", "dependabot[bot]")
    monkeypatch.setenv("PR_HEAD_REF", "feat/bot")
    check_branch_name.main()
    monkeypatch.setenv("PR_HEAD_REF", "bad")
    with pytest.raises(SystemExit):
        check_branch_name.main()


def test_check_command_stops_on_failed_check(monkeypatch):
    monkeypatch.setenv("UV_EXECUTABLE", "test-uv")
    runner = Mock()
    monkeypatch.setattr(check.subprocess, "run", runner)
    check.main()
    assert runner.call_count == 4
    assert all(c.kwargs["check"] for c in runner.call_args_list)
    monkeypatch.delenv("UV_EXECUTABLE")
    monkeypatch.setattr(check.shutil, "which", lambda _: None)
    with pytest.raises(SystemExit):
        check.main()


def test_run_uses_configured_token_without_logging_it(monkeypatch, tmp_path, capsys):
    token = tmp_path / "token"
    token.write_text("synthetic-secret")
    config = Mock(token_file=token)
    monkeypatch.setattr("mithril_discord.__main__.Config.load", Mock(return_value=config))
    client = Mock()
    monkeypatch.setattr("mithril_discord.__main__.CommunityBot", Mock(return_value=client))
    monkeypatch.setattr(sys, "argv", ["bot", "run", "--config", str(tmp_path / "config.json")])
    main()
    client.run.assert_called_once_with("synthetic-secret", log_handler=None)
    assert "synthetic-secret" not in capsys.readouterr().out


def test_run_configuration_errors_do_not_echo_secret(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["bot", "run", "--config", str(tmp_path / "missing")])
    with pytest.raises(SystemExit, match="Startup failed"):
        main()
