import os
import subprocess
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
import yaml


@pytest.fixture
def site(tmp_path):
    directory = tmp_path / "site"
    directory.mkdir()
    (directory / "empty.html").write_text("<html><body></body></html>", encoding="utf-8")
    (directory / "index.html").write_text(
        "<html><head><title>Example Domain</title></head><body><article>"
        "<h1>Example Domain</h1><p>This domain is for use in illustrative examples in documents. "
        "You may use this domain in literature without prior coordination or asking for permission.</p>"
        "</article></body></html>",
        encoding="utf-8",
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(directory)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture
def run_cli(tmp_path):
    workdir = tmp_path / "output"
    workdir.mkdir()

    def run(*args, terminal_input=None):
        command = [sys.executable, "-m", "clipit.cli", "--no-create-domain-subdir", "--no-use-readability-js", *args]
        if terminal_input is None:
            return subprocess.run(command, cwd=workdir, input="", capture_output=True, text=True, timeout=10)

        if os.name != "posix":
            pytest.skip("Terminal interaction requires a POSIX pseudo-terminal")
        import pty

        master, slave = pty.openpty()
        try:
            os.write(master, terminal_input.encode())
            result = subprocess.run(
                command, cwd=workdir, stdin=slave, stdout=subprocess.PIPE, stderr=slave, text=True, timeout=10
            )
            result.stderr = os.read(master, 65536).decode()
            return result
        finally:
            os.close(master)
            os.close(slave)

    return workdir, run


def test_noninteractive_download_failure_errors_by_default(site, run_cli):
    workdir, run = run_cli
    result = run(f"{site}/missing", "--title", "Bookmark", "--notes", "Notes")

    assert result.returncode == 1
    assert "404" in result.stderr
    assert "Save a bookmark" not in result.stderr
    assert list(workdir.iterdir()) == []


def test_noninteractive_fallback_saves_metadata_and_notes(site, run_cli):
    workdir, run = run_cli
    result = run(
        f"{site}/missing", "--bookmark-on-failure", "--title", "My bookmark", "--notes", "Some **Markdown** notes."
    )

    assert result.returncode == 0, result.stderr
    markdown = (workdir / "My bookmark.md").read_text()
    metadata = yaml.safe_load(markdown.split("---", 2)[1])
    assert metadata["title"] == "My bookmark"
    assert metadata["source"] == f"{site}/missing"
    assert "Some **Markdown** notes." in markdown


def test_fallback_stdout_preserves_url_without_frontmatter(site, run_cli):
    workdir, run = run_cli
    result = run(f"{site}/missing", "--bookmark-on-failure", "-f", "stdout.md", "--no-yaml-frontmatter")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"# 127.0.0.1\n\n[Source]({site}/missing)"
    assert list(workdir.iterdir()) == []


@pytest.mark.parametrize(
    "args, terminal_input",
    [
        ([], "y\nManual title\nManual notes\n"),
        (["--bookmark-on-failure"], "Manual title\nManual notes\n"),
    ],
)
def test_interactive_fallback_saves_manual_details(site, run_cli, args, terminal_input):
    workdir, run = run_cli
    result = run(f"{site}/missing", *args, terminal_input=terminal_input)

    assert result.returncode == 0, result.stderr
    markdown = (workdir / "Manual title.md").read_text()
    assert "# Manual title" in markdown
    assert "Manual notes" in markdown


def test_declining_bookmark_preserves_download_error(site, run_cli):
    workdir, run = run_cli
    result = run(f"{site}/missing", terminal_input="n\n")

    assert result.returncode == 1
    assert "404" in result.stderr
    assert list(workdir.iterdir()) == []


def test_successful_download_ignores_bookmark_options(site, run_cli):
    workdir, run = run_cli
    result = run(site, "--bookmark-on-failure", "--title", "Bookmark title", "--notes", "Bookmark notes")

    assert result.returncode == 0, result.stderr
    markdown = (workdir / "Example Domain.md").read_text()
    assert "illustrative examples" in markdown
    assert "Bookmark notes" not in markdown


def test_extraction_failure_does_not_create_a_bookmark(site, run_cli):
    workdir, run = run_cli
    result = run(f"{site}/empty.html", "--bookmark-on-failure")

    assert result.returncode == 1
    assert "Error processing HTML content" in result.stderr
    assert list(workdir.iterdir()) == []


def test_html_download_failure_saves_a_markdown_bookmark(site, run_cli):
    workdir, run = run_cli
    result = run(f"{site}/missing", "--bookmark-on-failure", "--title", "Bookmark", "-f", "html")

    assert result.returncode == 0, result.stderr
    assert (workdir / "Bookmark.md").exists()
    assert not (workdir / "Bookmark.html").exists()
