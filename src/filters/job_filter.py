"""Shared title and location filtering for normalized job records."""

import pandas as pd

from src.filters.location_filter import is_excluded_location
from src.scrapers.greenhouse import (
    SCRAPED_JOB_COLUMNS,
    title_has_excluded_keyword,
    title_has_target_keyword,
)


def filter_normalized_jobs(jobs_dataframe: pd.DataFrame) -> pd.DataFrame:
    """Apply the existing title and location rules to normalized jobs."""
    retained_jobs: list[dict] = []

    for job in jobs_dataframe.to_dict(orient="records"):
        title = str(job.get("Title") or "").strip()
        location = str(job.get("Location") or "Unknown").strip()
        if not title_has_target_keyword(title):
            continue
        if title_has_excluded_keyword(title):
            continue
        if is_excluded_location(location):
            continue
        if not str(job.get("Job Description") or "").strip():
            continue
        retained_jobs.append(job)

    return pd.DataFrame(retained_jobs, columns=SCRAPED_JOB_COLUMNS)
