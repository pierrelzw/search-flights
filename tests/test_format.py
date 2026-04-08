"""Tests for output formatting."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from search_flights import format_table, format_oneway_table, format_date_zh


class TestFormatDateZh:
    def test_weekday(self):
        assert format_date_zh("2026-07-01") == "7/1 (三)"  # Wednesday
        assert format_date_zh("2026-07-05") == "7/5 (日)"  # Sunday

    def test_single_digit_month_day(self):
        result = format_date_zh("2026-01-05")
        assert result.startswith("1/5")


class TestFormatTable:
    def _make_result(self, **overrides):
        base = {
            "departure": "2026-07-01",
            "return": "2026-07-15",
            "days": 14,
            "price": 900,
            "currency": "USD",
            "stops_out": 0,
            "stops_ret": 0,
            "airline_out": "Air China",
            "airline_ret": "Air China",
            "via_out": "Direct",
            "via_ret": "Direct",
            "duration_out_hrs": 10.5,
            "duration_ret_hrs": 11.0,
            "booking_url": "https://example.com",
        }
        base.update(overrides)
        return base

    def test_empty_results(self):
        assert format_table([], "YVR", "PEK", None) == "No flights found."

    def test_header_contains_route(self):
        results = [self._make_result()]
        output = format_table(results, "YVR", "PEK", None)
        assert "YVR → PEK" in output

    def test_direct_label(self):
        results = [self._make_result()]
        output = format_table(results, "YVR", "PEK", None)
        assert "直飞" in output

    def test_no_direct_label_with_stops(self):
        results = [self._make_result(stops_out=1, stops_ret=1)]
        output = format_table(results, "YVR", "PEK", None)
        assert "直飞" not in output
        assert "中转" in output

    def test_cheapest_bolded(self):
        results = [
            self._make_result(price=800),
            self._make_result(price=1200, departure="2026-07-03", **{"return": "2026-07-17"}),
        ]
        output = format_table(results, "YVR", "PEK", None)
        assert "**$800**" in output
        assert "**$1,200**" not in output

    def test_mixed_airlines_column(self):
        results = [
            self._make_result(airline_out="Air China"),
            self._make_result(airline_out="United", departure="2026-07-03", **{"return": "2026-07-17"}),
        ]
        output = format_table(results, "YVR", "PEK", None)
        assert "航司" in output

    def test_single_airline_no_column(self):
        results = [self._make_result()]
        output = format_table(results, "YVR", "PEK", None)
        assert "航司" not in output

    def test_booking_link(self):
        results = [self._make_result()]
        output = format_table(results, "YVR", "PEK", None)
        assert "[Google Flights]" in output


class TestFormatOnewayTable:
    def _make_result(self, **overrides):
        base = {
            "departure": "2026-08-25",
            "price": 500,
            "currency": "USD",
            "stops": 0,
            "airline": "Air Canada",
            "via": "Direct",
            "duration_hrs": 10.5,
            "booking_url": "https://example.com",
        }
        base.update(overrides)
        return base

    def test_empty(self):
        assert format_oneway_table([], "YVR", "NRT", None) == "No flights found."

    def test_header_contains_oneway(self):
        results = [self._make_result()]
        output = format_oneway_table(results, "YVR", "NRT", None)
        assert "单程" in output

    def test_cheapest_bolded(self):
        results = [
            self._make_result(price=400),
            self._make_result(price=600),
        ]
        output = format_oneway_table(results, "YVR", "NRT", None)
        assert "**$400**" in output
