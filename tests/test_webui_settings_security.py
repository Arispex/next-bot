from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import server.settings_service as settings_service
from server.routes.webui import _build_session_cookie
from server.server_config import WebServerSettings
from server.settings_service import SettingsValidationError, save_settings
from server.web_server import create_app


class SettingsServiceSecurityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env_path = Path(self.temp_dir.name) / ".env"
        self.original_env_text = (
            "KEEP_ME=value\n"
            "ONEBOT_ACCESS_TOKEN=old-token\n"
            "WEB_SERVER_HOST=127.0.0.1\n"
            "WEB_SERVER_PUBLIC_BASE_URL=http://127.0.0.1:18081\n"
            "COMMAND_DISABLED_MODE=reply\n"
            "COMMAND_DISABLED_MESSAGE=该命令暂时关闭\n"
        )
        self.env_path.write_text(self.original_env_text, encoding="utf-8")
        self.env_path_patch = patch.object(settings_service, "_ENV_PATH", self.env_path)
        self.env_path_patch.start()

    def tearDown(self) -> None:
        self.env_path_patch.stop()
        self.temp_dir.cleanup()

    def test_save_settings_rejects_newlines_for_single_line_scalar_fields(self) -> None:
        cases = [
            ("onebot_access_token", "token\nnext", "INJECTED_TOKEN"),
            ("onebot_access_token", "token\rnext", "INJECTED_TOKEN"),
            ("onebot_access_token", "token\r\nnext", "INJECTED_TOKEN"),
            ("web_server_host", "127.0.0.1\nINJECTED_HOST=1", "INJECTED_HOST"),
            (
                "web_server_public_base_url",
                "https://example.com\nINJECTED_URL=1",
                "INJECTED_URL",
            ),
            ("command_disabled_mode", "reply\nsilent", "INJECTED_MODE"),
            (
                "command_disabled_message",
                "该命令暂时关闭\nINJECTED_MESSAGE=1",
                "INJECTED_MESSAGE",
            ),
        ]

        for field, value, injected_key in cases:
            with self.subTest(field=field, value=value):
                with self.assertRaises(SettingsValidationError) as context:
                    save_settings({field: value})

                self.assertEqual(context.exception.field, field)
                self.assertEqual(str(context.exception), f"{field} 不能包含换行")
                env_text = self.env_path.read_text(encoding="utf-8")
                self.assertEqual(env_text, self.original_env_text)
                self.assertNotIn(injected_key, env_text)

    def test_save_settings_allows_read_path_newlines_for_existing_values(self) -> None:
        self.assertEqual(
            settings_service._normalize_field("command_disabled_message", " line 1\nline 2 "),
            "line 1\nline 2",
        )
        self.assertEqual(
            settings_service._normalize_field("onebot_access_token", " token\nvalue "),
            "token\nvalue",
        )

    def test_save_settings_allows_literal_backslash_sequences_for_single_line_fields(self) -> None:
        result = save_settings(
            {
                "onebot_access_token": " 令牌\\n文字 ",
                "command_disabled_message": " 提示\\r文字 ",
            }
        )

        self.assertEqual(
            result.saved_fields,
            ["onebot_access_token", "command_disabled_message"],
        )
        env_text = self.env_path.read_text(encoding="utf-8")
        self.assertIn("ONEBOT_ACCESS_TOKEN=令牌\\n文字\n", env_text)
        self.assertIn("COMMAND_DISABLED_MESSAGE=提示\\r文字\n", env_text)
        self.assertIn("KEEP_ME=value\n", env_text)


class WebuiSettingsSecurityRouteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env_path = Path(self.temp_dir.name) / ".env"
        self.env_path.write_text(
            (
                "ONEBOT_ACCESS_TOKEN=old-token\n"
                "WEB_SERVER_HOST=127.0.0.1\n"
                "WEB_SERVER_PORT=18081\n"
                "WEB_SERVER_PUBLIC_BASE_URL=http://127.0.0.1:18081\n"
                "COMMAND_DISABLED_MODE=reply\n"
                "COMMAND_DISABLED_MESSAGE=该命令暂时关闭\n"
            ),
            encoding="utf-8",
        )
        self.settings = WebServerSettings(
            host="127.0.0.1",
            port=18081,
            public_base_url="http://127.0.0.1:18081",
            webui_token="test-token",
            session_secret="test-session-secret",
            auth_file_path=str(Path(self.temp_dir.name) / ".webui_auth.json"),
            auth_file_created=False,
        )
        app = create_app(self.settings)
        self.client = TestClient(app)
        self.client.cookies.set(
            self.settings.cookie_name,
            _build_session_cookie(self.settings.session_secret),
        )
        self.env_path_patch = patch.object(settings_service, "_ENV_PATH", self.env_path)
        self.env_path_patch.start()

    def tearDown(self) -> None:
        self.env_path_patch.stop()
        self.client.close()
        self.temp_dir.cleanup()

    def test_put_settings_rejects_newline_input_for_wrapped_and_raw_payloads(self) -> None:
        cases = [
            {"data": {"onebot_access_token": "token\nnext"}},
            {"command_disabled_message": "该命令暂时关闭\nINJECTED=1"},
        ]

        for payload in cases:
            with self.subTest(payload=payload):
                original_env = self.env_path.read_text(encoding="utf-8")
                with patch("server.routes.webui_settings._schedule_process_restart") as restart_mock:
                    response = self.client.put("/webui/api/settings", json=payload)

                self.assertEqual(response.status_code, 422)
                body = response.json()
                self.assertIs(body["ok"], False)
                self.assertIn("保存失败，", body["message"])
                self.assertIn("不能包含换行", body["message"])
                self.assertIn(body["field"], {"onebot_access_token", "command_disabled_message"})
                restart_mock.assert_not_called()
                self.assertEqual(self.env_path.read_text(encoding="utf-8"), original_env)

    def test_get_settings_keeps_ok_data_meta_envelope(self) -> None:
        snapshot = {"onebot_access_token": "visible-token"}
        metadata = {
            "managed_fields": ["onebot_access_token"],
            "sensitive_fields": ["onebot_access_token"],
        }
        with (
            patch("server.routes.webui_settings.get_settings_snapshot", return_value=snapshot),
            patch("server.routes.webui_settings.get_settings_metadata", return_value=metadata),
        ):
            response = self.client.get("/webui/api/settings")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"ok": True, "data": snapshot, "meta": metadata},
        )

    def test_put_settings_success_keeps_existing_response_shape(self) -> None:
        with patch("server.routes.webui_settings._schedule_process_restart", return_value=True):
            response = self.client.put(
                "/webui/api/settings",
                json={"data": {"web_server_host": "0.0.0.0"}},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "ok": True,
                "message": "保存成功，正在重启程序",
                "restart_scheduled": True,
                "saved_fields": ["web_server_host"],
            },
        )
        env_text = self.env_path.read_text(encoding="utf-8")
        self.assertIn("WEB_SERVER_HOST=0.0.0.0\n", env_text)


if __name__ == "__main__":
    unittest.main()
