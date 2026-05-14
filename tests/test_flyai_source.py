"""Unit tests for flyai_source — parsing and normalization, no subprocess."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import flyai_source


SAMPLE_ROUND_TRIP = {
    "data": {
        "itemList": [
            {
                "ticketPrice": "5438.00",
                "jumpUrl": "https://a.feizhu.com/xxx",
                "journeys": [
                    {
                        "journeyType": "直达",
                        "totalDuration": "735",
                        "segments": [
                            {
                                "depCityCode": "YVR", "depStationCode": "YVR",
                                "arrCityCode": "BJS", "arrStationCode": "PEK",
                                "arrStationName": "首都国际机场",
                                "depDateTime": "2026-07-15 13:40:00",
                                "arrDateTime": "2026-07-16 16:55:00",
                                "marketingTransportName": "加拿大航空",
                                "marketingTransportNo": "AC029",
                                "duration": "735",
                            }
                        ],
                    },
                    {
                        "journeyType": "中转",
                        "totalDuration": "1555",
                        "segments": [
                            {
                                "depCityCode": "BJS", "arrCityCode": "HKG",
                                "arrStationName": "香港国际机场",
                                "depDateTime": "2026-08-10 09:20:00",
                                "arrDateTime": "2026-08-10 13:15:00",
                                "marketingTransportName": "香港航",
                                "duration": "235",
                            },
                            {
                                "depCityCode": "HKG", "arrCityCode": "YVR",
                                "arrStationName": "温哥华国际机场",
                                "depDateTime": "2026-08-10 22:25:00",
                                "arrDateTime": "2026-08-10 20:15:00",
                                "marketingTransportName": "香港航",
                                "duration": "770",
                            },
                        ],
                    },
                ],
            }
        ]
    }
}


def test_parse_items_extracts_core_fields(monkeypatch):
    monkeypatch.setenv("FLYAI_CNY_TO_USD", "7.2")
    items = flyai_source.parse_items(SAMPLE_ROUND_TRIP)
    assert len(items) == 1
    item = items[0]
    assert item["departure"] == "2026-07-15"
    assert item["return"] == "2026-08-10"
    assert item["airline_out"] == "加拿大航空"
    assert item["airline_ret"] == "香港航"
    assert item["stops_out"] == 0
    assert item["stops_ret"] == 1
    assert item["via_out"] == "Direct"
    assert "香港" in item["via_ret"]
    assert item["duration_out_hrs"] == round(735 / 60, 1)
    assert item["price_cny"] == 5438.0
    # 5438 / 7.2 ≈ 755
    assert 750 <= item["price_usd"] <= 760


def test_parse_items_drops_zero_price():
    raw = {"data": {"itemList": [{"ticketPrice": "0", "journeys": SAMPLE_ROUND_TRIP["data"]["itemList"][0]["journeys"]}]}}
    assert flyai_source.parse_items(raw) == []


def test_parse_items_handles_missing_data():
    assert flyai_source.parse_items({}) == []
    assert flyai_source.parse_items({"data": {}}) == []
    assert flyai_source.parse_items({"data": {"itemList": []}}) == []


def test_cny_to_usd_env_override(monkeypatch):
    monkeypatch.setenv("FLYAI_CNY_TO_USD", "10")
    items = flyai_source.parse_items(SAMPLE_ROUND_TRIP)
    assert items[0]["price_usd"] == round(5438 / 10)


def test_cny_to_usd_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("FLYAI_CNY_TO_USD", "not-a-number")
    assert flyai_source._cny_to_usd_rate() == flyai_source.DEFAULT_CNY_TO_USD
    monkeypatch.setenv("FLYAI_CNY_TO_USD", "-5")
    assert flyai_source._cny_to_usd_rate() == flyai_source.DEFAULT_CNY_TO_USD


def test_search_roundtrip_returns_empty_when_cli_absent(monkeypatch):
    monkeypatch.setattr(flyai_source, "is_available", lambda: False)
    assert flyai_source.search_roundtrip("YVR", "PEK", "2026-07-15", "2026-08-10") == []
    assert flyai_source.search_oneway("YVR", "PEK", "2026-07-15") == []


def test_enrich_overrides_when_flyai_cheaper(monkeypatch):
    """fli row with a real price gets replaced when flyai is >5% cheaper."""
    import search_flights as sf
    monkeypatch.setattr(sf.flyai_source, "is_available", lambda: True)
    monkeypatch.setattr(sf.flyai_source, "cheapest_roundtrip", lambda *a, **kw: {
        "price_usd": 1000, "stops_out": 1, "stops_ret": 1,
        "airline_out": "A", "airline_ret": "A", "via_out": "X", "via_ret": "X",
        "duration_out_hrs": 10, "duration_ret_hrs": 10,
    })
    rows = [{
        "departure": "2026-07-15", "return": "2026-08-10", "days": 26,
        "price": 1643, "currency": "USD", "stops_out": 1, "stops_ret": 1,
        "airline_out": "Korean Air", "airline_ret": "Asiana",
        "via_out": "ICN", "via_ret": "ICN",
        "duration_out_hrs": 23.9, "duration_ret_hrs": 21.1,
        "booking_url": "x",
    }]
    out = sf.enrich_roundtrip_with_flyai(rows, "YVR", "PEK", 1)
    assert out[0]["price"] == 1000
    assert out[0]["source"] == "flyai"


def test_enrich_keeps_fli_when_flyai_not_meaningfully_cheaper(monkeypatch):
    """fli row stays when flyai is within 5% (noise, not a real saving)."""
    import search_flights as sf
    monkeypatch.setattr(sf.flyai_source, "is_available", lambda: True)
    monkeypatch.setattr(sf.flyai_source, "cheapest_roundtrip", lambda *a, **kw: {
        "price_usd": 1600, "stops_out": 0, "stops_ret": 0,
        "airline_out": "A", "airline_ret": "A", "via_out": "", "via_ret": "",
        "duration_out_hrs": 10, "duration_ret_hrs": 10,
    })
    rows = [{
        "departure": "2026-07-15", "return": "2026-08-10", "days": 26,
        "price": 1643, "currency": "USD", "stops_out": 1, "stops_ret": 1,
        "airline_out": "Korean Air", "airline_ret": "Asiana",
        "via_out": "ICN", "via_ret": "ICN",
        "duration_out_hrs": 23.9, "duration_ret_hrs": 21.1,
        "booking_url": "x",
    }]
    out = sf.enrich_roundtrip_with_flyai(rows, "YVR", "PEK", 1)
    assert out[0]["price"] == 1643
    assert "source" not in out[0]


def test_cheapest_roundtrip_respects_max_stops(monkeypatch):
    def fake_search(*_a, **_kw):
        return [
            {"stops_out": 2, "stops_ret": 0, "price_usd": 500, "departure": "x", "return": "y",
             "airline_out": "A", "airline_ret": "A", "via_out": "", "via_ret": "",
             "duration_out_hrs": 1, "duration_ret_hrs": 1, "price_cny": 0, "jump_url": ""},
            {"stops_out": 0, "stops_ret": 1, "price_usd": 700, "departure": "x", "return": "y",
             "airline_out": "B", "airline_ret": "B", "via_out": "", "via_ret": "",
             "duration_out_hrs": 1, "duration_ret_hrs": 1, "price_cny": 0, "jump_url": ""},
        ]
    monkeypatch.setattr(flyai_source, "search_roundtrip", fake_search)
    r = flyai_source.cheapest_roundtrip("O", "D", "x", "y", max_stops=1)
    assert r["airline_out"] == "B"
    r = flyai_source.cheapest_roundtrip("O", "D", "x", "y", max_stops=0)
    assert r is None
