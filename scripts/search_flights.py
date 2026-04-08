#!/usr/bin/env python3
"""Search flights across flexible date ranges using Google Flights (via fli library).

Three modes:
  1. Flexible date range: enumerate departure dates x trip durations
  2. Exact dates: single round-trip pair, skip Phase 1
  3. One-way: single departure date, no return
"""

import argparse
import json
import sys
import urllib.parse
from datetime import datetime, timedelta

from fli.core import (
    build_date_search_segments,
    build_flight_segments,
    resolve_airport,
    parse_max_stops,
)
from fli.models import (
    DateSearchFilters,
    FlightSearchFilters,
    PassengerInfo,
    SeatType,
    SortBy,
)
from fli.search import SearchDates, SearchFlights


CITY_TO_IATA = {
    "vancouver": "YVR", "温哥华": "YVR",
    "beijing": "PEK", "北京": "PEK",
    "shanghai": "PVG", "上海": "PVG",
    "toronto": "YYZ", "多伦多": "YYZ",
    "tokyo": "NRT", "东京": "NRT",
    "hong kong": "HKG", "香港": "HKG",
    "taipei": "TPE", "台北": "TPE",
    "singapore": "SIN", "新加坡": "SIN",
    "seoul": "ICN", "首尔": "ICN",
    "los angeles": "LAX", "洛杉矶": "LAX",
    "san francisco": "SFO", "旧金山": "SFO",
    "new york": "JFK", "纽约": "JFK",
    "london": "LHR", "伦敦": "LHR",
    "guangzhou": "CAN", "广州": "CAN",
    "shenzhen": "SZX", "深圳": "SZX",
    "chengdu": "CTU", "成都": "CTU",
    "osaka": "KIX", "大阪": "KIX",
    "bangkok": "BKK", "曼谷": "BKK",
    "kuala lumpur": "KUL", "吉隆坡": "KUL",
    "sydney": "SYD", "悉尼": "SYD",
    "melbourne": "MEL", "墨尔本": "MEL",
    "paris": "CDG", "巴黎": "CDG",
    "dubai": "DXB", "迪拜": "DXB",
    "seattle": "SEA", "西雅图": "SEA",
    "chicago": "ORD", "芝加哥": "ORD",
    "calgary": "YYC", "卡尔加里": "YYC",
    "hangzhou": "HGH", "杭州": "HGH",
    "nanjing": "NKG", "南京": "NKG",
    "xiamen": "XMN", "厦门": "XMN",
    "chongqing": "CKG", "重庆": "CKG",
    "wuhan": "WUH", "武汉": "WUH",
    "xian": "XIY", "西安": "XIY",
    "kunming": "KMG", "昆明": "KMG",
}


def resolve_city_or_iata(code_or_city: str) -> str:
    """Resolve city name to IATA code, or pass through IATA codes."""
    upper = code_or_city.strip().upper()
    if len(upper) == 3 and upper.isascii() and upper.isalpha():
        return upper
    lower = code_or_city.strip().lower()
    if lower in CITY_TO_IATA:
        return CITY_TO_IATA[lower]
    raise ValueError(f"Unknown airport/city: {code_or_city}. Use IATA code (e.g., YVR).")


def google_flights_url(origin, dest, departure, return_date=None, max_stops=None):
    """Build a Google Flights search URL."""
    if return_date:
        q = f"Flights from {origin} to {dest} on {departure} returning {return_date}"
    else:
        q = f"Flights from {origin} to {dest} on {departure} one way"
    if max_stops == 0:
        q += " nonstop"
    params = urllib.parse.urlencode({"q": q, "curr": "USD", "hl": "en"})
    return f"https://www.google.com/travel/flights?{params}"


def phase1_date_scan(origin_code, dest_code, depart_from, depart_to, durations, max_stops_str):
    """Phase 1: Coarse scan using SearchDates for each trip duration."""
    searcher = SearchDates()
    origin = resolve_airport(origin_code)
    dest = resolve_airport(dest_code)
    candidates = []

    for dur in durations:
        print(f"  Scanning {dur}-day trips ({depart_from} to {depart_to})...", file=sys.stderr)
        try:
            segments, trip_type = build_date_search_segments(
                origin=origin,
                destination=dest,
                start_date=depart_from,
                trip_duration=dur,
                is_round_trip=True,
            )
            filters = DateSearchFilters(
                trip_type=trip_type,
                passenger_info=PassengerInfo(adults=1),
                flight_segments=segments,
                stops=parse_max_stops(max_stops_str),
                from_date=depart_from,
                to_date=depart_to,
                duration=dur,
            )
            results = searcher.search(filters)
            if results:
                for dp in results:
                    dep_dt = dp.date[0] if isinstance(dp.date, tuple) else dp.date
                    ret_dt = dp.date[1] if isinstance(dp.date, tuple) and len(dp.date) > 1 else dep_dt + timedelta(days=dur)
                    candidates.append({
                        "departure": dep_dt.strftime("%Y-%m-%d"),
                        "return": ret_dt.strftime("%Y-%m-%d"),
                        "days": (ret_dt - dep_dt).days,
                        "price": dp.price,
                    })
                print(f"    Found {len(results)} prices for {dur}d trips", file=sys.stderr)
        except Exception as e:
            print(f"  Warning: search_dates failed for {dur}d trips: {e}", file=sys.stderr)

    return candidates


def format_airline(airline_enum) -> str:
    """Format airline enum to readable name."""
    return str(airline_enum.value)


def discover_airlines(origin_code, dest_code, sample_date, max_stops_int=None):
    """Discover all airlines on a route, including those with missing pricing.

    Does a one-way search to find all airlines. Returns (priced, unpriced) sets.
    """
    searcher = SearchFlights()
    origin = resolve_airport(origin_code)
    dest = resolve_airport(dest_code)

    try:
        segments, trip_type = build_flight_segments(
            origin=origin, destination=dest, departure_date=sample_date,
        )
        max_stops = parse_max_stops(str(max_stops_int)) if max_stops_int is not None else parse_max_stops("ANY")
        filters = FlightSearchFilters(
            trip_type=trip_type,
            passenger_info=PassengerInfo(adults=1),
            flight_segments=segments,
            seat_type=SeatType.ECONOMY,
            stops=max_stops,
            sort_by=SortBy.CHEAPEST,
        )
        flights = searcher.search(filters, top_n=10)
        if not flights:
            return set(), set()

        priced = set()
        unpriced = set()
        for f in flights:
            flight = f[0] if isinstance(f, tuple) else f
            airline = format_airline(flight.legs[0].airline) if flight.legs else None
            if not airline:
                continue
            if flight.price > 0:
                priced.add(airline)
            else:
                unpriced.add(airline)
        # Airlines that have at least one priced flight are considered "priced"
        unpriced -= priced
        return priced, unpriced
    except Exception:
        return set(), set()


def phase2_detail_search(origin_code, dest_code, candidates, max_stops_str, top_n, max_stops_int=None):
    """Phase 2: Get detailed flight info for top candidates (round-trip)."""
    searcher = SearchFlights()
    origin = resolve_airport(origin_code)
    dest = resolve_airport(dest_code)
    max_stops = parse_max_stops(max_stops_str)
    results = []

    seen = set()
    unique = []
    for c in sorted(candidates, key=lambda x: x["price"]):
        key = (c["departure"], c["return"])
        if key not in seen:
            seen.add(key)
            unique.append(c)

    fetch_limit = top_n * 3 if max_stops_int is not None else top_n
    for c in unique[:fetch_limit]:
        if len(results) >= top_n:
            break
        dep_date = c["departure"]
        ret_date = c["return"]
        print(f"  Details: {dep_date} → {ret_date} ({c['days']}d, ~${c['price']})...", file=sys.stderr)

        try:
            segments, trip_type = build_flight_segments(
                origin=origin,
                destination=dest,
                departure_date=dep_date,
                return_date=ret_date,
            )
            filters = FlightSearchFilters(
                trip_type=trip_type,
                passenger_info=PassengerInfo(adults=1),
                flight_segments=segments,
                seat_type=SeatType.ECONOMY,
                stops=max_stops,
                sort_by=SortBy.CHEAPEST,
            )
            flight_pairs = searcher.search(filters, top_n=1)
            if flight_pairs:
                pair = flight_pairs[0]
                if isinstance(pair, tuple):
                    out_flight, ret_flight = pair
                else:
                    out_flight, ret_flight = pair, None

                out_airline = format_airline(out_flight.legs[0].airline) if out_flight.legs else "Unknown"
                ret_airline = format_airline(ret_flight.legs[0].airline) if ret_flight and ret_flight.legs else out_airline

                out_via = ", ".join(
                    leg.arrival_airport.name for leg in out_flight.legs[:-1]
                ) if len(out_flight.legs) > 1 else "Direct"
                ret_via = "Direct"
                if ret_flight and len(ret_flight.legs) > 1:
                    ret_via = ", ".join(
                        leg.arrival_airport.name for leg in ret_flight.legs[:-1]
                    )

                if max_stops_int is not None:
                    out_over = out_flight.stops > max_stops_int
                    ret_over = ret_flight.stops > max_stops_int if ret_flight else False
                    if out_over or ret_over:
                        print(f"    Skipped: stops {out_flight.stops}/{ret_flight.stops if ret_flight else 0} > max {max_stops_int}", file=sys.stderr)
                        continue

                total_price = out_flight.price if out_flight.price > 0 else c["price"]

                results.append({
                    "departure": dep_date,
                    "return": ret_date,
                    "days": c["days"],
                    "price": total_price,
                    "currency": "USD",
                    "stops_out": out_flight.stops,
                    "stops_ret": ret_flight.stops if ret_flight else 0,
                    "airline_out": out_airline,
                    "airline_ret": ret_airline,
                    "via_out": out_via,
                    "via_ret": ret_via,
                    "duration_out_hrs": round(out_flight.duration / 60, 1),
                    "duration_ret_hrs": round(ret_flight.duration / 60, 1) if ret_flight else 0,
                    "booking_url": google_flights_url(origin_code, dest_code, dep_date, ret_date, max_stops_int),
                })
            else:
                results.append(_fallback_result(c, origin_code, dest_code, max_stops_int))
        except Exception as e:
            print(f"  Warning: detail search failed for {dep_date}: {e}", file=sys.stderr)
            results.append(_fallback_result(c, origin_code, dest_code, max_stops_int))

    results.sort(key=lambda x: x["price"])
    return results


def search_oneway(origin_code, dest_code, depart_date, max_stops_str, top_n, max_stops_int=None):
    """Search one-way flights for a specific date."""
    searcher = SearchFlights()
    origin = resolve_airport(origin_code)
    dest = resolve_airport(dest_code)
    max_stops = parse_max_stops(max_stops_str)
    results = []

    print(f"  Searching one-way: {origin_code} → {dest_code} on {depart_date}...", file=sys.stderr)

    try:
        segments, trip_type = build_flight_segments(
            origin=origin,
            destination=dest,
            departure_date=depart_date,
        )
        filters = FlightSearchFilters(
            trip_type=trip_type,
            passenger_info=PassengerInfo(adults=1),
            flight_segments=segments,
            seat_type=SeatType.ECONOMY,
            stops=max_stops,
            sort_by=SortBy.CHEAPEST,
        )
        flights = searcher.search(filters, top_n=top_n)
        for f in (flights or []):
            flight = f[0] if isinstance(f, tuple) else f

            airline = format_airline(flight.legs[0].airline) if flight.legs else "Unknown"
            via = ", ".join(
                leg.arrival_airport.name for leg in flight.legs[:-1]
            ) if len(flight.legs) > 1 else "Direct"

            if max_stops_int is not None and flight.stops > max_stops_int:
                continue

            results.append({
                "departure": depart_date,
                "price": flight.price,
                "currency": "USD",
                "stops": flight.stops,
                "airline": airline,
                "via": via,
                "duration_hrs": round(flight.duration / 60, 1),
                "booking_url": google_flights_url(origin_code, dest_code, depart_date, max_stops=max_stops_int),
            })
    except Exception as e:
        print(f"  Warning: one-way search failed: {e}", file=sys.stderr)

    results.sort(key=lambda x: x["price"])
    return results


def _fallback_result(candidate, origin_code=None, dest_code=None, max_stops_int=None):
    result = {
        "departure": candidate["departure"],
        "return": candidate["return"],
        "days": candidate["days"],
        "price": candidate["price"],
        "currency": "USD",
        "stops_out": -1,
        "stops_ret": -1,
        "airline_out": "Unknown",
        "airline_ret": "Unknown",
        "via_out": "",
        "via_ret": "",
        "duration_out_hrs": 0,
        "duration_ret_hrs": 0,
    }
    if origin_code and dest_code:
        result["booking_url"] = google_flights_url(
            origin_code, dest_code, candidate["departure"], candidate["return"], max_stops_int
        )
    return result


WEEKDAY_ZH = ["一", "二", "三", "四", "五", "六", "日"]


def format_date_zh(date_str):
    """Format date as 'M/D (周X)'."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    wd = WEEKDAY_ZH[dt.weekday()]
    return f"{dt.month}/{dt.day} ({wd})"


def format_table(results, origin_code, dest_code, max_stops_int, unpriced_airlines=None):
    """Format round-trip results as a markdown table."""
    if not results:
        return "No flights found."

    airlines = set()
    all_direct = True
    for r in results:
        airlines.add(r["airline_out"])
        if r.get("airline_ret") and r["airline_ret"] != r["airline_out"]:
            airlines.add(r["airline_ret"])
        if r["stops_out"] > 0 or r["stops_ret"] > 0:
            all_direct = False

    header_parts = [f"## {origin_code} → {dest_code}"]
    if all_direct:
        header_parts.append("直飞")
    if len(airlines) == 1:
        header_parts.append(f"| {list(airlines)[0]}")
    if results[0]["duration_out_hrs"] > 0:
        header_parts.append(f"| 去程 {results[0]['duration_out_hrs']}h 回程 {results[0]['duration_ret_hrs']}h")
    header = " ".join(header_parts)

    lines = [header, ""]

    has_mixed_airlines = len(airlines) > 1
    has_stops = not all_direct

    cols = ["#", "出发", "返回", "天数", "价格 (USD)"]
    if has_stops:
        cols.append("中转")
    if has_mixed_airlines:
        cols.append("航司")
    cols.append("购票")

    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "|".join(["---"] * len(cols)) + "|")

    min_price = min(r["price"] for r in results)
    for i, r in enumerate(results, 1):
        price_str = f"${r['price']:,.0f}"
        if r["price"] == min_price:
            price_str = f"**{price_str}**"

        row = [
            str(i),
            format_date_zh(r["departure"]),
            format_date_zh(r["return"]),
            str(r["days"]),
            price_str,
        ]
        if has_stops:
            stops = f"{r['stops_out']}/{r['stops_ret']}"
            via_parts = []
            if r["via_out"] and r["via_out"] != "Direct":
                via_parts.append(r["via_out"])
            if r["via_ret"] and r["via_ret"] != "Direct":
                via_parts.append(r["via_ret"])
            via_str = f" ({', '.join(via_parts)})" if via_parts else ""
            row.append(f"{stops}{via_str}")
        if has_mixed_airlines:
            if r["airline_out"] == r.get("airline_ret", r["airline_out"]):
                row.append(r["airline_out"])
            else:
                row.append(f"{r['airline_out']}/{r['airline_ret']}")
        row.append(f"[Google Flights]({r['booking_url']})")

        lines.append("| " + " | ".join(row) + " |")

    if unpriced_airlines:
        lines.append("")
        names = ", ".join(sorted(unpriced_airlines))
        lines.append(f"> **注意**: 以下航司在该航线有航班但价格数据不可用: {names}。建议到 Google Flights 查看完整结果。")

    return "\n".join(lines)


def format_oneway_table(results, origin_code, dest_code, max_stops_int, unpriced_airlines=None):
    """Format one-way results as a markdown table."""
    if not results:
        return "No flights found."

    airlines = set()
    all_direct = True
    for r in results:
        airlines.add(r["airline"])
        if r["stops"] > 0:
            all_direct = False

    header_parts = [f"## {origin_code} → {dest_code} 单程"]
    if all_direct:
        header_parts.append("直飞")
    if len(airlines) == 1:
        header_parts.append(f"| {list(airlines)[0]}")
    if results[0]["duration_hrs"] > 0:
        header_parts.append(f"| {results[0]['duration_hrs']}h")
    header = " ".join(header_parts)

    lines = [header, ""]

    has_mixed_airlines = len(airlines) > 1
    has_stops = not all_direct

    cols = ["#", "出发", "价格 (USD)", "时长"]
    if has_stops:
        cols.append("中转")
    if has_mixed_airlines:
        cols.append("航司")
    cols.append("购票")

    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "|".join(["---"] * len(cols)) + "|")

    min_price = min(r["price"] for r in results)
    for i, r in enumerate(results, 1):
        price_str = f"${r['price']:,.0f}"
        if r["price"] == min_price:
            price_str = f"**{price_str}**"

        row = [
            str(i),
            format_date_zh(r["departure"]),
            price_str,
            f"{r['duration_hrs']}h",
        ]
        if has_stops:
            via_str = f" ({r['via']})" if r["via"] and r["via"] != "Direct" else ""
            row.append(f"{r['stops']}{via_str}")
        if has_mixed_airlines:
            row.append(r["airline"])
        row.append(f"[Google Flights]({r['booking_url']})")

        lines.append("| " + " | ".join(row) + " |")

    if unpriced_airlines:
        lines.append("")
        names = ", ".join(sorted(unpriced_airlines))
        lines.append(f"> **注意**: 以下航司在该航线有航班但价格数据不可用: {names}。建议到 Google Flights 查看完整结果。")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Search flights across date ranges")
    parser.add_argument("origin", help="Origin airport/city (IATA code or city name)")
    parser.add_argument("destination", help="Destination airport/city (IATA code or city name)")

    # Flexible date range mode
    parser.add_argument("--from", dest="date_from", help="Travel window start (YYYY-MM-DD)")
    parser.add_argument("--to", dest="date_to", help="Travel window end (YYYY-MM-DD)")
    parser.add_argument("--min-days", type=int, default=7, help="Minimum trip duration (days)")
    parser.add_argument("--max-days", type=int, default=30, help="Maximum trip duration (days)")

    # Exact date / one-way mode
    parser.add_argument("--depart", help="Exact departure date (YYYY-MM-DD)")
    parser.add_argument("--return", dest="return_date", help="Exact return date (YYYY-MM-DD)")
    parser.add_argument("--one-way", action="store_true", help="One-way search (no return)")

    # Common options
    parser.add_argument("--max-stops", default="ANY", help="Max stops: ANY, 0, 1, 2")
    parser.add_argument("--top", type=int, default=15, help="Number of top results")
    parser.add_argument("--format", choices=["table", "json"], default="table", help="Output format")
    args = parser.parse_args()

    origin_code = resolve_city_or_iata(args.origin)
    dest_code = resolve_city_or_iata(args.destination)
    max_stops_int = int(args.max_stops) if args.max_stops.isdigit() else None

    # Determine search mode
    if args.one_way:
        # One-way mode
        depart = args.depart
        if not depart:
            print("Error: --depart is required for one-way search.", file=sys.stderr)
            sys.exit(1)

        print(f"One-way flight search: {origin_code} → {dest_code}", file=sys.stderr)
        print(f"Departure: {depart}", file=sys.stderr)
        print(f"Max stops: {args.max_stops}", file=sys.stderr)
        print(file=sys.stderr)

        results = search_oneway(origin_code, dest_code, depart, args.max_stops, args.top, max_stops_int)

        # Discover airlines with missing pricing (reuses the same one-way search pattern)
        print("Checking airline coverage...", file=sys.stderr)
        _, unpriced = discover_airlines(origin_code, dest_code, depart, max_stops_int)

        print(f"\nDone! {len(results)} results.", file=sys.stderr)

        if args.format == "table":
            print(format_oneway_table(results, origin_code, dest_code, max_stops_int, unpriced))
        else:
            json.dump(results, sys.stdout, indent=2, ensure_ascii=False)

    elif args.depart and args.return_date:
        # Exact date mode — skip Phase 1, go straight to detail search
        days = (datetime.strptime(args.return_date, "%Y-%m-%d") - datetime.strptime(args.depart, "%Y-%m-%d")).days

        print(f"Exact date flight search: {origin_code} → {dest_code}", file=sys.stderr)
        print(f"Departure: {args.depart}, Return: {args.return_date} ({days}d)", file=sys.stderr)
        print(f"Max stops: {args.max_stops}", file=sys.stderr)
        print(file=sys.stderr)

        candidates = [{
            "departure": args.depart,
            "return": args.return_date,
            "days": days,
            "price": 0,
        }]

        print("Fetching flight details...", file=sys.stderr)
        results = phase2_detail_search(origin_code, dest_code, candidates, args.max_stops, args.top, max_stops_int)

        print("Checking airline coverage...", file=sys.stderr)
        _, unpriced = discover_airlines(origin_code, dest_code, args.depart, max_stops_int)

        print(f"\nDone! {len(results)} results.", file=sys.stderr)

        if args.format == "table":
            print(format_table(results, origin_code, dest_code, max_stops_int, unpriced))
        else:
            json.dump(results, sys.stdout, indent=2, ensure_ascii=False)

    elif args.date_from and args.date_to:
        # Flexible date range mode
        window_start = datetime.strptime(args.date_from, "%Y-%m-%d")
        window_end = datetime.strptime(args.date_to, "%Y-%m-%d")
        window_days = (window_end - window_start).days

        max_days = min(args.max_days, window_days)
        if max_days < args.min_days:
            print(f"Error: travel window ({window_days}d) is shorter than min trip duration ({args.min_days}d).", file=sys.stderr)
            sys.exit(1)

        latest_depart = (window_end - timedelta(days=args.min_days)).strftime("%Y-%m-%d")

        print(f"Flight search: {origin_code} → {dest_code}", file=sys.stderr)
        print(f"Travel window: {args.date_from} to {args.date_to} ({window_days} days)", file=sys.stderr)
        print(f"Departure range: {args.date_from} to {latest_depart}", file=sys.stderr)
        print(f"Trip duration: {args.min_days}-{max_days} days", file=sys.stderr)
        print(f"Max stops: {args.max_stops}", file=sys.stderr)
        print(f"Top results: {args.top}", file=sys.stderr)
        print(file=sys.stderr)

        # Phase 1
        print("Phase 1: Scanning date range for cheapest prices...", file=sys.stderr)
        all_candidates = []
        for dur in range(args.min_days, max_days + 1):
            depart_to = (window_end - timedelta(days=dur)).strftime("%Y-%m-%d")
            if depart_to < args.date_from:
                continue
            candidates = phase1_date_scan(origin_code, dest_code, args.date_from, depart_to, [dur], args.max_stops)
            all_candidates.extend(candidates)
        print(f"  Found {len(all_candidates)} price points total", file=sys.stderr)

        if not all_candidates:
            print("No flights found for the given parameters.", file=sys.stderr)
            if args.format == "json":
                json.dump([], sys.stdout, indent=2)
            else:
                print("No flights found.")
            sys.exit(0)

        # Phase 2
        print(f"\nPhase 2: Fetching details for top {args.top} candidates...", file=sys.stderr)
        results = phase2_detail_search(origin_code, dest_code, all_candidates, args.max_stops, args.top, max_stops_int)

        # Discover airlines with missing pricing (use first candidate's date)
        sample_date = sorted(all_candidates, key=lambda x: x["price"])[0]["departure"]
        print("Checking airline coverage...", file=sys.stderr)
        _, unpriced = discover_airlines(origin_code, dest_code, sample_date, max_stops_int)

        print(f"\nDone! {len(results)} results.", file=sys.stderr)

        if args.format == "table":
            print(format_table(results, origin_code, dest_code, max_stops_int, unpriced))
        else:
            json.dump(results, sys.stdout, indent=2, ensure_ascii=False)

    else:
        print("Error: specify either --from/--to (flexible), --depart/--return (exact), or --depart --one-way.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
