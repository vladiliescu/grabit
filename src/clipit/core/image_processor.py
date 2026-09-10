from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlparse

from bs4 import BeautifulSoup

from clipit.core.downloader import download_image
from clipit.core.misc import sanitize_filename


def extract_image_urls(html_content: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html_content, "html.parser")
    image_urls: list[str] = []
    seen: set[str] = set()

    for img_tag in soup.find_all("img"):
        src = img_tag.get("src")
        if not isinstance(src, str) or not src:
            continue
        if src.startswith("data:"):
            continue

        absolute_url = urljoin(base_url, src)
        if absolute_url in seen:
            continue

        seen.add(absolute_url)
        image_urls.append(absolute_url)

    return image_urls


def _generate_image_filename(url: str, used_filenames: set[str], content_type: str = "") -> str:
    parsed = urlparse(url)
    path = Path(unquote(parsed.path))
    stem = path.stem or "image"
    extension = path.suffix or ".jpg"
    if content_type.startswith("image/") and mimetypes.guess_type(path.name)[0] != content_type:
        extension = ".jpg" if content_type == "image/jpeg" else mimetypes.guess_extension(content_type) or extension

    sanitized_stem = sanitize_filename(stem) or "image"
    sanitized_extension = extension if extension.startswith(".") else f".{extension}"

    def candidate_name(suffix: str) -> str:
        stem_bytes = sanitized_stem.encode("utf-8")[: 240 - len(suffix.encode("utf-8"))]
        return f"{stem_bytes.decode('utf-8', errors='ignore')}{suffix}"

    candidate = candidate_name(sanitized_extension)
    counter = 1

    while candidate in used_filenames:
        candidate = candidate_name(f"_{counter}{sanitized_extension}")
        counter += 1

    return candidate


def _image_identity(url: str) -> str:
    """Recognize Substack renditions of the same upstream image."""
    parsed = urlparse(url)
    if parsed.hostname == "substackcdn.com" and parsed.path.startswith("/image/fetch/"):
        return unquote(parsed.path.rsplit("/", 1)[-1])
    return url


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
    html_content: str, title: str, base_url: str, user_agent: str | None, directory: Path | None = None
) -> tuple[str, list[tuple[str, bytes]]]:
    if directory is None:
        directory = Path(sanitize_filename(title) or "Untitled")
    soup = BeautifulSoup(html_content, "html.parser")
    images: list[tuple[str, bytes]] = []
    image_url_to_filename: dict[str, str] = {}
    used_filenames: set[str] = set()

    for img_tag in soup.find_all("img"):
        original_src = img_tag.get("src")
        if not isinstance(original_src, str) or not original_src:
            continue
        if original_src.startswith("data:"):
            continue

        absolute_url = urljoin(base_url, original_src)

        if absolute_url not in image_url_to_filename:
            downloaded_image = download_image(absolute_url, user_agent)
            if downloaded_image is None:
                img_tag["src"] = absolute_url
                continue

            image_bytes, content_type = downloaded_image
            filename = _generate_image_filename(absolute_url, used_filenames, content_type)
            used_filenames.add(filename)
            image_url_to_filename[absolute_url] = filename
            images.append(((directory / filename).as_posix(), image_bytes))

        # URL-encode the path to prevent mdformat from escaping brackets
        encoded_path = quote((directory / image_url_to_filename[absolute_url]).as_posix(), safe="/")
        img_tag["src"] = encoded_path
        img_tag.attrs.pop("srcset", None)
        img_tag.attrs.pop("sizes", None)
        picture = img_tag.find_parent("picture")
        if picture is not None:
            for source in picture.find_all("source"):
                source.decompose()

        link = img_tag.find_parent("a", href=True)
        if link is not None:
            href = urljoin(base_url, str(link["href"]))
            if _image_identity(href) == _image_identity(absolute_url):
                link["href"] = encoded_path

    return str(soup), images
