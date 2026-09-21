import os

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "worofyousef@gmail.com")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "worofyousef@gmail.com")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

DEFAULT_CSV_PATH = "/content/gta_v_worldwide_sales_player_analytics_2013_2026.csv"
DASHBOARD_STATE_PATH = "dashboard_state.json"
REPORTS_DIR = "reports"

LLM_MODEL_NAME = "google/flan-t5-base"
WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/Grand_Theft_Auto_V"

ANOMALY_ZSCORE_THRESHOLD = 2.0
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2

PREPARED_FOR = "Marketing Team Lead"

# Persistent "learned" column-role mapping, keyed by each CSV's column signature.
COLUMN_MAP_CACHE_PATH = "column_map_cache.json"

REPORT_TYPES = {
    "overall": {"title": "Overall Performance Report", "title_ar": "تقرير الأداء العام",
                "email_subject": "Overall Performance Report — For the Marketing Team Lead"},
    "regional": {"title": "Regional Deep-Dive Report", "title_ar": "تقرير تفصيلي للأداء الإقليمي",
                 "email_subject": "Regional Deep-Dive Report — For the Marketing Team Lead"},
    "platform": {"title": "Platform Performance Report", "title_ar": "تقرير أداء المنصات",
                 "email_subject": "Platform Performance Report — For the Marketing Team Lead"},
    "engagement": {"title": "Player Engagement Report", "title_ar": "تقرير تفاعل اللاعبين",
                   "email_subject": "Player Engagement Report — For the Marketing Team Lead"},
    "risk": {"title": "Anomaly & Risk Report", "title_ar": "تقرير الشذوذ والمخاطر",
             "email_subject": "Anomaly & Risk Report — For the Marketing Team Lead"},
}
