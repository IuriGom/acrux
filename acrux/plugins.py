"""Plugin API for acrux.

Plugins extend acrux with custom reflection providers, skill verifiers, and
exporters. They can be loaded from plain Python modules placed in a plugin
directory (default ``~/.acrux/plugins``) or from installed packages that
advertise the ``acrux.plugins`` entry point group.

A plugin is any module exposing a ``register(manager)`` function:

    def register(manager):
        manager.register_exporter("csv", export_csv)

Loading a broken plugin never crashes the host: the failure is logged and
recorded in ``PluginManager.errors``.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from acrux.models import Skill
from acrux.reflection.base import ReflectionProvider

logger = logging.getLogger("acrux")

ENTRY_POINT_GROUP = "acrux.plugins"

ProviderFactory = Callable[..., ReflectionProvider]
VerifierHook = Callable[[Skill], tuple[bool, list[str]]]
ExporterHook = Callable[[list[Skill], Path], None]


def default_plugin_dir() -> Path:
    """Return the default plugin directory (``~/.acrux/plugins``)."""
    return Path.home() / ".acrux" / "plugins"


class PluginManager:
    """Registry and loader for acrux plugins.

    Hooks are organized in three registries:

    - reflection providers: named factories producing ReflectionProvider instances
    - skill verifiers: named callables (or objects with ``verify``) returning
      ``(ok, errors)`` for a Skill
    - exporters: named callables writing a list of skills to a path
    """

    def __init__(self, plugin_dir: Path | None = None):
        self.plugin_dir = plugin_dir if plugin_dir is not None else default_plugin_dir()
        self.reflection_providers: dict[str, ProviderFactory] = {}
        self.skill_verifiers: dict[str, Any] = {}
        self.exporters: dict[str, ExporterHook] = {}
        self.loaded: list[str] = []
        self.errors: list[str] = []

    # --- Registration API (called by plugins) ---

    def register_reflection_provider(self, name: str, factory: ProviderFactory) -> None:
        """Register a factory that creates a custom ReflectionProvider."""
        if not callable(factory):
            raise TypeError(f"reflection provider {name!r} must be callable")
        if name in self.reflection_providers:
            logger.warning("Overwriting reflection provider %r", name)
        self.reflection_providers[name] = factory

    def register_skill_verifier(self, name: str, verifier: Any) -> None:
        """Register a custom skill verifier.

        ``verifier`` is either a callable ``(skill) -> (ok, errors)`` or an
        object exposing a ``verify(skill)`` method with the same signature.
        """
        if not callable(verifier) and not hasattr(verifier, "verify"):
            raise TypeError(f"skill verifier {name!r} must be callable or expose verify()")
        if name in self.skill_verifiers:
            logger.warning("Overwriting skill verifier %r", name)
        self.skill_verifiers[name] = verifier

    def register_exporter(self, name: str, exporter: ExporterHook) -> None:
        """Register a custom exporter: ``(skills, path) -> None``."""
        if not callable(exporter):
            raise TypeError(f"exporter {name!r} must be callable")
        if name in self.exporters:
            logger.warning("Overwriting exporter %r", name)
        self.exporters[name] = exporter

    # --- Hook consumption API ---

    def create_reflection_provider(self, name: str, *args: Any, **kwargs: Any) -> ReflectionProvider:
        """Instantiate a registered reflection provider by name."""
        if name not in self.reflection_providers:
            raise KeyError(f"unknown reflection provider {name!r}")
        provider = self.reflection_providers[name](*args, **kwargs)
        if not isinstance(provider, ReflectionProvider):
            raise TypeError(f"reflection provider {name!r} did not produce a ReflectionProvider")
        return provider

    def run_skill_verifiers(self, skill: Skill) -> dict[str, list[str]]:
        """Run all registered verifiers against a skill.

        Returns a mapping of verifier name to its error list; an empty error
        list means the verifier accepted the skill. A verifier that raises is
        reported as failed with the exception message instead of propagating.
        """
        results: dict[str, list[str]] = {}
        for name, verifier in self.skill_verifiers.items():
            try:
                if hasattr(verifier, "verify"):
                    ok, errors = verifier.verify(skill)
                else:
                    ok, errors = verifier(skill)
            except Exception as exc:  # plugins must not crash the host
                logger.warning("Skill verifier %r raised: %s", name, exc)
                results[name] = [f"verifier raised: {exc}"]
                continue
            results[name] = list(errors) if not ok else []
        return results

    def export_with(self, name: str, skills: list[Skill], path: Path) -> None:
        """Export skills using a registered exporter."""
        if name not in self.exporters:
            raise KeyError(f"unknown exporter {name!r}")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.exporters[name](skills, path)

    # --- Loading ---

    def load_all(self) -> list[str]:
        """Load plugins from the plugin directory and entry points."""
        self.load_directory()
        self.load_entry_points()
        return self.loaded

    def load_directory(self, path: Path | None = None) -> list[str]:
        """Load every ``*.py`` plugin module from a directory.

        Files starting with ``_`` are skipped. Returns the names of the
        modules loaded successfully.
        """
        directory = path if path is not None else self.plugin_dir
        if not directory.is_dir():
            return []
        loaded: list[str] = []
        for file in sorted(directory.glob("*.py")):
            if file.name.startswith("_"):
                continue
            try:
                module = self._import_file(file)
                self._activate(module, source=str(file))
            except Exception as exc:
                message = f"failed to load plugin {file}: {exc}"
                logger.warning(message)
                self.errors.append(message)
                continue
            self.loaded.append(file.stem)
            loaded.append(file.stem)
        return loaded

    def load_entry_points(self, group: str = ENTRY_POINT_GROUP) -> list[str]:
        """Load plugins advertised through the ``acrux.plugins`` entry point group.

        Each entry point must resolve to a callable accepting this manager
        (like a plugin module's ``register`` function).
        """
        loaded: list[str] = []
        for ep in importlib.metadata.entry_points(group=group):
            try:
                hook = ep.load()
                if not callable(hook):
                    raise TypeError(f"entry point {ep.name!r} is not callable")
                hook(self)
            except Exception as exc:
                message = f"failed to load plugin entry point {ep.name!r}: {exc}"
                logger.warning(message)
                self.errors.append(message)
                continue
            self.loaded.append(ep.name)
            loaded.append(ep.name)
        return loaded

    # --- Internals ---

    def _import_file(self, path: Path) -> ModuleType:
        """Import a plugin file as an isolated module."""
        module_name = f"acrux_plugin_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot create import spec for {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(module_name, None)
            raise
        return module

    def _activate(self, module: ModuleType, source: str) -> None:
        register = getattr(module, "register", None)
        if not callable(register):
            raise TypeError(f"plugin {source} has no register(manager) function")
        register(self)
