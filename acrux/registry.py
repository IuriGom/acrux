"""Local verified skill registry (signed skill packages).

New packages are signed with ed25519 (via ``cryptography``). Legacy packages
signed with HMAC-SHA256 are still accepted when loading, but new exports
always use ed25519.

A simple JSON index file can list known packages with name, version,
description and signature (see :func:`update_index` / :func:`load_index`).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from acrux.utils import utcnow
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from acrux.models import Skill

SIGNATURE_ALG_ED25519 = "ed25519"


def _registry_key_path() -> Path:
    return Path.home() / ".acrux" / "registry.key"


def _registry_ed25519_private_key_path() -> Path:
    return _registry_key_path().with_name("registry.ed25519.key")


def _registry_ed25519_public_key_path() -> Path:
    return _registry_key_path().with_name("registry.ed25519.pub")


def _registry_key() -> str:
    path = _registry_key_path()
    if path.exists():
        return path.read_text().strip()
    key = secrets.token_urlsafe(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(key)
    return key


def _ed25519_private_key() -> Ed25519PrivateKey:
    """Load or create the registry ed25519 private key (hex-encoded raw seed)."""
    path = _registry_ed25519_private_key_path()
    if path.exists():
        seed = bytes.fromhex(path.read_text().strip())
        return Ed25519PrivateKey.from_private_bytes(seed)
    key = Ed25519PrivateKey.generate()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(key.private_bytes_raw().hex())
    _registry_ed25519_public_key_path().write_text(key.public_key().public_bytes_raw().hex())
    return key


def _ed25519_public_key_hex() -> str | None:
    """Return the local registry ed25519 public key (hex), if any exists."""
    pub_path = _registry_ed25519_public_key_path()
    if pub_path.exists():
        return pub_path.read_text().strip()
    if _registry_ed25519_private_key_path().exists():
        return _ed25519_private_key().public_key().public_bytes_raw().hex()
    return None


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True).encode()


def _signed_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Extract the fields covered by the package signature."""
    payload: dict[str, Any] = {
        "version": data.get("version"),
        "created_at": data.get("created_at"),
        "skills": data.get("skills", []),
    }
    # Newer packages also bind name/description into the signature; legacy
    # HMAC packages predate those fields and must verify without them.
    if "name" in data:
        payload["name"] = data.get("name")
    if "description" in data:
        payload["description"] = data.get("description")
    return payload


def _sign(payload: dict[str, Any], key: str) -> str:
    """Legacy HMAC-SHA256 signature (kept for backward compatibility)."""
    return hmac.new(key.encode(), _canonical(payload), hashlib.sha256).hexdigest()


def _sign_ed25519(payload: dict[str, Any], private_key: Ed25519PrivateKey) -> str:
    return private_key.sign(_canonical(payload)).hex()


def _verify_ed25519(payload: dict[str, Any], signature_hex: str, public_key_hex: str) -> bool:
    try:
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        public_key.verify(bytes.fromhex(signature_hex), _canonical(payload))
        return True
    except (InvalidSignature, ValueError):
        return False


def export_package(
    skills: list[Skill],
    path: Path,
    name: str | None = None,
    description: str = "",
) -> None:
    """Export skills as a signed registry package (ed25519)."""
    payload: dict[str, Any] = {
        "version": 1,
        "name": name or path.stem,
        "description": description,
        "created_at": utcnow().isoformat(),
        "skills": [s.to_dict() for s in skills],
    }
    private_key = _ed25519_private_key()
    payload["signature_alg"] = SIGNATURE_ALG_ED25519
    payload["public_key"] = private_key.public_key().public_bytes_raw().hex()
    payload["signature"] = _sign_ed25519(_signed_payload(payload), private_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, default_flow_style=False, sort_keys=False))


def load_package(path: Path) -> list[Skill]:
    """Load and verify a signed registry package.

    ed25519 packages are verified against the public key embedded in the
    package, falling back to the local registry public key. Legacy
    HMAC-SHA256 packages are verified against the local registry key.
    """
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("Invalid registry package")
    signature = data.get("signature")
    if not signature:
        raise ValueError("Package is unsigned")
    payload = _signed_payload(data)
    if data.get("signature_alg") == SIGNATURE_ALG_ED25519:
        public_key_hex = data.get("public_key") or _ed25519_public_key_hex()
        if not public_key_hex:
            raise ValueError("No ed25519 public key available to verify package")
        if not _verify_ed25519(payload, signature, public_key_hex):
            raise ValueError("Package signature does not match")
    else:
        expected = _sign(payload, _registry_key())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Package signature does not match")
    skills_data = data.get("skills", [])
    if not isinstance(skills_data, list):
        raise ValueError("Invalid skills list")
    return [Skill.from_dict(item) for item in skills_data]


def list_package(path: Path) -> list[dict[str, Any]]:
    """List skills in a package without importing."""
    data = yaml.safe_load(path.read_text())
    skills_data = data.get("skills", []) if isinstance(data, dict) else []
    return [
        {
            "name": item.get("name", ""),
            "project": item.get("project", ""),
            "verified": bool(item.get("verified", False)),
            "evidence_count": len(item.get("evidence", [])),
        }
        for item in skills_data
        if isinstance(item, dict)
    ]


def load_index(path: Path) -> list[dict[str, Any]]:
    """Load the JSON package index (empty list if the file does not exist)."""
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        raise ValueError("Invalid registry index")
    return [entry for entry in data if isinstance(entry, dict)]


def write_index(entries: list[dict[str, Any]], path: Path) -> None:
    """Write the JSON package index."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2, sort_keys=True) + "\n")


def update_index(
    index_path: Path,
    package_path: Path,
    name: str | None = None,
    version: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Add or replace a package entry in the JSON index.

    Entry fields default to the values stored in the package itself:
    name, version, description and signature.
    """
    data = yaml.safe_load(package_path.read_text())
    if not isinstance(data, dict):
        raise ValueError("Invalid registry package")
    entry = {
        "name": name or data.get("name") or package_path.stem,
        "version": str(version if version is not None else data.get("version", "")),
        "description": description if description is not None else data.get("description", ""),
        "signature": data.get("signature", ""),
    }
    entries = [e for e in load_index(index_path) if e.get("name") != entry["name"]]
    entries.append(entry)
    entries.sort(key=lambda e: str(e.get("name", "")))
    write_index(entries, index_path)
    return entry
