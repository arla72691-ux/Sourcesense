# config.py
import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Database and DMS Configuration
DB_PATH = os.getenv("DB_PATH", "s2c_sourcesense.db")
DMS_ROOT = os.getenv("DMS_ROOT", "DMS_Documents")

# Gemini API Configuration
# Ensure your GEMINI_API_KEY is set in your .env file
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

# SMTP Configuration for sending emails
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

# A simple check to ensure email configuration is present if needed
def is_email_configured():
    return all([SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SENDER_EMAIL])
