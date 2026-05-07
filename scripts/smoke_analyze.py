"""
Synthetic probe for /api/analyze stream stability.

Usage:
  python scripts/smoke_analyze.py \
    --base-url https://aguai.net \
    --stock-code 600519 \
    --token "<JWT>"

Exit code:
  0 = success (received init + completed/error frame)
  2 = unhealthy (timeout or no stream payload)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Optional

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test /api/analyze stream")
    parser.add_argument("--base-url", default="https://aguai.net")
    parser.add_argument("--stock-code", default="600519")
    parser.add_argument("--market-type", default="A")
    parser.add_argument("--token", default="")
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    url = f"{args.base_url.rstrip('/')}/api/analyze"
    headers = {
        "Content-Type": "application/json",
        "X-Anonymous-Id": "synthetic-probe",
    }
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    payload = {"stock_codes": [args.stock_code], "market_type": args.market_type}
    start = time.time()
    got_init = False
    got_terminal = False
    chunks = 0

    try:
        with httpx.stream(
            "POST",
            url,
            headers=headers,
            json=payload,
            timeout=args.timeout_seconds,
        ) as response:
            if response.status_code != 200:
                print(f"[probe] non-200: {response.status_code}", flush=True)
                return 2

            for line in response.iter_lines():
                if not line:
                    continue
                chunks += 1
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if data.get("stream_type") in ("single", "batch"):
                    got_init = True
                if data.get("status") in ("completed", "error") or data.get("error"):
                    got_terminal = True
                    break

        elapsed = round((time.time() - start) * 1000, 2)
        print(
            json.dumps(
                {
                    "ok": got_init and got_terminal,
                    "elapsed_ms": elapsed,
                    "chunks": chunks,
                    "got_init": got_init,
                    "got_terminal": got_terminal,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        return 0 if got_init and got_terminal else 2
    except Exception as exc:
        print(f"[probe] exception: {exc}", flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
