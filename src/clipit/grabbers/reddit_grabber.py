import json
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from clipit.core import ClipitError, RenderFlags
from clipit.core.downloader import download_html_content
from clipit.core.output_format import OutputFormat, OutputFormatList
from clipit.grabbers.base_grabber import BaseGrabber


class RedditGrabber(BaseGrabber):
    def can_handle(self, url: str) -> bool:
        domain = urlparse(url).netloc.lower()
        return domain == "www.reddit.com" or domain == "old.reddit.com"

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
        if (
            output_formats.should_output_raw_html()
            or output_formats.should_output_readable_html()
            or not output_formats.should_output_markdown()
        ):
            raise ClipitError("Reddit posts can only be converted to Markdown.")

        outputs = {}

        json_url = self._convert_to_json_url(url)
        json_content = json.loads(download_html_content(json_url, user_agent))

        title = json_content[0]["data"]["children"][0]["data"].get("title", None)
        title = self.post_process_title(title, fallback_title)

        markdown_content = self._reddit_json_to_markdown(json_content)
        markdown_content = self.post_process_markdown(url, title, markdown_content, render_flags)

        outputs[OutputFormat.MD] = markdown_content
        outputs[OutputFormat.STDOUT_MD] = markdown_content

        return title, outputs, []

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

            markdown = f"**{author}** [{score} score]:\n> {selftext if selftext else post_url}\n\n"

            # Extract comments
            comments_data = reddit_post_json[1]["data"]["children"]
            markdown += "## Comments\n\n"
            markdown += parse_comments(comments_data)

        except Exception as e:
            raise ClipitError(f"Error converting Reddit JSON to Markdown: {str(e)}")

        return markdown
