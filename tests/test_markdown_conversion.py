from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from clipit.core.markdown_converter import convert_to_markdown
from markdown_it import MarkdownIt


def test_converts_bold_and_italics_with_different_markup():
    html_content = "<strong>Bold Text</strong> and <i>Italic Text</i>"
    markdown_content = convert_to_markdown(html_content)

    assert "**Bold Text**" in markdown_content, "Bold text conversion failed"
    assert "_Italic Text_" in markdown_content, "Italic text conversion failed"


def test_converts_title_with_links():
    html_content = '<h2>TITLE (<a href="https://example.com">Link</a>)</h2>'
    markdown_content = convert_to_markdown(html_content)

    assert markdown_content == "## TITLE ([Link](https://example.com))\n", "Header conversion failed"


@pytest.mark.parametrize("linked_image", [False, True])
def test_preserves_boring_technology_slide_images_and_notes(linked_image):
    html = (Path(__file__).parent / "fixtures" / "boring-table.html").read_text()
    if linked_image:
        soup = BeautifulSoup(html, "html.parser")
        img = soup.select("img")[0]
        img.wrap(soup.new_tag("a", href=str(img["src"])))
        html = str(soup)

    markdown = convert_to_markdown(html)

    image_sources = [
        child.attrGet("src")
        for token in MarkdownIt().parse(markdown)
        for child in token.children or []
        if child.type == "image"
    ]
    assert image_sources == [f"slides/slides.{number:03d}.jpeg" for number in range(1, 4)]
    assert "I’m Dan McKinley." in markdown
