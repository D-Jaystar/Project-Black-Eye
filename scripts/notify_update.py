#!/usr/bin/env python3
## scripts/notify_update.py
## Minimal Telegram sender used by update.sh to report update results.
## Usage: python3 notify_update.py <token> <chat_id> <message>

import json
import sys
import urllib.request

def main() -> None:
    if len(sys.argv) < 4:
        print("Usage: notify_update.py <token> <chat_id> <message>")
        sys.exit(1)

    token, chat_id, message = sys.argv[1], sys.argv[2], sys.argv[3]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status != 200:
            print(f"Telegram error: HTTP {resp.status}")
            sys.exit(1)

if __name__ == "__main__":
    main()
