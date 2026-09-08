import pytest

from src.scrapers.greenhouse import title_is_relevant


@pytest.mark.parametrize(
    "title",
    [
        "Data Scientist",
        "Product Data Scientist",
        "Decision Scientist",
        "Data Analyst",
        "Product Analyst",
        "Quantitative Analyst",
        "Business Intelligence Analyst",
        "BI Analyst",
        "Machine Learning Engineer",
        "ML Engineer",
        "Applied Machine Learning Engineer",
        "AI Engineer",
        "Applied AI Engineer",
        "Data Engineer",
        "Analytics Engineer",
        "Biostatistician",
        "Statistical Programmer",
        "Health Data Analyst",
        "Clinical Data Scientist",
        "Business Systems Analyst",
        "Data Scientist II",
        "Data Analyst II",
    ],
)
def test_relevant_titles_are_accepted(title: str) -> None:
    assert title_is_relevant(title)


@pytest.mark.parametrize(
    "title",
    [
        "Software Engineer",
        "Software Engineer, Frontend",
        "Software Engineer, Data Platform",
        "Software Engineer, Data Infrastructure",
        "Software Engineer, Infrastructure - Analytics Platform",
        "Security Engineer",
        "Customer Success Manager",
        "Account Manager",
        "Marketing Analyst",
        "Financial Analyst",
        "Risk Analyst",
        "IT Operations Analyst",
        "Analyst, Customer Trust",
        "Full Stack Analyst, GTM",
        "Senior Data Scientist",
        "Sr. Data Engineer",
        "Sr Data Engineer",
        "Staff Machine Learning Engineer",
        "Principal Data Engineer",
        "VP, Data Science",
    ],
)
def test_irrelevant_or_senior_titles_are_rejected(title: str) -> None:
    assert not title_is_relevant(title)


def test_title_matching_uses_phrase_boundaries() -> None:
    assert not title_is_relevant("Biomedical Engineer")
    assert not title_is_relevant("Metadata Engineer")
