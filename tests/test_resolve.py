"""Tests for city/IATA resolution."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import pytest
from search_flights import resolve_city_or_iata, CITY_TO_IATA


class TestResolveIATA:
    def test_iata_passthrough(self):
        assert resolve_city_or_iata("YVR") == "YVR"
        assert resolve_city_or_iata("pek") == "PEK"
        assert resolve_city_or_iata(" SFO ") == "SFO"

    def test_english_city(self):
        assert resolve_city_or_iata("vancouver") == "YVR"
        assert resolve_city_or_iata("Vancouver") == "YVR"
        assert resolve_city_or_iata("VANCOUVER") == "YVR"

    def test_chinese_city(self):
        assert resolve_city_or_iata("北京") == "PEK"
        assert resolve_city_or_iata("上海") == "PVG"
        assert resolve_city_or_iata("温哥华") == "YVR"

    def test_multi_word_city(self):
        assert resolve_city_or_iata("hong kong") == "HKG"
        assert resolve_city_or_iata("los angeles") == "LAX"
        assert resolve_city_or_iata("san francisco") == "SFO"
        assert resolve_city_or_iata("new york") == "JFK"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown airport/city"):
            resolve_city_or_iata("Atlantis")

    def test_all_mappings_are_valid_iata(self):
        for city, code in CITY_TO_IATA.items():
            assert len(code) == 3
            assert code.isalpha()
            assert code == code.upper()
