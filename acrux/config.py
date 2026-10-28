"""Configuration management for acrux."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import yaml

if TYPE_CHECKING:
    from acrux.embeddings import OllamaEmbedder


Profile = Literal["minimal", "light", "standard", "workstation"]
Provider = Literal["ollama", "kimi", "none"]


PROFILE_DEFAULTS: dict[Profile, dict[str, Any]] = {
    "minimal": {
        "ram_target_mb": 256,
        "storage_gb": 5,
        "reflection_provider": "none",
        "search": "keyword",
        "cache_size": 50,
        "embedding_dimensions": 0,
    },
    "light": {
        "ram_target_mb": 512,
        "storage_gb": 15,
        "reflection_provider": "kimi",
        "search": "keyword_semantic",
        "cache_size": 100,
        "embedding_dimensions": 384,
    },
    "standard": {
        "ram_target_mb": 1024,
        "storage_gb": 50,
        "reflection_provider": "ollama",
        "search": "vector",
        "cache_size": 250,
        "embedding_dimensions": 384,
    },
    "workstation": {
        "ram_target_mb": 2048,
        "storage_gb": 0,  # unlimited
        "reflection_provider": "ollama",
        "search": "vector",
        "cache_size": 500,
        "embedding_dimensions": 384,
    },
}


@dataclass
class ReflectionConfig:
    provider: Provider = "none"
    model: str = "qwen3:14b"
    host: str = "http://localhost:11434"
    schedule: str = "0 2 * * *"
    embedding_model: str = ""
    adaptive_threshold: int = 10
    routing: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "host": self.host,
            "schedule": self.schedule,
            "embedding_model": self.embedding_model,
            "adaptive_threshold": self.adaptive_threshold,
            "routing": dict(self.routing),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReflectionConfig:
        return cls(
            provider=data.get("provider", "none"),
            model=data.get("model", "qwen3:14b"),
            host=data.get("host", "http://localhost:11434"),
            schedule=data.get("schedule", "0 2 * * *"),
            embedding_model=data.get("embedding_model", ""),
            adaptive_threshold=data.get("adaptive_threshold", 10),
            routing=data.get("routing", {}),
        )


@dataclass
class MCPConfig:
    transport: Literal["stdio", "http"] = "stdio"
    port: int = 11435

    def to_dict(self) -> dict[str, Any]:
        return {"transport": self.transport, "port": self.port}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MCPConfig:
        return cls(
            transport=data.get("transport", "stdio"),
            port=data.get("port", 11435),
        )


@dataclass
class RetentionConfig:
    episodes_days: int = 30
    max_storage_gb: int = 0  # 0 = unlimited or profile default

    def to_dict(self) -> dict[str, Any]:
        return {"episodes_days": self.episodes_days, "max_storage_gb": self.max_storage_gb}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RetentionConfig:
        return cls(
            episodes_days=data.get("episodes_days", 30),
            max_storage_gb=data.get("max_storage_gb", 0),
        )


@dataclass
class AcruxConfig:
    profile: Profile = "standard"
    data_dir: Path = field(default_factory=lambda: Path.home() / ".acrux" / "data")
    global_dir: Path = field(default_factory=lambda: Path.home() / ".acrux" / "data" / "global")
    log_dir: Path = field(default_factory=lambda: Path.home() / ".acrux" / "logs")
    reflection: ReflectionConfig = field(default_factory=ReflectionConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    retention: RetentionConfig = field(default_factory=RetentionConfig)
    api_auth: bool = True
    api_token: str = ""

    def create_embedder(self) -> OllamaEmbedder | None:
        from acrux.embeddings import OllamaEmbedder

        # Minimal profile never uses embeddings
        if self.profile == "minimal":
            return None
        # Light profile only if explicitly enabled
        if self.profile == "light" and not self.reflection.embedding_model:
            return None
        # Multi-model routing takes precedence for embedding
        model = self.reflection.routing.get("embedding", "")
        if not model:
            model = self.reflection.embedding_model or (
                self.reflection.model if self.reflection.provider == "ollama" else ""
            )
        if not model:
            return None
        dim = self._embedding_dimensions_for(model)
        if dim is None:
            dim = self.profile_defaults.get("embedding_dimensions", 0) or None
        return OllamaEmbedder(
            model=model,
            host=self.reflection.host,
            ram_target_mb=self.ram_target_bytes // (1024 * 1024),
            dim=int(dim) if dim else None,
        )

    @staticmethod
    def _embedding_dimensions_for(model: str) -> int | None:
        """Return known embedding dimension for common Ollama embedding models."""
        name = model.lower()
        if "bge-m3" in name or "mxbai-embed-large" in name or "snowflake-arctic-embed" in name:
            return 1024
        if "nomic-embed-text" in name or "bge-large" in name:
            return 768
        if "all-minilm" in name or "bge-small" in name or "gte-small" in name:
            return 384
        return None

    @property
    def profile_defaults(self) -> dict[str, Any]:
        return PROFILE_DEFAULTS.get(self.profile, PROFILE_DEFAULTS["standard"])

    @property
    def max_batch_size(self) -> int:
        sizes = {"minimal": 1, "light": 3, "standard": 10, "workstation": 20}
        return sizes.get(self.profile, 10)

    @property
    def max_cache_size(self) -> int:
        return int(self.profile_defaults.get("cache_size", 100))

    @property
    def storage_limit_bytes(self) -> int:
        gb = self.retention.max_storage_gb or self.profile_defaults.get("storage_gb", 0)
        if gb <= 0:
            return 0
        return gb * 1024**3

    @property
    def ram_target_bytes(self) -> int:
        return int(self.profile_defaults.get("ram_target_mb", 1024)) * 1024 * 1024

    @property
    def embedding_enabled(self) -> bool:
        return self.create_embedder() is not None

    def check_storage_budget(self) -> bool:
        """Return True if storage is within budget."""
        import os

        limit = self.storage_limit_bytes
        if limit <= 0:
            return True
        if not self.data_dir.exists():
            return True
        total = 0
        for dirpath, _, filenames in os.walk(self.data_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
        return total < limit

    @property
    def projects_dir(self) -> Path:
        return self.data_dir / "projects"

    @property
    def backup_dir(self) -> Path:
        return Path.home() / ".acrux" / "backups"

    @property
    def config_path(self) -> Path:
        return Path.home() / ".acrux" / "config.yaml"

    def to_dict(self) -> dict[str, Any]:
        return {
            "acrux": {
                "profile": self.profile,
                "data_dir": str(self.data_dir),
                "api_auth": self.api_auth,
                "api_token": self.api_token,
            },
            "reflection": self.reflection.to_dict(),
            "mcp": self.mcp.to_dict(),
            "retention": self.retention.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AcruxConfig:
        acrux_data = data.get("acrux") or data.get("brain", {})
        profile = acrux_data.get("profile", "standard")
        data_dir = Path(acrux_data.get("data_dir", str(Path.home() / ".acrux" / "data")))

        cfg = cls(
            profile=profile,
            data_dir=data_dir,
            global_dir=data_dir / "global",
            log_dir=Path.home() / ".acrux" / "logs",
            reflection=ReflectionConfig.from_dict(data.get("reflection", {})),
            mcp=MCPConfig.from_dict(data.get("mcp", {})),
            retention=RetentionConfig.from_dict(data.get("retention", {})),
            api_auth=bool(acrux_data.get("api_auth", True)),
            api_token=acrux_data.get("api_token", ""),
        )
        return cfg

    def apply_profile_defaults(self) -> None:
        """Apply profile defaults where not explicitly overridden."""
        defaults = PROFILE_DEFAULTS.get(self.profile, PROFILE_DEFAULTS["standard"])
        if self.retention.max_storage_gb == 0:
            self.retention.max_storage_gb = defaults["storage_gb"]
        if self.reflection.provider == "none" and self.profile != "minimal":
            self.reflection.provider = defaults["reflection_provider"]

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            yaml.safe_dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

    @classmethod
    def load(cls) -> AcruxConfig:
        # Migrate legacy ~/.brain to ~/.acrux on first load.
        old_home = Path.home() / ".brain"
        new_home = Path.home() / ".acrux"
        if old_home.exists() and not new_home.exists():
            try:
                import shutil

                shutil.move(str(old_home), str(new_home))
                old_home.symlink_to(new_home)
            except Exception:
                # If move fails (e.g. cross-device), copy instead.
                try:
                    shutil.copytree(old_home, new_home)
                    old_home.symlink_to(new_home)
                except Exception:
                    pass

        config_path = new_home / "config.yaml"
        if not config_path.exists():
            cfg = cls()
            cfg.api_token = _generate_api_token()
            cfg.save()
            return cfg
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        cfg = cls.from_dict(data)
        if not cfg.api_token:
            cfg.api_token = _generate_api_token()
            cfg.save()
        return cfg

    @classmethod
    def init(cls, profile: Profile = "standard") -> AcruxConfig:
        home = Path.home() / ".acrux"
        home.mkdir(parents=True, exist_ok=True)
        (home / "data" / "projects").mkdir(parents=True, exist_ok=True)
        (home / "data" / "global").mkdir(parents=True, exist_ok=True)
        (home / "logs").mkdir(parents=True, exist_ok=True)

        cfg = cls(profile=profile)
        cfg.apply_profile_defaults()
        if not cfg.api_token:
            cfg.api_token = _generate_api_token()
        cfg.save()
        return cfg

    def ensure_token(self) -> str:
        if not self.api_token:
            self.api_token = _generate_api_token()
            self.save()
        return self.api_token


def _generate_api_token() -> str:
    import secrets

    return secrets.token_urlsafe(32)
