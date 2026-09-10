from os.path import relpath
from pathlib import Path
from string import Template
from urllib.parse import urlparse

from clipit.core.misc import ClipitError, sanitize_filename


def get_output_directory(url: str, create_domain_subdir: bool) -> Path:
    domain = urlparse(url).netloc.replace("www.", "") or "unknown_domain"
    return Path(domain) if create_domain_subdir else Path(".")


def get_image_directory(title: str, url: str, download_folder: str | None, output_dir: Path) -> Path:
    """Return the attachment directory relative to the document directory."""
    file_name = sanitize_filename(title) or "Untitled"
    if download_folder is None:
        return Path(file_name)

    try:
        folder = Template(download_folder).substitute(
            domain=get_output_directory(url, True).name,
            file_name=file_name,
        )
    except (KeyError, ValueError) as exc:
        raise ClipitError("Invalid download folder template. Use ${domain} and ${file_name}.") from exc

    return Path(relpath(folder, output_dir))
