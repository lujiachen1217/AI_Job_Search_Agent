"""Controlled aliases that normalize textual variants to canonical skills."""

import re


SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Machine Learning": (
        "ML",
    ),
    "LLM": (
        "LLMs",
        "Large Language Model",
        "Large Language Models",
    ),
    "Scikit-learn": (
        "sklearn",
        "scikit learn",
        "scikit_learn",
    ),
    "Power BI": (
        "PowerBI",
        "Power-BI",
    ),
    "GCP": (
        "Google Cloud Platform",
        "Google Cloud",
    ),
    "AWS": (
        "Amazon Web Services",
    ),
    "Data Pipeline": (
        "data pipeline",
        "data pipelines",
    ),
}

_CANONICAL_BY_VARIANT = {
    variant.casefold(): canonical
    for canonical, aliases in SKILL_ALIASES.items()
    for variant in (canonical, *aliases)
}


def canonicalize_skill(skill: str) -> str:
    """Return the configured canonical name for a skill or variant."""
    return _CANONICAL_BY_VARIANT.get(skill.casefold(), skill)


def extract_alias_skills(text: str) -> set[str]:
    """Recognize controlled aliases in text and return canonical names."""
    found_skills: set[str] = set()

    for variant, canonical in _CANONICAL_BY_VARIANT.items():
        pattern = r"(?<!\w)" + re.escape(variant) + r"(?!\w)"
        if re.search(pattern, text, flags=re.IGNORECASE):
            found_skills.add(canonical)

    return found_skills
