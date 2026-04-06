from readabilipy import simple_json_from_html_string

from clipit.core import ClipitError
from clipit.core.readabilipy_runtime import ensure_readabilipy_node_runtime


def extract_readable_content_and_title(html_content, use_readability_js):
    try:
        use_readability = use_readability_js and ensure_readabilipy_node_runtime()
        rpy = None
        content_html = ""

        if use_readability:
            try:
                rpy = simple_json_from_html_string(html_content, use_readability=True)
                content_html = rpy.get("content") or ""
            except Exception:
                content_html = ""

        if not content_html:
            rpy = simple_json_from_html_string(html_content, use_readability=False)
            content_html = rpy.get("content") or ""
            if not content_html:
                raise ClipitError("No content found")

        if rpy is None:
            raise ClipitError("No content found")

        content_html = content_html.replace(
            'href="about:blank/', 'href="../'
        )  # Fix for readability replacing ".." with "about:blank"
        title = (rpy.get("title") or "").strip()
    except Exception as e:
        raise ClipitError(f"Error processing HTML content: {e}")
    return (
        content_html,
        title,
    )
