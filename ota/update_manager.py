import hashlib
from typing import Optional
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

from config import (
    MAIN_EXE_BASENAME,
    OTA_HTTP_USER_AGENT,
    OTA_TEMP_DIR_NAME,
    UPDATER_EXE_BASENAME,
    UPDATE_ERROR_CAPTION,
    UPDATE_WINDOW_TITLE,
)
from ota.github import (
    UpdateInfo,
    fetch_latest_release_json,
    load_repo_from_embedded_source,
    normalize_github_repo,
    parse_update_info,
)
from ui_components import ModernPromptDialog, ModernProgressDialog


class OTALocalCancelled(Exception):
    """Raised when the user cancels an OTA download in the progress dialog."""


class UpdateManager:
    """
    GitHub Releases lookup, manifest + ZIP download with sha256 check,
    and spawning the platform OTA updater to replace the installed app folder.
    """

    def __init__(
        self,
        *,
        github_repo: str,
        current_version: str,
        config_dir: Path,
        github_api_url_template: str = "https://api.github.com/repos/{repo}/releases/latest",
        manifest_asset_name: Optional[str] = None,
        timeout_s: int = 20,
    ):
        self.github_repo = (github_repo or "").strip()
        self.current_version = current_version
        self.config_dir = Path(config_dir)
        self.github_api_url_template = github_api_url_template
        if manifest_asset_name:
            self.manifest_asset_name = manifest_asset_name
        else:
            self.manifest_asset_name = self._default_manifest_asset_name()
        self.timeout_s = timeout_s
        self.log_file = self.config_dir / "ota.log"

    @staticmethod
    def _default_manifest_asset_name() -> Optional[str]:
        if sys.platform.startswith("win"):
            return "manifest-win.json"
        if sys.platform.startswith("linux"):
            return "manifest-linux.json"
        if sys.platform.startswith("darwin"):
            return "manifest-macos.json"
        return None

    @staticmethod
    def _candidate_binary_names(name: str) -> list[str]:
        name = (name or "").strip()
        if not name:
            return []
        candidates = [name]
        if sys.platform.startswith("win") and not name.lower().endswith(".exe"):
            candidates.append(f"{name}.exe")
        return candidates

    def _resolve_binary_path(self, installed_dir: Path, configured_name: str) -> Optional[Path]:
        for candidate in self._candidate_binary_names(configured_name):
            candidate_path = installed_dir / candidate
            if candidate_path.exists():
                return candidate_path
        return None

    def _write_log(self, msg: str):
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(msg.rstrip() + "\n")
        except Exception:
            pass

    def _download_to_file(
        self,
        url: str,
        dest_path: Path,
        *,
        cancel_check=None,
        progress_dialog=None,
        label_prefix: Optional[str] = None,
    ):
        headers = {"User-Agent": OTA_HTTP_USER_AGENT}
        timeout = (10, max(60, int(self.timeout_s) * 6))
        written = 0
        total = None
        with requests.get(url, headers=headers, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            try:
                cl = r.headers.get("Content-Length")
                if cl:
                    total = int(cl)
            except Exception:
                total = None

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                if progress_dialog is not None and total:
                    progress_dialog.setRange(0, total)
                    progress_dialog.setValue(0)
                elif progress_dialog is not None:
                    progress_dialog.setRange(0, 0)

                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    if cancel_check and cancel_check():
                        raise OTALocalCancelled()
                    f.write(chunk)
                    written += len(chunk)

                    if progress_dialog is not None and total:
                        progress_dialog.setValue(min(written, total))
                        if label_prefix:
                            percent = int((written * 100) / total)
                            progress_dialog.setLabelText(f"{label_prefix} {percent}%")

    def _sha256_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()

    def _get_update_info(self) -> Optional[UpdateInfo]:
        if not self.manifest_asset_name:
            self._write_log("[startup_check] no manifest asset configured for this platform")
            return None

        repo = self.github_repo or load_repo_from_embedded_source(write_log=self._write_log) or ""
        repo = normalize_github_repo(repo) or ""
        if not repo:
            return None

        release = fetch_latest_release_json(
            repo,
            api_url_template=self.github_api_url_template,
            timeout_s=self.timeout_s,
            write_log=self._write_log,
        )
        if not release:
            return None

        info = parse_update_info(
            release,
            current_version=self.current_version,
            manifest_asset_name=self.manifest_asset_name,
            timeout_s=self.timeout_s,
            write_log=self._write_log,
        )
        return info

    def prompt_and_update(self, parent_widget=None) -> bool:
        try:
            from PyQt6.QtCore import Qt
            from PyQt6.QtWidgets import (
                QApplication,
                QDialog,
                QHBoxLayout,
                QLabel,
                QMessageBox,
                QProgressDialog,
                QPushButton,
                QVBoxLayout,
            )
        except Exception as e:
            self._write_log(f"[prompt_and_update] PyQt6 import failed: {e}")
            return False

        raw_repo_input = self.github_repo
        resolved_repo = raw_repo_input or load_repo_from_embedded_source(write_log=self._write_log) or ""
        resolved_repo = normalize_github_repo(resolved_repo) or ""

        self._write_log(
            f"[startup_check] current_version={self.current_version!r} "
            f"github_repo={resolved_repo!r}"
        )

        info = self._get_update_info()
        if not info:
            self._write_log("[startup_check] no update available")
            return False

        current_version = self.current_version
        latest_version = info.latest_version

        dlg = ModernPromptDialog(
            parent=parent_widget,
            title=UPDATE_WINDOW_TITLE,
            headline_text="An update is available.",
            info_text=f"Current: {current_version}\nLatest:  {latest_version}\n\nDownload and update now?",
            min_width=460,
            min_height=200
        )
        dlg.exec()

        if not dlg.is_accepted:
            return False

        progress = ModernProgressDialog(
            parent=parent_widget,
            title=UPDATE_WINDOW_TITLE,
            label_text="Preparing update...",
            min_width=480,
            min_height=210
        )
        progress.show()

        cancelled = {"value": False}

        def _cancel_check() -> bool:
            return cancelled["value"] or progress.wasCanceled()

        def _on_cancel():
            cancelled["value"] = True
            progress.setLabelText("Cancelling...")

        try:
            progress.canceled.connect(_on_cancel)
        except Exception:
            pass

        try:
            def _on_finished():
                cancelled["value"] = progress.wasCanceled()

            progress.finished.connect(_on_finished)
        except Exception:
            pass

        try:
            tmp_dir = Path(tempfile.gettempdir()) / OTA_TEMP_DIR_NAME
            zip_path = tmp_dir / f"update_{info.latest_version}.zip"
            if zip_path.exists():
                try:
                    zip_path.unlink()
                except Exception:
                    pass

            progress.setLabelText("Downloading update...")
            progress.setRange(0, 0)
            self._write_log(f"[download] url={info.zip_url}")
            QApplication.processEvents()
            self._download_to_file(
                info.zip_url,
                zip_path,
                cancel_check=_cancel_check,
                progress_dialog=progress,
                label_prefix="Downloading update...",
            )

            if progress.wasCanceled():
                self._write_log("[download] cancelled by user")
                return False

            progress.setLabelText("Verifying download...")
            QApplication.processEvents()

            self._write_log("[download] verifying sha256...")
            QApplication.processEvents()
            actual = self._sha256_file(zip_path)
            if actual.lower() != info.sha256.lower():
                QMessageBox.critical(
                    parent_widget,
                    UPDATE_ERROR_CAPTION,
                    "Update download verification failed (sha256 mismatch).",
                )
                return False

            installed_dir = Path(os.path.dirname(sys.executable))
            updater_exe = self._resolve_binary_path(installed_dir, UPDATER_EXE_BASENAME)
            if updater_exe is None:
                QMessageBox.critical(
                    parent_widget,
                    UPDATE_ERROR_CAPTION,
                    (
                        "Updater executable not found. "
                        f"Tried: {', '.join(self._candidate_binary_names(UPDATER_EXE_BASENAME))}"
                    ),
                )
                return False

            main_exe = self._resolve_binary_path(installed_dir, MAIN_EXE_BASENAME)
            if main_exe is None:
                QMessageBox.critical(
                    parent_widget,
                    UPDATE_ERROR_CAPTION,
                    (
                        "Main executable not found. "
                        f"Tried: {', '.join(self._candidate_binary_names(MAIN_EXE_BASENAME))}"
                    ),
                )
                return False
            log_path = str(self.log_file)
            subprocess.Popen(
                [
                    str(updater_exe),
                    "--target-dir",
                    str(installed_dir),
                    "--update-zip",
                    str(zip_path),
                    "--main-exe",
                    str(main_exe),
                    "--log-file",
                    log_path,
                    "--new-version",
                    info.latest_version,
                ],
                close_fds=True,
                cwd=str(installed_dir),
            )
            return True
        except OTALocalCancelled:
            self._write_log("[download] cancelled by user (exception)")
            return False
        except Exception as e:
            self._write_log(f"[prompt_and_update] failed: {e}")
            QMessageBox.critical(parent_widget, UPDATE_ERROR_CAPTION, str(e))
            return False
        finally:
            try:
                progress.close()
            except Exception:
                pass
