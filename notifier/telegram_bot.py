## notifier/telegram_bot.py
## Sends motion-alert messages and video clips to the owner via the Telegram Bot API.
## Also listens for incoming commands (/update, /status, /heartbeat) via long-polling.
## Uses only stdlib urllib — no extra pip package needed.
## All network calls run on background daemon threads — the event loop is never blocked.

import json
import logging
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Dict, Optional

## Base URL for the Telegram Bot API
_TELEGRAM_API_BASE: str = "https://api.telegram.org/bot{token}/{method}"

## Type alias for command handler functions
CommandHandler = Callable[[], str]


class TelegramNotifier:
    ## Dispatches alert messages and video clips to a Telegram chat.
    ## Optionally runs a command listener that handles /update, /status, /heartbeat.

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

        ## Command registry: maps "/command" → handler function returning reply string
        self._commands: Dict[str, CommandHandler] = {}

        ## Long-polling state
        self._polling_thread: Optional[threading.Thread] = None
        self._polling_active: bool = False
        self._last_update_id: int = 0

        logging.info(f"TelegramNotifier initialized (chat_id: {self._chat_id})")

    @classmethod
    def from_env(cls) -> "TelegramNotifier":
        ## Factory: reads credentials from environment variables.
        token = os.environ.get("BLACKEYE_TELEGRAM_TOKEN", "").strip()
        chat_id = os.environ.get("BLACKEYE_TELEGRAM_CHAT_ID", "").strip()
        return cls(bot_token=token, chat_id=chat_id)

    # ── Command listener ───────────────────────────────────────────────────────

    def register_command(self, command: str, handler: CommandHandler) -> None:
        ## Register a handler for an incoming Telegram command (e.g. "/update").
        ## handler() must return the reply string to send back.
        self._commands[command.lower()] = handler

    def start_command_listener(self) -> None:
        ## Start a background thread that long-polls Telegram for incoming commands.
        ## Guard Clause: do not start twice
        if self._polling_active:
            logging.warning("TelegramNotifier: command listener is already running.")
            return

        self._polling_active = True
        self._polling_thread = threading.Thread(
            target=self._poll_loop,
            daemon=True,
            name="TelegramCommander-Thread",
        )
        self._polling_thread.start()
        logging.info("TelegramNotifier: command listener started.")

    def stop_command_listener(self) -> None:
        self._polling_active = False
        logging.info("TelegramNotifier: command listener stopped.")

    def _poll_loop(self) -> None:
        ## Long-polling loop: asks Telegram for new messages every 30 seconds.
        ## Only processes messages from the authorised chat_id — all others are ignored.
        while self._polling_active:
            try:
                url = _TELEGRAM_API_BASE.format(token=self._bot_token, method="getUpdates")
                params = json.dumps({
                    "offset": self._last_update_id + 1,
                    "timeout": 30,
                    "allowed_updates": ["message"],
                }).encode("utf-8")

                req = urllib.request.Request(
                    url, data=params,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )

                with urllib.request.urlopen(req, timeout=40) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                for update in data.get("result", []):
                    self._last_update_id = update["update_id"]
                    self._handle_update(update)

            except Exception as exc:
                ## Network hiccup — wait 15 s before retrying
                logging.warning(f"TelegramNotifier: polling error ({exc}), retrying in 15 s...")
                time.sleep(15)

    def _handle_update(self, update: dict) -> None:
        ## Parse an incoming update and dispatch to the matching command handler.
        message = update.get("message", {})
        chat_id_str = str(message.get("chat", {}).get("id", ""))
        text: str = message.get("text", "").strip().lower()

        ## Guard Clause: only process messages from the authorised chat
        if chat_id_str != self._chat_id:
            logging.warning(f"TelegramNotifier: ignoring message from unknown chat {chat_id_str}")
            return

        ## Guard Clause: only process known commands
        if not text.startswith("/"):
            return

        ## Strip any @botname suffix (e.g. /update@mybot → /update)
        command = text.split("@")[0].split()[0]

        handler = self._commands.get(command)
        if handler is None:
            logging.info(f"TelegramNotifier: unknown command '{command}' — ignoring.")
            return

        logging.info(f"TelegramNotifier: executing command '{command}'")
        try:
            reply = handler()
            self._send_message(reply)
        except Exception as exc:
            self._send_message(f"❌ Command <code>{command}</code> failed: {exc}")

    # ── Public alert API ───────────────────────────────────────────────────────

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
        self._send_message(message)

        if video_path is None:
            return

        video_file = Path(video_path)
        if not video_file.is_file():
            logging.warning(f"TelegramNotifier: video file not found, skipping upload: {video_path}")
            return

        self._send_video(video_file)

    def _send_message(self, text: str) -> None:
        url = _TELEGRAM_API_BASE.format(token=self._bot_token, method="sendMessage")
        payload = json.dumps({
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "HTML",
        }).encode("utf-8")
        self._post_json(url, payload, label="sendMessage")

    def _send_video(self, video_file: Path) -> None:
        url = _TELEGRAM_API_BASE.format(token=self._bot_token, method="sendVideo")
        try:
            boundary = "BlackEyeBoundary"
            body_parts: list[bytes] = []

            body_parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n"
                f"{self._chat_id}\r\n".encode("utf-8")
            )
            caption = f"🎥 BlackEye clip: <code>{video_file.name}</code>"
            body_parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n"
                f"Content-Type: text/plain; charset=utf-8\r\n\r\n"
                f"{caption}\r\n".encode("utf-8")
            )
            body_parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\n"
                f"HTML\r\n".encode("utf-8")
            )
            with video_file.open("rb") as fh:
                video_bytes = fh.read()
            body_parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"video\"; "
                f"filename=\"{video_file.name}\"\r\nContent-Type: video/mp4\r\n\r\n".encode("utf-8")
                + video_bytes + b"\r\n"
            )
            body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
            body = b"".join(body_parts)

            req = urllib.request.Request(
                url, data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                if resp.status == 200:
                    logging.info(f"TelegramNotifier: video uploaded ({video_file.name})")
                else:
                    logging.error(f"TelegramNotifier: sendVideo returned HTTP {resp.status}")

        except Exception as exc:
            logging.error(f"TelegramNotifier: error uploading video: {exc}")

    def _post_json(self, url: str, payload: bytes, label: str) -> None:
        try:
            req = urllib.request.Request(
                url, data=payload,
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
