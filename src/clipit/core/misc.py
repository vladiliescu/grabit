import re


class ClipitError(Exception):
    pass


def sanitize_filename(filename: str) -> str:
    """Return a version of filename safe for most filesystems."""
    sanitized = re.sub(r"[#|%\^\[\]]", "", filename)
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "", sanitized)
    sanitized = re.sub(r"^(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?$", r"_\1\2", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"[\s.]+$", "", sanitized)
    sanitized = re.sub(r"^\.+", "", sanitized)
    sanitized = sanitized[:240]
    return sanitized
