from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import readabilipy

PINNED_READABILIPY_JS_DEPENDENCIES = {
    "@mozilla/readability": "0.6.0",
    "jsdom": "27.0.0",
    "minimist": "1.2.8",
}

REQUIRED_READABILIPY_JS_PACKAGES = (
    "@mozilla/readability",
    "jsdom",
    "minimist",
    "@asamuzakjp/css-color",
)


def ensure_readabilipy_node_runtime() -> bool:
    js_directory = Path(readabilipy.__file__).resolve().parent / "javascript"

    if _runtime_is_compatible(js_directory):
        return True

    if shutil.which("node") is None or shutil.which("npm") is None:
        return False

    return _repair_node_runtime(js_directory)


def _repair_node_runtime(js_directory: Path) -> bool:
    package_json_path = js_directory / "package.json"
    if not package_json_path.exists():
        return False

    try:
        _pin_package_json_dependencies(package_json_path)
        _remove_runtime_artifacts(js_directory)
        subprocess.run(
            ["npm", "install", "--no-audit", "--no-fund"],
            cwd=js_directory,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (json.JSONDecodeError, OSError, subprocess.CalledProcessError):
        return False

    return _runtime_is_compatible(js_directory)


def _runtime_is_compatible(js_directory: Path) -> bool:
    node_modules_path = js_directory / "node_modules"
    if not node_modules_path.exists():
        return False

    package_versions = {
        package_name: _read_installed_package_version(js_directory, package_name)
        for package_name in REQUIRED_READABILIPY_JS_PACKAGES
    }
    if any(version is None for version in package_versions.values()):
        return False

    jsdom_version = package_versions["jsdom"]
    jsdom_major = _version_major(jsdom_version)
    if jsdom_major is None:
        return False
    if jsdom_major >= 29:
        return False

    css_color_version = package_versions["@asamuzakjp/css-color"]
    css_color_major = _version_major(css_color_version)
    if css_color_major is None:
        return False
    if css_color_major >= 5:
        return False

    return True


def _read_installed_package_version(js_directory: Path, package_name: str) -> str | None:
    package_json_path = js_directory / "node_modules" / package_name / "package.json"
    if not package_json_path.exists():
        return None

    try:
        package_data = json.loads(package_json_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    version = package_data.get("version")
    if isinstance(version, str):
        return version

    return None


def _version_major(version: str | None) -> int | None:
    if version is None:
        return None

    major, _, _ = version.partition(".")
    if not major.isdigit():
        return None

    return int(major)


def _pin_package_json_dependencies(package_json_path: Path) -> None:
    package_data = json.loads(package_json_path.read_text())
    dependencies = package_data.setdefault("dependencies", {})
    dependencies.update(PINNED_READABILIPY_JS_DEPENDENCIES)
    package_json_path.write_text(json.dumps(package_data, indent=2) + "\n")


def _remove_runtime_artifacts(js_directory: Path) -> None:
    _delete_runtime_artifact(js_directory / "node_modules")
    _delete_runtime_artifact(js_directory / "package-lock.json")


def _delete_runtime_artifact(path: Path) -> None:
    if not path.exists():
        return

    if path.is_dir():
        shutil.rmtree(path)
        return

    path.unlink()
