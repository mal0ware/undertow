"""Download the public data into data/ (gitignored). No key, no account.

    uv run python scripts/fetch_data.py            # Binance archive files, about 0.9 GB
    uv run python scripts/fetch_data.py --fast     # one day only, about 0.2 GB

Archive files come from data.binance.vision and are verified against the SHA-256 checksum
file published next to each one. Nothing else is downloaded or recorded.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
import urllib.request
from pathlib import Path

from undertow.data import DAYS, KLINE_MONTHS, SYMBOL, archive_files

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://data.binance.vision/"
USER_AGENT = "undertow-research/0.1"


def _get(url: str, dest: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(request, timeout=120) as response, tmp.open("wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)
    tmp.replace(dest)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(key: str, dest: Path) -> None:
    """Download one archive file and verify it against the published checksum."""
    checksum_path = dest.with_suffix(dest.suffix + ".CHECKSUM")
    if not checksum_path.exists():
        _get(BASE + key + ".CHECKSUM", checksum_path)
    expected = checksum_path.read_text().split()[0]
    if dest.exists() and _sha256(dest) == expected:
        print(f"ok       {dest.name}")
        return
    start = time.time()
    _get(BASE + key, dest)
    if _sha256(dest) != expected:
        dest.unlink()
        raise SystemExit(f"checksum mismatch for {key}")
    size = dest.stat().st_size / 1e6
    print(f"fetched  {dest.name}  {size:.1f} MB  {time.time() - start:.0f}s")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--fast", action="store_true", help="first day only")
    args = parser.parse_args()

    raw = ROOT / "data" / "binance"
    raw.mkdir(parents=True, exist_ok=True)
    days = DAYS[:1] if args.fast else DAYS
    for key in archive_files(SYMBOL, days, KLINE_MONTHS):
        fetch(key, raw / key.rsplit("/", 1)[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
