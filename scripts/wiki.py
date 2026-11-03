"""Accès à Wikipedia avec cache disque (data/cache) pour ne télécharger qu'une fois."""
import hashlib
import json
import time
from pathlib import Path

import requests

UA = {"User-Agent": "comparaison-sport-dataviz/1.0 (personal project)"}
CACHE = Path(__file__).resolve().parent.parent / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)


def get(url, params=None, binary=False):
    key = hashlib.md5((url + json.dumps(params, sort_keys=True)).encode()).hexdigest()
    p = CACHE / key
    if p.exists():
        return p.read_bytes() if binary else p.read_text(encoding="utf-8")
    for i in range(4):
        r = requests.get(url, params=params, headers=UA, timeout=60)
        if r.status_code == 429 or (not binary and r.text.startswith("You are making too many")):
            attente = int(r.headers.get("Retry-After", 0) or 0)
            time.sleep(max(attente, 15 * (i + 1)))
            continue
        r.raise_for_status()
        break
    else:
        raise RuntimeError(f"limite de débit persistante : {url}")
    time.sleep(2 if binary else 1)
    if binary:
        p.write_bytes(r.content)
        return r.content
    p.write_text(r.text, encoding="utf-8")
    return r.text
