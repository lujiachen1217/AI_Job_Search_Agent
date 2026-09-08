from unittest.mock import Mock, patch

import pandas as pd
import requests

from src.scrapers.greenhouse import SCRAPED_JOB_COLUMNS
from src.scrapers.smartrecruiters import (
    add_smartrecruiters_descriptions,
    build_smartrecruiters_description,
    fetch_smartrecruiters_company,
    format_smartrecruiters_location,
    normalize_smartrecruiters_job,
    scrape_smartrecruiters_jobs,
)


def _response(payload: object) -> Mock:
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_normalizes_listing_and_location() -> None:
    result = normalize_smartrecruiters_job("Acme", {
        "id": "123",
        "name": "Data Analyst",
        "location": {"city": "New York", "region": "NY", "country": "us"},
    })

    assert result == {
        "Company": "Acme",
        "Title": "Data Analyst",
        "Location": "New York, NY, United States",
        "Job Description": "",
        "Apply Link": "https://jobs.smartrecruiters.com/Acme/123",
    }


def test_location_prefers_full_location_and_handles_remote() -> None:
    assert format_smartrecruiters_location({
        "fullLocation": "San Francisco, CA, United States"
    }) == "San Francisco, CA, United States"
    assert format_smartrecruiters_location({
        "fullLocation": "Singapore, , Singapore"
    }) == "Singapore"
    assert format_smartrecruiters_location({"remote": True}) == "Remote"
    assert format_smartrecruiters_location(None) == "Unknown"


def test_description_combines_supported_sections() -> None:
    description = build_smartrecruiters_description({
        "jobAd": {"sections": {
            "jobDescription": {"title": "Role", "text": "<p>Analyze data.</p>"},
            "qualifications": {"title": "Qualifications", "text": "SQL"},
            "additionalInformation": {"title": "More", "text": "Remote"},
        }}
    })

    assert description == "Role Analyze data. Qualifications SQL More Remote"


@patch("src.scrapers.smartrecruiters.requests.get")
def test_fetches_all_pages(mock_get: Mock) -> None:
    mock_get.side_effect = [
        _response({"totalFound": 3, "content": [{"id": "1"}, {"id": "2"}]}),
        _response({"totalFound": 3, "content": [{"id": "3"}]}),
    ]

    result = fetch_smartrecruiters_company("Acme")

    assert [job["id"] for job in result] == ["1", "2", "3"]
    assert mock_get.call_count == 2
    assert mock_get.call_args_list[1].kwargs["params"]["offset"] == 2


@patch("src.scrapers.smartrecruiters.requests.get")
def test_repeated_page_stops_malformed_pagination(mock_get: Mock) -> None:
    repeated_page = _response({"content": [{"id": "1"}]})
    mock_get.side_effect = [repeated_page, repeated_page]

    result = fetch_smartrecruiters_company("Acme")

    assert [job["id"] for job in result] == ["1"]
    assert mock_get.call_count == 2


@patch("src.scrapers.smartrecruiters.requests.get")
def test_empty_response_returns_shared_schema(mock_get: Mock) -> None:
    mock_get.return_value = _response({"totalFound": 0, "content": []})

    result = scrape_smartrecruiters_jobs(["Acme"])

    assert result.empty
    assert list(result.columns) == SCRAPED_JOB_COLUMNS


@patch("src.scrapers.smartrecruiters.requests.get")
def test_company_failure_does_not_stop_later_company(mock_get: Mock) -> None:
    mock_get.side_effect = [
        requests.Timeout("timeout"),
        _response({"totalFound": 0, "content": []}),
    ]

    result = scrape_smartrecruiters_jobs(["Broken", "Working"])

    assert result.empty
    assert mock_get.call_count == 2


def test_malformed_or_incomplete_records_are_skipped() -> None:
    assert normalize_smartrecruiters_job("Acme", {}) is None
    assert normalize_smartrecruiters_job("Acme", {"id": "1"}) is None
    assert normalize_smartrecruiters_job("Acme", "invalid") is None


@patch("src.scrapers.smartrecruiters.requests.get")
def test_detail_hydration_uses_full_description_and_apply_link(mock_get: Mock) -> None:
    mock_get.return_value = _response({
        "id": "123",
        "name": "Data Analyst",
        "postingUrl": "https://jobs.smartrecruiters.com/Acme/123-data-analyst",
        "location": {"fullLocation": "Remote"},
        "jobAd": {"sections": {
            "jobDescription": {"title": "Role", "text": "Analyze data"},
        }},
    })
    listings = normalize_smartrecruiters_job("Acme", {
        "id": "123", "name": "Data Analyst"
    })

    result = add_smartrecruiters_descriptions(
        pd.DataFrame([listings])
    )

    assert result.iloc[0]["Job Description"] == "Role Analyze data"
    assert result.iloc[0]["Apply Link"].endswith("123-data-analyst")
