from __future__ import annotations

from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

from bs4 import BeautifulSoup

from clipit.core.downloader import download_image
from clipit.core.misc import sanitize_filename


def extract_image_urls(html_content: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html_content, "html.parser")
    image_urls: list[str] = []
    seen: set[str] = set()

    for img_tag in soup.find_all("img"):
        src = img_tag.get("src")
        if not src:
            continue
        if src.startswith("data:"):
            continue

        absolute_url = urljoin(base_url, src)
        if absolute_url in seen:
            continue

        seen.add(absolute_url)
        image_urls.append(absolute_url)

    return image_urls


def _generate_image_filename(url: str, used_filenames: set[str]) -> str:
    parsed = urlparse(url)
    path = Path(parsed.path)
    stem = path.stem or "image"
    extension = path.suffix or ".jpg"

    sanitized_stem = sanitize_filename(stem) or "image"
    sanitized_extension = extension if extension.startswith(".") else f".{extension}"

    candidate = f"{sanitized_stem}{sanitized_extension}"
    counter = 1

    while candidate in used_filenames:
        candidate = f"{sanitized_stem}_{counter}{sanitized_extension}"
        counter += 1

    return candidate


def _get_best_image_url(img_tag, base_url: str) -> str | None:
    """Get the best quality image URL from an img tag, preferring srcset over src."""
    srcset = img_tag.get("srcset")

    if srcset:
        # srcset format: "url1 descriptor1, url2 descriptor2, ..."
        # Pick the last one which is typically the highest resolution
        candidates = [c.strip().split()[0] for c in srcset.split(",") if c.strip()]
        if candidates:
            return urljoin(base_url, candidates[-1])

    # Fall back to src attribute
    src = img_tag.get("src")
    if src:
        return urljoin(base_url, src)

    return None


def process_images(
    html_content: str, title: str, base_url: str, user_agent: str | None
) -> tuple[str, list[tuple[str, bytes]]]:
    directory = sanitize_filename(title)
    if not directory:
        directory = "images"
    soup = BeautifulSoup(html_content, "html.parser")
    images: list[tuple[str, bytes]] = []
    image_url_to_filename: dict[str, str] = {}
    used_filenames: set[str] = set()

    for img_tag in soup.find_all("img"):
        original_src = img_tag.get("src")
        if not original_src:
            continue
        if original_src.startswith("data:"):
            continue

        absolute_url = urljoin(base_url, original_src)

        if absolute_url in image_url_to_filename:
            # URL-encode the path to prevent mdformat from escaping brackets
            encoded_path = quote(f"{directory}/{image_url_to_filename[absolute_url]}", safe="/")
            img_tag["src"] = encoded_path
            continue

        image_bytes = download_image(absolute_url, user_agent)
        if image_bytes is None:
            # TODO: log warning about failed download
            continue

        filename = _generate_image_filename(absolute_url, used_filenames)
        used_filenames.add(filename)

        image_url_to_filename[absolute_url] = filename
        images.append((f"{directory}/{filename}", image_bytes))
        encoded_path = quote(f"{directory}/{filename}", safe="/")
        img_tag["src"] = encoded_path

    return str(soup), images
