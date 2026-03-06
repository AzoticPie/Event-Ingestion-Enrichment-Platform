"""GeoIP parser adapter."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import maxminddb


class GeoIpUnavailableError(RuntimeError):
    """Raised when GeoIP resource is unavailable due to infrastructure issues."""


@dataclass(slots=True)
class GeoData:
    """Normalized GeoIP enrichment output."""

    country: str | None


def parse_geo_country(ip: str | None, geoip_db_path: str) -> GeoData:
    """Lookup country code from GeoLite2 database when available."""
    if not ip:
        return GeoData(country=None)

    db_path = Path(geoip_db_path)
    if not db_path.exists():
        return GeoData(country=None)

    try:
        reader = _get_reader(str(db_path))
        record = reader.get(ip) or {}
    except OSError as exc:  # includes file and low-level IO errors
        raise GeoIpUnavailableError(f"GeoIP DB access failed: {exc}") from exc

    country = (record.get("country") or {}).get("iso_code") if isinstance(record, dict) else None
    if not isinstance(country, str):
        return GeoData(country=None)

    return GeoData(country=country.strip() or None)


@lru_cache(maxsize=4)
def _get_reader(db_path: str):
    return maxminddb.open_database(db_path)

