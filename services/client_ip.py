"""Resolve the visitor IP for rate limits and anonymous quota.

nginx overwrites X-Real-IP with $remote_addr, so that header is the edge
address. A client-supplied X-Forwarded-For is not trusted.
"""
from __future__ import annotations

from fastapi import Request


def resolve_client_ip(request: Request) -> str:
    raw = (request.headers.get("x-real-ip") or "").split(",")[0].strip()
    if not raw and request.client is not None:
        raw = (request.client.host or "").strip()
    if not raw or any(ch.isspace() for ch in raw):
        return "unknown"
    return raw[:64]
