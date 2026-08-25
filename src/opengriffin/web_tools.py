"""Small, provider-neutral internet tools for the non-Claude chat path.

Search is delegated to Tavily. Page fetching is deliberately conservative:
only public HTTP(S) URLs are allowed, redirects are validated, responses are
bounded, and HTML is reduced to text before it reaches the model.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests

TAVILY_URL = "https://api.tavily.com/search"
MAX_RESULTS = 5
MAX_FETCH_BYTES = 1_500_000
MAX_TEXT_CHARS = 24_000
REQUEST_TIMEOUT = (5, 20)

WEB_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the public internet with Tavily. Use this for current "
                "facts, news, research, or when the user asks to browse. "
                "Return source URLs in the final answer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."},
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "description": "Number of sources to return.",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": (
                "Fetch and extract readable text from one public HTTP(S) page. "
                "Use a URL returned by web_search or a URL supplied by the user."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Public http(s) URL."},
                },
                "required": ["url"],
                "additionalProperties": False,
            },
        },
    },
]


class _TextExtractor(HTMLParser):
    _SKIP = {"script", "style", "noscript", "template", "svg"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self._SKIP:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)


def _html_to_text(body: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(body)
        text = "\n".join(parser.parts)
    except Exception:
        text = body
    return text[:MAX_TEXT_CHARS]


def _public_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("only public http(s) URLs are allowed")
    host = parsed.hostname.rstrip(".").lower()
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            addresses = [
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
            ]
        except OSError as exc:
            raise ValueError("could not resolve URL host") from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("private, loopback, reserved, or link-local hosts are blocked")
    return parsed.geturl()


def _tavily_search(query: str, max_results: int = MAX_RESULTS) -> str:
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not key:
        return "web_search unavailable: TAVILY_API_KEY is not configured"
    query = query.strip()
    if not query:
        return "web_search requires a non-empty query"
    payload = {
        "api_key": key,
        "query": query[:500],
        "search_depth": "advanced",
        "max_results": max(1, min(int(max_results), 10)),
        "include_answer": False,
        "include_raw_content": False,
    }
    try:
        response = requests.post(TAVILY_URL, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        return f"web_search failed: {type(exc).__name__}"
    rows = []
    for item in data.get("results", [])[:10]:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        rows.append(
            {
                "title": str(item.get("title") or "")[:300],
                "url": str(item["url"])[:1000],
                "content": str(item.get("content") or "")[:1800],
            }
        )
    if not rows:
        return "web_search returned no results"
    return json.dumps({"query": query, "results": rows}, ensure_ascii=False)


def _fetch_page(url: str) -> str:
    current = _public_url(url)
    headers = {"User-Agent": "OpenGriffin/0.1 (+public-web-fetch)"}
    try:
        for _ in range(4):
            response = requests.get(
                current,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                stream=True,
                allow_redirects=False,
            )
            if response.is_redirect:
                location = response.headers.get("Location")
                if not location:
                    return "web_fetch failed: redirect without Location"
                current = _public_url(urljoin(current, location))
                continue
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(8192):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_FETCH_BYTES:
                    break
                chunks.append(chunk)
            raw = b"".join(chunks)
            encoding = response.encoding or "utf-8"
            body = raw.decode(encoding, errors="replace")
            text = _html_to_text(body) if "html" in content_type else body[:MAX_TEXT_CHARS]
            return json.dumps(
                {
                    "url": current,
                    "status": response.status_code,
                    "content_type": content_type,
                    "text": text,
                },
                ensure_ascii=False,
            )
        return "web_fetch failed: too many redirects"
    except (requests.RequestException, ValueError) as exc:
        return f"web_fetch failed: {type(exc).__name__}"


async def run_web_tool(name: str, arguments: dict) -> str:
    """Dispatch a model tool call without blocking the Telegram event loop."""
    if name == "web_search":
        return await asyncio.to_thread(
            _tavily_search,
            str(arguments.get("query") or ""),
            int(arguments.get("max_results", MAX_RESULTS)),
        )
    if name == "web_fetch":
        return await asyncio.to_thread(_fetch_page, str(arguments.get("url") or ""))
    return f"unknown web tool: {name}"


__all__ = ["WEB_TOOLS", "run_web_tool", "_html_to_text", "_public_url"]
