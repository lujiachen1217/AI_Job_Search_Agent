"""Parse explicit experience requirements and filter senior jobs."""

import re
from dataclasses import dataclass

import pandas as pd


NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}
NUMBER_PATTERN = r"(?:\d{1,2}|zero|one|two|three|four|five|six|seven|eight|nine|ten)"
SOFT_LANGUAGE = re.compile(
    r"\b(?:preferred|nice to have|ideally|ideal(?:ly)? candidate|bonus)\b",
    re.IGNORECASE,
)
REQUIRED_LANGUAGE = re.compile(
    r"\b(?:required|must have|minimum|at least|qualifications include)\b",
    re.IGNORECASE,
)
OVERALL_EXPERIENCE = re.compile(
    r"\b(?:total|overall|professional|relevant|industry|work)\s+experience\b"
    r"|\byears?\s+of\s+(?:professional|relevant|industry|work)?\s*experience\b",
    re.IGNORECASE,
)
EXPERIENCE_CONTEXT = re.compile(
    r"\b(?:experience|building|developing|working|designing|deploying|"
    r"production|analytics|data science|machine learning|software engineering)\b",
    re.IGNORECASE,
)
NO_PRIOR_EXPERIENCE = re.compile(
    r"\bno\s+(?:prior\s+)?(?:professional\s+|relevant\s+|work\s+)?"
    r"experience\s+(?:is\s+)?required\b",
    re.IGNORECASE,
)

# Capture a minimum year value, including ranges such as 3-5 and 3 to 5.
YEARS_PATTERN = re.compile(
    rf"(?P<minimum>{NUMBER_PATTERN})\s*"
    rf"(?:\+|(?:-|–|—|to)\s*{NUMBER_PATTERN})?\s*years?\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExperienceCandidate:
    """One explicit years-of-experience statement found in a JD."""

    minimum_years: int
    evidence: str
    required: bool
    overall: bool


def _parse_number(value: str) -> int:
    """Convert a digit or supported English number word to an integer."""
    normalized = value.casefold()
    return int(normalized) if normalized.isdigit() else NUMBER_WORDS[normalized]


def _clean_evidence(text: str) -> str:
    """Collapse whitespace in a short evidence excerpt."""
    return re.sub(r"\s+", " ", text).strip(" ,;:-")


def _sentence_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    """Find a bounded sentence-like context around a matched year value."""
    left_delimiters = [text.rfind(mark, 0, start) for mark in ".;\n•"]
    left = max(left_delimiters) + 1
    right_candidates = [
        position
        for mark in ".;\n•"
        if (position := text.find(mark, end)) != -1
    ]
    right = min(right_candidates) if right_candidates else len(text)
    return max(left, start - 100), min(right, end + 140)


def _requirement_clause(
    text: str,
    match: re.Match,
    context_start: int,
    context_end: int,
) -> str:
    """Isolate the clause associated with one years requirement."""
    separator = r"(?:[,.;\n•]|\b(?:and|or)\b)"
    before = text[context_start:match.start()]
    after = text[match.end():context_end]
    before_clause = re.split(separator, before, flags=re.IGNORECASE)[-1]
    after_clause = re.split(separator, after, maxsplit=1, flags=re.IGNORECASE)[0]
    return f"{before_clause}{match.group()}{after_clause}"


def _find_candidates(job_description: str) -> list[ExperienceCandidate]:
    """Extract meaningful explicit experience statements from a JD."""
    candidates: list[ExperienceCandidate] = []

    for match in YEARS_PATTERN.finditer(job_description):
        context_start, context_end = _sentence_bounds(
            job_description, match.start(), match.end()
        )
        context = job_description[context_start:context_end]
        clause = _requirement_clause(
            job_description, match, context_start, context_end
        )

        soft = bool(SOFT_LANGUAGE.search(clause))
        explicitly_required = bool(REQUIRED_LANGUAGE.search(clause))
        # Numeric years without experience context are dates or unrelated
        # quantities. Explicit soft language is still useful to record, but it
        # never causes exclusion.
        if (
            not EXPERIENCE_CONTEXT.search(clause)
            and not soft
            and not explicitly_required
        ):
            continue

        candidates.append(
            ExperienceCandidate(
                minimum_years=_parse_number(match.group("minimum")),
                evidence=_clean_evidence(clause),
                required=explicitly_required or not soft,
                overall=bool(OVERALL_EXPERIENCE.search(clause)),
            )
        )

    return candidates


def experience_level(minimum_years: int | None) -> str:
    """Map a minimum experience requirement to a readable level."""
    if minimum_years is None:
        return "Unknown"
    if minimum_years <= 1:
        return "Entry Level"
    if minimum_years == 2:
        return "Early Career"
    if minimum_years <= 4:
        return "Mid Level"
    return "Senior"


def analyze_experience_requirement(job_description: str) -> dict:
    """Return the most meaningful explicit experience requirement in a JD."""
    no_prior_match = NO_PRIOR_EXPERIENCE.search(job_description)
    if no_prior_match:
        return {
            "min_years_experience": 0,
            "experience_level": "Entry Level",
            "experience_requirement_found": True,
            "experience_evidence": _clean_evidence(no_prior_match.group()),
            "is_required": True,
        }

    candidates = _find_candidates(job_description)
    if not candidates:
        return {
            "min_years_experience": None,
            "experience_level": "Unknown",
            "experience_requirement_found": False,
            "experience_evidence": "",
            "is_required": False,
        }

    # Required statements outrank soft preferences. Within the selected
    # strength, prefer overall/professional requirements over tool-specific
    # experience, then use the highest stated minimum.
    required_candidates = [candidate for candidate in candidates if candidate.required]
    strength_candidates = required_candidates or candidates
    overall_candidates = [
        candidate for candidate in strength_candidates if candidate.overall
    ]
    relevant_candidates = overall_candidates or strength_candidates
    selected = max(relevant_candidates, key=lambda candidate: candidate.minimum_years)

    return {
        "min_years_experience": selected.minimum_years,
        "experience_level": experience_level(selected.minimum_years),
        "experience_requirement_found": True,
        "experience_evidence": selected.evidence,
        "is_required": selected.required,
    }


def filter_early_career_jobs(
    jobs_dataframe: pd.DataFrame,
    max_required_experience_years: int,
) -> pd.DataFrame:
    """Keep jobs requiring at most the configured number of years."""
    retained_jobs: list[dict] = []

    for job in jobs_dataframe.to_dict(orient="records"):
        analysis = analyze_experience_requirement(job["Job Description"])
        minimum_years = analysis["min_years_experience"]
        should_exclude = (
            analysis["is_required"]
            and minimum_years is not None
            and minimum_years > max_required_experience_years
        )

        if should_exclude:
            print(
                f"排除岗位：{job['Title']} | "
                f"Required Experience：{minimum_years} years"
            )
            continue

        retained_jobs.append(
            {
                **job,
                "Minimum Experience Years": minimum_years,
                "Experience Level": analysis["experience_level"],
                "Experience Evidence": analysis["experience_evidence"],
            }
        )

    result = pd.DataFrame(
        retained_jobs,
        columns=[
            *jobs_dataframe.columns,
            "Minimum Experience Years",
            "Experience Level",
            "Experience Evidence",
        ],
    )
    print(f"After experience requirement filtering: {len(result)}")
    return result
