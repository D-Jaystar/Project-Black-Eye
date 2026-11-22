# 🕵️ BlackEye

> **Stealth surveillance & security system voor Raspberry Pi Zero 2 W**  
> PIR-triggered video + audio capture → automatische Telegram-notificatie met videoclip

---

## Wat doet het?

BlackEye bewaakt een ruimte via een AM312 PIR-bewegingssensor. Zodra er beweging is:

1. **Detectie** — hardware-interrupt op GPIO 17 wekt het systeem
2. **Opname** — audio (WAV) en video (H.264) starten gelijktijdig
3. **Verwerking** — na bewegingsstop muxed FFmpeg beide streams naar één `.mp4`
4. **Notificatie** — de clip wordt direct als Telegram-bericht naar de eigenaar gestuurd

## Architectuur

```
StateMachine ──► DISARMED → ARMED → RECORDING → ALERTING
Controller   ──► koppelt PIR, AudioRecorder, VideoRecorder, MediaMuxer, TelegramNotifier
```

## Snelstart (Raspberry Pi)

```bash
git clone https://github.com/D-Jaystar/Project-Black-Eye.git
cd Project-Black-Eye
bash install.sh        # installeert alles automatisch
nano .env              # vul BLACKEYE_TELEGRAM_TOKEN en BLACKEYE_TELEGRAM_CHAT_ID in
sudo systemctl start blackeye
```

Logs bekijken:
```bash
journalctl -u blackeye -f
```

## Configuratie

Alle instellingen staan in [`config/settings.py`](config/settings.py):

| Constante | Standaard | Omschrijving |
|-----------|-----------|-------------|
| `PIR_GPIO_PIN` | `17` | BCM GPIO-pin voor AM312 |
| `AUDIO_SAMPLE_RATE` | `44100` | Sample rate in Hz |
| `VIDEO_WIDTH / HEIGHT` | `1280 × 720` | Camera resolutie |
| `VIDEO_FRAMERATE` | `30` | Frames per seconde |
| `RECORDINGS_DIR` | `recordings/` | Lokale opslag |

Telegram-credentials via omgevingsvariabelen (nooit in code):
```bash
export BLACKEYE_TELEGRAM_TOKEN="123456:ABC..."
export BLACKEYE_TELEGRAM_CHAT_ID="987654321"
```

## Project structuur

```
blackeye/
├── core/
│   ├── state_machine.py   # FSM: DISARMED / ARMED / RECORDING / ALERTING
│   └── controller.py      # Centrale orchestrator
├── detector/
│   └── pir_sensor.py      # HAL voor AM312 via gpiozero
├── capture/
│   ├── audio_recorder.py  # WAV-opname via sounddevice
│   ├── video_recorder.py  # H.264-opname via Picamera2
│   └── media_muxer.py     # WAV + H.264 → MP4 via FFmpeg
├── notifier/
│   └── telegram_bot.py    # Alert + video-upload via Telegram Bot API
├── config/
│   └── settings.py        # Centrale configuratie
├── main.py                # Entry point
├── install.sh             # Geautomatiseerde Pi-installatie
├── blackeye.service       # systemd unit voor autostart op boot
└── requirements.txt       # Python-afhankelijkheden
```

## Hardware

Zie [`USER_MANUAL.md`](USER_MANUAL.md) voor de volledige hardware-bestellijst en aansluitschema.

## Licentie

MIT
