## notifier/telegram_bot.py
## Sends motion-alert messages and video clips to the owner via the Telegram Bot API.
## Uses only the stdlib urllib so no extra install is needed beyond requests (optional).
## All network calls run on a background daemon thread — the event loop is never blocked.

import json
import logging
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

## Base URL for the Telegram Bot API
_TELEGRAM_API_BASE: str = "https://api.telegram.org/bot{token}/{method}"


class TelegramNotifier:
    ## Dispatches alert messages and video clips to a Telegram chat.

    def __init__(self, bot_token: str, chat_id: str) -> None:
        ## Guard Clause: token must be a non-empty string
        if not isinstance(bot_token, str) or not bot_token.strip():
            raise ValueError(
                "[ERROR] Telegram bot_token is empty. "
                "Set the BLACKEYE_TELEGRAM_TOKEN environment variable."
            )

        ## Guard Clause: chat_id must be a non-empty string
        if not isinstance(chat_id, str) or not chat_id.strip():
            raise ValueError(
                "[ERROR] Telegram chat_id is empty. "
                "Set the BLACKEYE_TELEGRAM_CHAT_ID environment variable."
            )

        self._bot_token: str = bot_token.strip()
        self._chat_id: str = chat_id.strip()
        logging.info(f"TelegramNotifier initialized (chat_id: {self._chat_id})")

    @classmethod
    def from_env(cls) -> "TelegramNotifier":
        ## Factory: reads credentials from environment variables.
        ## Raises ValueError if either variable is not set.
        token = os.environ.get("BLACKEYE_TELEGRAM_TOKEN", "").strip()
        chat_id = os.environ.get("BLACKEYE_TELEGRAM_CHAT_ID", "").strip()
        return cls(bot_token=token, chat_id=chat_id)

    # ── Public API ─────────────────────────────────────────────────────────────

    def send_alert(self, message: str, video_path: Optional[str] = None) -> None:
        ## Fire-and-forget: dispatches the notification on a background thread.
        thread = threading.Thread(
            target=self._dispatch,
            args=(message, video_path),
            daemon=True,
            name="TelegramNotifier-Thread",
        )
        thread.start()

    # ── Private helpers ────────────────────────────────────────────────────────

    def _dispatch(self, message: str, video_path: Optional[str]) -> None:
        ## Runs on the background thread: sends text first, then video if provided.
        self._send_message(message)

        ## Guard Clause: skip video upload if no path provided
        if video_path is None:
            return

        video_file = Path(video_path)

        ## Guard Clause: skip video upload if file does not exist
        if not video_file.is_file():
            logging.warning(f"TelegramNotifier: video file not found, skipping upload: {video_path}")
            return

        self._send_video(video_file)

    def _send_message(self, text: str) -> None:
        ## Sends a plain text message via sendMessage.
        url = _TELEGRAM_API_BASE.format(token=self._bot_token, method="sendMessage")
        payload = json.dumps({
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "HTML",
        }).encode("utf-8")

        self._post_json(url, payload, label="sendMessage")

    def _send_video(self, video_file: Path) -> None:
        ## Sends an MP4 file via sendVideo using multipart/form-data.
        url = _TELEGRAM_API_BASE.format(token=self._bot_token, method="sendVideo")

        try:
            boundary = "BlackEyeBoundary"
            body_parts: list[bytes] = []

            ## chat_id field
            body_parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n"
                f"{self._chat_id}\r\n".encode("utf-8")
            )

            ## caption field
            caption = f"🎥 BlackEye clip: <code>{video_file.name}</code>"
            body_parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n"
                f"Content-Type: text/plain; charset=utf-8\r\n\r\n"
                f"{caption}\r\n".encode("utf-8")
            )

            ## parse_mode field
            body_parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\n"
                f"HTML\r\n".encode("utf-8")
            )

            ## video file field
            with video_file.open("rb") as fh:
                video_bytes = fh.read()

            body_parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"video\"; "
                f"filename=\"{video_file.name}\"\r\nContent-Type: video/mp4\r\n\r\n".encode("utf-8")
                + video_bytes
                + b"\r\n"
            )

            body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
            body = b"".join(body_parts)

            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                if resp.status == 200:
                    logging.info(f"TelegramNotifier: video uploaded successfully ({video_file.name})")
                else:
                    logging.error(f"TelegramNotifier: sendVideo returned HTTP {resp.status}")

        except Exception as exc:
            logging.error(f"TelegramNotifier: error uploading video: {exc}")

    def _post_json(self, url: str, payload: bytes, label: str) -> None:
        ## Generic JSON POST with error handling.
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    logging.info(f"TelegramNotifier: {label} sent successfully.")
                else:
                    logging.error(f"TelegramNotifier: {label} returned HTTP {resp.status}")

        except urllib.error.URLError as exc:
            logging.error(f"TelegramNotifier: network error during {label}: {exc}")
        except Exception as exc:
            logging.error(f"TelegramNotifier: unexpected error during {label}: {exc}")
