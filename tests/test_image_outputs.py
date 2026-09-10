from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest
from bs4 import BeautifulSoup
from click.testing import CliRunner
from clipit.cli import main
from clipit.core.misc import sanitize_filename
from markdown_it import MarkdownIt


@pytest.mark.parametrize("domain_subdir", [True, False])
@pytest.mark.parametrize("folder_kind", ["default", "relative", "absolute"])
def test_cli_keeps_each_articles_images_with_valid_links(image_server, tmp_path, monkeypatch, domain_subdir, folder_kind):
    base_url, server_directory, _ = image_server
    monkeypatch.chdir(tmp_path)
    table = BeautifulSoup((Path(__file__).parent / "fixtures" / "boring-table.html").read_text(), "html.parser")
    # Keep the row with article text so Readability selects it as content.
    for row in table.find_all("tr")[:-1]:
        row.decompose()
    for img in table.find_all("img"):
        img["src"] = "/converted.png"
    domain = urlparse(base_url).netloc
    output_dir = tmp_path / domain if domain_subdir else tmp_path
    args = ["--download-images", "--no-yaml-frontmatter", "-f", "md", "-f", "html"]
    args.append("--create-domain-subdir" if domain_subdir else "--no-create-domain-subdir")
    if folder_kind != "default":
        template = "attachments/${domain}/${file_name}"
        if folder_kind == "absolute":
            template = str(tmp_path / template)
        args.extend(["--download-folder", template])

    for title in ("Choose Boring Technology", "Choose Boring Technology’s [50%] slides"):
        page = f"<html><head><title>{title}</title></head><body>{table}</body></html>"
        (server_directory / "article.html").write_text(page)
        result = CliRunner().invoke(main, [*args, f"{base_url}/article.html"])
        assert result.exit_code == 0, result.output

        file_name = sanitize_filename(title)
        md_path = output_dir / f"{file_name}.md"
        image_dir = output_dir / file_name if folder_kind == "default" else tmp_path / "attachments" / domain / file_name
        image_path = image_dir / "converted.jpg"
        assert image_path.read_bytes() == (server_directory / "converted.png").read_bytes()
        destinations = [
            child.attrGet("src")
            for token in MarkdownIt().parse(md_path.read_text())
            for child in token.children or []
            if child.type == "image"
        ]
        html = BeautifulSoup(md_path.with_suffix(".html").read_text(), "html.parser")
        assert len(destinations) == len(html.find_all("img")) == 1
        for destination in destinations + [str(img["src"]) for img in html.find_all("img")]:
            assert isinstance(destination, str)
            assert (output_dir / unquote(destination)).resolve() == image_path.resolve()
        assert list(image_dir.iterdir()) == [image_path]
