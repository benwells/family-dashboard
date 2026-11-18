# Family dashboard

A full-screen page for a TV or a countertop screen: clock and date, live weather, the silver spot price, Charleston Harbor tides, sunrise and sunset, and a "Heads up" board of school events and things to bring.

## How the private part stays private

The site is public, but the school info is not readable on it. It's published only as `school-data.enc.json`, encrypted with AES-256-GCM using a key derived from a passphrase (PBKDF2-SHA256). The page decrypts it in the browser with the passphrase in the link:

```
https://<site>/#k=word-word-word-word-word
```

Everything after `#` stays in the browser. It is never sent to the web server. A screen that has opened the full link once remembers the passphrase, so the plain address works on it afterwards.

## Files

| File | What it is |
|---|---|
| `index.html` | The dashboard |
| `school-data.enc.json` | Encrypted school events and reminders, re-read every 30 minutes |
| `tools/schoolcrypt.py` | Encrypts, decrypts and checks the school data |

`school-data.json` (plain text) is in `.gitignore` and never committed.

## Updating the school data

```sh
pip install cryptography
export DASH_PASS='word-word-word-word-word'
python3 tools/schoolcrypt.py decrypt > school-data.json   # get the current data
# edit school-data.json
python3 tools/schoolcrypt.py encrypt school-data.json     # checks it, then writes school-data.enc.json
git commit -am "Update school info" && git push
```

`check` refuses bad dates, unknown event types and duplicate reminder ids before anything is encrypted.

## Live data

| Panel | Source | Refresh |
|---|---|---|
| Weather | Open-Meteo, no key | 15 min |
| Silver | gold-api.com, no key | 10 min |
| Tides | NOAA station 8665530 | 3 hours |
| Day and night colors | Sunrise and sunset | automatic |

## On the screen

- Tap the clock to go full screen (Fully Kiosk is already full screen on the TV).
- Tap a reminder under Today to mark it done for the day.
- Add `?mode=night` or `?mode=day` before the `#` to force a color scheme.
- The page reloads itself at 3:05 AM to pick up code changes.

## Data format

```js
{ updated, family, kids: { key: { name, class, color } },
  events: [{ date, end?, time?, title, detail?, bring?, wear?, who: [kid key | "all" | "family"],
             type: "noschool" | "early" | "event" | "bring" | "wear" | "homework", countdown? }],
  todos:  [{ id, title, detail?, who, type, from?, until? }] }
```
