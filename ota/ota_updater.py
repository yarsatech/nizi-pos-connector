import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

from config import (
    INSTALL_BACKUP_DIR_PREFIX,
    MAIN_EXE_BASENAME,
    OTA_HELPER_CAPTION,
    OTA_STAGING_DIR_PREFIX,
)


logger = logging.getLogger("nizi_pos_connector.ota_updater")


def _configure_logger(log_file: str | None):
    if not log_file:
        return
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
            datefmt="%H:%M:%S",
            handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
        )
    except Exception:
        pass


def _show_error_box(text: str, caption: str = OTA_HELPER_CAPTION):
    """
    Show a Windows-only message box (best-effort).
    """
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, caption, 0x10)
    except Exception:
        pass


def _safe_delete_entry(path: str):
    if os.path.isfile(path) or os.path.islink(path):
        os.unlink(path)
    else:
        shutil.rmtree(path, ignore_errors=True)


def _move_with_retry(src: str, dst: str, *, retries: int = 25, delay_s: float = 0.2):
    """
    Windows can temporarily lock files right as the app exits.
    This small retry loop makes the update more robust.
    """
    last_exc: Exception | None = None
    for _ in range(retries):
        try:
            shutil.move(src, dst)
            return
        except PermissionError as e:
            last_exc = e
            time.sleep(delay_s)
        except Exception:
            raise
    if last_exc:
        raise last_exc


def _find_app_root(extract_root: str) -> str | None:
    main = os.path.join(extract_root, MAIN_EXE_BASENAME)
    if os.path.exists(main):
        return extract_root

    try:
        for name in os.listdir(extract_root):
            candidate = os.path.join(extract_root, name)
            if os.path.isdir(candidate) and os.path.exists(os.path.join(candidate, MAIN_EXE_BASENAME)):
                return candidate
    except Exception:
        pass

    return None


def main():
    parser = argparse.ArgumentParser(description="Nizi POS Connector OTA updater helper")
    parser.add_argument(
        "--target-dir", required=True, help=f"Installed folder containing {MAIN_EXE_BASENAME}"
    )
    parser.add_argument("--update-zip", required=True, help="Downloaded OTA zip file")
    parser.add_argument(
        "--main-exe", required=False, help=f"Path to {MAIN_EXE_BASENAME} inside target-dir"
    )
    parser.add_argument("--log-file", required=False, help="Updater log file path")
    args = parser.parse_args()

    _configure_logger(args.log_file)

    target_dir = os.path.abspath(args.target_dir)
    update_zip = os.path.abspath(args.update_zip)
    main_exe_arg = args.main_exe

    # If the log file is inside the target folder, we must avoid moving it during
    # backup on Windows (moving/renaming a file that's open causes WinError 32).
    log_file_abs = os.path.abspath(args.log_file) if args.log_file else None

    updater_exe_name = os.path.basename(sys.executable)
    updater_exe_name_lower = updater_exe_name.lower()

    if not os.path.isdir(target_dir):
        _show_error_box(f"Updater cannot find target folder:\n{target_dir}")
        return 2
    if not os.path.exists(update_zip):
        _show_error_box(f"Updater cannot find update zip:\n{update_zip}")
        return 2

    backup_dir = None
    staging_dir = None

    try:
        staging_dir = tempfile.mkdtemp(prefix=OTA_STAGING_DIR_PREFIX)
        extract_root = os.path.join(staging_dir, "extract")
        os.makedirs(extract_root, exist_ok=True)

        logger.info(f"Extracting update zip: {update_zip}")
        with zipfile.ZipFile(update_zip, "r") as zf:
            zf.extractall(extract_root)

        app_root = _find_app_root(extract_root)
        if not app_root:
            raise RuntimeError(f"Could not locate {MAIN_EXE_BASENAME} inside the update ZIP.")

        new_main_exe = os.path.join(app_root, MAIN_EXE_BASENAME)
        if not os.path.exists(new_main_exe):
            raise RuntimeError(f"Update ZIP does not contain {MAIN_EXE_BASENAME}.")

        main_exe_path = (
            os.path.abspath(main_exe_arg)
            if main_exe_arg
            else os.path.join(target_dir, MAIN_EXE_BASENAME)
        )

        # Backup everything except the updater itself.
        ts = int(time.time())
        backup_dir = os.path.join(os.path.dirname(target_dir), f"{INSTALL_BACKUP_DIR_PREFIX}{ts}")
        os.makedirs(backup_dir, exist_ok=False)

        logger.info(f"Backing up old install to: {backup_dir}")
        for entry in os.listdir(target_dir):
            if entry.lower() == updater_exe_name_lower:
                continue
            src = os.path.join(target_dir, entry)
            if log_file_abs and os.path.abspath(src).lower() == log_file_abs.lower():
                logger.info("Skipping backup of open log file: ota.log")
                continue
            dst = os.path.join(backup_dir, entry)
            _move_with_retry(src, dst)

        # Copy the new app contents into target_dir.
        logger.info(f"Installing new files into: {target_dir}")
        for entry in os.listdir(app_root):
            if entry.lower() == updater_exe_name_lower:
                # Safety: never overwrite the running updater.
                continue

            src = os.path.join(app_root, entry)
            dst = os.path.join(target_dir, entry)

            if os.path.exists(dst):
                _safe_delete_entry(dst)

            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        if not os.path.exists(main_exe_path):
            raise RuntimeError(
                f"Update failed validation: {MAIN_EXE_BASENAME} not found after install."
            )

        # Cleanup backup after success.
        try:
            shutil.rmtree(backup_dir, ignore_errors=True)
            backup_dir = None
        except Exception:
            pass

        # Restart new version.
        logger.info("Restarting updated app...")
        subprocess.Popen([main_exe_path], cwd=target_dir)
        return 0
    except Exception as e:
        logger.exception("OTA update failed")
        _show_error_box(str(e))

        # Restore previous install if we already moved files.
        if backup_dir and os.path.isdir(backup_dir):
            try:
                # Remove partially installed new files (keep updater).
                for entry in os.listdir(target_dir):
                    if entry.lower() == updater_exe_name_lower:
                        continue
                    dst = os.path.join(target_dir, entry)
                    _safe_delete_entry(dst)

                # Move backup back.
                for entry in os.listdir(backup_dir):
                    src = os.path.join(backup_dir, entry)
                    dst = os.path.join(target_dir, entry)
                    _move_with_retry(src, dst)

                # Try to launch the current (restored) version.
                restored_main = os.path.join(target_dir, MAIN_EXE_BASENAME)
                if os.path.exists(restored_main):
                    subprocess.Popen([restored_main], cwd=target_dir)
            except Exception:
                pass
            finally:
                try:
                    shutil.rmtree(backup_dir, ignore_errors=True)
                except Exception:
                    pass

        return 1
    finally:
        if staging_dir and os.path.isdir(staging_dir):
            try:
                shutil.rmtree(staging_dir, ignore_errors=True)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())

