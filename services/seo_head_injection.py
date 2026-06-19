"""
SSR placeholder injection for SPA index.html.

Placeholders use the form:
  <!--SSR:KEY-->default value<!--/SSR:KEY-->
"""
from __future__ import annotations

import html
import re
from typing import Dict, Iterable, Set

_SSR_PATTERN = re.compile(
    r"<!--SSR:(?P<key>[A-Z0-9_]+)-->.*?<!--/SSR:\1-->",
    re.DOTALL,
)


def replace_ssr_placeholder(content: str, key: str, value: str) -> str:
    escaped = html.escape(str(value), quote=True)
    pattern = re.compile(
        rf"<!--SSR:{re.escape(key)}-->.*?<!--/SSR:{key}-->",
        re.DOTALL,
    )
    if not pattern.search(content):
        raise KeyError(f"SSR placeholder not found: {key}")
    return pattern.sub(escaped, content, count=1)


def replace_ssr_placeholder_raw(content: str, key: str, value: str) -> str:
    pattern = re.compile(
        rf"<!--SSR:{re.escape(key)}-->.*?<!--/SSR:{key}-->",
        re.DOTALL,
    )
    if not pattern.search(content):
        raise KeyError(f"SSR placeholder not found: {key}")
    return pattern.sub(value, content, count=1)


def inject_ssr_fields(
    content: str,
    fields: Dict[str, str],
    *,
    raw_keys: Iterable[str] = (),
) -> str:
    raw_key_set: Set[str] = set(raw_keys)
    for key, value in fields.items():
        if key in raw_key_set:
            content = replace_ssr_placeholder_raw(content, key, value)
        else:
            content = replace_ssr_placeholder(content, key, value)
    return content


def assert_no_ssr_placeholders_remain(content: str) -> None:
    if "<!--SSR:" in content:
        unresolved = sorted({match.group("key") for match in _SSR_PATTERN.finditer(content)})
        raise ValueError(f"Unresolved SSR placeholders remain: {unresolved}")
