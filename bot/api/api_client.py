import argparse
import os
import httpx
from dotenv import load_dotenv
import json
from openapi_schema_validator import validate

load_dotenv()

parser = argparse.ArgumentParser(description="Start Telegram Bot with specified URL")
parser.add_argument('--url', required=True, help="Specify the URL (TEST_URL for test, PROD_URL for production)")
args = parser.parse_args()


BASE_URL = os.getenv(args.url)

schema_file = "bot/api/schema.json"


class ServerError(Exception):
    pass


def validate_json(json_data, schema_file):
    try:
        with open(schema_file, "r", encoding="utf-8") as file:
            schema = json.load(file)

        validate(json_data, schema)
        print("✅ JSON прошел валидацию!")
    except Exception as e:
        raise ServerError("Ошибка валидации JSON") from e


def get_mentors(base_url):
    url = f"{base_url}/mentors"

    try:
        response = httpx.get(url)
        response.raise_for_status()

        print("Полученный JSON (text):", response.text)

        try:
            json_data = response.json()
        except json.JSONDecodeError as e:
            raise ServerError("Ошибка: сервер вернул некорректный JSON") from e

        validate_json(json_data, schema_file)
        return json_data

    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        if 400 <= status_code < 500:
            raise e
        if 500 <= status_code < 600:
            raise ServerError(f"Ошибка сервера: {status_code}") from e
        raise e

    except httpx.RequestError as e:
        raise ServerError(f"Ошибка сети: {e}") from e


def get_postcards(base_url):
    url = f"{base_url}/postcards"

    try:
        response = httpx.get(url)
        response.raise_for_status()

        print("Полученный JSON (text):", response.text)

        try:
            json_data = response.json()
        except json.JSONDecodeError as e:
            raise ServerError("Ошибка: сервер вернул некорректный JSON") from e

        validate_json(json_data, schema_file)
        return json_data

    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        if 400 <= status_code < 500:
            raise e
        if 500 <= status_code < 600:
            raise ServerError(f"Ошибка сервера: {status_code}") from e
        raise e

    except httpx.RequestError as e:
        raise ServerError(f"Ошибка сети: {e}") from e
