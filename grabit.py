# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "click>=8.1.0,<8.2",
#   "readabilipy==0.3.0",
#   "markdownify==0.14.1",
#   "PyYAML==6.0.2",
#   "requests==2.32.3",
#   "text-unidecode==1.3",
#   "mdformat==0.7.21",
# ]
# ///
import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import click
import requests
import yaml
from click import ClickException
from markdownify import ATX, UNDERSCORE, MarkdownConverter, abstract_inline_conversion
from mdformat import text as mdformat_text
from readabilipy import simple_json_from_html_string
from requests import RequestException
from text_unidecode import unidecode

VERSION = "0.7.0"


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


@dataclass
class RenderFlags:
    include_source: bool
    include_title: bool
    yaml_frontmatter: bool


@dataclass
class OutputFlags:
    output_formats: list[OutputFormat]
    create_domain_subdir: bool
    overwrite: bool


class BaseGrabber:
    def can_handle(self, url: str):
        return True

    def grab(
        self,
        url: str,
        use_readability_js: bool,
        fallback_title: str,
        render_flags: RenderFlags,
        output_formats: list[OutputFormat],
    ) -> (str, dict[OutputFormat, str]):
        outputs = {}

        html_content = download_html_content(url)
        if should_output_raw_html(output_formats):
            outputs[OutputFormat.RAW_HTML] = html_content

        html_readable_content, title = extract_readable_content_and_title(html_content, use_readability_js)
        title = self.post_process_title(title, fallback_title)

        if should_output_readable_html(output_formats):
            outputs[OutputFormat.READABLE_HTML] = html_readable_content

        if should_output_markdown(output_formats):
            markdown_content = convert_to_markdown(html_readable_content)
            markdown_content = self.post_process_markdown(url, title, markdown_content, render_flags)

            outputs[OutputFormat.MD] = markdown_content
            outputs[OutputFormat.STDOUT_MD] = markdown_content

        return title, outputs

    def render_markdown(self, markdown_content):
        return markdown_content

    def handle_missing_title(self, title: str, fallback_title: str):
        if not title:
            title = fallback_title.format(date=datetime.now().strftime("%Y-%m-%d"))

        return title

    def post_process_markdown(
        self,
        url: str,
        title: str,
        markdown_content: str,
        render_flags: RenderFlags,
    ):
        markdown_content = try_include_source(render_flags.include_source, markdown_content, url)
        markdown_content = try_include_title(render_flags.include_title, markdown_content, title)
        markdown_content = try_add_yaml_frontmatter(render_flags.yaml_frontmatter, markdown_content, title, url)

        return markdown_content

    def post_process_title(self, title: str, fallback_title: str):
        title = self.handle_missing_title(title, fallback_title)
        title = unidecode(title)

        return title


class RedditGrabber(BaseGrabber):
    def can_handle(self, url: str):
        domain = urlparse(url).netloc.lower()
        return domain == "www.reddit.com" or domain == "old.reddit.com"

    def grab(
        self,
        url: str,
        use_readability_js: bool,
        fallback_title: str,
        render_flags: RenderFlags,
        output_formats: list[OutputFormat],
    ) -> (str, dict[OutputFormat, str]):
        if (
            should_output_raw_html(output_formats)
            or should_output_readable_html(output_formats)
            or not should_output_markdown(output_formats)
        ):
            raise ClickException("Reddit posts can only be converted to Markdown.")

        outputs = {}

        json_url = self._convert_to_json_url(url)
        json_content = json.loads(download_html_content(json_url))

        title = json_content[0]["data"]["children"][0]["data"].get("title", None)
        title = self.post_process_title(title, fallback_title)

        markdown_content = self._reddit_json_to_markdown(json_content)
        markdown_content = self.post_process_markdown(url, title, markdown_content, render_flags)

        outputs[OutputFormat.MD] = markdown_content
        outputs[OutputFormat.STDOUT_MD] = markdown_content

        return title, outputs

    def _convert_to_json_url(self, url):
        parsed_url = urlparse(url)

        path = parsed_url.path.rstrip("/")
        new_path = f"{path}.json"

        json_url = urlunparse(parsed_url._replace(path=new_path))
        return json_url

    def _reddit_json_to_markdown(self, reddit_post_json):
        def parse_comments(comments_data, depth=0):
            comments_md = ""
            # Sort comments by score, highest first
            sorted_comments = sorted(comments_data, key=lambda x: x["data"].get("score", 0), reverse=True)
            for comment in sorted_comments:
                comment_data = comment["data"]
                author = comment_data.get("author", "[deleted]")
                score = comment_data.get("score", 0)
                body = comment_data.get("body", "").replace("\n", "\n" + "    " * (depth + 1))
                indentation = "    " * depth

                comments_md += f"{indentation}- **{author}** [{score} score]:\n{indentation}    {body}\n\n"

                # Check if 'replies' is a dict (has replies), and recursively parse them
                if isinstance(comment_data.get("replies"), dict):
                    nested_comments = comment_data["replies"]["data"]["children"]
                    comments_md += parse_comments(nested_comments, depth + 1)

            return comments_md

        try:
            # Extract post information
            post_data = reddit_post_json[0]["data"]["children"][0]["data"]
            selftext = post_data.get("selftext", "").replace("\n", "\n> ")
            post_url = post_data.get("url", "")  # needed for link posts
            author = post_data.get("author", "[deleted]")
            score = post_data.get("score", 0)

            markdown = f"**{author}** [{score} score]:\n> {selftext if selftext else post_url  }\n\n"

            # Extract comments
            comments_data = reddit_post_json[1]["data"]["children"]
            markdown += "## Comments\n\n"
            markdown += parse_comments(comments_data)

        except Exception as e:
            raise ClickException(f"Error converting Reddit JSON to Markdown: {e}")

        return markdown


grabbers = [RedditGrabber()]


@click.command()
@click.argument("url")
@click.version_option(version=VERSION, prog_name="Grabit")
@click.option(
    "--yaml-frontmatter/--no-yaml-frontmatter",
    default=True,
    help="Include YAML front matter with metadata.",
    show_default=True,
)
@click.option(
    "--include-title/--no-include-title",
    default=True,
    help="Include the page title as an H1 heading.",
    show_default=True,
)
@click.option(
    "--include-source/--no-include-source",
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
    "--use-readability-js/--no-use-readability-js",
    default=True,
    help="Use Readability.js for processing pages, requires Node to be installed (recommended).",
    show_default=True,
)
@click.option(
    "--create-domain-subdir/--no-create-domain-subdir",
    default=True,
    help="Save the resulting file(s) in a subdirectory named after the domain.",
    show_default=True,
)
@click.option(
    "--overwrite/--no-overwrite",
    default=False,
    help="Overwrite existing files if they already exist.",
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
    overwrite: bool,
):
    """
    Download an URL, convert it to Markdown with specified options, and save it to a file.
    """

    grabber = next((g for g in grabbers if g.can_handle(url)), BaseGrabber())
    output_formats = [OutputFormat(format_str) for format_str in output_formats]

    render_flags = RenderFlags(
        include_source=include_source,
        include_title=include_title,
        yaml_frontmatter=yaml_frontmatter,
    )
    output_flags = OutputFlags(
        output_formats=output_formats,
        create_domain_subdir=create_domain_subdir,
        overwrite=overwrite,
    )

    title, outputs = grabber.grab(url, use_readability_js, fallback_title, render_flags, output_formats)
    output(title, outputs, url, output_flags)


def output(title: str, outputs: dict[OutputFormat, str], url: str, output_flags: OutputFlags):
    if should_output_file(outputs):
        if output_flags.create_domain_subdir:
            output_dir = create_output_dir(url)
        else:
            output_dir = Path(".")
        safe_title = sanitize_filename(title)

    for fmt in output_flags.output_formats:
        content = outputs.get(fmt)
        if should_output_file([fmt]):
            # output_dir and safe_title are only defined if we're saving to a file
            write_to_file(content, output_dir, safe_title, fmt, output_flags.overwrite)
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


def write_to_file(
    markdown_content: str,
    output_dir: str,
    safe_title: str,
    extension: str,
    overwrite: bool,
):
    output_file = Path(output_dir) / f"{safe_title}.{extension}"

    if not overwrite and output_file.exists():
        click.echo(f"File {output_file} already exists. Use --overwrite to replace it.")
        return

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


class GrabitMarkdownConverter(MarkdownConverter):
    def convert_em(self, el, text, convert_as_inline):
        return self.convert_i(el, text, convert_as_inline)

    def convert_i(self, el, text, convert_as_inline):
        """I like my bolds ** and my italics _."""
        return abstract_inline_conversion(lambda s: UNDERSCORE)(self, el, text, convert_as_inline)

    def _convert_hn(self, n: int, el: any, text: str, convert_as_inline: bool) -> str:
        header = super()._convert_hn(n, el, text, convert_as_inline)

        if convert_as_inline:
            return header

        # Add newline if the header doesn't start with one
        if not re.search(r"^\n", text):
            return "\n" + header

        return header


def convert_to_markdown(content_html):
    converter = GrabitMarkdownConverter(heading_style=ATX, bullets="-")
    markdown_content = converter.convert(content_html)
    pretty_markdown_content = mdformat_text(markdown_content)
    return pretty_markdown_content


def extract_readable_content_and_title(html_content, use_readability_js):
    try:
        rpy = simple_json_from_html_string(html_content, use_readability=use_readability_js)
        content_html = rpy.get("content", "")

        # If readability.js fails, try again without it
        if not content_html and use_readability_js:
            rpy = simple_json_from_html_string(html_content, use_readability=False)
            content_html = rpy.get("content", "")
            if not content_html:
                raise ClickException("No content found")

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
