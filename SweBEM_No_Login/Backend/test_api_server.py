import asyncio
import hashlib
import sqlite3
import subprocess
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import api_server
from fastapi import HTTPException


class CacheVersionTests(unittest.TestCase):
    def test_normal_and_custom_results_are_versioned(self):
        params = {
            "weatherStation": "lund", "buildingType": "single-family-house",
            "wallU": 0.3, "atticU": 0.2, "groundU": 0.2, "ach": 0.5,
            "windowType": "double", "wwr": 15,
        }
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(api_server, "CACHE_DB", Path(directory) / "cache.db"):
                api_server.init_database()
                old_key = hashlib.md5(b"lund_1986-1995_single-family-house").hexdigest()
                with closing(sqlite3.connect(api_server.CACHE_DB)) as conn:
                    with conn:
                        conn.execute(
                            "INSERT INTO simulation_cache (id, annual_results, hourly_results) VALUES (?, ?, ?)",
                            (old_key, '{"old": true}', "{}"),
                        )
                with patch.object(api_server, "get_energyplus_version", return_value="25.2.0"):
                    self.assertIsNone(api_server.get_cached_result("lund", "1986-1995", "single-family-house"))
                    api_server.save_to_cache("lund", "1986-1995", "single-family-house", {"version": 25}, {})
                    api_server.save_custom_to_cache(params, {"version": 25}, {})
                with patch.object(api_server, "get_energyplus_version", return_value="26.2.0"):
                    self.assertIsNone(api_server.get_cached_result("lund", "1986-1995", "single-family-house"))
                    self.assertIsNone(api_server.get_cached_custom_result(params))
                    api_server.save_to_cache("lund", "1986-1995", "single-family-house", {"version": 26}, {})
                    api_server.save_custom_to_cache(params, {"version": 26}, {})
                    self.assertEqual(api_server.get_cached_result("lund", "1986-1995", "single-family-house")["annual"]["version"], 26)
                    self.assertEqual(api_server.get_cached_custom_result(params)["annual"]["version"], 26)
                with patch.object(api_server, "get_energyplus_version", return_value="25.2.0"):
                    self.assertEqual(api_server.get_cached_result("lund", "1986-1995", "single-family-house")["annual"]["version"], 25)
                    self.assertEqual(api_server.get_cached_custom_result(params)["annual"]["version"], 25)

    def test_version_failure_is_explicit(self):
        with patch.object(api_server.subprocess, "run", side_effect=FileNotFoundError("missing")):
            with self.assertRaises(HTTPException) as error:
                api_server.get_energyplus_version()
            self.assertEqual(error.exception.status_code, 503)
        with patch.object(api_server.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout="unexpected")):
            with self.assertRaises(HTTPException) as error:
                api_server.get_energyplus_version()
            self.assertEqual(error.exception.status_code, 503)


class CorsTests(unittest.TestCase):
    def test_launcher_origin_is_allowed(self):
        async def preflight(origin):
            messages = []
            scope = {
                "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                "method": "OPTIONS", "scheme": "http", "path": "/simulate",
                "raw_path": b"/simulate", "query_string": b"",
                "headers": [
                    (b"origin", origin.encode()),
                    (b"access-control-request-method", b"POST"),
                    (b"access-control-request-headers", b"content-type"),
                ],
                "client": ("127.0.0.1", 1234), "server": ("127.0.0.1", 8000),
            }

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message):
                messages.append(message)

            await api_server.app(scope, receive, send)
            return messages[0]

        for origin in ("http://localhost:3000", "http://127.0.0.1:3000", "http://swebem.local:3000"):
            with self.subTest(origin=origin):
                response = asyncio.run(preflight(origin))
                self.assertEqual(response["status"], 200)
                self.assertEqual(dict(response["headers"])[b"access-control-allow-origin"], origin.encode())
        self.assertEqual(asyncio.run(preflight("http://example.com"))["status"], 400)


if __name__ == "__main__":
    unittest.main()
