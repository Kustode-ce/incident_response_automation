from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict


_ENV_PATTERN = re.compile(r"\$\{([^}:]+)(?::([^}]*))?\}")


def _resolve_env_value(value: str) -> str:
    def replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        default = match.group(2) or ""
        return os.getenv(var_name, default)

    return _ENV_PATTERN.sub(replacer, value)


def _resolve_env_in_config(data: Any) -> Any:
    if isinstance(data, dict):
        return {key: _resolve_env_in_config(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_resolve_env_in_config(item) for item in data]
    if isinstance(data, str):
        return _resolve_env_value(data)
    return data


def load_integrations_config(path: str | None = None) -> Dict[str, Any]:
    config_path = Path(path) if path else Path(__file__).resolve().parent / "integrations.yaml"
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to load integrations config.") from exc

    if not config_path.exists():
        return {}

    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return _resolve_env_in_config(raw)
