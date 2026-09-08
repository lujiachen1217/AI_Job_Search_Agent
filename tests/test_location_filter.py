import pytest

from src.filters.location_filter import is_allowed_location, is_excluded_location


@pytest.mark.parametrize(
    "location",
    [
        "San Francisco",
        "San Francisco, CA",
        "San Francisco, California",
        "San Francisco / New York",
        "San Francisco; New York",
        "Seattle",
        "Seattle, WA",
        "New York",
        "New York, NY",
        "New York City",
        "Cambridge, MA",
        "Remote - United States",
        "Remote - US",
        "Remote, United States",
        "Hong Kong",
        "Hong Kong SAR",
        "Singapore",
        "Shanghai",
        "Beijing",
    ],
)
def test_allowed_locations(location: str) -> None:
    assert is_allowed_location(location)
    assert not is_excluded_location(location)


@pytest.mark.parametrize(
    "location",
    [
        "London",
        "Canada",
        "Toronto",
        "Vancouver",
        "Bengaluru",
        "Berlin",
        "Belgrade",
        "North America",
        "Europe",
        "EMEA",
    ],
)
def test_excluded_locations(location: str) -> None:
    assert not is_allowed_location(location)
    assert is_excluded_location(location)


def test_city_matching_uses_token_boundaries() -> None:
    assert not is_allowed_location("Seattleton")
    assert not is_allowed_location("New Yorkshire")
    assert not is_allowed_location("Cambridgehire")
