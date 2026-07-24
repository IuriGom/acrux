"""Tests for ed25519-signed registry packages and the JSON package index."""

import hashlib
import hmac
import json
from pathlib import Path

import pytest
import yaml

from acrux.models import Skill
from acrux.registry import (
    export_package,
    load_index,
    load_package,
    update_index,
)


@pytest.fixture()
def key_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect all registry key material (HMAC + ed25519) into tmp_path."""
    monkeypatch.setattr("acrux.registry._registry_key_path", lambda: tmp_path / "registry.key")
    return tmp_path


def _make_skill(name: str = "ed_skill") -> Skill:
    return Skill(project="test", name=name, preconditions=["a"], procedure=["one"])


def _write_legacy_hmac_package(key_dir: Path, path: Path, skills: list[dict]) -> None:
    """Build a package exactly the way the old HMAC-SHA256 exporter did."""
    key = "legacy-test-key"
    (key_dir / "registry.key").write_text(key)
    payload: dict = {
        "version": 1,
        "created_at": "2024-01-01T00:00:00",
        "skills": skills,
    }
    canonical = json.dumps(payload, sort_keys=True)
    payload["signature"] = hmac.new(
        key.encode(), canonical.encode(), hashlib.sha256
    ).hexdigest()
    path.write_text(yaml.safe_dump(payload))


def test_export_is_ed25519_by_default(key_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "skills.pkg.yaml"
    export_package([_make_skill()], out, name="pack", description="demo")

    data = yaml.safe_load(out.read_text())
    assert data["signature_alg"] == "ed25519"
    assert len(data["signature"]) == 128  # 64-byte ed25519 signature as hex
    assert len(data["public_key"]) == 64  # 32-byte public key as hex
    # key material created inside the redirected dir only
    assert (key_dir / "registry.ed25519.key").exists()
    assert (key_dir / "registry.ed25519.pub").exists()


def test_export_load_roundtrip(key_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "skills.pkg.yaml"
    export_package([_make_skill("roundtrip")], out)

    loaded = load_package(out)
    assert len(loaded) == 1
    assert loaded[0].name == "roundtrip"


def test_tampered_skills_rejected(key_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "skills.pkg.yaml"
    export_package([_make_skill()], out)

    data = yaml.safe_load(out.read_text())
    data["skills"][0]["name"] = "tampered"
    out.write_text(yaml.safe_dump(data))

    with pytest.raises(ValueError, match="signature"):
        load_package(out)


def test_tampered_name_rejected(key_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "skills.pkg.yaml"
    export_package([_make_skill()], out, name="pack")

    data = yaml.safe_load(out.read_text())
    data["name"] = "other"
    out.write_text(yaml.safe_dump(data))

    with pytest.raises(ValueError, match="signature"):
        load_package(out)


def test_forged_signature_rejected(key_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "skills.pkg.yaml"
    export_package([_make_skill()], out)

    data = yaml.safe_load(out.read_text())
    data["signature"] = "00" * 64
    out.write_text(yaml.safe_dump(data))

    with pytest.raises(ValueError, match="signature"):
        load_package(out)


def test_unsigned_package_rejected(key_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "skills.pkg.yaml"
    export_package([_make_skill()], out)

    data = yaml.safe_load(out.read_text())
    del data["signature"]
    out.write_text(yaml.safe_dump(data))

    with pytest.raises(ValueError, match="unsigned"):
        load_package(out)


def test_public_key_stable_across_exports(key_dir: Path, tmp_path: Path) -> None:
    out1 = tmp_path / "a.pkg.yaml"
    out2 = tmp_path / "b.pkg.yaml"
    export_package([_make_skill("a")], out1)
    export_package([_make_skill("b")], out2)

    pub1 = yaml.safe_load(out1.read_text())["public_key"]
    pub2 = yaml.safe_load(out2.read_text())["public_key"]
    assert pub1 == pub2


def test_package_verifies_without_local_keys(
    key_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "skills.pkg.yaml"
    export_package([_make_skill("portable")], out)

    # Point at a fresh, empty key dir: no local HMAC or ed25519 key material.
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    monkeypatch.setattr("acrux.registry._registry_key_path", lambda: fresh / "registry.key")

    loaded = load_package(out)
    assert loaded[0].name == "portable"


def test_package_verifies_from_local_public_key(
    key_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "skills.pkg.yaml"
    export_package([_make_skill()], out)

    # Strip the embedded public key; the local one must be used instead.
    data = yaml.safe_load(out.read_text())
    del data["public_key"]
    out.write_text(yaml.safe_dump(data))

    loaded = load_package(out)
    assert loaded[0].name == "ed_skill"


def test_legacy_hmac_package_still_loads(key_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "legacy.pkg.yaml"
    _write_legacy_hmac_package(key_dir, out, [_make_skill("legacy").to_dict()])

    loaded = load_package(out)
    assert [s.name for s in loaded] == ["legacy"]


def test_legacy_hmac_tamper_rejected(key_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "legacy.pkg.yaml"
    _write_legacy_hmac_package(key_dir, out, [_make_skill("legacy").to_dict()])

    data = yaml.safe_load(out.read_text())
    data["skills"][0]["name"] = "tampered"
    out.write_text(yaml.safe_dump(data))

    with pytest.raises(ValueError, match="signature"):
        load_package(out)


def test_index_roundtrip(key_dir: Path, tmp_path: Path) -> None:
    pkg = tmp_path / "pack.pkg.yaml"
    export_package([_make_skill()], pkg, name="pack", description="demo package")
    index = tmp_path / "index.json"

    entry = update_index(index, pkg)
    assert entry["name"] == "pack"
    assert entry["version"] == "1"
    assert entry["description"] == "demo package"
    signature = yaml.safe_load(pkg.read_text())["signature"]
    assert entry["signature"] == signature

    entries = load_index(index)
    assert entries == [entry]
    raw = json.loads(index.read_text())
    assert raw[0]["name"] == "pack"


def test_index_upsert_replaces_entry(key_dir: Path, tmp_path: Path) -> None:
    pkg = tmp_path / "pack.pkg.yaml"
    index = tmp_path / "index.json"

    export_package([_make_skill("v1")], pkg, name="pack", description="first")
    first = update_index(index, pkg)

    export_package([_make_skill("v2")], pkg, name="pack", description="second")
    second = update_index(index, pkg)

    assert first["signature"] != second["signature"]
    entries = load_index(index)
    assert len(entries) == 1
    assert entries[0]["description"] == "second"
    assert entries[0]["signature"] == second["signature"]


def test_index_multiple_packages_sorted(key_dir: Path, tmp_path: Path) -> None:
    index = tmp_path / "index.json"
    pkg_b = tmp_path / "b.pkg.yaml"
    pkg_a = tmp_path / "a.pkg.yaml"
    export_package([_make_skill("b")], pkg_b, name="b-pack")
    export_package([_make_skill("a")], pkg_a, name="a-pack")

    update_index(index, pkg_b)
    update_index(index, pkg_a)

    entries = load_index(index)
    assert [e["name"] for e in entries] == ["a-pack", "b-pack"]


def test_index_overrides(key_dir: Path, tmp_path: Path) -> None:
    pkg = tmp_path / "pack.pkg.yaml"
    export_package([_make_skill()], pkg, name="pack")
    index = tmp_path / "index.json"

    entry = update_index(index, pkg, version="2.1.0", description="override")
    assert entry["version"] == "2.1.0"
    assert entry["description"] == "override"


def test_load_index_missing_file(tmp_path: Path) -> None:
    assert load_index(tmp_path / "index.json") == []


def test_load_index_invalid_file(tmp_path: Path) -> None:
    index = tmp_path / "index.json"
    index.write_text(json.dumps({"not": "a list"}))

    with pytest.raises(ValueError, match="Invalid registry index"):
        load_index(index)
