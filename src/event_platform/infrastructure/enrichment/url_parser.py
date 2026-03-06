"""URL and referrer parser adapter."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

import tldextract

_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=())


@dataclass(slots=True)
class UrlData:
    """Normalized URL enrichment output."""

    url_host: str | None
    url_path: str | None
    referrer_domain: str | None


def parse_url_fields(url: str | None, referrer: str | None) -> UrlData:
    """Extract host/path and referrer domain fields."""
    parsed_url = urlparse(url) if url else None
    parsed_referrer = urlparse(referrer) if referrer else None

    host = _clean(parsed_url.netloc) if parsed_url else None
    path = _clean(parsed_url.path) if parsed_url else None

    ref_host = _clean(parsed_referrer.netloc) if parsed_referrer else None
    referrer_domain = _registrable_domain(ref_host)

    return UrlData(url_host=host, url_path=path, referrer_domain=referrer_domain)


def _registrable_domain(host: str | None) -> str | None:
    if not host:
        return None
    extracted = _EXTRACTOR(host)
    candidate = extracted.registered_domain
    return _clean(candidate)


def _clean(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None

