import pytest
from clipit.core.output_format import OutputFormat
from clipit.core.writer import output, sanitize_filename


@pytest.mark.parametrize(
    "input_filename, expected_output",
    [
        ("invalid|file:name.txt", "invalidfilename.txt"),
        ("another/invalid\\name.txt", "anotherinvalidname.txt"),
        ("0%, 50%, or 200%", "0, 50, or 200"),
        ("valid_name.txt", "valid_name.txt"),
    ],
)
def test_sanitize_filename_should_work(input_filename, expected_output):
    assert sanitize_filename(input_filename) == expected_output


def test_sanitize_filename_should_not_create_hidden_files():
    assert sanitize_filename(".NET Core") == "NET Core"


def test_output_uses_fallback_when_sanitized_title_is_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    output(
        title="%",
        outputs={OutputFormat.MD: "# Title"},
        url="https://example.com/article",
        create_domain_subdir=False,
        overwrite=True,
    )

    assert (tmp_path / "Untitled.md").exists()


def test_output_saves_images_to_default_subfolder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    outputs = {OutputFormat.MD: "# Title"}
    images = [("sample.png", b"data")]

    output(
        title="Sample",
        outputs=outputs,
        url="https://example.com/article",
        create_domain_subdir=False,
        overwrite=True,
        images=images,
    )

    assert (tmp_path / "Sample.md").exists()
    assert (tmp_path / "sample.png").exists()


def test_output_saves_images_inside_domain_subdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    outputs = {OutputFormat.MD: "# Title"}
    images = [("sample.png", b"data")]

    output(
        title="Sample",
        outputs=outputs,
        url="https://www.example.com/article",
        create_domain_subdir=True,
        overwrite=True,
        images=images,
    )

    expected_dir = tmp_path / "example.com"
    assert (expected_dir / "Sample.md").exists()
    assert (expected_dir / "sample.png").exists()
