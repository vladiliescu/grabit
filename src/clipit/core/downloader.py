import logging

import requests
from requests import RequestException

from clipit.core import DownloadError


def download_html_content(url, user_agent: str | None) -> str:
    request_headers = {
        "User-Agent": user_agent,
        "Accept-Language": "en-US,en;q=0.9",
    }

    if user_agent is None:
        del request_headers["User-Agent"]

    try:
        response = requests.get(url, headers=request_headers)
        response.raise_for_status()
        html_content = response.content.decode("utf-8")
    except RequestException as e:
        raise DownloadError(f"Error downloading {url}: {e}") from e

    return html_content


def download_image(url: str, user_agent: str | None) -> tuple[bytes, str] | None:
    request_headers = {
        "User-Agent": user_agent,
        "Accept": "image/*",
    }

    if user_agent is None:
        del request_headers["User-Agent"]

    try:
        response = requests.get(url, headers=request_headers, timeout=10)
        response.raise_for_status()
    except RequestException as exc:
        logging.getLogger(__name__).warning("Failed to download image %s: %s", url, exc)
        return None

    return response.content, response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
