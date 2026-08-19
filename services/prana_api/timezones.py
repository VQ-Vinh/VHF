"""Country to IANA timezone mapping for user region settings.

Curated rather than derived: it only needs to cover countries PRANA ELEX is
operated from, and a short table keeps the picker on the app readable. Adding a
country is one line here -- the app reads the list from GET /v1/countries, so no
client change is needed.

Countries that span several zones list them in the order the picker should show
them; the first entry is what a client gets when it sends only a country code.
"""

from __future__ import annotations

from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

COUNTRY_TIMEZONES: dict[str, tuple[str, ...]] = {
    # Southeast Asia
    "VN": ("Asia/Ho_Chi_Minh",),
    "TH": ("Asia/Bangkok",),
    "SG": ("Asia/Singapore",),
    "MY": ("Asia/Kuala_Lumpur", "Asia/Kuching"),
    "ID": ("Asia/Jakarta", "Asia/Makassar", "Asia/Jayapura"),
    "PH": ("Asia/Manila",),
    "KH": ("Asia/Phnom_Penh",),
    "LA": ("Asia/Vientiane",),
    "MM": ("Asia/Yangon",),
    "BN": ("Asia/Brunei",),
    # East Asia
    "CN": ("Asia/Shanghai", "Asia/Urumqi"),
    "HK": ("Asia/Hong_Kong",),
    "TW": ("Asia/Taipei",),
    "JP": ("Asia/Tokyo",),
    "KR": ("Asia/Seoul",),
    "MO": ("Asia/Macau",),
    "MN": ("Asia/Ulaanbaatar",),
    # South and Central Asia
    "IN": ("Asia/Kolkata",),
    "BD": ("Asia/Dhaka",),
    "LK": ("Asia/Colombo",),
    "NP": ("Asia/Kathmandu",),
    "PK": ("Asia/Karachi",),
    # Middle East
    "AE": ("Asia/Dubai",),
    "SA": ("Asia/Riyadh",),
    "QA": ("Asia/Qatar",),
    "IL": ("Asia/Jerusalem",),
    "TR": ("Europe/Istanbul",),
    # Oceania
    "AU": (
        "Australia/Sydney",
        "Australia/Brisbane",
        "Australia/Adelaide",
        "Australia/Perth",
        "Australia/Darwin",
        "Australia/Hobart",
    ),
    "NZ": ("Pacific/Auckland",),
    "PG": ("Pacific/Port_Moresby",),
    "FJ": ("Pacific/Fiji",),
    # Europe
    "GB": ("Europe/London",),
    "IE": ("Europe/Dublin",),
    "FR": ("Europe/Paris",),
    "DE": ("Europe/Berlin",),
    "NL": ("Europe/Amsterdam",),
    "BE": ("Europe/Brussels",),
    "ES": ("Europe/Madrid", "Atlantic/Canary"),
    "PT": ("Europe/Lisbon", "Atlantic/Azores"),
    "IT": ("Europe/Rome",),
    "CH": ("Europe/Zurich",),
    "AT": ("Europe/Vienna",),
    "SE": ("Europe/Stockholm",),
    "NO": ("Europe/Oslo",),
    "DK": ("Europe/Copenhagen",),
    "FI": ("Europe/Helsinki",),
    "PL": ("Europe/Warsaw",),
    "CZ": ("Europe/Prague",),
    "GR": ("Europe/Athens",),
    "RO": ("Europe/Bucharest",),
    "UA": ("Europe/Kyiv",),
    "RU": (
        "Europe/Moscow",
        "Europe/Kaliningrad",
        "Asia/Yekaterinburg",
        "Asia/Novosibirsk",
        "Asia/Irkutsk",
        "Asia/Vladivostok",
        "Asia/Kamchatka",
    ),
    # Americas
    "US": (
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Phoenix",
        "America/Los_Angeles",
        "America/Anchorage",
        "Pacific/Honolulu",
    ),
    "CA": (
        "America/Toronto",
        "America/Winnipeg",
        "America/Edmonton",
        "America/Vancouver",
        "America/Halifax",
        "America/St_Johns",
    ),
    "MX": ("America/Mexico_City", "America/Tijuana", "America/Cancun"),
    "BR": ("America/Sao_Paulo", "America/Manaus", "America/Belem"),
    "AR": ("America/Argentina/Buenos_Aires",),
    "CL": ("America/Santiago",),
    "CO": ("America/Bogota",),
    "PE": ("America/Lima",),
    # Africa
    "ZA": ("Africa/Johannesburg",),
    "EG": ("Africa/Cairo",),
    "NG": ("Africa/Lagos",),
    "KE": ("Africa/Nairobi",),
    "MA": ("Africa/Casablanca",),
    # Fallback for anyone the table does not cover yet.
    "UN": ("UTC",),
}

COUNTRY_NAMES: dict[str, str] = {
    "VN": "Vietnam",
    "TH": "Thailand",
    "SG": "Singapore",
    "MY": "Malaysia",
    "ID": "Indonesia",
    "PH": "Philippines",
    "KH": "Cambodia",
    "LA": "Laos",
    "MM": "Myanmar",
    "BN": "Brunei",
    "CN": "China",
    "HK": "Hong Kong",
    "TW": "Taiwan",
    "JP": "Japan",
    "KR": "South Korea",
    "MO": "Macao",
    "MN": "Mongolia",
    "IN": "India",
    "BD": "Bangladesh",
    "LK": "Sri Lanka",
    "NP": "Nepal",
    "PK": "Pakistan",
    "AE": "United Arab Emirates",
    "SA": "Saudi Arabia",
    "QA": "Qatar",
    "IL": "Israel",
    "TR": "Turkey",
    "AU": "Australia",
    "NZ": "New Zealand",
    "PG": "Papua New Guinea",
    "FJ": "Fiji",
    "GB": "United Kingdom",
    "IE": "Ireland",
    "FR": "France",
    "DE": "Germany",
    "NL": "Netherlands",
    "BE": "Belgium",
    "ES": "Spain",
    "PT": "Portugal",
    "IT": "Italy",
    "CH": "Switzerland",
    "AT": "Austria",
    "SE": "Sweden",
    "NO": "Norway",
    "DK": "Denmark",
    "FI": "Finland",
    "PL": "Poland",
    "CZ": "Czechia",
    "GR": "Greece",
    "RO": "Romania",
    "UA": "Ukraine",
    "RU": "Russia",
    "US": "United States",
    "CA": "Canada",
    "MX": "Mexico",
    "BR": "Brazil",
    "AR": "Argentina",
    "CL": "Chile",
    "CO": "Colombia",
    "PE": "Peru",
    "ZA": "South Africa",
    "EG": "Egypt",
    "NG": "Nigeria",
    "KE": "Kenya",
    "MA": "Morocco",
    "UN": "Other (UTC)",
}


@lru_cache(maxsize=1)
def _known_timezones() -> frozenset[str]:
    """Every timezone this table offers.

    Not zoneinfo.available_timezones(): that scans the filesystem, and it would
    let a client store a zone that is real but unrelated to its country.
    """
    return frozenset(name for names in COUNTRY_TIMEZONES.values() for name in names)


def country_timezones(country_code: str) -> tuple[str, ...]:
    return COUNTRY_TIMEZONES.get(country_code.upper(), ())


def is_known_timezone(name: str) -> bool:
    return name in _known_timezones()


@lru_cache(maxsize=256)
def load_timezone(name: str) -> ZoneInfo | None:
    """Return the tzinfo for a name, or None when the tz database lacks it.

    Returns None rather than raising so a missing tzdata degrades the date
    folder to UTC instead of failing the request that writes the recording.
    """
    if not name:
        return None
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def resolve_timezone(name: str, default: str = "UTC") -> ZoneInfo:
    """Return the tzinfo for a stored timezone, falling back to `default`."""
    return load_timezone(name) or load_timezone(default) or ZoneInfo("UTC")


def country_catalog() -> list[dict]:
    """The country list served to clients, sorted by display name."""
    return sorted(
        (
            {
                "code": code,
                "name": COUNTRY_NAMES.get(code, code),
                "timezones": list(timezones),
            }
            for code, timezones in COUNTRY_TIMEZONES.items()
        ),
        key=lambda entry: entry["name"],
    )
