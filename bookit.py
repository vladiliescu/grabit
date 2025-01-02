# /// script
# dependencies = [
# ]
# ///
import re

import click
import requests
from readabilipy import simple_json_from_html_string
from markdownify import ATX
from urllib.parse import urlparse
from datetime import datetime
import os
import yaml
import sys
from text_unidecode import unidecode
from markdownify import MarkdownConverter


from pathlib import Path


# Function to sanitize filenames
def sanitize_filename(filename):
    return Path(filename)


@click.command()
@click.argument("url")
@click.option(
    "--inline-links",
    is_flag=True,
    default=True,
    help="Use inline links instead of reference-style links.",
)
@click.option(
    "--metadata-yaml",
    is_flag=True,
    default=True,
    help="Include YAML front matter with metadata.",
)
@click.option(
    "--include-title",
    is_flag=True,
    default=True,
    help="Include the page title as an H1 heading.",
)
@click.option(
    "--include-comments",
    is_flag=True,
    default=True,
    help="Include comments from StackExchange pages.",
)
@click.option(
    "--fallback-title",
    default="webclip {date}",
    help="Fallback title if no title is found. Use {date} for current date.",
)
@click.option(
    "--use-readability-js",
    is_flag=True,
    default=True,
    help="Use Readability.js for processing pages, requires Node to be installed (recommended).",
)
@click.option(
    "--format",
    multiple=True,
    default=["md"],
    help="Output format(s) to save the content in (md, html, raw.html). Can be specified multiple times i.e. --format md --format html",
)
def save(
    url,
    inline_links,
    use_readability_js,
    metadata_yaml,
    include_title,
    include_comments,
    fallback_title,
    format,
):
    """
    Download a URL, convert it to Markdown with specified options, and save it to a file.
    """

    html_content = download_html_content(url)
    html_readable_content, title = extract_readable_content_and_title(
        html_content, use_readability_js
    )
    title = handle_missing_title(fallback_title, title)
    title = unidecode(title)

    markdown_content = convert_to_markdown(html_readable_content)

    # Include title as H1
    if include_title:
        markdown_content = f"# {title}\n\n{markdown_content}"

    # Include comments for StackExchange pages
    if include_comments and "stackoverflow.com/questions/" in url:
        comments_md = extract_stackexchange_comments(html_content)
        if comments_md:
            markdown_content += f"\n\n## Comments\n\n{comments_md}"

    # Add YAML front matter
    if metadata_yaml:
        metadata = {
            "title": title,
            "source": url,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        yaml_metadata = yaml.dump(metadata, sort_keys=False)
        markdown_content = f"---\n{yaml_metadata}---\n\n{markdown_content}"

    output_dir = create_output_dir(url)

    safe_title = sanitize_filename(title)

    content_formats = {
        "md": markdown_content,
        "html": html_readable_content,
        "raw.html": html_content,
    }

    for fmt in format:
        if fmt not in content_formats:
            click.echo(f"Invalid format: {fmt}", err=True)
            continue

        write_to_file(content_formats[fmt], output_dir, safe_title, fmt)


def write_to_file(markdown_content, output_dir, safe_title, extension):
    output_file = os.path.join(output_dir, f"{safe_title}.{extension}")
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        click.echo(f"Saved {extension} content to {output_file}")
    except Exception as e:
        click.echo(f"Error writing to file {output_file}: {e}", err=True)
        sys.exit(1)


def create_output_dir(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace("www.", "")
    if not domain:
        domain = "unknown_domain"
    output_dir = os.path.join(os.getcwd(), domain)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


class BookitConverter(MarkdownConverter):
    def _convert_hn(self, n: int, el: any, text: str, convert_as_inline: bool) -> str:
        header = super()._convert_hn(n, el, text, convert_as_inline)

        if convert_as_inline:
            return header

        # Remove anchor link if present
        parts = header.split("[", 1)
        if len(parts) > 1 and "](" in parts[1]:
            header = parts[0].strip()

        # Add newline if the header doesn't start with one
        if not re.search(r"^\n", text):
            return "\n" + header

        return header


def convert_to_markdown(content_html):
    converter = BookitConverter(heading_style=ATX, bullets="-")
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
        )  # Fix for readability replacing .. with about:blank
        title = rpy.get("title", "").strip()
        source_url = rpy.get("domain", "")
    except Exception as e:
        click.echo(f"Error processing HTML content: {e}", err=True)
        sys.exit(1)
    return content_html, title


def download_html_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        html_content = response.text
    except requests.RequestException as e:
        click.echo(f"Error downloading {url}: {e}", err=True)
        sys.exit(1)
    return html_content


def extract_stackexchange_comments(html_content):
    """
    Extract comments from StackExchange question pages.
    Returns Markdown formatted comments.
    """
    from bs4 import BeautifulSoup

    try:
        soup = BeautifulSoup(html_content, "html.parser")
        comments_div = soup.find("div", {"id": "comments"})
        if not comments_div:
            return ""

        comments = []
        for comment in comments_div.find_all("div", {"class": "comment"}):
            author = comment.find("a", {"class": "comment-user"}).get_text(strip=True)
            content = comment.find("span", {"class": "comment-copy"}).get_text(
                strip=True
            )
            comments.append(f"**{author}:** {content}")

        return "\n\n".join(comments)
    except Exception as e:
        click.echo(f"Error extracting comments: {e}", err=True)
        return ""


if __name__ == "__main__":
    save()
