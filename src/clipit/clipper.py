from pathlib import Path

from clipit.core import OutputFormat, OutputFormatList
from clipit.core.dtos import RenderFlags
from clipit.core.paths import get_output_directory
from clipit.core.writer import output
from clipit.grabbers import BaseGrabber, RedditGrabber

grabbers: list[BaseGrabber] = [RedditGrabber(), BaseGrabber()]


class Clipper:
    def __init__(self, user_agent: str | None = None):
        self.user_agent = user_agent

    def clip(
        self,
        url: str,
        use_readability_js: bool,
        fallback_title: str,
        include_source: bool,
        include_title: bool,
        yaml_frontmatter: bool,
        output_formats: list[str],
        download_images: bool = False,
        download_folder: str | None = None,
        output_dir: Path = Path("."),
    ) -> tuple[str, dict[OutputFormat, str], list[tuple[str, bytes]]]:
        grabber = next((g for g in grabbers if g.can_handle(url)), None)
        if grabber is None:
            raise ValueError("No grabber found for the given URL.")

        output_format_list: OutputFormatList = OutputFormatList(output_formats)
        render_flags = RenderFlags(
            include_source=include_source,
            include_title=include_title,
            yaml_frontmatter=yaml_frontmatter,
        )

        return grabber.grab(
            url,
            self.user_agent,
            use_readability_js,
            fallback_title,
            render_flags,
            output_format_list,
            download_images,
            download_folder,
            output_dir,
        )

    def clip_and_save(
        self,
        url: str,
        use_readability_js: bool,
        fallback_title: str,
        include_source: bool,
        include_title: bool,
        yaml_frontmatter: bool,
        output_formats: list[str],
        create_domain_subdir: bool,
        overwrite: bool,
        download_images: bool = False,
        download_folder: str | None = None,
    ) -> None:
        output_dir = get_output_directory(url, create_domain_subdir)
        title, outputs, images = self.clip(
            url,
            use_readability_js,
            fallback_title,
            include_source,
            include_title,
            yaml_frontmatter,
            output_formats,
            download_images,
            download_folder,
            output_dir,
        )
        output(
            title,
            outputs,
            url,
            create_domain_subdir,
            overwrite,
            images=images,
            output_dir=output_dir,
        )
