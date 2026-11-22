# BlackEye — User Manual

> **Versie:** 1.0  
> **Doelplatform:** Raspberry Pi Zero 2 W · Raspberry Pi OS (64-bit Lite)  
> **Laatste update:** November 2026

---

## Inhoudsopgave

1. [Overzicht](#1-overzicht)
2. [Hardware benodigdheden](#2-hardware-benodigdheden)
3. [Hardware aansluiten](#3-hardware-aansluiten)
4. [Raspberry Pi OS installeren](#4-raspberry-pi-os-installeren)
5. [BlackEye installeren](#5-blackeye-installeren)
6. [Telegram-bot instellen](#6-telegram-bot-instellen)
7. [BlackEye starten](#7-blackeye-starten)
8. [Autostart bij opstarten](#8-autostart-bij-opstarten)
9. [Configuratie aanpassen](#9-configuratie-aanpassen)
10. [Hoe het systeem werkt](#10-hoe-het-systeem-werkt)
11. [Opnames terugvinden](#11-opnames-terugvinden)
12. [Problemen oplossen](#12-problemen-oplossen)
13. [Veiligheid & privacy](#13-veiligheid--privacy)

---

## 1. Overzicht

BlackEye is een standalone surveillance-systeem dat:

- **Automatisch opneemt** zodra de PIR-sensor beweging detecteert
- **Audio en video combineert** tot één `.mp4`-bestand via FFmpeg
- **Direct een notificatie stuurt** via Telegram, inclusief de videoclip
- **Geen cloud-afhankelijkheid** heeft — alles draait lokaal op de Pi

```
Beweging gedetecteerd
       │
       ▼
  Audio + Video starten ──► Beweging stopt
                                  │
                                  ▼
                         FFmpeg mux → capture.mp4
                                  │
                                  ▼
                       Telegram: tekst + video
```

---

## 2. Hardware benodigdheden

| # | Onderdeel | Specificatie |
|---|-----------|-------------|
| 1 | Raspberry Pi Zero 2 W | Koop de **WH**-variant (met headers) |
| 2 | Pi Camera Module v2 of v3 | v3 heeft autofocus en betere low-light |
| 3 | CSI lint-kabel 15→22 pin | Speciaal voor Pi Zero — de standaardkabel past niet |
| 4 | AM312 PIR mini-sensor | Precies de sensor waarvoor de code gebouwd is |
| 5 | USB mini-microfoon | USB-audio (geen 3,5 mm jack — Pi Zero heeft die niet) |
| 6 | Micro-USB OTG-adapter | Om de USB-microfoon aan te sluiten |
| 7 | MicroSD-kaart ≥ 32 GB (A1) | SanDisk Endurance of Samsung Pro Endurance |
| 8 | 5V / 2,5 A voeding (micro-USB) | Minder stroom = willekeurige crashes |
| 9 | 3× jumper wires (female-female) | Voor de PIR-sensor |

---

## 3. Hardware aansluiten

### 3.1 AM312 PIR-sensor

De AM312 heeft drie pinnen. Sluit ze als volgt aan op de Pi Zero 2 W GPIO-header:

```
AM312-pin    →   Pi Zero 2 W (fysieke pin)   BCM-naam
─────────────────────────────────────────────────────
VCC          →   Pin 1   (3,3 V)
OUT          →   Pin 11  (GPIO 17)           ← ingesteld in settings.py
GND          →   Pin 6   (GND)
```

> **Let op:** De AM312 werkt op 3,3 V. Gebruik **nooit** de 5 V-pin — dit beschadigt de sensor.

### 3.2 Pi Camera Module

1. Klap de CSI-poort (kleine zwarte klem naast de HDMI-poort) voorzichtig omhoog
2. Schuif het 22-pins uiteinde van de lint-kabel erin (contacten naar de HDMI-kant)
3. Klap de klem terug omlaag en druk stevig aan
4. Het andere uiteinde (15-pins) gaat in de camera-module

### 3.3 USB-microfoon

Sluit de USB-microfoon aan via de OTG-adapter op de **data** micro-USB-poort (de poort dichter bij het midden van de Pi). De poort dichter bij de rand is **alleen voor stroom**.

---

## 4. Raspberry Pi OS installeren

1. Download **Raspberry Pi Imager** via [raspberrypi.com/software](https://www.raspberrypi.com/software/)
2. Kies OS: **Raspberry Pi OS Lite (64-bit)**
3. Klik het tandwiel-icoon ⚙️ en stel in:
   - Hostname: `blackeye`
   - SSH inschakelen (met wachtwoord of SSH-sleutel)
   - Wi-Fi SSID en wachtwoord
   - Gebruikersnaam: `pi`
4. Flash naar de microSD-kaart
5. Plaats de kaart in de Pi en start op

Verbind via SSH zodra de Pi op het netwerk staat:
```bash
ssh pi@blackeye.local
```

---

## 5. BlackEye installeren

```bash
# Kloon de repository
git clone https://github.com/D-Jaystar/Project-Black-Eye.git
cd Project-Black-Eye

# Voer het installatiescript uit (installeert alle dependencies automatisch)
bash install.sh
```

Het script doet het volgende:
- `sudo apt install ffmpeg python3-picamera2` — systeempakketten
- `pip3 install -r requirements.txt` — Python-pakketten
- Maakt de `.env`-configuratiefile aan
- Maakt de `recordings/`-map aan
- Installeert en enabled de `blackeye.service` systemd-eenheid

---

## 6. Telegram-bot instellen

### Stap 1 — Bot aanmaken

1. Open Telegram en zoek **@BotFather**
2. Stuur: `/newbot`
3. Geef een naam (bijv. `BlackEye Alert`) en een gebruikersnaam (bijv. `blackeye_mijnhuis_bot`)
4. Kopieer het **token** dat BotFather teruggeeft — het ziet eruit als: `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ`

### Stap 2 — Jouw chat-ID vinden

1. Zoek **@userinfobot** op Telegram
2. Stuur `/start` — de bot antwoordt met jouw numerieke **Id** (bijv. `987654321`)

### Stap 3 — Bot activeren

Stuur minimaal één bericht naar jouw eigen bot (zoek hem op via de gebruikersnaam), anders kan hij je geen berichten sturen.

### Stap 4 — Credentials invullen

```bash
nano /home/pi/Project-Black-Eye/.env
```

Vul in:
```
BLACKEYE_TELEGRAM_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
BLACKEYE_TELEGRAM_CHAT_ID=987654321
```

Sla op met `Ctrl+O`, sluit met `Ctrl+X`.

---

## 7. BlackEye starten

### Handmatig (testen)

```bash
cd /home/pi/Project-Black-Eye
python3 main.py
```

Je ziet log-output zoals:
```
2026-11-22 01:00:00 [INFO]  AudioRecorder initialized (Sample Rate: 44100Hz, Channels: 1)
2026-11-22 01:00:00 [INFO]  VideoRecorder initialized (1280x720 @ 30fps)
2026-11-22 01:00:00 [INFO]  MediaMuxer initialized (ffmpeg found on PATH)
2026-11-22 01:00:00 [INFO]  TelegramNotifier initialized (chat_id: 987654321)
2026-11-22 01:00:00 [INFO]  Controller initialized
2026-11-22 01:00:00 [INFO]  System armed. Motion detection active.
2026-11-22 01:00:00 [INFO]  BlackEye is running. Waiting for events...
```

Stop met `Ctrl+C`.

### Als systemd-service

```bash
sudo systemctl start blackeye
```

---

## 8. Autostart bij opstarten

De installatie heeft de service al enabled. Controleer de status:

```bash
sudo systemctl status blackeye
```

Logs live bekijken:
```bash
journalctl -u blackeye -f
```

Handmatig stoppen / herstarten:
```bash
sudo systemctl stop blackeye
sudo systemctl restart blackeye
```

Autostart uitschakelen (bijv. voor onderhoud):
```bash
sudo systemctl disable blackeye
```

---

## 9. Configuratie aanpassen

Alle parameters staan in [`config/settings.py`](config/settings.py). Pas waarden aan en herstart de service daarna.

| Instelling | Standaard | Omschrijving |
|-----------|-----------|-------------|
| `PIR_GPIO_PIN` | `17` | BCM GPIO-pin voor de PIR-sensor |
| `AUDIO_SAMPLE_RATE` | `44100` | Sample rate in Hz (16000 = kleiner bestand) |
| `AUDIO_CHANNELS` | `1` | 1 = mono, 2 = stereo |
| `VIDEO_WIDTH` | `1280` | Breedte in pixels |
| `VIDEO_HEIGHT` | `720` | Hoogte in pixels |
| `VIDEO_FRAMERATE` | `30` | Frames per seconde |
| `RECORDINGS_DIR` | `recordings/` | Map voor lokale opslag |
| `LOG_LEVEL` | `INFO` | `DEBUG` voor meer detail |

> **Tip:** Verlaag `VIDEO_WIDTH` naar `640` en `VIDEO_HEIGHT` naar `480` voor kleinere bestanden en minder CPU-gebruik op de Pi Zero.

---

## 10. Hoe het systeem werkt

### Toestandsmachine

BlackEye draait een strikte Finite State Machine met vier toestanden:

```
DISARMED ──arm()──► ARMED
                      │
              beweging detectie
                      │
                      ▼
                  RECORDING
                      │
              beweging gestopt
                      │
                      ▼
                  ALERTING ──acknowledge_alert()──► ARMED
```

### Wat er bij elke overgang gebeurt

| Overgang | Wat er uitvoert |
|----------|----------------|
| DISARMED → ARMED | PIR-sensor geactiveerd via GPIO-interrupt |
| ARMED → RECORDING | AudioRecorder + VideoRecorder starten gelijktijdig |
| RECORDING → ALERTING | Beide recorders stoppen; FFmpeg mux start in achtergrond |
| Mux klaar | Telegram: tekst + videoclip |
| ALERTING → ARMED | `acknowledge_alert()` reset alle paden |

### Bestandsnamen

Alle bestanden voor één sessie delen dezelfde timestamp-stam:
```
recordings/
├── audio_20261122_010000.wav      ← ruwe audio
├── video_20261122_010000.h264     ← ruwe video
└── capture_20261122_010000.mp4   ← definitieve clip (Telegram-bijlage)
```

---

## 11. Opnames terugvinden

Opnames staan in de `recordings/`-map op de Pi:

```bash
ls -lh /home/pi/Project-Black-Eye/recordings/
```

Kopieer een clip naar je computer:
```bash
scp pi@blackeye.local:/home/pi/Project-Black-Eye/recordings/capture_*.mp4 ~/Downloads/
```

Of bekijk ze rechtstreeks via Telegram — de bot stuurt elke clip automatisch.

> **Let op:** De `recordings/`-map staat in `.gitignore` en wordt nooit naar GitHub gepusht.

---

## 12. Problemen oplossen

### Camera wordt niet gevonden

```bash
# Controleer of de camera herkend wordt
libcamera-hello --list-cameras
```

Als er geen camera verschijnt:
- Controleer of de lint-kabel goed vastzit aan beide kanten
- Zorg dat de camera ingeschakeld is: `sudo raspi-config` → Interface Options → Camera

### Microfoon werkt niet

```bash
# Lijst alle audio-apparaten
python3 -c "import sounddevice; print(sounddevice.query_devices())"
```

Als de USB-mic niet in de lijst staat, controleer dan de OTG-aansluiting en probeer:
```bash
arecord -l
```

### Telegram-berichten komen niet aan

1. Controleer of de `.env`-waarden correct zijn
2. Test de verbinding handmatig:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getMe"
   ```
3. Zorg dat je de bot **eerst een bericht hebt gestuurd** voordat hij jou kan bereiken

### FFmpeg niet gevonden

```bash
sudo apt install ffmpeg
ffmpeg -version  # bevestig installatie
```

### Service start niet op

```bash
journalctl -u blackeye -n 50 --no-pager
```

Zoek naar `ERROR` of `Traceback` in de output voor de oorzaak.

### Pi crasht tijdens opname

Mogelijke oorzaken:
- **Onderspanning** — gebruik een voeding van minimaal 2,5 A
- **MicroSD te traag** — gebruik een A1-rated kaart
- Controleer de spanning-indicator: `vcgencmd get_throttled` (output `0x0` = alles OK)

---

## 13. Veiligheid & privacy

> [!CAUTION]
> Gebruik BlackEye alleen op locaties waarvoor je de eigenaar bent of expliciete toestemming hebt. Heimelijk filmen van personen zonder toestemming is in Nederland strafbaar.

**Beveiligingstips:**
- Sla het Telegram-token **nooit op in Git** — gebruik altijd de `.env`-file
- Zorg dat SSH alleen via sleutels werkt (geen wachtwoord): `ssh-copy-id pi@blackeye.local`
- Houd Raspberry Pi OS up-to-date: `sudo apt upgrade`
- De `recordings/`-map staat in `.gitignore` en wordt nooit gepubliceerd

---

*BlackEye — gebouwd met Python, gpiozero, Picamera2, sounddevice en FFmpeg.*
