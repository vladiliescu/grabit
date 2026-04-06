import json
import subprocess

from clipit.core import readabilipy_runtime
from clipit.core.readabilipy_runtime import (
    PINNED_READABILIPY_JS_DEPENDENCIES,
    _pin_package_json_dependencies,
    _repair_node_runtime,
    _runtime_is_compatible,
)


def test_runtime_is_compatible_for_known_good_jsdom_bundle(tmp_path):
    js_directory = tmp_path / "javascript"
    jsdom_package = js_directory / "node_modules" / "jsdom"
    css_color_package = js_directory / "node_modules" / "@asamuzakjp" / "css-color"
    readability_package = js_directory / "node_modules" / "@mozilla" / "readability"
    minimist_package = js_directory / "node_modules" / "minimist"
    jsdom_package.mkdir(parents=True)
    css_color_package.mkdir(parents=True)
    readability_package.mkdir(parents=True)
    minimist_package.mkdir(parents=True)
    (jsdom_package / "package.json").write_text(json.dumps({"version": "27.0.0"}))
    (css_color_package / "package.json").write_text(json.dumps({"version": "4.0.5"}))
    (readability_package / "package.json").write_text(json.dumps({"version": "0.6.0"}))
    (minimist_package / "package.json").write_text(json.dumps({"version": "1.2.8"}))

    assert _runtime_is_compatible(js_directory) is True


def test_runtime_is_incompatible_for_jsdom_29_bundle(tmp_path):
    js_directory = tmp_path / "javascript"
    jsdom_package = js_directory / "node_modules" / "jsdom"
    css_color_package = js_directory / "node_modules" / "@asamuzakjp" / "css-color"
    readability_package = js_directory / "node_modules" / "@mozilla" / "readability"
    minimist_package = js_directory / "node_modules" / "minimist"
    jsdom_package.mkdir(parents=True)
    css_color_package.mkdir(parents=True)
    readability_package.mkdir(parents=True)
    minimist_package.mkdir(parents=True)
    (jsdom_package / "package.json").write_text(json.dumps({"version": "29.0.1"}))
    (css_color_package / "package.json").write_text(json.dumps({"version": "5.1.5"}))
    (readability_package / "package.json").write_text(json.dumps({"version": "0.6.0"}))
    (minimist_package / "package.json").write_text(json.dumps({"version": "1.2.8"}))

    assert _runtime_is_compatible(js_directory) is False


def test_pin_package_json_dependencies_writes_exact_versions(tmp_path):
    package_json_path = tmp_path / "package.json"
    package_json_path.write_text(
        json.dumps(
            {
                "name": "ReadabiliPy",
                "dependencies": {
                    "@mozilla/readability": ">=0.4.1",
                    "jsdom": ">=12.2.0",
                    "minimist": "^1.2.3",
                },
            }
        )
    )

    _pin_package_json_dependencies(package_json_path)

    package_data = json.loads(package_json_path.read_text())
    assert package_data["dependencies"] == PINNED_READABILIPY_JS_DEPENDENCIES


def test_runtime_is_incompatible_for_incomplete_runtime(tmp_path):
    js_directory = tmp_path / "javascript"
    jsdom_package = js_directory / "node_modules" / "jsdom"
    jsdom_package.mkdir(parents=True)
    (jsdom_package / "package.json").write_text(json.dumps({"version": "27.0.0"}))

    assert _runtime_is_compatible(js_directory) is False


def test_repair_node_runtime_reinstalls_with_pinned_dependencies(tmp_path, monkeypatch):
    js_directory = tmp_path / "javascript"
    js_directory.mkdir()

    package_json_path = js_directory / "package.json"
    package_json_path.write_text(
        json.dumps(
            {
                "name": "ReadabiliPy",
                "dependencies": {
                    "@mozilla/readability": ">=0.4.1",
                    "jsdom": ">=12.2.0",
                    "minimist": "^1.2.3",
                },
            }
        )
    )
    (js_directory / "package-lock.json").write_text('{"lock":"original"}\n')

    existing_jsdom_path = js_directory / "node_modules" / "jsdom"
    existing_jsdom_path.mkdir(parents=True)
    (existing_jsdom_path / "package.json").write_text(json.dumps({"version": "29.0.1"}))

    def fake_run(*_args, **_kwargs):
        assert not (js_directory / "node_modules").exists()
        assert not (js_directory / "package-lock.json").exists()
        package_data = json.loads(package_json_path.read_text())
        assert package_data["dependencies"] == PINNED_READABILIPY_JS_DEPENDENCIES

        repaired_jsdom_path = js_directory / "node_modules" / "jsdom"
        repaired_css_color_path = js_directory / "node_modules" / "@asamuzakjp" / "css-color"
        repaired_readability_path = js_directory / "node_modules" / "@mozilla" / "readability"
        repaired_minimist_path = js_directory / "node_modules" / "minimist"
        repaired_jsdom_path.mkdir(parents=True, exist_ok=True)
        repaired_css_color_path.mkdir(parents=True, exist_ok=True)
        repaired_readability_path.mkdir(parents=True, exist_ok=True)
        repaired_minimist_path.mkdir(parents=True, exist_ok=True)
        (repaired_jsdom_path / "package.json").write_text(json.dumps({"version": "27.0.0"}))
        (repaired_css_color_path / "package.json").write_text(json.dumps({"version": "4.0.5"}))
        (repaired_readability_path / "package.json").write_text(json.dumps({"version": "0.6.0"}))
        (repaired_minimist_path / "package.json").write_text(json.dumps({"version": "1.2.8"}))
        (js_directory / "package-lock.json").write_text('{"lock":"repaired"}\n')
        return None

    monkeypatch.setattr(readabilipy_runtime.subprocess, "run", fake_run)

    assert _repair_node_runtime(js_directory) is True
    assert _runtime_is_compatible(js_directory) is True


def test_repair_node_runtime_returns_false_when_install_fails(tmp_path, monkeypatch):
    js_directory = tmp_path / "javascript"
    js_directory.mkdir()

    package_json_path = js_directory / "package.json"
    package_json_path.write_text(
        json.dumps(
            {
                "name": "ReadabiliPy",
                "dependencies": {
                    "@mozilla/readability": ">=0.4.1",
                    "jsdom": ">=12.2.0",
                    "minimist": "^1.2.3",
                },
            }
        )
    )

    def fake_run(*_args, **_kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=["npm", "install"])

    monkeypatch.setattr(readabilipy_runtime.subprocess, "run", fake_run)

    assert _repair_node_runtime(js_directory) is False
