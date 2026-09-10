from datetime import datetime

import yaml
from markdownify import (
    ATX,
    UNDERSCORE,
    MarkdownConverter,
    abstract_inline_conversion,  # type: ignore
)
from mdformat import text as mdformat_text


def try_include_title(include_title, markdown_content, title):
    if include_title:
        markdown_content = f"# {title}\n\n{markdown_content}"
    return markdown_content


def try_include_source(include_source, markdown_content, url):
    if include_source:
        markdown_content = f"[Source]({url})\n\n{markdown_content}"
    return markdown_content


def try_add_yaml_frontmatter(yaml_frontmatter: bool, markdown_content, title, url):
    if not yaml_frontmatter:
        return markdown_content

    metadata = {
        "title": title,
        "source": url,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    yaml_metadata = yaml.dump(metadata, sort_keys=False)
    markdown_content = f"---\n{yaml_metadata}---\n\n{markdown_content}"
    return markdown_content


class ClipitMarkdownConverter(MarkdownConverter):
    def convert_img(self, el, text, parent_tags):
        # Table images can be wrapped in links or other inline elements.
        if {"td", "th"} & parent_tags:
            parent_tags = parent_tags - {"_inline"}
        return super().convert_img(el, text, parent_tags)  # ty: ignore[unresolved-attribute]

    def convert_em(self, el, text, parent_tags):
        return self.convert_i(el, text, parent_tags)

    def convert_i(self, el, text, parent_tags):
        """I like my bolds ** and my italics _."""
        return abstract_inline_conversion(lambda s: UNDERSCORE)(self, el, text, parent_tags)


def convert_to_markdown(content_html):
    converter = ClipitMarkdownConverter(heading_style=ATX, bullets="-")
    markdown_content = converter.convert(content_html)
    pretty_markdown_content = mdformat_text(markdown_content)
    return pretty_markdown_content
