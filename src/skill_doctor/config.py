from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FORMATS = {"markdown", "json", "github", "sarif"}
SEVERITIES = {"error", "warning", "info"}


class ConfigError(ValueError):
    """Raised when a Skill Doctor config file is invalid."""


@dataclass(frozen=True)
class Config:
    format: str | None = None
    fail_on: str | None = None
    body_line_limit: int | None = None


def load_config(path: Path | None) -> Config:
    if path is None:
        return Config()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid config JSON in {path}: {exc.msg}") from exc
    except OSError as exc:
        raise ConfigError(f"Could not read config file {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"Config file {path} must contain a JSON object")

    _reject_unknown_keys(raw, path)
    return Config(
        format=_optional_choice(raw, "format", FORMATS, path),
        fail_on=_optional_choice(raw, "fail_on", SEVERITIES, path),
        body_line_limit=_optional_positive_int(raw, "body_line_limit", path),
    )


def _reject_unknown_keys(raw: dict[str, Any], path: Path) -> None:
    allowed = {"format", "fail_on", "body_line_limit"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        joined = ", ".join(unknown)
        raise ConfigError(f"Unknown config key(s) in {path}: {joined}")


def _optional_choice(raw: dict[str, Any], key: str, choices: set[str], path: Path) -> str | None:
    if key not in raw:
        return None
    value = raw[key]
    if not isinstance(value, str) or value not in choices:
        joined = ", ".join(sorted(choices))
        raise ConfigError(f"Config key `{key}` in {path} must be one of: {joined}")
    return value


def _optional_positive_int(raw: dict[str, Any], key: str, path: Path) -> int | None:
    if key not in raw:
        return None
    value = raw[key]
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"Config key `{key}` in {path} must be a positive integer")
    return value
