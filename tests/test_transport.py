import json
from unittest.mock import Mock

import pytest

from mithril_discord.backend import MAX_RESPONSE, fetch


@pytest.mark.parametrize(
    "status,data,encoding",
    [
        (302, b"{}", "identity"),
        (401, b"{}", "identity"),
        (200, b"x" * (MAX_RESPONSE + 1), "identity"),
        (200, b"bad", "identity"),
        (200, b'{"version":2}', "identity"),
        (200, b"[]", "identity"),
        (200, b'{"version":1}', "gzip"),
    ],
    ids=["redirect", "auth", "oversized", "json", "version", "shape", "encoding"],
)
def test_rejects_bad_backend_responses(monkeypatch, status, data, encoding):
    connection = Mock()
    response = connection.getresponse.return_value
    response.status, response.read.return_value = status, data
    response.getheader.return_value = encoding
    monkeypatch.setattr(
        "mithril_discord.backend.http.client.HTTPConnection", Mock(return_value=connection)
    )
    with pytest.raises(ValueError):
        fetch("releases", "synthetic-secret")
    connection.close.assert_called_once()


def test_only_fixed_loopback_endpoint(monkeypatch):
    connection = Mock()
    response = connection.getresponse.return_value
    response.status = 200
    response.getheader.return_value = "identity"
    response.read.return_value = json.dumps({"version": 1}).encode()
    factory = Mock(return_value=connection)
    monkeypatch.setattr("mithril_discord.backend.http.client.HTTPConnection", factory)
    assert fetch("summary", "synthetic-secret") == {"version": 1}
    factory.assert_called_once_with("127.0.0.1", 8781, timeout=5)
    assert connection.request.call_args.args[:2] == ("GET", "/internal/v1/summary")
    response.read.assert_called_once_with(MAX_RESPONSE + 1)
    with pytest.raises(ValueError):
        fetch("http://evil.invalid", "synthetic-secret")
