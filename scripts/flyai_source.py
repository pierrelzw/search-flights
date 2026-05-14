"""Supplemental flight data from the `flyai` CLI (Fliggy / 飞猪).

Used to fill gaps when `fli` (Google Flights) returns no flights or price=0.
Output is normalized to the same schema used by `search_flights.py` so rows
are interchangeable.

flyai is optional; if the binary is missing or the call fails, helpers return
empty results and callers proceed with fli-only data.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from typing import Optional


DEFAULT_CNY_TO_USD = 7.2


def _cny_to_usd_rate() -> float:
    raw = os.environ.get("FLYAI_CNY_TO_USD")
    if not raw:
        return DEFAULT_CNY_TO_USD
    try:
        rate = float(raw)
        return rate if rate > 0 else DEFAULT_CNY_TO_USD
    except ValueError:
        return DEFAULT_CNY_TO_USD


def is_available() -> bool:
    return shutil.which("flyai") is not None


def _run(args: list[str], timeout: int = 45) -> Optional[dict]:
    if not is_available():
        return None
    try:
        proc = subprocess.run(
            ["flyai", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"  flyai: call failed ({e})", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(f"  flyai: exit {proc.returncode}: {proc.stderr.strip()[:200]}", file=sys.stderr)
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def _duration_minutes(raw) -> int:
    if raw is None or raw == "":
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _stops(segments: list) -> int:
    return max(0, len(segments) - 1)


def _via(segments: list) -> str:
    if len(segments) <= 1:
        return "Direct"
    return ", ".join(s.get("arrStationName") or s.get("arrCityName") or "" for s in segments[:-1])


def _airline(segments: list) -> str:
    if not segments:
        return "Unknown"
    name = segments[0].get("marketingTransportName") or "Unknown"
    return str(name)


def _parse_item(item: dict) -> Optional[dict]:
    """Extract normalized fields from a single flyai itemList entry.

    Returns None when required structure is missing.
    """
    journeys = item.get("journeys") or []
    if not journeys:
        return None
    try:
        price_cny = float(item.get("ticketPrice") or 0)
    except (TypeError, ValueError):
        price_cny = 0.0
    if price_cny <= 0:
        return None

    out = journeys[0]
    out_segs = out.get("segments") or []
    if not out_segs:
        return None

    ret = journeys[1] if len(journeys) > 1 else None
    ret_segs = (ret or {}).get("segments") or []

    usd = round(price_cny / _cny_to_usd_rate())

    dep_date = (out_segs[0].get("depDateTime") or "")[:10]
    ret_date = (ret_segs[0].get("depDateTime") or "")[:10] if ret_segs else None

    return {
        "departure": dep_date,
        "return": ret_date,
        "price_usd": usd,
        "price_cny": price_cny,
        "stops_out": _stops(out_segs),
        "stops_ret": _stops(ret_segs) if ret_segs else 0,
        "airline_out": _airline(out_segs),
        "airline_ret": _airline(ret_segs) if ret_segs else _airline(out_segs),
        "via_out": _via(out_segs),
        "via_ret": _via(ret_segs) if ret_segs else "Direct",
        "duration_out_hrs": round(_duration_minutes(out.get("totalDuration")) / 60, 1),
        "duration_ret_hrs": round(_duration_minutes((ret or {}).get("totalDuration")) / 60, 1) if ret else 0,
        "jump_url": item.get("jumpUrl"),
    }


def parse_items(raw: dict) -> list[dict]:
    items = ((raw or {}).get("data") or {}).get("itemList") or []
    parsed = [_parse_item(it) for it in items]
    return [p for p in parsed if p is not None]


def search_roundtrip(origin: str, dest: str, depart: str, return_date: str) -> list[dict]:
    """Return a list of normalized round-trip candidates, cheapest first."""
    raw = _run([
        "search-flight",
        "--origin", origin,
        "--destination", dest,
        "--dep-date", depart,
        "--back-date", return_date,
        "--sort-type", "3",
    ])
    results = parse_items(raw) if raw else []
    results.sort(key=lambda r: r["price_usd"])
    return results


def search_oneway(origin: str, dest: str, depart: str) -> list[dict]:
    """Return a list of normalized one-way candidates, cheapest first."""
    raw = _run([
        "search-flight",
        "--origin", origin,
        "--destination", dest,
        "--dep-date", depart,
        "--sort-type", "3",
    ])
    results = parse_items(raw) if raw else []
    results.sort(key=lambda r: r["price_usd"])
    return results


def cheapest_roundtrip(origin: str, dest: str, depart: str, return_date: str, max_stops: Optional[int] = None) -> Optional[dict]:
    for r in search_roundtrip(origin, dest, depart, return_date):
        if max_stops is not None and (r["stops_out"] > max_stops or r["stops_ret"] > max_stops):
            continue
        return r
    return None


def cheapest_oneway(origin: str, dest: str, depart: str, max_stops: Optional[int] = None) -> Optional[dict]:
    for r in search_oneway(origin, dest, depart):
        if max_stops is not None and r["stops_out"] > max_stops:
            continue
        return r
    return None


# Re-exported so callers don't need to import datetime when validating dates
def _valid_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except (TypeError, ValueError):
        return False
