from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup
from clipit.core.image_processor import _image_identity, extract_image_urls, process_images


def test_extract_image_urls_resolves_relative_and_deduplicates():
    html = """
    <html>
        <body>
            <img src="/images/photo.jpg">
            <img src="https://cdn.example.com/logo.png">
            <img src="/images/photo.jpg">
            <img src="data:image/png;base64,AAAA">
        </body>
    </html>
    """

    urls = extract_image_urls(html, "https://example.com/articles/123")

    assert urls == ["https://example.com/images/photo.jpg", "https://cdn.example.com/logo.png"]


def test_generate_image_filename_handles_duplicates_and_extensions(image_server):
    """Verifies that:
    1. Original extension is preserved (photo.JPEG)
    2. Duplicate names get numbered (photo_1.JPEG)
    3. Missing extensions get default extension (.jpg added to banner)
    """
    html = """
    <html>
        <body>
            <img src="/photo.JPEG">
            <img src="/photo.JPEG?size=large">
            <img src="/banner">
        </body>
    </html>
    """

    base_url, _, _ = image_server
    processed_html, images = process_images(html, "test-title", base_url, user_agent=None)

    filenames = [filename for filename, _ in images]

    assert filenames == ["test-title/photo.JPEG", "test-title/photo_1.JPEG", "test-title/banner.jpg"]


def test_process_images_downloads_once_and_rewrites_src(image_server):
    html = """
    <html>
        <body>
            <img src="/photo.JPEG">
            <a href="/photo.JPEG"><picture><source srcset="/photo.JPEG 2x">
                <img src="/photo.JPEG" srcset="/photo.JPEG 2x">
            </picture></a>
            <img src="/banner">
        </body>
    </html>
    """

    base_url, directory, received_requests = image_server
    processed_html, images = process_images(html, "test-title", base_url, user_agent=None)

    soup = BeautifulSoup(processed_html, "html.parser")
    rewritten_sources = [img["src"] for img in soup.find_all("img")]

    assert received_requests == ["/photo.JPEG", "/banner"]

    assert rewritten_sources == ["test-title/photo.JPEG", "test-title/photo.JPEG", "test-title/banner.jpg"]
    assert soup.select("a")[0]["href"] == "test-title/photo.JPEG"
    assert not soup.select("source, img[srcset]")

    assert images == [
        ("test-title/photo.JPEG", (directory / "photo.JPEG").read_bytes()),
        ("test-title/banner.jpg", (directory / "banner").read_bytes()),
    ]


def test_process_images_preserves_remote_src_on_failure(image_server, caplog):
    html = """
    <html>
        <body>
            <img src="/missing.jpg">
            <img src="/converted.png">
        </body>
    </html>
    """

    base_url, directory, _ = image_server
    processed_html, images = process_images(html, "test-title", base_url, user_agent=None)
    soup = BeautifulSoup(processed_html, "html.parser")
    rewritten_sources = [img["src"] for img in soup.find_all("img")]

    assert rewritten_sources == [f"{base_url}/missing.jpg", "test-title/converted.jpg"]
    assert images == [("test-title/converted.jpg", (directory / "converted.png").read_bytes())]
    assert f"{base_url}/missing.jpg" in caplog.text
    assert "404" in caplog.text


def test_encoded_image_names_match_downloads_and_leave_article_links_alone(image_server):
    base_url, directory, _ = image_server
    filename = "https%3A%2F%2Fexample.com%2Fphotos%2Fbook%20cover.png"
    src = f"/{quote(filename, safe='%')}"
    # SimpleHTTPRequestHandler decodes URL paths when locating files.
    nested_file = directory / "https:" / "example.com" / "photos" / "book cover.png"
    nested_file.parent.mkdir(parents=True)
    nested_file.write_bytes((directory / "converted.png").read_bytes())
    html = f'<a href="/article"><img src="{src}"></a>'

    processed_html, images = process_images(html, "A Review [50%]", base_url, None)

    soup = BeautifulSoup(processed_html, "html.parser")
    assert soup.select("img")[0]["src"] == "A%20Review%2050/book%20cover.jpg"
    assert soup.select("a")[0]["href"] == "/article"
    assert images == [("A Review 50/book cover.jpg", nested_file.read_bytes())]


def test_substack_resized_and_fullsize_urls_identify_the_same_image():
    html = (Path(__file__).parent / "fixtures" / "substack-image.html").read_text()
    soup = BeautifulSoup(html, "html.parser")
    src = soup.select("img")[0]["src"]
    href = soup.select("a")[0]["href"]

    assert src != href
    assert _image_identity(str(src)) == _image_identity(str(href))
    assert _image_identity(str(src)).endswith("14fa9a26-c37b-410f-8c3d-16465182c68f_5094x1762.png")
