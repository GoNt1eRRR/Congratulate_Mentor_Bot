import argparse
import os

from dotenv import load_dotenv


def get_url():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Start Telegram Bot with specified URL")
    parser.add_argument('--url', required=True, help="Specify the URL (TEST_URL for test, PROD_URL for production)")
    args = parser.parse_args()

    BASE_URL = os.getenv(args.url)

    return BASE_URL


BASE_URL = get_url()
SCHEMA_FILE = "libs/schema.json"


def validate_api_response(data, error_message):
    if not data:
        raise ValueError(error_message)
    return data


def format_mentor(mentor):
    first = mentor["name"]["first"].split()[0] if mentor["name"]["first"] else ""
    second = mentor["name"]["second"].split()[0] if mentor["name"]["second"] else ""
    return f"{mentor['tg_username']} {first} {second}"
