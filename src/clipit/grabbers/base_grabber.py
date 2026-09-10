from datetime import datetime
from pathlib import Path

from clipit.core import OutputFormat, OutputFormatList, RenderFlags
from clipit.core.downloader import download_html_content
from clipit.core.extractor import extract_readable_content_and_title
from clipit.core.image_processor import process_images
from clipit.core.markdown_converter import (
    convert_to_markdown,
    try_add_yaml_frontmatter,
    try_include_source,
    try_include_title,
)
from clipit.core.paths import get_image_directory


class BaseGrabber:
    def can_handle(self, url: str) -> bool:
        return True

    def grab(
        self,
        url: str,
        user_agent: str | None,
        use_readability_js: bool,
        fallback_title: str,
        render_flags: RenderFlags,
        output_formats: OutputFormatList,
        download_images: bool,
        download_folder: str | None = None,
        output_dir: Path = Path("."),
    ) -> tuple[str, dict[OutputFormat, str], list[tuple[str, bytes]]]:
        outputs = {}
        images: list[tuple[str, bytes]] = []

        html_content = download_html_content(url, user_agent)
        if output_formats.should_output_raw_html():
            outputs[OutputFormat.RAW_HTML] = html_content

        html_readable_content, title = extract_readable_content_and_title(html_content, use_readability_js)
        title = self.post_process_title(title, fallback_title)

        should_download_images = download_images and any(fmt.is_file_output() for fmt in output_formats)

        if should_download_images:
            directory = get_image_directory(title, url, download_folder, output_dir)
            processed_html, images = process_images(html_readable_content, title, url, user_agent, directory)
            html_readable_content = processed_html

        if output_formats.should_output_readable_html():
            outputs[OutputFormat.READABLE_HTML] = html_readable_content

        if output_formats.should_output_markdown():
            markdown_content = convert_to_markdown(html_readable_content)
            markdown_content = self.post_process_markdown(url, title, markdown_content, render_flags)

            if output_formats.should_output_markdown_file():
                outputs[OutputFormat.MD] = markdown_content

            if output_formats.should_output_markdown_stdout():
                outputs[OutputFormat.STDOUT_MD] = markdown_content

        return title, outputs, images

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

        return title
