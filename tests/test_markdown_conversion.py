from grabit import convert_to_markdown


def test_converts_bold_and_italics_with_different_markup():
    html_content = "<strong>Bold Text</strong> and <i>Italic Text</i>"
    markdown_content = convert_to_markdown(html_content)

    assert "**Bold Text**" in markdown_content, "Bold text conversion failed"
    assert "_Italic Text_" in markdown_content, "Italic text conversion failed"


def test_converts_title_with_links():
    html_content = '<h2>TITLE (<a href="https://example.com">Link</a>)</h2>'
    markdown_content = convert_to_markdown(html_content)

    assert markdown_content == "## TITLE ([Link](https://example.com))\n", "Header conversion failed"
