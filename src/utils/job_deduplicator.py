"""Deduplication helpers for normalized job postings."""

import re

import pandas as pd


def _normalize_key_part(value: object) -> str:
    """Normalize text used in a fallback identity key."""
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def deduplicate_jobs(jobs_dataframe: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate by Apply Link, falling back to company/title/location."""
    if jobs_dataframe.empty:
        return jobs_dataframe.copy()

    retained_indexes: list[object] = []
    seen_keys: set[tuple[str, ...]] = set()

    for index, job in jobs_dataframe.iterrows():
        apply_link = _normalize_key_part(job.get("Apply Link", ""))
        if apply_link:
            identity = ("link", apply_link)
        else:
            identity = (
                "fallback",
                _normalize_key_part(job.get("Company", "")),
                _normalize_key_part(job.get("Title", "")),
                _normalize_key_part(job.get("Location", "")),
            )

        if identity in seen_keys:
            continue
        seen_keys.add(identity)
        retained_indexes.append(index)

    return jobs_dataframe.loc[retained_indexes].reset_index(drop=True)
