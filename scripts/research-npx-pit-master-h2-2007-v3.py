#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2_SCRIPT = ROOT / "scripts/research-npx-pit-master-h2-2007-v2.py"
UA = {
    "User-Agent": "Kensuke Kawamura kensuke5704@gmail.com momentum-console research",
    "Accept": "text/plain,text/html,*/*",
    "Accept-Encoding": "identity",
}
EXPECTED = {
    "2007-07": (64, 64),
    "2007-08": (75, 139),
    "2007-09": (75, 181),
    "2007-10": (75, 205),
    "2007-11": (75, 205),
    "2007-12": (75, 205),
}
MIN_INTERVAL_SECONDS = 1.15
BACKOFF_SECONDS = (3, 6, 12, 24, 36, 48)
_last_request_at = 0.0


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


v2 = load_module("h2_2007_npx_pit_v2", V2_SCRIPT)
base = v2.base


def pace() -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < MIN_INTERVAL_SECONDS:
        time.sleep(MIN_INTERVAL_SECONDS - elapsed)
    _last_request_at = time.monotonic()


def fetch_text_official(url: str) -> str:
    if not url.startswith("https://www.sec.gov/Archives/"):
        raise RuntimeError(f"unexpected non-SEC filing URL: {url}")
    last_error: Exception | None = None
    max_attempts = len(BACKOFF_SECONDS) + 1
    for attempt in range(1, max_attempts + 1):
        pace()
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as response:
                payload = response.read(20_000_000)
            print(f"filing transport ok attempt={attempt} bytes={len(payload):,} url={url}", flush=True)
            return payload.decode("latin-1", "replace")
        except urllib.error.HTTPError as exc:
            last_error = exc
            transient = exc.code == 429 or 500 <= exc.code <= 599
            print(f"filing transport HTTP attempt={attempt}/{max_attempts} code={exc.code} url={url}", flush=True)
            if not transient or attempt >= max_attempts:
                break
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as exc:
            last_error = exc
            print(f"filing transport transient attempt={attempt}/{max_attempts} error={exc!r} url={url}", flush=True)
            if attempt >= max_attempts:
                break
        delay = BACKOFF_SECONDS[attempt - 1]
        print(f"filing transport retry same-url backoff={delay}s", flush=True)
        time.sleep(delay)
    raise RuntimeError(f"official SEC filing transport exhausted for {url}") from last_error


def preload_and_assert_selection():
    filings, index_sources = base.filing_index_2007()
    primary = [x for x in filings if x["form"] == "N-PX"]
    amendments = [x for x in filings if x["form"] == "N-PX/A"]
    if (len(filings), len(primary), len(amendments)) != (3512, 3409, 103):
        raise RuntimeError(
            "2007 N-PX inventory changed before filing transport retry: "
            f"got={(len(filings), len(primary), len(amendments))} expected={(3512, 3409, 103)}"
        )

    admitted = set()
    observed = {}
    for signal_month, as_of in base.SIGNALS:
        public_primary = [x for x in primary if x["dateFiled"] <= as_of]
        reps = base.representatives(public_primary)
        sampled = base.deterministic_quantile_sample(reps)
        broad = [x for x in reps if x["cik"] in base.BROAD_CIKS]
        selected = {base.source_key(x): x for x in sampled + broad}
        admitted.update(selected)
        observed[signal_month] = (len(selected), len(admitted))
    if observed != EXPECTED:
        raise RuntimeError(f"selected-source boundary changed before transport retry: got={observed} expected={EXPECTED}")
    print(f"PRETRANSPORT_SELECTION_ASSERT PASS inventory=3512 primary=3409 amendments=103 selection={observed}", flush=True)
    return filings, index_sources


def main() -> None:
    filings, index_sources = preload_and_assert_selection()
    base.filing_index_2007 = lambda: (filings, index_sources)
    base.pilot.fetch_text = fetch_text_official
    base.main()


if __name__ == "__main__":
    main()
