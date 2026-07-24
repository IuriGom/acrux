"""Tests for the registry hosting layer (public index + push/pull client)."""

import json
from pathlib import Path

import httpx
import pytest
import yaml
from click.testing import CliRunner

from acrux.cli import cli
from acrux.config import AcruxConfig
from acrux.memory.procedural_db import ProceduralDBStore
from acrux.models import Skill
from acrux.registry import export_package, load_index, load_package
from acrux.registry_hosting import (
    RegistryClient,
    build_index,
    package_entry,
    package_url,
)

INDEX_URL = "https://registry.example.com/registry-index.json"


@pytest.fixture()
def key_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect all registry key material (HMAC + ed25519) into tmp_path."""
    monkeypatch.setattr("acrux.registry._registry_key_path", lambda: tmp_path / "registry.key")
    return tmp_path


@pytest.fixture()
def cli_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AcruxConfig:
    """Give CLI invocations a config rooted in tmp_path (never touches ~)."""
    cfg = AcruxConfig(
        profile="minimal",
        data_dir=tmp_path / "data",
        global_dir=tmp_path / "data" / "global",
        log_dir=tmp_path / "logs",
    )
    monkeypatch.setattr(AcruxConfig, "load", classmethod(lambda cls: cfg))
    return cfg


def _make_skill(name: str = "hosting_skill") -> Skill:
    return Skill(project="test", name=name, preconditions=["a"], procedure=["one"])


def _export(packages_dir: Path, filename: str, name: str, description: str = "") -> Path:
    packages_dir.mkdir(parents=True, exist_ok=True)
    path = packages_dir / filename
    export_package([_make_skill(name)], path, name=name, description=description)
    return path


def _mock_client(handler, monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    """Patch httpx.Client to a MockTransport client; return the request log."""
    requests: list[httpx.Request] = []

    def recording_handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    transport = httpx.MockTransport(recording_handler)
    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda *a, **kw: real_client(transport=transport))
    return requests


# ---------------------------------------------------------------------------
# Index generation
# ---------------------------------------------------------------------------


def test_package_entry_fields(key_dir: Path, tmp_path: Path) -> None:
    pkg = _export(tmp_path / "packages", "pack.pkg.yaml", "pack", description="demo")
    entry = package_entry(pkg)
    assert entry["name"] == "pack"
    assert entry["version"] == "1"
    assert entry["description"] == "demo"
    assert entry["signature"] == yaml.safe_load(pkg.read_text())["signature"]
    assert entry["path"] == str(pkg)


def test_build_index_writes_sorted_index(key_dir: Path, tmp_path: Path) -> None:
    packages = tmp_path / "packages"
    _export(packages, "b.pkg.yaml", "b-pack")
    _export(packages, "a.pkg.yaml", "a-pack", description="first alphabetically")
    index = tmp_path / "registry-index.json"

    entries = build_index(packages, index)

    assert [e["name"] for e in entries] == ["a-pack", "b-pack"]
    for entry in entries:
        assert set(entry) == {"name", "version", "description", "signature", "path"}
        assert Path(entry["path"]).is_file()
        assert entry["signature"]
    assert index.exists()
    assert json.loads(index.read_text()) == entries
    assert load_index(index) == entries


def test_build_index_regenerate_updates_entry(key_dir: Path, tmp_path: Path) -> None:
    packages = tmp_path / "packages"
    pkg = _export(packages, "pack.pkg.yaml", "pack", description="first")
    index = tmp_path / "registry-index.json"
    first = build_index(packages, index)

    export_package([_make_skill("pack")], pkg, name="pack", description="second")
    second = build_index(packages, index)

    assert len(second) == 1
    assert second[0]["description"] == "second"
    assert second[0]["signature"] != first[0]["signature"]


def test_build_index_empty_packages_dir(key_dir: Path, tmp_path: Path) -> None:
    packages = tmp_path / "packages"
    packages.mkdir()
    index = tmp_path / "registry-index.json"

    assert build_index(packages, index) == []
    assert json.loads(index.read_text()) == []


def test_build_index_missing_packages_dir(key_dir: Path, tmp_path: Path) -> None:
    index = tmp_path / "registry-index.json"
    assert build_index(tmp_path / "nope", index) == []
    assert json.loads(index.read_text()) == []


def test_build_index_ignores_non_yaml_files(key_dir: Path, tmp_path: Path) -> None:
    packages = tmp_path / "packages"
    _export(packages, "pack.pkg.yaml", "pack")
    (packages / "notes.txt").write_text("not a package")
    (packages / "other.json").write_text("{}")

    entries = build_index(packages, tmp_path / "registry-index.json")
    assert [e["name"] for e in entries] == ["pack"]


def test_build_index_invalid_package_raises(key_dir: Path, tmp_path: Path) -> None:
    packages = tmp_path / "packages"
    packages.mkdir()
    (packages / "broken.pkg.yaml").write_text("- just\n- a\n- list\n")

    with pytest.raises(ValueError, match="Invalid registry package"):
        build_index(packages, tmp_path / "registry-index.json")


def test_build_index_duplicate_names_last_wins(key_dir: Path, tmp_path: Path) -> None:
    packages = tmp_path / "packages"
    _export(packages, "a.pkg.yaml", "pack", description="from a")
    _export(packages, "b.pkg.yaml", "pack", description="from b")

    entries = build_index(packages, tmp_path / "registry-index.json")
    assert len(entries) == 1
    assert entries[0]["description"] == "from b"
    assert entries[0]["path"].endswith("b.pkg.yaml")


# ---------------------------------------------------------------------------
# URL handling
# ---------------------------------------------------------------------------


def test_package_url_derivation() -> None:
    entry = {"name": "pack", "path": "/home/u/.acrux/packages/pack.pkg.yaml"}
    assert package_url(INDEX_URL, entry) == "https://registry.example.com/packages/pack.pkg.yaml"
    assert (
        package_url("https://registry.example.com/sub/registry-index.json", entry)
        == "https://registry.example.com/sub/packages/pack.pkg.yaml"
    )
    # Index URL pointing at a directory or a bare host.
    assert (
        package_url("https://registry.example.com/reg/", entry)
        == "https://registry.example.com/reg/packages/pack.pkg.yaml"
    )
    assert (
        package_url("https://registry.example.com", entry)
        == "https://registry.example.com/packages/pack.pkg.yaml"
    )


def test_package_url_falls_back_to_entry_name() -> None:
    entry = {"name": "pack"}
    assert package_url(INDEX_URL, entry) == "https://registry.example.com/packages/pack.pkg.yaml"


# ---------------------------------------------------------------------------
# Push (mocked httpx)
# ---------------------------------------------------------------------------


def test_push_puts_index_then_packages(key_dir: Path, tmp_path: Path) -> None:
    packages = tmp_path / "packages"
    pkg_a = _export(packages, "a.pkg.yaml", "a-pack")
    pkg_b = _export(packages, "b.pkg.yaml", "b-pack")
    index = tmp_path / "registry-index.json"
    entries = build_index(packages, index)

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200)

    client = RegistryClient(INDEX_URL, client=httpx.Client(transport=httpx.MockTransport(handler)))
    summary = client.push(index)

    assert summary["index_url"] == INDEX_URL
    assert summary["pushed"] == ["a-pack", "b-pack"]
    assert summary["skipped"] == []

    assert len(requests) == 3
    index_req = requests[0]
    assert index_req.method == "PUT"
    assert str(index_req.url) == INDEX_URL
    assert index_req.headers["Content-Type"] == "application/json"
    assert json.loads(index_req.content) == entries

    pkg_reqs = {str(r.url): r for r in requests[1:]}
    assert set(pkg_reqs) == {
        "https://registry.example.com/packages/a.pkg.yaml",
        "https://registry.example.com/packages/b.pkg.yaml",
    }
    assert (
        pkg_reqs["https://registry.example.com/packages/a.pkg.yaml"].content == pkg_a.read_bytes()
    )
    assert (
        pkg_reqs["https://registry.example.com/packages/b.pkg.yaml"].content == pkg_b.read_bytes()
    )


def test_push_skips_missing_package_files(key_dir: Path, tmp_path: Path) -> None:
    packages = tmp_path / "packages"
    _export(packages, "a.pkg.yaml", "a-pack")
    index = tmp_path / "registry-index.json"
    build_index(packages, index)
    # Add a stale entry pointing at a file that no longer exists.
    entries = load_index(index)
    entries.append(
        {
            "name": "gone-pack",
            "version": "1",
            "description": "",
            "signature": "00",
            "path": str(packages / "gone.pkg.yaml"),
        }
    )
    from acrux.registry import write_index

    write_index(entries, index)

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200)

    client = RegistryClient(INDEX_URL, client=httpx.Client(transport=httpx.MockTransport(handler)))
    summary = client.push(index)

    assert summary["pushed"] == ["a-pack"]
    assert summary["skipped"] == ["gone-pack"]
    assert [r.method for r in requests] == ["PUT", "PUT"]


def test_push_server_error_raises(key_dir: Path, tmp_path: Path) -> None:
    packages = tmp_path / "packages"
    _export(packages, "a.pkg.yaml", "a-pack")
    index = tmp_path / "registry-index.json"
    build_index(packages, index)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = RegistryClient(INDEX_URL, client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(httpx.HTTPStatusError):
        client.push(index)


# ---------------------------------------------------------------------------
# Pull (mocked httpx)
# ---------------------------------------------------------------------------


def test_pull_index_returns_entries(key_dir: Path, tmp_path: Path) -> None:
    packages = tmp_path / "packages"
    _export(packages, "a.pkg.yaml", "a-pack")
    entries = build_index(packages, tmp_path / "registry-index.json")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == INDEX_URL
        return httpx.Response(200, json=entries)

    client = RegistryClient(INDEX_URL, client=httpx.Client(transport=httpx.MockTransport(handler)))
    pulled = client.pull_index()
    assert pulled == entries


def test_pull_index_rejects_non_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"not": "a list"})

    client = RegistryClient(INDEX_URL, client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ValueError, match="Invalid registry index"):
        client.pull_index()


def test_download_package_roundtrip_verifies(key_dir: Path, tmp_path: Path) -> None:
    """A package served over (mocked) HTTP still passes signature verification."""
    packages = tmp_path / "publisher"
    pkg = _export(packages, "pack.pkg.yaml", "pack", description="served")
    entries = build_index(packages, tmp_path / "registry-index.json")

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://registry.example.com/packages/pack.pkg.yaml":
            return httpx.Response(200, content=pkg.read_bytes())
        return httpx.Response(404)

    client = RegistryClient(INDEX_URL, client=httpx.Client(transport=httpx.MockTransport(handler)))
    dest = client.download_package(entries[0], tmp_path / "downloads")

    assert dest == tmp_path / "downloads" / "pack.pkg.yaml"
    assert dest.read_bytes() == pkg.read_bytes()
    loaded = load_package(dest)
    assert [s.name for s in loaded] == ["pack"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_registry_index(key_dir: Path, cli_config: AcruxConfig, tmp_path: Path) -> None:
    packages = tmp_path / "packages"
    _export(packages, "pack.pkg.yaml", "pack", description="cli demo")
    index = tmp_path / "registry-index.json"

    result = CliRunner().invoke(
        cli, ["registry-index", "--packages-dir", str(packages), "--output", str(index)]
    )

    assert result.exit_code == 0, result.output
    assert "Indexed 1 package(s)" in result.output
    assert "- pack 1" in result.output
    entries = load_index(index)
    assert entries[0]["name"] == "pack"
    assert entries[0]["path"] == str(packages / "pack.pkg.yaml")


def test_cli_registry_push_dry_run_makes_no_http(
    key_dir: Path, cli_config: AcruxConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    packages = tmp_path / "packages"
    _export(packages, "pack.pkg.yaml", "pack")
    index = tmp_path / "registry-index.json"

    def fail_client(*a, **kw):  # any real HTTP client construction is a bug here
        raise AssertionError("httpx.Client must not be used in dry-run mode")

    monkeypatch.setattr(httpx, "Client", fail_client)

    result = CliRunner().invoke(
        cli,
        [
            "registry-push",
            INDEX_URL,
            "--packages-dir",
            str(packages),
            "--index",
            str(index),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert f"would PUT index (1 package(s)) to {INDEX_URL}" in result.output
    assert (
        "would PUT package pack to https://registry.example.com/packages/pack.pkg.yaml"
        in result.output
    )
    # The dry run still (re)generates the local index.
    assert load_index(index)[0]["name"] == "pack"


def test_cli_registry_push_uses_httpx(
    key_dir: Path, cli_config: AcruxConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    packages = tmp_path / "packages"
    _export(packages, "pack.pkg.yaml", "pack")
    index = tmp_path / "registry-index.json"
    requests = _mock_client(lambda request: httpx.Response(200), monkeypatch)

    result = CliRunner().invoke(
        cli,
        ["registry-push", INDEX_URL, "--packages-dir", str(packages), "--index", str(index)],
    )

    assert result.exit_code == 0, result.output
    assert "Pushed index" in result.output
    assert "- pushed pack" in result.output
    assert [r.method for r in requests] == ["PUT", "PUT"]
    assert str(requests[0].url) == INDEX_URL
    assert str(requests[1].url) == "https://registry.example.com/packages/pack.pkg.yaml"


def test_cli_registry_push_http_error_exits_1(
    key_dir: Path, cli_config: AcruxConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    packages = tmp_path / "packages"
    _export(packages, "pack.pkg.yaml", "pack")
    _mock_client(lambda request: httpx.Response(503), monkeypatch)

    result = CliRunner().invoke(
        cli,
        [
            "registry-push",
            INDEX_URL,
            "--packages-dir",
            str(packages),
            "--index",
            str(tmp_path / "registry-index.json"),
        ],
    )

    assert result.exit_code == 1
    assert "Push failed" in result.output


def test_cli_registry_pull_installs_selected_package(
    key_dir: Path, cli_config: AcruxConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    packages = tmp_path / "publisher"
    pkg_one = _export(packages, "one.pkg.yaml", "one-pack")
    _export(packages, "two.pkg.yaml", "two-pack")
    entries = build_index(packages, tmp_path / "registry-index.json")

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == INDEX_URL:
            return httpx.Response(200, json=entries)
        if str(request.url) == "https://registry.example.com/packages/one.pkg.yaml":
            return httpx.Response(200, content=pkg_one.read_bytes())
        return httpx.Response(404)

    _mock_client(handler, monkeypatch)
    downloads = tmp_path / "downloads"

    result = CliRunner().invoke(
        cli,
        [
            "registry-pull",
            INDEX_URL,
            "--package",
            "one-pack",
            "--packages-dir",
            str(downloads),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Installed 1 skills from one.pkg.yaml into global." in result.output
    # Only the selected package was downloaded.
    assert (downloads / "one.pkg.yaml").exists()
    assert not (downloads / "two.pkg.yaml").exists()
    # The skill landed in the configured project's store.
    store = ProceduralDBStore(cli_config.projects_dir / "global" / "skills.db")
    assert [s.name for s in store.get_all("global")] == ["one-pack"]


def test_cli_registry_pull_unknown_package_exits_1(
    key_dir: Path, cli_config: AcruxConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    packages = tmp_path / "publisher"
    _export(packages, "one.pkg.yaml", "one-pack")
    entries = build_index(packages, tmp_path / "registry-index.json")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=entries)

    _mock_client(handler, monkeypatch)

    result = CliRunner().invoke(
        cli,
        [
            "registry-pull",
            INDEX_URL,
            "--package",
            "nope-pack",
            "--packages-dir",
            str(tmp_path / "downloads"),
        ],
    )

    assert result.exit_code == 1
    assert "Package(s) not in index: nope-pack" in result.output
