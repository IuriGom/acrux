"""Tests for the plugin API."""

import textwrap
from pathlib import Path

import pytest

from acrux.models import Episode, Fact, Skill
from acrux.plugins import PluginManager, default_plugin_dir
from acrux.reflection.base import ReflectionProvider


class DummyProvider(ReflectionProvider):
    async def reflect_episodes(self, episodes: list[Episode]) -> list[Fact]:
        return []

    async def extract_skills(self, episodes: list[Episode], facts: list[Fact]) -> list[Skill]:
        return []


def test_default_plugin_dir() -> None:
    assert default_plugin_dir() == Path.home() / ".acrux" / "plugins"


def test_register_and_create_reflection_provider() -> None:
    manager = PluginManager()
    manager.register_reflection_provider("dummy", lambda: DummyProvider())

    provider = manager.create_reflection_provider("dummy")
    assert isinstance(provider, DummyProvider)


def test_create_unknown_provider_raises() -> None:
    manager = PluginManager()
    with pytest.raises(KeyError, match="unknown reflection provider"):
        manager.create_reflection_provider("nope")


def test_provider_factory_must_return_provider() -> None:
    manager = PluginManager()
    manager.register_reflection_provider("bad", lambda: object())
    with pytest.raises(TypeError, match="ReflectionProvider"):
        manager.create_reflection_provider("bad")


def test_register_rejects_non_callables() -> None:
    manager = PluginManager()
    with pytest.raises(TypeError):
        manager.register_reflection_provider("x", "not-callable")
    with pytest.raises(TypeError):
        manager.register_skill_verifier("x", 42)
    with pytest.raises(TypeError):
        manager.register_exporter("x", None)


def test_run_skill_verifiers_callable() -> None:
    manager = PluginManager()
    manager.register_skill_verifier("has_name", lambda skill: (bool(skill.name), ["missing name"]))

    results = manager.run_skill_verifiers(Skill(name="ok"))
    assert results == {"has_name": []}

    results = manager.run_skill_verifiers(Skill(name=""))
    assert results == {"has_name": ["missing name"]}


def test_run_skill_verifiers_object_with_verify() -> None:
    class Verifier:
        def verify(self, skill: Skill) -> tuple[bool, list[str]]:
            return True, []

    manager = PluginManager()
    manager.register_skill_verifier("obj", Verifier())
    assert manager.run_skill_verifiers(Skill()) == {"obj": []}


def test_run_skill_verifiers_catches_exceptions() -> None:
    def boom(skill: Skill) -> tuple[bool, list[str]]:
        raise RuntimeError("boom")

    manager = PluginManager()
    manager.register_skill_verifier("boom", boom)
    results = manager.run_skill_verifiers(Skill())
    assert results["boom"] == ["verifier raised: boom"]


def test_export_with(tmp_path: Path) -> None:
    manager = PluginManager()
    manager.register_exporter(
        "names", lambda skills, path: path.write_text("\n".join(s.name for s in skills))
    )

    out = tmp_path / "nested" / "skills.txt"
    manager.export_with("names", [Skill(name="a"), Skill(name="b")], out)
    assert out.read_text() == "a\nb"


def test_export_with_unknown_raises(tmp_path: Path) -> None:
    manager = PluginManager()
    with pytest.raises(KeyError, match="unknown exporter"):
        manager.export_with("nope", [], tmp_path / "out.txt")


def test_load_directory(tmp_path: Path) -> None:
    plugin = tmp_path / "my_plugin.py"
    plugin.write_text(
        textwrap.dedent(
            """
            def register(manager):
                manager.register_exporter("txt", lambda skills, path: path.write_text("ok"))
                manager.register_skill_verifier("always", lambda skill: (True, []))
            """
        )
    )

    manager = PluginManager(plugin_dir=tmp_path)
    loaded = manager.load_directory()

    assert loaded == ["my_plugin"]
    assert manager.loaded == ["my_plugin"]
    assert manager.errors == []
    assert "txt" in manager.exporters
    assert "always" in manager.skill_verifiers


def test_load_directory_missing_dir(tmp_path: Path) -> None:
    manager = PluginManager(plugin_dir=tmp_path / "nonexistent")
    assert manager.load_directory() == []
    assert manager.errors == []


def test_load_directory_skips_underscore_files(tmp_path: Path) -> None:
    (tmp_path / "_private.py").write_text("raise RuntimeError('should not load')")
    (tmp_path / "notes.txt").write_text("not python")

    manager = PluginManager(plugin_dir=tmp_path)
    assert manager.load_directory() == []
    assert manager.errors == []


def test_load_directory_bad_plugin_does_not_crash(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text("import nonexistent_module_xyz")
    (tmp_path / "good.py").write_text(
        "def register(manager):\n    manager.register_exporter('e', lambda s, p: None)\n"
    )

    manager = PluginManager(plugin_dir=tmp_path)
    loaded = manager.load_directory()

    assert loaded == ["good"]
    assert len(manager.errors) == 1
    assert "broken.py" in manager.errors[0]
    assert "e" in manager.exporters


def test_load_directory_requires_register(tmp_path: Path) -> None:
    (tmp_path / "no_register.py").write_text("X = 1\n")

    manager = PluginManager(plugin_dir=tmp_path)
    assert manager.load_directory() == []
    assert len(manager.errors) == 1
    assert "register" in manager.errors[0]


def test_plugin_module_can_build_provider(tmp_path: Path) -> None:
    plugin = tmp_path / "provider_plugin.py"
    plugin.write_text(
        textwrap.dedent(
            """
            from acrux.reflection.base import ReflectionProvider

            class MyProvider(ReflectionProvider):
                async def reflect_episodes(self, episodes):
                    return []

                async def extract_skills(self, episodes, facts):
                    return []

            def register(manager):
                manager.register_reflection_provider("mine", MyProvider)
            """
        )
    )

    manager = PluginManager(plugin_dir=tmp_path)
    assert manager.load_directory() == ["provider_plugin"]
    provider = manager.create_reflection_provider("mine")
    assert isinstance(provider, ReflectionProvider)


def test_load_entry_points(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeEntryPoint:
        name = "ep_plugin"

        def load(self):
            def register(manager: PluginManager) -> None:
                manager.register_exporter("ep", lambda skills, path: None)

            return register

    monkeypatch.setattr(
        "acrux.plugins.importlib.metadata.entry_points",
        lambda group: [FakeEntryPoint()] if group == "acrux.plugins" else [],
    )

    manager = PluginManager()
    loaded = manager.load_entry_points()

    assert loaded == ["ep_plugin"]
    assert "ep" in manager.exporters


def test_load_entry_points_failure_isolated(monkeypatch: pytest.MonkeyPatch) -> None:
    class BadEntryPoint:
        name = "bad_ep"

        def load(self):
            raise ImportError("missing dep")

    monkeypatch.setattr(
        "acrux.plugins.importlib.metadata.entry_points",
        lambda group: [BadEntryPoint()],
    )

    manager = PluginManager()
    assert manager.load_entry_points() == []
    assert len(manager.errors) == 1
    assert "bad_ep" in manager.errors[0]


def test_load_all(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "p.py").write_text("def register(manager): pass\n")
    monkeypatch.setattr(
        "acrux.plugins.importlib.metadata.entry_points", lambda group: []
    )

    manager = PluginManager(plugin_dir=tmp_path)
    assert manager.load_all() == ["p"]
