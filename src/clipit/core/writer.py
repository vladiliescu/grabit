from pathlib import Path
from urllib.parse import urlparse

import click

from clipit.core import ClipitError, OutputFlags, OutputFormat
from clipit.core.misc import sanitize_filename


def should_output_file(output_formats: dict[OutputFormat, str]) -> bool:
    return any(fmt.is_file_output() for fmt in output_formats)


def output(
    title: str,
    outputs: dict[OutputFormat, str],
    url: str,
    create_domain_subdir: bool,
    overwrite: bool,
    images: list[tuple[str, bytes]] | None = None,
):
    output_dir = None
    safe_title = None

    output_flags = OutputFlags(
        create_domain_subdir=create_domain_subdir,
        overwrite=overwrite,
    )

    if should_output_file(outputs):
        if output_flags.create_domain_subdir:
            output_dir = create_output_dir(url)
        else:
            output_dir = Path(".")
        safe_title = sanitize_filename(title) or "Untitled"

        if images:
            save_images(output_dir, images, output_flags.overwrite)

    for format, output in outputs.items():
        if format.is_file_output():
            # output_dir and safe_title are only defined if we're saving to a file
            if output is not None and output_dir is not None and safe_title is not None:
                write_to_file(output, str(output_dir), safe_title, format.value, output_flags.overwrite)
        else:
            if output is not None:
                click.echo(output)


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
        raise ClipitError(f"Error writing to file {output_file}: {e}")


def create_output_dir(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace("www.", "")
    if not domain:
        domain = "unknown_domain"
    output_dir = Path(".") / domain
    output_dir.mkdir(exist_ok=True, parents=True)

    return output_dir


def save_images(output_dir: Path, images: list[tuple[str, bytes]], overwrite: bool) -> None:
    for filename, image_bytes in images:
        image_path = output_dir / filename
        if not overwrite and image_path.exists():
            click.echo(f"Image {image_path} already exists. Use --overwrite to replace it.")
            continue

        try:
            image_path.parent.mkdir(parents=True, exist_ok=True)
            with open(image_path, "wb") as image_file:
                image_file.write(image_bytes)
            click.echo(f"Saved image to {image_path}")
        except Exception as exc:
            click.echo(f"Failed to save image {image_path}: {exc}")
