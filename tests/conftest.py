"""Every test is offline; accidental socket connects fail immediately."""

import socket

import aiohttp
import pytest


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not contact external services")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(aiohttp.ClientSession, "_request", blocked)
