#!/usr/bin/env python3
"""Encrypt, decrypt and check the dashboard's school data.

The site is public, so school info is only ever published encrypted
(school-data.enc.json). The page decrypts it in the browser with the
passphrase that follows #k= in the dashboard link.

  DASH_PASS='word-word-word-word-word' python3 tools/schoolcrypt.py encrypt school-data.json
  DASH_PASS='...' python3 tools/schoolcrypt.py decrypt > school-data.json
  python3 tools/schoolcrypt.py check school-data.json
  python3 tools/schoolcrypt.py localjs school-data.json   # writes school-data.js for opening index.html from disk

Needs: pip install cryptography
"""
import base64
import json
import os
import re
import secrets
import sys

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ITER = 250_000
ENC_FILE = "school-data.enc.json"
TYPES = {"noschool", "early", "event", "bring", "wear", "homework"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _key(passphrase, salt, iterations=ITER):
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
    return kdf.derive(passphrase.encode())


def _b64(b):
    return base64.b64encode(b).decode()


def encrypt(data, passphrase):
    salt, iv = secrets.token_bytes(16), secrets.token_bytes(12)
    plain = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    ct = AESGCM(_key(passphrase, salt)).encrypt(iv, plain, None)
    return {"v": 1, "kdf": "pbkdf2-sha256", "iter": ITER, "salt": _b64(salt), "iv": _b64(iv), "ct": _b64(ct)}


def decrypt(enc, passphrase):
    key = _key(passphrase, base64.b64decode(enc["salt"]), enc["iter"])
    plain = AESGCM(key).decrypt(base64.b64decode(enc["iv"]), base64.b64decode(enc["ct"]), None)
    return json.loads(plain)


def check(data):
    """Return a list of problems; empty means the data is safe to publish."""
    errs = []
    kids = data.get("kids", {})
    allowed_who = set(kids) | {"all", "family"}
    if not isinstance(data.get("updated"), str):
        errs.append("missing 'updated' timestamp")
    for i, e in enumerate(data.get("events", [])):
        tag = f"events[{i}] {e.get('title', '?')!r}"
        for f in ("date", "title", "type", "who"):
            if f not in e:
                errs.append(f"{tag}: missing {f}")
        if "date" in e and not DATE.match(e["date"]):
            errs.append(f"{tag}: date must be YYYY-MM-DD")
        if "end" in e and (not DATE.match(e["end"]) or e["end"] < e.get("date", "")):
            errs.append(f"{tag}: bad end date")
        if e.get("type") not in TYPES:
            errs.append(f"{tag}: type must be one of {sorted(TYPES)}")
        for w in e.get("who", []):
            if w not in allowed_who:
                errs.append(f"{tag}: unknown who {w!r}")
    ids = set()
    for i, t in enumerate(data.get("todos", [])):
        tag = f"todos[{i}] {t.get('title', '?')!r}"
        for f in ("id", "title", "type", "who"):
            if f not in t:
                errs.append(f"{tag}: missing {f}")
        if t.get("id") in ids:
            errs.append(f"{tag}: duplicate id")
        ids.add(t.get("id"))
        for f in ("from", "until"):
            if f in t and not DATE.match(t[f]):
                errs.append(f"{tag}: {f} must be YYYY-MM-DD")
    return errs


def _pass():
    p = os.environ.get("DASH_PASS", "").strip()
    if not p:
        sys.exit("Set DASH_PASS to the dashboard passphrase.")
    return p


def main(argv):
    if len(argv) < 2 or argv[1] not in {"encrypt", "decrypt", "check", "localjs"}:
        sys.exit(__doc__)
    cmd = argv[1]
    if cmd == "decrypt":
        src = argv[2] if len(argv) > 2 else ENC_FILE
        print(json.dumps(decrypt(json.load(open(src)), _pass()), indent=2, ensure_ascii=False))
        return
    src = argv[2] if len(argv) > 2 else "school-data.json"
    data = json.load(open(src))
    problems = check(data)
    if problems:
        sys.exit("Not publishing, fix these first:\n  " + "\n  ".join(problems))
    if cmd == "check":
        print(f"OK: {len(data.get('events', []))} events, {len(data.get('todos', []))} reminders")
    elif cmd == "encrypt":
        out = argv[3] if len(argv) > 3 else ENC_FILE
        enc = encrypt(data, _pass())
        assert decrypt(enc, _pass()) == data  # round-trip before writing
        with open(out, "w") as f:
            json.dump(enc, f, indent=1)
            f.write("\n")
        print(f"Wrote {out}")
    elif cmd == "localjs":
        out = argv[3] if len(argv) > 3 else "school-data.js"
        with open(out, "w") as f:
            f.write("window.DASH_DATA = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n")
        print(f"Wrote {out}")


if __name__ == "__main__":
    main(sys.argv)
