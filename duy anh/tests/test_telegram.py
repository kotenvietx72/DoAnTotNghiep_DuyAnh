"""Kiểm thử cấu hình và bảo mật Telegram, không gọi Telegram thật."""
import atexit
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.parse import quote

os.environ["TELEGRAM_ENABLED"] = "0"
_import_database = tempfile.TemporaryDirectory()
atexit.register(_import_database.cleanup)
os.environ["ROOM_DATABASE"] = str(Path(_import_database.name) / "telegram.sqlite3")

import app as web


class TelegramTests(unittest.TestCase):
    def log_http_failure(self, status, body):
        response = web.requests.Response()
        response.status_code = status
        response.url = "https://api.telegram.org/botunit-test-private-token/sendMessage"
        response._content = json.dumps(body).encode() if not isinstance(body, bytes) else body
        with patch.dict(os.environ, {"TELEGRAM_ENABLED": "1"}), \
                patch.object(web, "TELEGRAM_TOKEN", "unit-test-private-token"), \
                patch.object(web, "TELEGRAM_CHAT_ID", "private-chat"), \
                patch.object(web.requests, "post", return_value=response) as post, \
                self.assertLogs(web.logger, level="WARNING") as logs:
            web.send_telegram_alert("private-message")
        post.assert_called_once()
        return "\n".join(logs.output)

    def test_http_errors_include_status_api_reason_and_rate_limit(self):
        for status, description in [(400,"Bad Request: chat not found"),
                                    (401,"Unauthorized"),
                                    (403,"Forbidden: bot was blocked by the user"),
                                    (429,"Too Many Requests"),
                                    (500,"Internal Server Error")]:
            with self.subTest(status=status):
                body = {"ok": False, "error_code": status, "description": description}
                if status == 429:
                    body["parameters"] = {"retry_after": 42}
                output = self.log_http_failure(status, body)
                self.assertIn(f"HTTP={status}", output)
                self.assertIn(f"error_code={status}", output)
                self.assertIn(description, output)
                if status == 429:
                    self.assertIn("retry_after=42s", output)

    def test_http_error_redacts_credentials_and_flattens_description(self):
        foreign_token = "123456789:" + "A" * 35
        body = {"ok": False, "error_code": 400, "description": (
            "Bad Request: private-chat unit-test-private-token "
            "https://api.telegram.org/botunit-test-private-token/sendMessage "
            + foreign_token + "\r\nFORGED LOG\x00")}
        output = self.log_http_failure(400, body)
        for value in ("private-chat", "unit-test-private-token", "api.telegram.org", foreign_token,
                      "private-message", "\r", "\n", "\x00"):
            self.assertNotIn(value, output)
        self.assertIn("Bad Request:", output)
        self.assertIn("HTTP=400", output)

    def test_non_json_error_and_unexpected_json_have_safe_fallback(self):
        for body in (b"<html>private-chat unit-test-private-token</html>", [],
                     {"description": {"secret": "unit-test-private-token"}},
                     {"description": "  ", "error_code": "unit-test-private-token"}):
            with self.subTest(body_type=type(body).__name__):
                output = self.log_http_failure(502, body)
                self.assertIn("HTTP=502", output)
                self.assertIn("Phản hồi không có mô tả lỗi JSON.", output)
                self.assertNotIn("unit-test-private-token", output)
                self.assertNotIn("private-chat", output)

    def test_url_encoded_credentials_are_redacted_before_truncation(self):
        with patch.object(web, "TELEGRAM_TOKEN", "unit-token:private"), \
                patch.object(web, "TELEGRAM_CHAT_ID", "@private-chat"), \
                self.assertLogs(web.logger, level="WARNING") as logs:
            response = Mock(status_code=400)
            response.json.return_value = {"description": "Error: " + quote("unit-token:private", safe="").replace('%3A','%3a') +
                                          " " + quote("@private-chat", safe="") + " " + "x" * 400}
            web.log_telegram_failure(response, "HTTPError")
        output = "\n".join(logs.output)
        for value in ("unit-token", "private-chat", "unit-token%3Aprivate", "%40private-chat"):
            self.assertNotIn(value, output)
        self.assertLess(len(output), 400)

    def test_missing_credentials_do_not_send_requests(self):
        for token, chat in [("", "123"), ("unit-test-token", ""), ("", "")]:
            with self.subTest(configured_token=bool(token), configured_chat=bool(chat)):
                with patch.dict(os.environ, {"TELEGRAM_ENABLED": "1"}), \
                        patch.object(web, "TELEGRAM_TOKEN", token), \
                        patch.object(web, "TELEGRAM_CHAT_ID", chat), \
                        patch.object(web.requests, "post") as post:
                    web.send_telegram_alert("test")
                    post.assert_not_called()

    def test_disabled_telegram_never_sends_or_starts_a_task(self):
        with patch.dict(os.environ, {"TELEGRAM_ENABLED": "0"}), \
                patch.object(web, "TELEGRAM_TOKEN", "unit-test-token"), \
                patch.object(web, "TELEGRAM_CHAT_ID", "123"), \
                patch.object(web.requests, "post") as post, \
                patch.object(web.socketio, "start_background_task") as task:
            web.send_telegram_alert("test")
            web.notify("test")
            post.assert_not_called()
            task.assert_not_called()

    def test_configured_telegram_sends_with_timeout_and_checks_status(self):
        response = Mock()
        with patch.dict(os.environ, {"TELEGRAM_ENABLED": "1"}), \
                patch.object(web, "TELEGRAM_TOKEN", "unit-test-token"), \
                patch.object(web, "TELEGRAM_CHAT_ID", "123"), \
                patch.object(web.requests, "post", return_value=response) as post:
            web.send_telegram_alert("test")
            post.assert_called_once_with(
                "https://api.telegram.org/botunit-test-token/sendMessage",
                json={"chat_id": "123", "text": "test", "parse_mode": "HTML"},
                timeout=3,
            )
            response.raise_for_status.assert_called_once_with()

    def test_request_errors_do_not_leak_token_url_or_chat_in_logs(self):
        error = web.requests.RequestException(
            "https://api.telegram.org/botunit-test-private-token/sendMessage chat=private-chat")
        with patch.dict(os.environ, {"TELEGRAM_ENABLED": "1"}), \
                patch.object(web, "TELEGRAM_TOKEN", "unit-test-private-token"), \
                patch.object(web, "TELEGRAM_CHAT_ID", "private-chat"), \
                patch.object(web.requests, "post", side_effect=error), \
                self.assertLogs(web.logger, level="WARNING") as logs:
            web.send_telegram_alert("test")
        output = "\n".join(logs.output)
        self.assertIn("RequestException", output)
        for private_value in ["unit-test-private-token", "private-chat", "api.telegram.org"]:
            self.assertNotIn(private_value, output)

    def test_clean_deployment_boots_without_local_env_or_telegram_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = dict(os.environ)
            environment.pop("TELEGRAM_TOKEN", None)
            environment.pop("TELEGRAM_CHAT_ID", None)
            environment.update({
                "PYTHON_DOTENV_DISABLED": "1",
                "TELEGRAM_ENABLED": "0",
                "ROOM_DATABASE": str(Path(directory) / "clean.sqlite3"),
            })
            result = subprocess.run(
                [sys.executable, "-c", (
                    "import app; "
                    "assert not app.TELEGRAM_TOKEN; "
                    "assert not app.TELEGRAM_CHAT_ID; "
                    "assert app.app.test_client().get('/api/state').status_code == 200"
                )], cwd=web.BASE_DIR, env=environment,
                capture_output=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, "Fresh deployment could not start safely")


if __name__ == "__main__":
    unittest.main()
