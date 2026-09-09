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
        command = [sys.executable, "-m", "clipit.cli", *args]
        if terminal_input is None:
            return subprocess.run(command, cwd=workdir, input="", capture_output=True, text=True, timeout=120)

        if os.name != "posix":
            pytest.skip("Terminal interaction requires a POSIX pseudo-terminal")
        import pty

        master, slave = pty.openpty()
        try:
            with subprocess.Popen(
                command, cwd=workdir, stdin=slave, stdout=subprocess.PIPE, stderr=slave, text=True
            ) as process:
                os.write(master, terminal_input.encode())
                try:
                    stdout, _ = process.communicate(timeout=120)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                    raise
                stderr = os.read(master, 65536).decode()
                return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
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


@pytest.mark.parametrize("supplied_title", [None, "My bookmark"])
def test_noninteractive_fallback_saves_metadata_and_notes(site, run_cli, supplied_title):
    workdir, run = run_cli
    args = [f"{site}/missing", "--bookmark-on-failure", "--notes", "Some **Markdown** notes."]
    if supplied_title:
        args.extend(["--title", supplied_title])
    result = run(*args)

    assert result.returncode == 0, result.stderr
    title = supplied_title or "127.0.0.1"
    markdown = (workdir / f"127.0.0.1:{site.rsplit(':', 1)[1]}" / f"{title}.md").read_text()
    metadata = yaml.safe_load(markdown.split("---", 2)[1])
    assert metadata["title"] == title
    assert metadata["source"] == f"{site}/missing"
    assert metadata["date"]
    assert f"# {title}" in markdown
    assert "Some **Markdown** notes." in markdown
    assert "Save a bookmark" not in result.stderr


def test_fallback_stdout_preserves_url_without_frontmatter(site, run_cli):
    workdir, run = run_cli
    result = run(
        f"{site}/missing", "--bookmark-on-failure", "-f", "stdout.md", "--no-yaml-frontmatter", "--no-include-title"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"[Source]({site}/missing)"
    assert "404" in result.stderr
    assert list(workdir.iterdir()) == []


@pytest.mark.parametrize(
    "args, terminal_input, saved, confirmation",
    [
        ([], "y\nManual title\nManual notes\n", True, True),
        ([], "n\n", False, True),
        (["--bookmark-on-failure"], "Manual title\nManual notes\n", True, False),
    ],
)
def test_interactive_fallback(site, run_cli, args, terminal_input, saved, confirmation):
    workdir, run = run_cli
    result = run(f"{site}/missing", "--no-create-domain-subdir", *args, terminal_input=terminal_input)

    assert ("Save a bookmark instead?" in result.stderr) is confirmation
    assert result.returncode == (0 if saved else 1), result.stderr
    if saved:
        markdown = (workdir / "Manual title.md").read_text()
        assert "# Manual title" in markdown
        assert "Manual notes" in markdown
    else:
        assert list(workdir.iterdir()) == []


def test_successful_download_ignores_bookmark_options(site, run_cli):
    workdir, run = run_cli
    result = run(
        site,
        "--bookmark-on-failure",
        "--title",
        "Bookmark title",
        "--notes",
        "Bookmark notes",
        "--no-use-readability-js",
        "--no-create-domain-subdir",
    )

    assert result.returncode == 0, result.stderr
    markdown = (workdir / "Example Domain.md").read_text()
    assert "illustrative examples" in markdown
    assert "Bookmark notes" not in markdown


def test_extraction_failure_does_not_create_a_bookmark(site, run_cli):
    workdir, run = run_cli
    result = run(f"{site}/empty.html", "--bookmark-on-failure", "--no-use-readability-js")

    assert result.returncode == 1
    assert "Error processing HTML content" in result.stderr
    assert list(workdir.iterdir()) == []


def test_fallback_honors_overwrite_and_uses_markdown_for_html_requests(site, run_cli):
    workdir, run = run_cli
    bookmark = workdir / "Bookmark.md"
    bookmark.write_text("Existing content")
    args = [
        f"{site}/missing",
        "--bookmark-on-failure",
        "--title",
        "Bookmark",
        "--notes",
        "Replacement notes",
        "--no-create-domain-subdir",
        "-f",
        "html",
    ]

    result = run(*args)
    assert result.returncode == 0, result.stderr
    assert bookmark.read_text() == "Existing content"

    result = run(*args, "--overwrite")
    assert result.returncode == 0, result.stderr
    assert "Replacement notes" in bookmark.read_text()
    assert not (workdir / "Bookmark.html").exists()
