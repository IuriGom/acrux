"""Tests for the local verified skill registry."""

from pathlib import Path

import pytest
import yaml

from acrux.memory.procedural_db import ProceduralDBStore
from acrux.models import Skill
from acrux.registry import export_package, list_package, load_package


def test_export_and_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    key_path = tmp_path / "registry.key"
    monkeypatch.setattr("acrux.registry._registry_key_path", lambda: key_path)

    skill = Skill(project="test", name="test_skill", preconditions=["a"], procedure=["one"])
    out = tmp_path / "skills.pkg.yaml"
    export_package([skill], out)
    assert out.exists()

    loaded = load_package(out)
    assert len(loaded) == 1
    assert loaded[0].name == "test_skill"


def test_signature_tamper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    key_path = tmp_path / "registry.key"
    monkeypatch.setattr("acrux.registry._registry_key_path", lambda: key_path)

    skill = Skill(project="test", name="test_skill")
    out = tmp_path / "skills.pkg.yaml"
    export_package([skill], out)

    data = yaml.safe_load(out.read_text())
    data["skills"][0]["name"] = "tampered"
    out.write_text(yaml.safe_dump(data))

    with pytest.raises(ValueError, match="signature"):
        load_package(out)


def test_list_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    key_path = tmp_path / "registry.key"
    monkeypatch.setattr("acrux.registry._registry_key_path", lambda: key_path)

    skill = Skill(project="test", name="listed", verified=True)
    out = tmp_path / "skills.pkg.yaml"
    export_package([skill], out)

    skills = list_package(out)
    assert skills[0]["name"] == "listed"
    assert skills[0]["verified"] is True


def test_registry_install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    key_path = tmp_path / "registry.key"
    monkeypatch.setattr("acrux.registry._registry_key_path", lambda: key_path)

    skill = Skill(project="test", name="install_me")
    out = tmp_path / "skills.pkg.yaml"
    export_package([skill], out)

    store = ProceduralDBStore(tmp_path / "skills.db")
    loaded = load_package(out)
    added = store.import_skills([s.to_dict() for s in loaded])
    assert added == 1
    assert store.get_all("test")[0].name == "install_me"
