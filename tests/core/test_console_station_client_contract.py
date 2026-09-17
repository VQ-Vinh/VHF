"""The operator client sends the control epoch wherever the API demands it.

The server's list of routes is read from `services/prana_api/main.py` as text,
not imported: this suite runs without the API's dependencies. Reading the real
file is the point. The desktop's TX calls once omitted the header, every
transmission was refused with a 422, and the console tests never noticed
because they drive a fake client that accepts any arguments.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from unittest import mock

import httpx

from prana_core.console import station_client
from prana_core.console.station_client import OperatorStationClient

ROOT = Path(__file__).resolve().parents[2]
API_MAIN = ROOT / "services" / "prana_api" / "main.py"
EPOCH = 7


def _epoch_routes() -> set[tuple[str, str]]:
    """(METHOD, path template) for every operator route taking X-Control-Epoch."""
    source = API_MAIN.read_text(encoding="utf-8")
    routes = set()
    for block in re.split(r"\n(?=@operator_router\.)", source):
        match = re.match(r'@operator_router\.(get|post|patch|delete)\(\s*"([^"]+)"', block)
        if not match:
            continue
        signature = block.split("):", 1)[0]
        if 'alias="X-Control-Epoch"' in signature:
            routes.add((match.group(1).upper(), match.group(2)))
    return routes


def _template(path: str) -> str:
    """Turn a concrete request path back into the router's template."""
    path = path.split("/v1/operator", 1)[1]
    path = re.sub(r"^/stations/station-1", "/stations/{station_id}", path)
    return path.replace("/draft-1", "/{job_id}")


class _Backend:
    api_url = "https://api.test"

    @staticmethod
    def auth_headers() -> dict:
        return {"Authorization": "Bearer test"}


class OperatorClientEpochContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sent: list[tuple[str, str, dict]] = []

        def fake_request(method, url, **kwargs):
            self.sent.append((method, _template(httpx.URL(url).path), kwargs["headers"]))
            request = httpx.Request(method, url)
            if method == "DELETE":
                return httpx.Response(204, request=request)
            body = {
                "holder_uid": "me",
                "holder_kind": "operator",
                "expires_at": "2030-01-01T00:00:00+00:00",
                "epoch": EPOCH,
                "id": "draft-1",
                "status": "review_ready",
            }
            return httpx.Response(200, json=body, request=request)

        patcher = mock.patch.object(station_client.httpx, "request", side_effect=fake_request)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = OperatorStationClient(_Backend())

    def _call_every_epoch_method(self) -> None:
        c = self.client
        c.renew_control("station-1", EPOCH)
        c.release_control("station-1", EPOCH)
        c.set_desired_state("station-1", EPOCH, running=True)
        c.create_tx_draft("station-1", EPOCH, b"RIFF", "vi", request_id="req-1")
        c.get_tx_draft("station-1", EPOCH, "draft-1")
        c.confirm_tx_draft("station-1", EPOCH, "draft-1", "Xin chao")
        c.cancel_tx_draft("station-1", EPOCH, "draft-1")
        c.retry_tx_draft("station-1", EPOCH, "draft-1")

    def test_the_route_list_was_actually_found(self) -> None:
        """Guards the parser: an empty set would make the next test pass vacuously."""
        routes = _epoch_routes()
        self.assertIn(("POST", "/stations/{station_id}/tx/drafts"), routes)
        self.assertIn(("PATCH", "/stations/{station_id}/desired-state"), routes)
        self.assertGreaterEqual(len(routes), 7)

    def test_every_route_that_requires_the_epoch_receives_it(self) -> None:
        self._call_every_epoch_method()
        for method, template in sorted(_epoch_routes()):
            with self.subTest(route=f"{method} {template}"):
                calls = [h for m, p, h in self.sent if m == method and p == template]
                self.assertTrue(calls, "the client has no call for this route")
                for headers in calls:
                    self.assertEqual(headers.get("X-Control-Epoch"), str(EPOCH))

    def test_tx_upload_keeps_its_idempotency_key(self) -> None:
        """Adding the epoch must not displace the key that prevents double TX."""
        self.client.create_tx_draft("station-1", EPOCH, b"RIFF", "vi", request_id="req-1")
        _method, _path, headers = self.sent[-1]
        self.assertEqual(headers["X-Request-ID"], "req-1")
        self.assertEqual(headers["X-Control-Epoch"], str(EPOCH))


if __name__ == "__main__":
    unittest.main()
