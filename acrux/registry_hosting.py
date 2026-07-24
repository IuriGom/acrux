"""Registry hosting layer: public index generation and a push/pull client.

Builds on :mod:`acrux.registry` (which owns package signing and
verification) and adds the pieces needed to publish signed packages to a
remote registry:

- :func:`build_index` — scan a packages directory and (re)generate the
  public JSON index (``~/.acrux/registry-index.json`` by default) listing
  every exported package with name, version, description, signature and
  file path.
- :class:`RegistryClient` — a small httpx-based client that pushes the
  index and its packages to an index URL (PUT) and pulls/installs packages
  from one (GET).

There is no dedicated hosting backend yet: the client speaks plain HTTP to
whatever URL it is given and logs every action it performs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
import yaml

from acrux.registry import load_index, write_index
from acrux.utils import get_logger

INDEX_FILENAME = "registry-index.json"
PACKAGES_DIRNAME = "packages"
PACKAGE_SUFFIXES = (".yaml", ".yml")


def default_index_path() -> Path:
    """Default location of the public registry index."""
    return Path.home() / ".acrux" / INDEX_FILENAME


def default_packages_dir() -> Path:
    """Default directory holding exported (signed) registry packages."""
    return Path.home() / ".acrux" / PACKAGES_DIRNAME


def package_entry(package_path: Path) -> dict[str, Any]:
    """Build one public index entry from a signed package file."""
    data = yaml.safe_load(package_path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Invalid registry package: {package_path}")
    return {
        "name": data.get("name") or package_path.stem,
        "version": str(data.get("version", "")),
        "description": data.get("description", ""),
        "signature": data.get("signature", ""),
        "path": str(package_path),
    }


def build_index(packages_dir: Path, index_path: Path) -> list[dict[str, Any]]:
    """(Re)generate the public registry index from exported packages.

    Scans ``packages_dir`` for YAML package files, writes the JSON index to
    ``index_path`` and returns the entries sorted by name. If two packages
    share a name, the one later in path order wins (and is logged).
    """
    logger = get_logger()
    entries: dict[str, dict[str, Any]] = {}
    if packages_dir.exists():
        for path in sorted(packages_dir.iterdir()):
            if not path.is_file() or path.suffix not in PACKAGE_SUFFIXES:
                continue
            entry = package_entry(path)
            name = str(entry["name"])
            if name in entries:
                logger.warning(
                    "registry index: duplicate package name %r (%s replaces %s)",
                    name,
                    path,
                    entries[name]["path"],
                )
            entries[name] = entry
    result = sorted(entries.values(), key=lambda e: str(e.get("name", "")))
    write_index(result, index_path)
    logger.info("registry index: wrote %d package(s) to %s", len(result), index_path)
    return result


def _base_url(index_url: str) -> str:
    """Directory portion of an index URL, used to resolve package URLs."""
    if index_url.endswith("/"):
        return index_url
    head, _, _ = index_url.rpartition("/")
    # "https://host" has no path component; host itself is the base.
    if head.count("/") < 2:
        return index_url + "/"
    return head + "/"


def package_filename(entry: dict[str, Any]) -> str:
    """File name a package entry is hosted under."""
    name = Path(str(entry.get("path") or "")).name
    return name or f"{entry.get('name', 'package')}.pkg.yaml"


def package_url(index_url: str, entry: dict[str, Any]) -> str:
    """URL a package is uploaded to / downloaded from.

    Convention: ``<index-url-dir>/packages/<package-file-name>``.
    """
    return urljoin(_base_url(index_url), f"packages/{package_filename(entry)}")


class RegistryClient:
    """httpx client for pushing/pulling a registry index to/from a URL."""

    def __init__(
        self,
        index_url: str,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.index_url = index_url
        self._client = client if client is not None else httpx.Client(timeout=timeout)
        self._owns_client = client is None
        self.log = get_logger()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> RegistryClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def push(self, index_path: Path) -> dict[str, Any]:
        """PUT the index JSON to the index URL, then PUT each package file.

        Returns a summary with the names of pushed and skipped packages
        (entries whose package file no longer exists are skipped).
        """
        entries = load_index(index_path)
        self.log.info(
            "registry push: PUT index (%d package(s)) -> %s", len(entries), self.index_url
        )
        resp = self._client.put(
            self.index_url,
            content=index_path.read_bytes(),
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()

        pushed: list[str] = []
        skipped: list[str] = []
        for entry in entries:
            name = str(entry.get("name", ""))
            pkg_path = Path(str(entry.get("path") or ""))
            if not pkg_path.is_file():
                self.log.warning(
                    "registry push: package file missing, skipping %s (%s)", name, pkg_path
                )
                skipped.append(name)
                continue
            url = package_url(self.index_url, entry)
            self.log.info("registry push: PUT package %s -> %s", name, url)
            resp = self._client.put(
                url,
                content=pkg_path.read_bytes(),
                headers={"Content-Type": "application/yaml"},
            )
            resp.raise_for_status()
            pushed.append(name)
        return {"index_url": self.index_url, "pushed": pushed, "skipped": skipped}

    def pull_index(self) -> list[dict[str, Any]]:
        """GET the remote index and return its entries."""
        self.log.info("registry pull: GET index <- %s", self.index_url)
        resp = self._client.get(self.index_url)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise ValueError("Invalid registry index downloaded")
        return [entry for entry in data if isinstance(entry, dict)]

    def download_package(self, entry: dict[str, Any], dest_dir: Path) -> Path:
        """Download one package referenced by an index entry into ``dest_dir``."""
        url = package_url(self.index_url, entry)
        self.log.info("registry pull: GET package %s <- %s", entry.get("name"), url)
        resp = self._client.get(url)
        resp.raise_for_status()
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / package_filename(entry)
        dest.write_bytes(resp.content)
        return dest
