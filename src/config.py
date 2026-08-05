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
    "plaid",
    "reddit",
    "discord",
    "affirm",
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

EXCLUDED_LOCATION_KEYWORDS = [
    "paris",
    "france",
    "london",
    "united kingdom",
    "canada",
    "doha",
    "qatar",
]

MINIMUM_MATCH_SCORE = 20
TOP_AI_MATCH_COUNT = 5
