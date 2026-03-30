"""GitHub Releases + manifest.json helpers for OTA (no UI)."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Callable

import requests

from config import OTA_HTTP_USER_AGENT


@dataclass(frozen=True)
class UpdateInfo:
    latest_version: str
    zip_url: str
    sha256: str


def _parse_version_tuple(v: str) -> tuple[int, ...]:
    v = (v or "").strip().lstrip("vV")
    v = re.sub(r"[^0-9.]", "", v)
    parts = [p for p in v.split(".") if p != ""]
    nums: list[int] = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    return tuple(nums)


def is_version_newer(latest: str, current: str) -> bool:
    return _parse_version_tuple(latest) > _parse_version_tuple(current)


def normalize_github_repo(repo: str) -> str | None:
    repo = (repo or "").strip()
    if not repo:
        return None
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        return repo
    m = re.search(r"github\.com/([^/]+)/([^/]+?)(?:\.git)?$", repo)
    if m:
        owner, name = m.group(1), m.group(2)
        if owner and name:
            return f"{owner}/{name}"
    m = re.search(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", repo)
    if m:
        owner, name = m.group(1), m.group(2)
        if owner and name:
            return f"{owner}/{name}"
    return None


def load_repo_from_embedded_source(
    *,
    write_log: Callable[[str], None] | None = None,
) -> str | None:
    """Read ``github_repo`` from ``config.json`` next to the frozen exe (or under ``_internal``)."""
    try:
        installed_dir = os.path.dirname(sys.executable)
        name = "config.json"
        src_path = os.path.join(installed_dir, name)
        if not os.path.exists(src_path) or os.path.isdir(src_path):
            src_path = os.path.join(installed_dir, "_internal", name)
            if os.path.exists(src_path) and os.path.isdir(src_path):
                src_path = os.path.join(src_path, name)
            if not os.path.exists(src_path):
                return None

        with open(src_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        repo = (payload.get("github_repo") or "").strip()
        return repo or None
    except Exception as e:
        if write_log:
            write_log(f"[load_repo_from_embedded_source] failed: {e}")
        return None


def fetch_latest_release_json(
    repo: str,
    *,
    api_url_template: str = "https://api.github.com/repos/{repo}/releases/latest",
    timeout_s: int = 20,
    write_log: Callable[[str], None] | None = None,
) -> dict | None:
    api_url = api_url_template.format(repo=repo)
    headers = {"User-Agent": OTA_HTTP_USER_AGENT}
    try:
        r = requests.get(api_url, headers=headers, timeout=timeout_s)
        if r.status_code != 200:
            if write_log:
                write_log(f"[check_latest_release_json] status_code={r.status_code}")
            return None
        return r.json()
    except Exception as e:
        if write_log:
            write_log(f"[check_latest_release_json] failed: {e}")
        return None


def download_text(
    url: str, *, timeout_s: int = 20, write_log: Callable[[str], None] | None = None
) -> str | None:
    headers = {"User-Agent": OTA_HTTP_USER_AGENT}
    try:
        r = requests.get(url, headers=headers, timeout=timeout_s)
        if r.status_code != 200:
            return None
        return r.text
    except Exception as e:
        if write_log:
            write_log(f"[download_text] failed: {e}")
        return None


def parse_update_info(
    release: dict,
    *,
    current_version: str,
    manifest_asset_name: str,
    timeout_s: int = 20,
    write_log: Callable[[str], None] | None = None,
) -> UpdateInfo | None:
    assets = release.get("assets") or []
    manifest_asset = next(
        (a for a in assets if (a.get("name") or "") == manifest_asset_name),
        None,
    )
    if not manifest_asset:
        if write_log:
            write_log("[get_update_info] manifest.json asset not found")
        return None
    manifest_url = manifest_asset.get("browser_download_url")
    if not manifest_url:
        return None

    manifest_text = download_text(manifest_url, timeout_s=timeout_s, write_log=write_log)
    if not manifest_text:
        return None

    try:
        manifest = json.loads(manifest_text)
    except Exception:
        if write_log:
            write_log("[get_update_info] manifest parse failed")
        return None

    latest_version = str(manifest.get("version") or release.get("tag_name") or "")
    sha256 = str(manifest.get("sha256") or "")
    if not latest_version or not sha256:
        if write_log:
            write_log("[get_update_info] manifest missing version/sha256")
        return None

    zip_url = None
    if manifest.get("zip_url"):
        zip_url = str(manifest["zip_url"])
    if not zip_url and manifest.get("zip_asset_name"):
        zip_asset_name = str(manifest["zip_asset_name"])
        zip_asset = next((a for a in assets if a.get("name") == zip_asset_name), None)
        if zip_asset and zip_asset.get("browser_download_url"):
            zip_url = str(zip_asset["browser_download_url"])

    if not zip_url:
        if write_log:
            write_log("[get_update_info] zip_url not found in manifest/assets")
        return None

    if not is_version_newer(latest_version, current_version):
        if write_log:
            write_log(
                f"[get_update_info] latest_version={latest_version!r} current_version={current_version!r}"
            )
        return None

    return UpdateInfo(latest_version=latest_version, zip_url=zip_url, sha256=sha256)
