import pytest

from grabit import sanitize_filename


@pytest.mark.parametrize(
    "input_filename, expected_output",
    [
        ("invalid|file:name.txt", "invalid_file_name.txt"),
        ("another/invalid\\name.txt", "another_invalid_name.txt"),
        ("valid_name.txt", "valid_name.txt"),
    ],
)
def test_sanitize_filename_should_work(input_filename, expected_output):
    assert sanitize_filename(input_filename) == expected_output
