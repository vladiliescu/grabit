from bookit import convert_to_markdown


def test_bold_and_italic():
    html_content = "<strong>Bold Text</strong> and <i>Italic Text</i>"
    markdown_content = convert_to_markdown(html_content)

    assert "**Bold Text**" in markdown_content, "Bold text conversion failed"
    assert "_Italic Text_" in markdown_content, "Italic text conversion failed"
