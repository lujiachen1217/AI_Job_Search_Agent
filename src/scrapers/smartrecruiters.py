"""SmartRecruiters public API scraper."""

from collections.abc import Iterable
from urllib.parse import urlparse

import pandas as pd
import requests

from src.config import SMARTRECRUITERS_COMPANIES
from src.scrapers.greenhouse import SCRAPED_JOB_COLUMNS, clean_job_description


POSTINGS_URL = "https://api.smartrecruiters.com/v1/companies/{company}/postings"
PAGE_SIZE = 100
COUNTRY_NAMES = {
    "cn": "China",
    "gb": "United Kingdom",
    "hk": "Hong Kong",
    "sg": "Singapore",
    "us": "United States",
}


def format_smartrecruiters_location(location: dict | None) -> str:
    """Convert structured SmartRecruiters location data to readable text."""
    if not isinstance(location, dict):
        return "Unknown"

    full_location = str(location.get("fullLocation") or "").strip()
    if full_location:
        parts = []
        for part in full_location.split(","):
            value = part.strip()
            if value and value.casefold() not in {
                existing.casefold() for existing in parts
            }:
                parts.append(value)
        return ", ".join(parts) or "Unknown"
    if location.get("remote") and not any(
        location.get(field) for field in ("city", "region", "country")
    ):
        return "Remote"

    parts = []
    for field in ("city", "region", "country"):
        value = str(location.get(field) or "").strip()
        if field == "country":
            value = COUNTRY_NAMES.get(value.casefold(), value)
        if value and value not in parts:
            parts.append(value)
    return ", ".join(parts) or (
        "Remote" if location.get("remote") else "Unknown"
    )


def normalize_smartrecruiters_job(company: str, job: dict) -> dict | None:
    """Normalize one listing record to the shared job schema."""
    if not isinstance(job, dict):
        return None

    posting_id = str(job.get("id") or "").strip()
    title = str(job.get("name") or "").strip()
    apply_link = str(job.get("postingUrl") or job.get("applyUrl") or "").strip()
    if not apply_link and posting_id:
        apply_link = f"https://jobs.smartrecruiters.com/{company}/{posting_id}"
    if not title or not apply_link:
        return None

    return {
        "Company": company,
        "Title": title,
        "Location": format_smartrecruiters_location(job.get("location")),
        "Job Description": build_smartrecruiters_description(job),
        "Apply Link": apply_link,
    }


def build_smartrecruiters_description(job: dict) -> str:
    """Combine the readable sections from a SmartRecruiters job detail."""
    job_ad = job.get("jobAd") or {}
    sections = job_ad.get("sections") or {} if isinstance(job_ad, dict) else {}
    if not isinstance(sections, dict):
        return ""

    parts: list[str] = []
    for section_name in (
        "companyDescription",
        "jobDescription",
        "qualifications",
        "additionalInformation",
    ):
        section = sections.get(section_name) or {}
        if not isinstance(section, dict):
            continue
        title = str(section.get("title") or "").strip()
        text = clean_job_description(str(section.get("text") or ""))
        if text:
            parts.append(" ".join(part for part in (title, text) if part))
    return " ".join(parts).strip()


def fetch_smartrecruiters_company(company: str) -> list[dict]:
    """Fetch every listing page for one SmartRecruiters company."""
    url = POSTINGS_URL.format(company=company)
    offset = 0
    jobs: list[dict] = []
    seen_page_signatures: set[tuple[str, ...]] = set()

    while True:
        response = requests.get(
            url,
            params={"limit": PAGE_SIZE, "offset": offset},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("SmartRecruiters response must be a JSON object")
        page = payload.get("content", [])
        if not isinstance(page, list):
            raise ValueError("SmartRecruiters content must be a JSON list")
        if not page:
            break

        page_signature = tuple(
            str(job.get("id") or "") if isinstance(job, dict) else repr(job)
            for job in page
        )
        if page_signature in seen_page_signatures:
            break
        seen_page_signatures.add(page_signature)

        jobs.extend(job for job in page if isinstance(job, dict))
        next_offset = offset + len(page)
        total_found = payload.get("totalFound")
        if isinstance(total_found, int) and next_offset >= total_found:
            break
        if next_offset <= offset:
            break
        offset = next_offset

    return jobs


def scrape_smartrecruiters_jobs(
    companies: Iterable[str] = SMARTRECRUITERS_COMPANIES,
) -> pd.DataFrame:
    """Fetch unfiltered SmartRecruiters listings with pagination."""
    results: list[dict] = []

    for company in companies:
        print(f"正在获取 {company} 的 SmartRecruiters 职位……")
        try:
            jobs = fetch_smartrecruiters_company(company)
        except (requests.RequestException, ValueError) as error:
            print(f"{company} SmartRecruiters 获取失败：{error}")
            print("-" * 50)
            continue

        normalized = [
            record
            for job in jobs
            if (record := normalize_smartrecruiters_job(company, job))
            is not None
        ]
        results.extend(normalized)
        print(f"{company} SmartRecruiters 获取成功，职位数：{len(normalized)}")
        print("-" * 50)

    return pd.DataFrame(results, columns=SCRAPED_JOB_COLUMNS)


def _posting_identity(apply_link: str) -> tuple[str, str] | None:
    """Extract company and posting ID from a normalized public job URL."""
    parts = [part for part in urlparse(apply_link).path.split("/") if part]
    if len(parts) < 2:
        return None
    posting_id = parts[1].split("-", 1)[0]
    return (parts[0], posting_id) if posting_id else None


def add_smartrecruiters_descriptions(
    jobs_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Fetch details only for filtered jobs and retain complete records."""
    results: list[dict] = []

    for job in jobs_dataframe.to_dict(orient="records"):
        identity = _posting_identity(str(job.get("Apply Link") or ""))
        if identity is None:
            continue
        company, posting_id = identity
        detail_url = f"{POSTINGS_URL.format(company=company)}/{posting_id}"
        try:
            response = requests.get(detail_url, timeout=15)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("SmartRecruiters detail must be a JSON object")
        except (requests.RequestException, ValueError) as error:
            print(f"SmartRecruiters 职位详情获取失败：{error}")
            continue

        normalized = normalize_smartrecruiters_job(company, payload)
        if normalized and normalized["Job Description"]:
            results.append(normalized)

    return pd.DataFrame(results, columns=SCRAPED_JOB_COLUMNS)
