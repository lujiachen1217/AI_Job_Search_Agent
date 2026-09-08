import pandas as pd

from src.utils.job_deduplicator import deduplicate_jobs


def _jobs(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_identical_apply_links_are_deduplicated() -> None:
    jobs = _jobs([
        {"Company": "Acme", "Title": "Data Analyst", "Location": "Remote", "Apply Link": "https://example.test/1"},
        {"Company": "Acme", "Title": "Data Analyst II", "Location": "New York, NY", "Apply Link": "https://example.test/1"},
    ])

    result = deduplicate_jobs(jobs)

    assert len(result) == 1
    assert result.iloc[0]["Title"] == "Data Analyst"


def test_different_apply_links_preserve_similar_jobs() -> None:
    jobs = _jobs([
        {"Company": "Acme", "Title": "Data Analyst", "Location": "Remote", "Apply Link": "https://example.test/1"},
        {"Company": "Acme", "Title": "Data Analyst", "Location": "Remote", "Apply Link": "https://example.test/2"},
    ])

    assert len(deduplicate_jobs(jobs)) == 2


def test_missing_links_use_normalized_fallback_key() -> None:
    jobs = _jobs([
        {"Company": " Acme ", "Title": "Data  Analyst", "Location": "REMOTE", "Apply Link": ""},
        {"Company": "acme", "Title": "data analyst", "Location": "remote", "Apply Link": None},
    ])

    assert len(deduplicate_jobs(jobs)) == 1
