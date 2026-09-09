from clipit.core import OutputFormat, RenderFlags
from clipit.grabbers.base_grabber import BaseGrabber


def bookmark_outputs(
    url: str,
    title: str,
    notes: str,
    render_flags: RenderFlags,
    output_formats: list[str],
) -> dict[OutputFormat, str]:
    markdown_content = BaseGrabber().post_process_markdown(url, title, notes, render_flags)
    formats = {
        OutputFormat.MD if OutputFormat(fmt).is_file_output() else OutputFormat.STDOUT_MD for fmt in output_formats
    }
    return {fmt: markdown_content for fmt in formats}
