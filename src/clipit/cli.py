import sys
from urllib.parse import urlparse

import click

from clipit import ClipitError, Clipper, OutputFormat, __version__
from clipit.core import DownloadError, RenderFlags
from clipit.core.bookmark import bookmark_outputs
from clipit.core.writer import output


@click.command()
@click.argument("url")
@click.option(
    "--bookmark-on-failure",
    is_flag=True,
    help="Save a Markdown bookmark on download failure without confirmation. Scripts fail by default.",
)
@click.option("--title", help="Title for the bookmark fallback (defaults to the URL hostname).")
@click.option("--notes", help="Markdown notes for the bookmark fallback.")
@click.option(
    "--user-agent",
    default=f"Clipit/{__version__}",
    help="The user agent reported when retrieving web pages",
    show_default=True,
)
@click.version_option(
    version=__version__,
    prog_name="Clipit",
    message="%(prog)s v%(version)s © 2025 Vlad Iliescu\n%(prog)s is licensed under the LGPL v3 License (https://www.gnu.org/licenses/lgpl-3.0.html)",
)
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
    "--download-images/--no-download-images",
    default=False,
    help="Download images referenced in the page and update links to point to local copies.",
    show_default=True,
)
@click.option(
    "-f",
    "--format",
    "output_formats",
    multiple=True,
    default=[OutputFormat.MD.value],
    type=click.Choice([fmt.value for fmt in OutputFormat], case_sensitive=False),
    help="Which output format(s) to use when saving the content. Can be specified multiple times i.e. -f md -f html",
    show_default=True,
)
def main(
    url: str,
    bookmark_on_failure: bool,
    title: str | None,
    notes: str | None,
    user_agent: str,
    use_readability_js: bool,
    yaml_frontmatter: bool,
    include_title: bool,
    include_source: bool,
    fallback_title: str,
    create_domain_subdir: bool,
    output_formats: list[str],
    overwrite: bool,
    download_images: bool,
) -> None:
    """
    Download a URL, convert it to Markdown/HTML with specified options, and save it to a file.
    """
    try:
        clipper = Clipper(user_agent=user_agent)
        try:
            clipper.clip_and_save(
                url=url,
                use_readability_js=use_readability_js,
                fallback_title=fallback_title,
                include_source=include_source,
                include_title=include_title,
                yaml_frontmatter=yaml_frontmatter,
                output_formats=list(output_formats),
                create_domain_subdir=create_domain_subdir,
                overwrite=overwrite,
                download_images=download_images,
            )
        except DownloadError as e:
            interactive = sys.stdin.isatty() and sys.stderr.isatty()
            if not bookmark_on_failure and not interactive:
                raise

            click.echo(str(e), err=True)
            if not bookmark_on_failure and not click.confirm("Save a bookmark instead?", default=False, err=True):
                raise

            page_title = title or urlparse(url).hostname or url
            if interactive:
                if title is None:
                    page_title = click.prompt("Title", default=page_title, err=True)
                if notes is None:
                    notes = click.prompt("Notes (optional)", default="", show_default=False, err=True)

            outputs = bookmark_outputs(
                url,
                page_title,
                notes or "",
                RenderFlags(
                    include_source=include_source or not yaml_frontmatter,
                    include_title=include_title,
                    yaml_frontmatter=yaml_frontmatter,
                ),
                list(output_formats),
            )
            output(page_title, outputs, url, create_domain_subdir, overwrite)
    except ClipitError as e:
        raise click.ClickException(str(e))


if __name__ == "__main__":
    main()
