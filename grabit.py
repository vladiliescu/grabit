# /// script
# dependencies = [
# ]
# ///
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse

import click
import requests
import yaml
from click import ClickException
from markdownify import ATX, UNDERSCORE, MarkdownConverter, abstract_inline_conversion
from readabilipy import simple_json_from_html_string
from requests import RequestException
from text_unidecode import unidecode


class OutputFormat(Enum):
    MD = "md"
    STDOUT_MD = "stdout.md"
    READABLE_HTML = "html"
    RAW_HTML = "raw.html"

    def __str__(self):
        return self.value


def should_output_raw_html(output_formats):
    return OutputFormat.RAW_HTML in output_formats


def should_output_readable_html(output_formats):
    return OutputFormat.READABLE_HTML in output_formats


def should_output_markdown(output_formats):
    return OutputFormat.MD in output_formats or OutputFormat.STDOUT_MD in output_formats


def should_output_file(output_formats):
    return any("stdout" not in fmt.value for fmt in output_formats)


@click.command()
@click.argument("url")
@click.option(
    "--yaml-frontmatter",
    is_flag=True,
    default=True,
    help="Include YAML front matter with metadata.",
    show_default=True,
)
@click.option(
    "--include-title",
    is_flag=True,
    default=True,
    help="Include the page title as an H1 heading.",
    show_default=True,
)
@click.option(
    "--include-source",
    is_flag=True,
    default=False,
    help="Include the page source.",
    show_default=True,
)
@click.option(
    "--fallback-title",
    default="Untitled {date}",
    help="Fallback title if no title is found. Use {date} for current date.",
    show_default=True,
)
@click.option(
    "--use-readability-js",
    is_flag=True,
    default=True,
    help="Use Readability.js for processing pages, requires Node to be installed (recommended).",
    show_default=True,
)
@click.option(
    "--create-domain-subdir",
    is_flag=True,
    default=True,
    help="Save the resulting file(s) in a subdirectory named after the domain.",
    show_default=True,
)
@click.option(
    "-f",
    "--format",
    "output_formats",
    multiple=True,
    default=[OutputFormat.MD.value],
    type=click.Choice(
        [fmt.value for fmt in OutputFormat],
        case_sensitive=False,
    ),
    help="Output format(s) to save the content in. Can be specified multiple times i.e. -f md -f html",
    show_default=True,
)
def save(
    url: str,
    use_readability_js: bool,
    yaml_frontmatter: bool,
    include_title: bool,
    include_source: bool,
    fallback_title: str,
    create_domain_subdir: bool,
    output_formats: list[str],
):
    """
    Download an URL, convert it to Markdown with specified options, and save it to a file.
    """

    output_formats = [OutputFormat(format_str) for format_str in output_formats]
    content_formats = {}

    html_content = download_html_content(url)
    if should_output_raw_html(output_formats):
        content_formats[OutputFormat.RAW_HTML] = html_content

    html_readable_content, title = extract_readable_content_and_title(
        html_content, use_readability_js
    )
    if should_output_readable_html(output_formats):
        content_formats[OutputFormat.READABLE_HTML] = html_readable_content

    title = handle_missing_title(fallback_title, title)
    title = unidecode(title)

    if should_output_markdown(output_formats):
        markdown_content = convert_to_markdown(html_readable_content)

        markdown_content = try_include_source(include_source, markdown_content, url)
        markdown_content = try_include_title(include_title, markdown_content, title)
        markdown_content = try_add_yaml_frontmatter(
            markdown_content, yaml_frontmatter, title, url
        )

        content_formats[OutputFormat.MD] = markdown_content
        content_formats[OutputFormat.STDOUT_MD] = markdown_content

    if should_output_file(output_formats):
        if create_domain_subdir:
            output_dir = create_output_dir(url)
        else:
            output_dir = Path(".")
        safe_title = sanitize_filename(title)

    for fmt in output_formats:
        content = content_formats[fmt]

        if should_output_file([fmt]):
            # output_dir and safe_title are only defined if we're saving to a file
            write_to_file(content, output_dir, safe_title, fmt)
        else:
            click.echo(content)


def sanitize_filename(filename):
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
    return sanitized


def try_include_title(include_title, markdown_content, title):
    if include_title:
        markdown_content = f"# {title}\n\n{markdown_content}"
    return markdown_content


def try_include_source(include_source, markdown_content, url):
    if include_source:
        markdown_content = f"[Source]({url})\n\n{markdown_content}"
    return markdown_content


def try_add_yaml_frontmatter(markdown_content, yaml_frontmatter, title, url):
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


def write_to_file(markdown_content, output_dir, safe_title, extension):
    output_file = Path(output_dir) / f"{safe_title}.{extension}"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        click.echo(f"Saved {extension} content to {output_file}")
    except Exception as e:
        raise ClickException(f"Error writing to file {output_file}: {e}")


def create_output_dir(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace("www.", "")
    if not domain:
        domain = "unknown_domain"
    output_dir = Path(".") / domain
    output_dir.mkdir(exist_ok=True, parents=True)

    return output_dir


class GrabitConverter(MarkdownConverter):
    def convert_em(self, el, text, convert_as_inline):
        return self.convert_i(el, text, convert_as_inline)

    def convert_i(self, el, text, convert_as_inline):
        """I like my bolds ** and my italics _."""
        return abstract_inline_conversion(lambda s: UNDERSCORE)(
            self, el, text, convert_as_inline
        )

    def _convert_hn(self, n: int, el: any, text: str, convert_as_inline: bool) -> str:
        header = super()._convert_hn(n, el, text, convert_as_inline)

        if convert_as_inline:
            return header

        # Add newline if the header doesn't start with one
        if not re.search(r"^\n", text):
            return "\n" + header

        return header


def convert_to_markdown(content_html):
    converter = GrabitConverter(heading_style=ATX, bullets="-")
    markdown_content = converter.convert(content_html)
    return markdown_content


def handle_missing_title(fallback_title, title):
    if not title:
        title = fallback_title.format(date=datetime.now().strftime("%Y-%m-%d"))

    return title


def extract_readable_content_and_title(html_content, use_readability_js):
    try:
        rpy = simple_json_from_html_string(
            html_content, use_readability=use_readability_js
        )
        content_html = rpy.get("content", "")
        content_html = content_html.replace(
            'href="about:blank/', 'href="../'
        )  # Fix for readability replacing ".." with "about:blank"
        title = rpy.get("title", "").strip()
    except Exception as e:
        raise ClickException(f"Error processing HTML content: {e}")
    return (
        content_html,
        title,
    )


def download_html_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        html_content = response.text
    except RequestException as e:
        raise ClickException(f"Error downloading {url}: {e}")
    return html_content


if __name__ == "__main__":
    save()
