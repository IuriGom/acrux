"""Tests for the installer shell scripts in install/.

The scripts are POSIX sh, so these tests check syntax (``sh -n`` / ``dash -n``),
required content, and — most importantly — the real behavior in a sandboxed
HOME with stub ``uv``/``curl`` binaries so nothing touches the network or the
host system.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_DIR = REPO_ROOT / "install"
INSTALL_SH = INSTALL_DIR / "install.sh"
UNINSTALL_SH = INSTALL_DIR / "uninstall.sh"
UPGRADE_SH = INSTALL_DIR / "upgrade.sh"
README = INSTALL_DIR / "README.md"
SCRIPTS = [INSTALL_SH, UNINSTALL_SH, UPGRADE_SH]

# Stub `uv`: logs every call, and on `uv venv <path> ...` creates a fake venv
# with stub `python` and `acrux` executables (the acrux stub logs its args).
UV_STUB = """#!/bin/sh
echo "uv $*" >> "$STUB_LOG"
if [ "$1" = "venv" ]; then
  v="$2"
  mkdir -p "$v/bin"
  printf '#!/bin/sh\\necho "acrux $*" >> "$STUB_LOG"\\nexit 0\\n' > "$v/bin/acrux"
  chmod +x "$v/bin/acrux"
  printf '#!/bin/sh\\nexit 0\\n' > "$v/bin/python"
  chmod +x "$v/bin/python"
fi
exit 0
"""

# Stub `curl`: serves fixture files for the release tarball and checksums.txt,
# fails on anything else so unexpected network access is caught by the test.
CURL_STUB = """#!/bin/sh
out=""
url=""
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    -*) shift ;;
    *) url="$1"; shift ;;
  esac
done
[ -n "$out" ] && [ -n "$url" ] || exit 1
case "$url" in
  */checksums.txt) cp "$FIXTURE_DIR/checksums.txt" "$out" ;;
  *.tar.gz) cp "$FIXTURE_DIR/pkg.tar.gz" "$out" ;;
  *) echo "stub curl: unexpected URL: $url" >&2; exit 1 ;;
esac
"""

# Standalone acrux stub used by the upgrade/uninstall tests.
ACRUX_STUB = """#!/bin/sh
echo "acrux $*" >> "$STUB_LOG"
exit 0
"""


def run_script(script: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["sh", str(script), *args],
        capture_output=True,
        text=True,
        env=env,
        stdin=subprocess.DEVNULL,  # scripts must not block on prompts in tests
        timeout=120,
    )


def make_executable(path: Path, body: str) -> Path:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


@pytest.fixture
def sandbox(tmp_path: Path):
    """Sandboxed HOME with a stub dir on PATH and a log file for stub calls."""
    home = tmp_path / "home"
    home.mkdir()
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    stub_log = tmp_path / "stub.log"
    make_executable(stub_dir / "uv", UV_STUB)

    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "PATH": f"{stub_dir}{os.pathsep}{env.get('PATH', '')}",
            "STUB_LOG": str(stub_log),
            "ACRUX_NO_SERVICE": "1",  # never touch real launchctl/systemctl
        }
    )

    class Sandbox:
        pass

    sb = Sandbox()
    sb.home = home
    sb.stub_dir = stub_dir
    sb.log = stub_log
    sb.env = env
    sb.pia = home / ".pia"
    sb.acrux_home = home / ".acrux"
    return sb


def stub_log_text(sandbox) -> str:
    return sandbox.log.read_text() if sandbox.log.exists() else ""


# ---------------------------------------------------------------------------
# Static checks: existence, executability, POSIX syntax, required content.
# ---------------------------------------------------------------------------


class TestFiles:
    def test_all_files_exist(self) -> None:
        for path in [*SCRIPTS, README]:
            assert path.is_file(), f"missing {path}"

    @pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
    def test_script_is_executable_and_sh_shebang(self, script: Path) -> None:
        assert os.access(script, os.X_OK), f"{script.name} is not executable"
        first_line = script.read_text().splitlines()[0]
        assert first_line == "#!/bin/sh", f"{script.name} must use a POSIX sh shebang"

    @pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
    def test_posix_syntax_sh(self, script: Path) -> None:
        result = subprocess.run(
            ["sh", "-n", str(script)], capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, result.stderr

    @pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
    def test_posix_syntax_dash(self, script: Path) -> None:
        if shutil.which("dash") is None:
            pytest.skip("dash not available")
        result = subprocess.run(
            ["dash", "-n", str(script)], capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, result.stderr

    @pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
    def test_no_bashisms(self, script: Path) -> None:
        text = script.read_text()
        # "[[ " with a space is the bash test keyword; "[[:space:]]" etc. are
        # legitimate POSIX character classes and must not be flagged.
        assert "[[ " not in text, f"{script.name} uses [[ ]] (bashism)"
        assert "\nfunction " not in text, f"{script.name} uses the `function` keyword (bashism)"


class TestContent:
    """The scripts must implement the steps from docs/installation-plan.md."""

    def test_install_sh_uses_uv_and_pia_venv(self) -> None:
        text = INSTALL_SH.read_text()
        assert "astral.sh/uv" in text
        assert "uv venv" in text
        assert "--python" in text
        assert 'INSTALL_HOME="${PIA_HOME:-$HOME/.pia}"' in text
        assert 'VENV="$INSTALL_HOME/venv"' in text

    def test_install_sh_installs_from_release_or_repo(self) -> None:
        text = INSTALL_SH.read_text()
        assert "releases/download/v$ACRUX_VERSION" in text  # GitHub release tarball
        assert "git+https://github.com/$ACRUX_GH_REPO.git@main" in text  # repo main
        assert "checksums.txt" in text  # SHA256 verification of the release

    def test_install_sh_inits_standard_profile(self) -> None:
        text = INSTALL_SH.read_text()
        assert "init --profile standard" in text

    def test_install_sh_sets_up_user_services(self) -> None:
        text = INSTALL_SH.read_text()
        # launchd (macOS)
        assert "Library/LaunchAgents/dev.pia.acrux.plist" in text
        assert "launchctl" in text
        assert "RunAtLoad" in text
        assert "KeepAlive" in text
        # systemd (Linux user unit)
        assert ".config/systemd/user/pia-acrux.service" in text
        assert "systemctl --user" in text
        assert "WantedBy=default.target" in text
        # the daemon command the task requires
        assert "daemon --background --mcp http" in text

    def test_install_sh_refuses_root_and_windows(self) -> None:
        text = INSTALL_SH.read_text()
        assert 'id -u' in text and "root" in text
        assert "WSL2" in text

    def test_uninstall_sh_supports_purge_and_removes_services(self) -> None:
        text = UNINSTALL_SH.read_text()
        assert "--purge" in text
        assert "dev.pia.acrux.plist" in text
        assert "pia-acrux.service" in text
        assert "bootout" in text
        assert "disable --now" in text

    def test_upgrade_sh_flow(self) -> None:
        text = UPGRADE_SH.read_text()
        assert "--upgrade" in text  # uv pip install --upgrade
        assert " doctor" in text  # runs acrux doctor
        assert " stop" in text  # stops the daemon first
        assert "daemon --background --mcp http" in text  # restarts it

    def test_readme_documents_all_scripts(self) -> None:
        text = README.read_text()
        for name in ("install.sh", "uninstall.sh", "upgrade.sh"):
            assert name in text
        assert "--purge" in text and "--channel main" in text

    @pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
    def test_help_flag(self, script: Path) -> None:
        result = run_script(script, "--help")
        assert result.returncode == 0
        assert "usage" in (result.stdout + result.stderr).lower()


# ---------------------------------------------------------------------------
# Functional tests in the sandbox.
# ---------------------------------------------------------------------------


class TestInstallFunctional:
    def test_main_channel_install(self, sandbox) -> None:
        result = run_script(INSTALL_SH, "--channel", "main", "--no-app", env=sandbox.env)
        assert result.returncode == 0, result.stderr

        log = stub_log_text(sandbox)
        # venv created at ~/.pia/venv with Python 3.12 via uv
        assert f"uv venv {sandbox.pia}/venv --python 3.12" in log
        # package installed from the repo main branch
        assert "uv pip install --python" in log
        assert "git+https://github.com/" in log and "@main" in log
        # acrux initialized with the standard profile
        assert "acrux init --profile standard" in log

        assert (sandbox.pia / "venv" / "bin" / "acrux").exists()

        if sys.platform == "darwin":
            plist = sandbox.home / "Library" / "LaunchAgents" / "dev.pia.acrux.plist"
            assert plist.is_file()
            text = plist.read_text()
            assert "<string>dev.pia.acrux</string>" in text
            assert f"<string>{sandbox.pia}/venv/bin/acrux</string>" in text
            for arg in ("daemon", "--background", "--mcp", "http"):
                assert f"<string>{arg}</string>" in text
            assert "<key>RunAtLoad</key>" in text and "<key>KeepAlive</key>" in text
        else:
            unit = sandbox.home / ".config" / "systemd" / "user" / "pia-acrux.service"
            assert unit.is_file()
            text = unit.read_text()
            assert "daemon --background --mcp http" in text
            assert "Restart=always" in text
            assert "WantedBy=default.target" in text

    def test_existing_config_is_not_reinitialized(self, sandbox) -> None:
        sandbox.acrux_home.mkdir(parents=True)
        (sandbox.acrux_home / "config.yaml").write_text("api_token: keep-me\n")
        result = run_script(INSTALL_SH, "--channel", "main", "--no-app", env=sandbox.env)
        assert result.returncode == 0, result.stderr
        assert "acrux init" not in stub_log_text(sandbox)
        assert (sandbox.acrux_home / "config.yaml").read_text() == "api_token: keep-me\n"

    def _write_release_fixture(self, sandbox, digest: str | None = None) -> None:
        fixture = sandbox.stub_dir.parent / "fixture"
        fixture.mkdir(exist_ok=True)
        payload = b"fake-acrux-sdist"
        (fixture / "pkg.tar.gz").write_bytes(payload)
        real = hashlib.sha256(payload).hexdigest()
        (fixture / "checksums.txt").write_text(
            f"{digest or real}  acrux-1.0.0.tar.gz\n"
        )
        sandbox.env["FIXTURE_DIR"] = str(fixture)
        make_executable(sandbox.stub_dir / "curl", CURL_STUB)

    def test_stable_channel_verifies_checksum(self, sandbox) -> None:
        self._write_release_fixture(sandbox)
        result = run_script(INSTALL_SH, "--channel", "stable", "--no-app", env=sandbox.env)
        assert result.returncode == 0, result.stderr
        assert "Checksum verified" in result.stdout
        # the verified local tarball is what got installed
        assert "acrux-1.0.0.tar.gz" in stub_log_text(sandbox)
        assert "acrux init --profile standard" in stub_log_text(sandbox)

    def test_stable_channel_rejects_checksum_mismatch(self, sandbox) -> None:
        bad = "0" * 64
        self._write_release_fixture(sandbox, digest=bad)
        result = run_script(INSTALL_SH, "--channel", "stable", "--no-app", env=sandbox.env)
        assert result.returncode != 0
        assert "checksum mismatch" in result.stderr.lower()

    def test_upgrade_flag_passes_upgrade_to_installer(self, sandbox) -> None:
        result = run_script(INSTALL_SH, "--channel", "main", "--no-app", "--upgrade", env=sandbox.env)
        assert result.returncode == 0, result.stderr
        log = stub_log_text(sandbox)
        assert "--upgrade" in log  # forwarded to uv pip install
        assert "acrux doctor" in log  # doctor runs after an upgrade


class TestUpgradeFunctional:
    def test_upgrade_stops_upgrades_doctors_restarts(self, sandbox) -> None:
        # Pretend an installation already exists.
        venv_bin = sandbox.pia / "venv" / "bin"
        venv_bin.mkdir(parents=True)
        make_executable(venv_bin / "acrux", ACRUX_STUB)
        make_executable(venv_bin / "python", "#!/bin/sh\nexit 0\n")

        result = run_script(UPGRADE_SH, "--channel", "main", env=sandbox.env)
        assert result.returncode == 0, result.stderr

        log = stub_log_text(sandbox)
        assert "acrux stop" in log
        assert "acrux backup create" in log
        assert "uv pip install --python" in log and "--upgrade" in log
        assert "@main" in log
        assert "acrux doctor" in log
        assert "acrux daemon --background --mcp http" in log
        assert log.index("acrux stop") < log.index("acrux backup create") < log.index("uv pip install") < log.index("acrux doctor") < log.index("acrux daemon")

    def test_upgrade_aborts_when_backup_fails(self, sandbox) -> None:
        venv_bin = sandbox.pia / "venv" / "bin"
        venv_bin.mkdir(parents=True)
        failing_stub = """#!/bin/sh
echo "acrux $*" >> "$STUB_LOG"
if [ "$1" = "backup" ]; then exit 1; fi
exit 0
"""
        make_executable(venv_bin / "acrux", failing_stub)
        make_executable(venv_bin / "python", "#!/bin/sh\nexit 0\n")

        result = run_script(UPGRADE_SH, "--channel", "main", env=sandbox.env)

        assert result.returncode != 0
        log = stub_log_text(sandbox)
        assert "acrux backup create" in log
        assert "uv pip install" not in log
        assert "acrux doctor" not in log
        assert "acrux daemon" not in log

    def test_upgrade_requires_existing_install(self, sandbox) -> None:
        result = run_script(UPGRADE_SH, "--channel", "main", env=sandbox.env)
        assert result.returncode != 0
        assert "install.sh" in result.stderr


class TestUninstallFunctional:
    def _seed_install(self, sandbox) -> None:
        venv_bin = sandbox.pia / "venv" / "bin"
        venv_bin.mkdir(parents=True)
        make_executable(venv_bin / "acrux", ACRUX_STUB)
        sandbox.acrux_home.mkdir(parents=True)
        (sandbox.acrux_home / "config.yaml").write_text("api_token: secret\n")
        if sys.platform == "darwin":
            plist = sandbox.home / "Library" / "LaunchAgents"
            plist.mkdir(parents=True)
            (plist / "dev.pia.acrux.plist").write_text("<plist/>")
        else:
            unit_dir = sandbox.home / ".config" / "systemd" / "user"
            unit_dir.mkdir(parents=True)
            (unit_dir / "pia-acrux.service").write_text("[Service]\n")

    def test_uninstall_keeps_data_by_default(self, sandbox) -> None:
        self._seed_install(sandbox)
        result = run_script(UNINSTALL_SH, "--yes", env=sandbox.env)
        assert result.returncode == 0, result.stderr
        assert not sandbox.pia.exists(), "~/.pia should be removed"
        assert (sandbox.acrux_home / "config.yaml").exists(), "~/.acrux is kept without --purge"
        if sys.platform == "darwin":
            assert not (sandbox.home / "Library" / "LaunchAgents" / "dev.pia.acrux.plist").exists()
        else:
            assert not (sandbox.home / ".config" / "systemd" / "user" / "pia-acrux.service").exists()

    def test_uninstall_purge_removes_data(self, sandbox) -> None:
        self._seed_install(sandbox)
        result = run_script(UNINSTALL_SH, "--yes", "--purge", env=sandbox.env)
        assert result.returncode == 0, result.stderr
        assert not sandbox.pia.exists()
        assert not sandbox.acrux_home.exists(), "--purge must remove ~/.acrux"

    def test_uninstall_requires_yes_when_non_interactive(self, sandbox) -> None:
        self._seed_install(sandbox)
        result = run_script(UNINSTALL_SH, env=sandbox.env)
        assert result.returncode != 0
        assert "--yes" in result.stderr
        assert sandbox.pia.exists(), "nothing should be removed without confirmation"
