"""Tests for the MkDocs documentation site structure."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MKDOCS_YML = REPO_ROOT / "mkdocs.yml"
DOCS_DIR = REPO_ROOT / "docs"

EXISTING_DOCS = ("installation-plan.md", "OPERATING.md", "system_prompt_plan.md")
NEW_DOCS = ("index.md", "quickstart.md", "architecture.md")


def _load_mkdocs_config() -> dict:
    assert MKDOCS_YML.is_file(), "mkdocs.yml is missing at the repo root"
    config = yaml.safe_load(MKDOCS_YML.read_text(encoding="utf-8"))
    assert isinstance(config, dict), "mkdocs.yml must parse to a mapping"
    return config


def _nav_paths(nav: list) -> list[str]:
    """Extract the file path of every leaf entry in the nav tree."""
    paths: list[str] = []
    for item in nav:
        if isinstance(item, dict):
            for value in item.values():
                if isinstance(value, str):
                    paths.append(value)
                elif isinstance(value, list):
                    paths.extend(_nav_paths(value))
        elif isinstance(item, str):
            paths.append(item)
    return paths


def test_mkdocs_yml_exists_and_is_valid() -> None:
    config = _load_mkdocs_config()
    assert config.get("site_name"), "mkdocs.yml must set site_name"
    assert "nav" in config, "mkdocs.yml must define a nav"
    assert "theme" in config, "mkdocs.yml must define a theme"


def test_docs_dir_matches_config() -> None:
    config = _load_mkdocs_config()
    docs_dir = REPO_ROOT / config.get("docs_dir", "docs")
    assert docs_dir.is_dir(), f"docs_dir {docs_dir} does not exist"
    assert docs_dir == DOCS_DIR


def test_all_nav_entries_exist() -> None:
    config = _load_mkdocs_config()
    nav_paths = _nav_paths(config["nav"])
    assert nav_paths, "nav must not be empty"
    for rel_path in nav_paths:
        page = DOCS_DIR / rel_path
        assert page.is_file(), f"nav entry {rel_path!r} does not exist under docs/"


def test_nav_includes_all_main_pages() -> None:
    config = _load_mkdocs_config()
    nav_paths = set(_nav_paths(config["nav"]))
    for page in (*NEW_DOCS, *EXISTING_DOCS):
        assert page in nav_paths, f"{page} is missing from the nav"


def test_index_links_to_existing_docs() -> None:
    index = (DOCS_DIR / "index.md").read_text(encoding="utf-8")
    for doc in EXISTING_DOCS:
        name = Path(doc).stem
        assert f"({doc})" in index or f"({name})" in index, (
            f"docs/index.md must link to {doc}"
        )


def test_new_docs_are_non_trivial() -> None:
    for doc in NEW_DOCS:
        path = DOCS_DIR / doc
        assert path.is_file(), f"{doc} is missing"
        content = path.read_text(encoding="utf-8")
        assert content.startswith("# "), f"{doc} must start with a top-level heading"
        assert len(content) > 500, f"{doc} looks too short to be useful"
