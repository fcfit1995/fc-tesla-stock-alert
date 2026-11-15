
import os
import re
import json
import logging
import requests
from html import unescape
from pathlib import Path

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

SOURCES = {
    "Sıfır Tesla Model Y": (
        "https://www.tesla.com/tr_TR/inventory/new/my"
        "?arrangeby=plh&zip=34096&range=0"
    ),
    "Sertifikalı İkinci El Tesla Model Y": (
        "https://www.tesla.com/tr_TR/inventory/used/my"
        "?arrangeby=plh&zip=34096&range=0"
    ),
}

STATE_FILE = Path("seen.json")
VIN_PATTERN = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")


def telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        data={"chat_id": CHAT_ID, "text": message},
        timeout=20,
    )
    response.raise_for_status()


def load_seen():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_seen(seen):
    STATE_FILE.write_text(
        json.dumps(seen, ensure_ascii=False, indent=2)
    )


def scan_source(name, url, seen):
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0)"
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    html = unescape(response.text)
    vins = set(VIN_PATTERN.findall(html))

    if not vins:
        logging.warning(
            "%s: Sayfada VIN bulunamadı. "
            "Tesla sayfasının dinamik verileri ayrıca incelenmeli.",
            name,
        )
        return

    for vin in sorted(vins):
        key = f"{name}:{vin}"

        if key in seen:
            continue

        message = (
            f"🚗 YENİ TESLA STOKU!\n\n"
            f"Kategori: {name}\n"
            f"VIN: {vin}\n\n"
            f"İlan sayfası:\n{url}"
        )

        telegram(message)
        seen[key] = True
        logging.info("Yeni araç bildirildi: %s", vin)


def main():
    seen = load_seen()

    for name, url in SOURCES.items():
        try:
            scan_source(name, url, seen)
        except Exception:
            logging.exception("%s taranamadı", name)

    save_seen(seen)


if __name__ == "__main__":
    main()
