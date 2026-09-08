from unittest.mock import Mock, patch

from src.scrapers.ashby import normalize_ashby_job, scrape_ashby_jobs
from src.scrapers.greenhouse import SCRAPED_JOB_COLUMNS


def test_normalize_ashby_job() -> None:
    result = normalize_ashby_job("acme", {
        "title": " Data Analyst ",
        "location": "New York, NY",
        "descriptionPlain": "Analyze <b>data</b>.",
        "applyUrl": "https://jobs.ashbyhq.com/acme/1/application",
        "jobUrl": "https://jobs.ashbyhq.com/acme/1",
    })

    assert result == {
        "Company": "acme",
        "Title": "Data Analyst",
        "Location": "New York, NY",
        "Job Description": "Analyze data .",
        "Apply Link": "https://jobs.ashbyhq.com/acme/1/application",
    }


def test_normalize_handles_missing_optional_fields_and_job_url_fallback() -> None:
    result = normalize_ashby_job("acme", {
        "title": "Data Scientist",
        "jobUrl": "https://jobs.ashbyhq.com/acme/2",
    })

    assert result is not None
    assert result["Location"] == "Unknown"
    assert result["Job Description"] == ""
    assert result["Apply Link"].endswith("/2")


def test_normalize_rejects_missing_title_or_apply_link() -> None:
    assert normalize_ashby_job("acme", {"applyUrl": "https://example.test"}) is None
    assert normalize_ashby_job("acme", {"title": "Data Analyst"}) is None


@patch("src.scrapers.ashby.requests.get")
def test_scraper_empty_response_returns_schema(mock_get: Mock) -> None:
    response = Mock()
    response.json.return_value = {"jobs": []}
    response.raise_for_status.return_value = None
    mock_get.return_value = response

    result = scrape_ashby_jobs(["acme"])

    assert result.empty
    assert list(result.columns) == SCRAPED_JOB_COLUMNS
