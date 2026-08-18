from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
RESUME_PATH = DATA_DIR / "resume.pdf"
SKILLS_PATH = DATA_DIR / "skills.csv"
EXCEL_OUTPUT_PATH = OUTPUT_DIR / "jobs.xlsx"

GREENHOUSE_COMPANIES = [
    "xai",
    "scaleai",
    "datadog",
    "figma",
    # Plaid's former Greenhouse board currently returns 404. Keep it disabled
    # until an official supported job source is configured.
    "reddit",
    "discord",
    "affirm",
]

LEVER_COMPANIES = [
    "spotify",
    "findigs",
    "sambatv",
    "analyticpartners",
]

TARGET_JOB_KEYWORDS = [
    "data analyst",
    "data scientist",
    "business analyst",
    "product analyst",
    "biostatistician",
    "biostatistics",
    "health data",
    "health analytics",
    "clinical data",
    "machine learning engineer",
    "research engineer",
    "analytics",
    "data science",
    "decision science",
    "insights analyst",
    "quantitative analyst",
    "statistical analyst",
    "research analyst",
    "business intelligence analyst",
    "bi analyst",
    "operations analyst",
    "strategy analyst",
    "risk analyst",
]

EXCLUDED_JOB_KEYWORDS = [
    "senior",
    "staff",
    "principal",
    "director",
    "manager",
    "lead",
    "head of",
    "vice president",
    "chief",
    "tutor",
    "account executive",
    "sales",
    "marketing",
    "recruiter",
    "research scientist",
    "phd",
    "postdoc",
    "postdoctoral",
]

ALLOWED_LOCATION_KEYWORDS = [
    "united states",
    "usa",
    "mainland china",
    "china",
    "hong kong sar",
    "hong kong",
    "singapore",
    "beijing",
    "shanghai",
    "shenzhen",
    "guangzhou",
    "hangzhou",
]

US_STATE_NAMES = [
    "alabama",
    "alaska",
    "arizona",
    "arkansas",
    "california",
    "colorado",
    "connecticut",
    "delaware",
    "district of columbia",
    "florida",
    "georgia",
    "hawaii",
    "idaho",
    "illinois",
    "indiana",
    "iowa",
    "kansas",
    "kentucky",
    "louisiana",
    "maine",
    "maryland",
    "massachusetts",
    "michigan",
    "minnesota",
    "mississippi",
    "missouri",
    "montana",
    "nebraska",
    "nevada",
    "new hampshire",
    "new jersey",
    "new mexico",
    "new york",
    "north carolina",
    "north dakota",
    "ohio",
    "oklahoma",
    "oregon",
    "pennsylvania",
    "rhode island",
    "south carolina",
    "south dakota",
    "tennessee",
    "texas",
    "utah",
    "vermont",
    "virginia",
    "washington",
    "west virginia",
    "wisconsin",
    "wyoming",
]

US_STATE_ABBREVIATIONS = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
    "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
    "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
    "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI",
    "WY",
]

MINIMUM_MATCH_SCORE = 20
MAX_REQUIRED_EXPERIENCE_YEARS = 2
SKILL_MATCH_DEBUG = True
TOP_AI_MATCH_COUNT = 5
AI_MATCH_MAX_WORKERS = 4
SPONSORSHIP_MAX_WORKERS = 4
DECISION_MAX_WORKERS = 4
