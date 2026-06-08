#!/usr/bin/env python3
"""Validate the privacy policy page before entering it in Play Console.

Use --local for the repository HTML source and --url after the owner hosts the
policy publicly. The URL mode is intentionally external and not required by the
local release verifier until the owner has a real HTTPS policy URL.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import re
import socket
import ssl
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_POLICY = ROOT / "play_store/privacy_policy_ru.html"

REQUIRED_TEXT_MARKERS = (
    "Линия 56",
    "не собирает",
    "не передаёт",
    "не продаёт",
    "локальные игровые данные",
    "Android backup",
    "аккаунты",
    "рекламу",
    "аналитику",
    "платежи",
    "Игра работает без обязательного подключения к интернету",
    "Пользователь может удалить локальные данные",
    "контакт поддержки разработчика",
    "Google Play",
)

FORBIDDEN_TEXT_MARKERS = (
    "contact-required",
    "replace-me",
    "TODO",
    "lorem ipsum",
    "example.com",
    "localhost",
    "127.0.0.1",
)

PLACEHOLDER_HOSTS = (
    "example.com",
    "example.org",
    "example.net",
)

RESERVED_HOST_SUFFIXES = (
    ".localhost",
    ".example",
    ".invalid",
    ".test",
    ".local",
)

PUBLIC_URL_ERROR_MARKER = "privacy policy URL must be public"

FORBIDDEN_HTML_MARKERS = (
    "<script",
    "<iframe",
    "document.cookie",
    "localstorage",
    "sessionstorage",
    "google-analytics",
    "googletagmanager",
    "gtag(",
    "metrica",
    "pixel",
)


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self.parts.append(stripped)

    @property
    def text(self) -> str:
        return " ".join(self.parts)


class PrivacyPolicyCheckError(RuntimeError):
    pass


def html_to_text(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    return re.sub(r"\s+", " ", parser.text).strip()


def canonical_policy_text(html: str) -> str:
    return html_to_text(html)


def canonical_text_sha256(html: str) -> str:
    return hashlib.sha256(canonical_policy_text(html).encode("utf-8")).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PrivacyPolicyCheckError(message)


def require_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address, source_label: str) -> None:
    public_message = PUBLIC_URL_ERROR_MARKER if source_label == "privacy policy URL" else f"{source_label} must be public"
    require(ip.is_global, f"{public_message}; {source_label} must resolve only to public global IPs, got {ip}")


def resolve_public_host(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise PrivacyPolicyCheckError(f"privacy policy URL host must resolve publicly: {host}") from exc
    resolved_ips = {
        ipaddress.ip_address(info[4][0])
        for info in infos
        if info[4] and info[4][0]
    }
    require(bool(resolved_ips), f"privacy policy URL host must resolve publicly: {host}")
    for ip in resolved_ips:
        require_public_ip(ip, "privacy policy URL host")


def reject_private_url(url: str, *, resolve_host: bool = True) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(url)
    require(parsed.scheme == "https", "privacy policy URL must use HTTPS")
    require(bool(parsed.netloc), "privacy policy URL must include a host")
    require(parsed.username is None and parsed.password is None, "privacy policy URL must not include credentials")
    require(parsed.query == "", "privacy policy URL must not include query parameters")
    require(parsed.fragment == "", "privacy policy URL must not include a fragment")
    host = parsed.hostname or ""
    lowered_host = host.lower()
    require(lowered_host not in {"localhost", "127.0.0.1", "::1"}, "privacy policy URL must not be localhost")
    require(lowered_host not in PLACEHOLDER_HOSTS, "privacy policy URL must not use a placeholder host")
    require(not any(lowered_host.endswith(suffix) for suffix in RESERVED_HOST_SUFFIXES), "privacy policy URL must not use a reserved local/test host")
    require(not parsed.path.lower().endswith(".pdf"), "privacy policy URL must not be a PDF path")
    try:
        ip = ipaddress.ip_address(lowered_host)
    except ValueError:
        if resolve_host:
            resolve_public_host(lowered_host)
    else:
        require_public_ip(ip, "privacy policy URL")
    return parsed


def fetch_url(url: str) -> tuple[str, str]:
    reject_private_url(url)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Line56PrivacyPolicyCheck/1.0"},
    )
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, timeout=20, context=context) as response:
        status = response.getcode()
        content_type = response.headers.get("content-type", "")
        final_url = response.geturl()
        require(status == 200, f"privacy policy URL must return HTTP 200, got {status}")
        reject_private_url(final_url)
        require(urllib.parse.urlparse(final_url).scheme == "https", "privacy policy final URL must stay HTTPS")
        require("pdf" not in content_type.lower(), "privacy policy must not be served as PDF")
        require(not urllib.parse.urlparse(final_url).path.lower().endswith(".pdf"), "privacy policy final URL must not be a PDF path")
        body = response.read(1024 * 1024 + 1)
        require(len(body) <= 1024 * 1024, "privacy policy page is unexpectedly large")
    try:
        html = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PrivacyPolicyCheckError("privacy policy page must be valid UTF-8") from exc
    return html, content_type


def validate_html(html: str, source_label: str, *, require_html_content_type: str | None = None) -> str:
    lowered = html.lower()
    require("<html" in lowered, f"{source_label} must look like HTML")
    require("<body" in lowered, f"{source_label} must include a body")
    if require_html_content_type is not None:
        content_type = require_html_content_type.lower()
        require(
            "text/html" in content_type or "application/xhtml+xml" in content_type or content_type == "",
            f"{source_label} should be served as HTML, got content-type {require_html_content_type!r}",
        )
    for marker in FORBIDDEN_HTML_MARKERS:
        require(marker not in lowered, f"{source_label} must not include scripts, trackers or embedded external widgets: {marker}")
    text = html_to_text(html)
    require(len(text) >= 500, f"{source_label} privacy text is too short")
    for marker in REQUIRED_TEXT_MARKERS:
        require(marker in text, f"{source_label} missing privacy marker: {marker}")
    lowered_text = text.lower()
    for marker in FORBIDDEN_TEXT_MARKERS:
        require(marker.lower() not in lowered_text, f"{source_label} contains forbidden placeholder/private marker: {marker}")
    require("не собирает" in text and "персональные данные" in text, f"{source_label} must say no personal data is collected")
    require("Android backup" in text and "отключён" in text, f"{source_label} must say Android backup is disabled")
    require("Google Play" in text and "контакт поддержки" in text, f"{source_label} must reference the Play listing support contact")
    return text


def require_matches_local_policy(hosted_html: str) -> None:
    local_html = LOCAL_POLICY.read_text(encoding="utf-8")
    local_text = canonical_policy_text(local_html)
    hosted_text = canonical_policy_text(hosted_html)
    require(
        hosted_text == local_text,
        "hosted privacy policy text must match play_store/privacy_policy_ru.html; re-upload the exact current HTML before Play Console entry",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Line 56 privacy policy HTML or public URL.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--local", action="store_true", help="Validate play_store/privacy_policy_ru.html.")
    group.add_argument("--url", help="Validate a public HTTPS privacy policy URL.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.local:
            html = LOCAL_POLICY.read_text(encoding="utf-8")
            validate_html(html, "local privacy policy")
            print(f"privacy_policy_text_sha256: {canonical_text_sha256(html)}")
            print("privacy_policy_local_ok")
        else:
            html, content_type = fetch_url(args.url)
            validate_html(html, "hosted privacy policy", require_html_content_type=content_type)
            require_matches_local_policy(html)
            print(f"privacy_policy_text_sha256: {canonical_text_sha256(html)}")
            print("privacy_policy_url_ok")
    except (OSError, PrivacyPolicyCheckError) as exc:
        print(f"privacy_policy_check_error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
