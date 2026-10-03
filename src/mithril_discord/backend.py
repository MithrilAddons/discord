"""Fixed loopback destinations with bounded responses and no redirect following."""

import http.client
import json

MAX_RESPONSE = 131072


def fetch(endpoint: str, secret: str):
    if endpoint not in ("summary", "releases"):
        raise ValueError("Unknown backend endpoint")
    connection = http.client.HTTPConnection("127.0.0.1", 8781, timeout=5)
    try:
        connection.request(
            "GET",
            f"/internal/v1/{endpoint}",
            headers={"Authorization": f"Bearer {secret}", "Accept-Encoding": "identity"},
        )
        response = connection.getresponse()
        if (
            response.status != 200
            or response.getheader("Content-Encoding", "identity") != "identity"
        ):
            raise ValueError("Backend unavailable")
        data = response.read(MAX_RESPONSE + 1)
        if len(data) > MAX_RESPONSE:
            raise ValueError("Backend response too large")
        result = json.loads(data)
        if not isinstance(result, dict) or result.get("version") != 1:
            raise ValueError("Unsupported backend response")
        return result
    finally:
        connection.close()
