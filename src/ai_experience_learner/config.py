"""Configuration management for ai-experience-learner."""

import os
import tomllib
from pathlib import Path

DEFAULT_BASE_DIR = Path.home() / ".ai-experience-learner"

DEFAULTS = {
    "data_dir": str(DEFAULT_BASE_DIR / "data"),
    "db_name": "experience.db",
    "lessons_dir_name": "lessons",
    "config_name": "config.toml",
    "retrieval_top_k": 3,
    "retrieval_lambda": 0.6,
    "embedding_api_url": "https://api.openai.com/v1",
    "embedding_api_key_env": "OPENAI_API_KEY",
    "embedding_model": "text-embedding-3-small",
    "embedding_dim": 1536,
    "consolidate_target_size": 30,
}


class Config:
    """Experience learner configuration."""

    def __init__(self, config_path: Path | None = None):
        self._cfg: dict = dict(DEFAULTS)
        self._path = config_path or (DEFAULT_BASE_DIR / DEFAULTS["config_name"])
        if self._path.exists():
            self._load(self._path)

    def _load(self, path: Path):
        with open(path, "rb") as f:
            data = tomllib.load(f)
        for section_name, section in data.items():
            if isinstance(section, dict):
                for k, v in section.items():
                    key = k.replace("-", "_")
                    # Try direct match first, then with section prefix
                    if key in self._cfg:
                        self._cfg[key] = v
                    else:
                        prefixed = f"{section_name}_{key}"
                        if prefixed in self._cfg:
                            self._cfg[prefixed] = v

    def save(self, path: Path | None = None):
        path = path or self._path
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# ai-experience-learner configuration",
            "",
            "[data]",
            f'dir = "{self.data_dir}"',
            "",
            "[retrieval]",
            f"top_k = {self.retrieval_top_k}",
            f"lambda = {self.retrieval_lambda}",
            "",
            "[embedding]",
            f'api_url = "{self.embedding_api_url}"',
            f'api_key_env = "{self.embedding_api_key_env}"',
            f'model = "{self.embedding_model}"',
            f"dim = {self.embedding_dim}",
            "",
            "[consolidate]",
            f"target_size = {self.consolidate_target_size}",
            "",
        ]
        path.write_text("\n".join(lines))

    @property
    def data_dir(self) -> Path:
        return Path(os.path.expanduser(self._cfg["data_dir"]))

    @property
    def db_path(self) -> Path:
        return self.data_dir / self._cfg["db_name"]

    @property
    def lessons_dir(self) -> Path:
        return self.data_dir / self._cfg["lessons_dir_name"]

    @property
    def config_path(self) -> Path:
        return self._path

    @property
    def retrieval_top_k(self) -> int:
        return int(self._cfg["retrieval_top_k"])

    @property
    def retrieval_lambda(self) -> float:
        return float(self._cfg["retrieval_lambda"])

    @property
    def embedding_api_url(self) -> str:
        return self._cfg["embedding_api_url"]

    @property
    def embedding_api_key_env(self) -> str:
        return self._cfg["embedding_api_key_env"]

    @property
    def embedding_model(self) -> str:
        return self._cfg["embedding_model"]

    @property
    def embedding_dim(self) -> int:
        return int(self._cfg["embedding_dim"])

    @property
    def consolidate_target_size(self) -> int:
        return int(self._cfg["consolidate_target_size"])

    @property
    def _resolved_key(self) -> str | None:
        """Resolve API key: if value looks like a key itself, use directly; else treat as env var name."""
        val = self._cfg.get("embedding_api_key_env", "")
        if not val:
            return None
        # Direct key: starts with common key prefixes or is long enough
        if any(val.startswith(p) for p in ("sk-", "rk-", "key-", "tk-")) or len(val) > 40:
            return val
        # Env var name
        return os.environ.get(val)

    @property
    def has_api_key(self) -> bool:
        return bool(self._resolved_key)

    @property
    def api_key(self) -> str | None:
        return self._resolved_key

    @property
    def tier(self) -> int:
        return 2 if self.has_api_key else 1

    def as_dict(self) -> dict:
        return dict(self._cfg)
