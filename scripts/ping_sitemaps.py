#!/usr/bin/env python3
"""
Ping search engines with the site sitemap URL.

Usage:
  python scripts/ping_sitemaps.py
  python scripts/ping_sitemaps.py --base-url https://aguai.net

Notes:
- Baidu requires the site to be verified in 百度搜索资源平台 first.
- Google/Bing ping endpoints are best-effort and may change over time.
"""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.parse
import urllib.request


def ping(url: str, timeout: int = 20) -> tuple[bool, str]:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(500).decode("utf-8", errors="replace")
            return True, f"HTTP {response.status} {body[:200]}"
    except urllib.error.HTTPError as exc:
        body = exc.read(200).decode("utf-8", errors="replace")
        return False, f"HTTP {exc.code} {body[:200]}"
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ping sitemap to search engines")
    parser.add_argument("--base-url", default="https://aguai.net")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    sitemap_url = f"{base_url}/sitemap.xml"
    encoded = urllib.parse.quote(sitemap_url, safe="")

    targets = {
        "baidu": f"http://data.zz.baidu.com/ping?sitemap={encoded}",
        "google": f"https://www.google.com/ping?sitemap={encoded}",
        "bing": f"https://www.bing.com/ping?sitemap={encoded}",
    }

    print(f"Sitemap: {sitemap_url}")
    failed = 0
    for name, url in targets.items():
        ok, message = ping(url)
        status = "OK" if ok else "FAIL"
        print(f"[{status}] {name}: {message}")
        if not ok:
            failed += 1

    if failed:
        print("\n提示：百度需先在 https://ziyuan.baidu.com 完成站点验证并手动提交一次 sitemap。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
