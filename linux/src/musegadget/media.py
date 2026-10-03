# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Gadget commands for a *arr + Jellyfin media stack.

Every call here is plain HTTP against the services' local APIs, so these
commands run on any gadget with LAN access to the media server -- they do not
need to run on the server itself.

Config lives in ``/var/lib/musegadget/media.env`` (``KEY=VALUE`` lines, mode
0600), e.g.::

    SONARR_URL=http://blade:8989
    SONARR_API_KEY=...
    RADARR_URL=http://blade:7878
    RADARR_API_KEY=...
    JELLYFIN_URL=http://blade:8096
    JELLYFIN_API_KEY=...
    MEDIA_QUALITY_PROFILE_ID=1   # optional, else the first profile
    MEDIA_ROOT_FOLDER=/media/tv  # optional, else the first root folder
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

CONFIG_PATH = "/var/lib/musegadget/media.env"
HTTP_TIMEOUT_S = 30


class MediaError(Exception):
    """A user-facing media command failure."""


def _load_config(path: str = CONFIG_PATH) -> dict:
    cfg: dict = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    cfg[key.strip()] = value.strip().strip("\"").strip("'")
    except OSError:
        pass
    return cfg


def _need(cfg: dict, *names: str) -> None:
    missing = [n for n in names if not cfg.get(n)]
    if missing:
        raise MediaError(f"not configured: {', '.join(missing)} (see {CONFIG_PATH})")


def _arr(cfg: dict, service: str, method: str, path: str, body: dict | None = None):
    """Call a Sonarr/Radarr v3 API endpoint."""
    prefix = service.upper()
    _need(cfg, f"{prefix}_URL", f"{prefix}_API_KEY")
    url = cfg[f"{prefix}_URL"].rstrip("/") + "/api/v3" + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "X-Api-Key": cfg[f"{prefix}_API_KEY"],
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise MediaError(f"{service} HTTP {exc.code}: {detail or exc.reason}")
    except (urllib.error.URLError, OSError) as exc:
        raise MediaError(f"cannot reach {service}: {exc}")


def _jellyfin(cfg: dict, method: str, path: str):
    """Call the Jellyfin API."""
    _need(cfg, "JELLYFIN_URL", "JELLYFIN_API_KEY")
    url = cfg["JELLYFIN_URL"].rstrip("/") + path
    req = urllib.request.Request(
        url, method=method,
        headers={"X-MediaBrowser-Token": cfg["JELLYFIN_API_KEY"],
                 "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise MediaError(f"jellyfin HTTP {exc.code}: {detail or exc.reason}")
    except (urllib.error.URLError, OSError) as exc:
        raise MediaError(f"cannot reach jellyfin: {exc}")


def _profile_and_root(cfg: dict, service: str) -> tuple:
    profile_id = cfg.get("MEDIA_QUALITY_PROFILE_ID")
    root = cfg.get("MEDIA_ROOT_FOLDER")
    if profile_id is None:
        profiles = _arr(cfg, service, "GET", "/qualityprofile")
        if not profiles:
            raise MediaError(f"{service}: no quality profiles found")
        profile_id = profiles[0]["id"]
    if root is None:
        folders = _arr(cfg, service, "GET", "/rootfolder")
        if not folders:
            raise MediaError(f"{service}: no root folders found")
        root = folders[0]["path"]
    return profile_id, root


def search(cfg: dict, params: dict) -> dict:
    query = params.get("query")
    if not isinstance(query, str) or not query.strip():
        raise MediaError("query is required")
    kind = params.get("type") or "series"
    if kind == "series":
        _need(cfg, "SONARR_URL", "SONARR_API_KEY")
        results = _arr(cfg, "sonarr", "GET",
                       "/series/lookup?term=" + urllib.parse.quote(query))
        return {"results": [
            {"title": r.get("title"), "year": r.get("year"),
             "tvdbId": r.get("tvdbId"),
             "overview": (r.get("overview") or "")[:200]}
            for r in results[:10]
        ]}
    if kind == "movie":
        _need(cfg, "RADARR_URL", "RADARR_API_KEY")
        results = _arr(cfg, "radarr", "GET",
                       "/movie/lookup?term=" + urllib.parse.quote(query))
        return {"results": [
            {"title": r.get("title"), "year": r.get("year"),
             "tmdbId": r.get("tmdbId"),
             "overview": (r.get("overview") or "")[:200]}
            for r in results[:10]
        ]}
    raise MediaError("type must be 'series' or 'movie'")


def add(cfg: dict, params: dict) -> dict:
    kind = params.get("type") or "series"
    title = params.get("title")
    ref_id = params.get("id")
    if not isinstance(title, str) or not title.strip():
        raise MediaError("title is required")
    if not isinstance(ref_id, int):
        raise MediaError("id is required (tvdbId for series, tmdbId for movie)")
    if kind == "series":
        service, key, lookup = "sonarr", "tvdbId", "tvdbId"
        results = _arr(cfg, service, "GET",
                       "/series/lookup?term=" + urllib.parse.quote(title))
        match = next((r for r in results if r.get(key) == ref_id), None)
        if match is None:
            raise MediaError(f"no series lookup result with tvdbId {ref_id}")
        profile_id, root = _profile_and_root(cfg, service)
        payload = {
            "tvdbId": match["tvdbId"], "title": match["title"],
            "titleSlug": match.get("titleSlug"), "images": match.get("images", []),
            "seasons": match.get("seasons", []),
            "qualityProfileId": profile_id, "rootFolderPath": root,
            "monitored": True, "seasonFolder": True,
            "addOptions": {"searchForMissingEpisodes": True},
        }
        created = _arr(cfg, service, "POST", "/series", payload)
        _arr(cfg, service, "POST", "/command",
             {"name": "SeriesSearch", "seriesId": created["id"]})
        return {"added": created["title"], "searching": True}
    if kind == "movie":
        results = _arr(cfg, "radarr", "GET",
                       "/movie/lookup?term=" + urllib.parse.quote(title))
        match = next((r for r in results if r.get("tmdbId") == ref_id), None)
        if match is None:
            raise MediaError(f"no movie lookup result with tmdbId {ref_id}")
        profile_id, root = _profile_and_root(cfg, "radarr")
        payload = {
            "tmdbId": match["tmdbId"], "title": match["title"],
            "titleSlug": match.get("titleSlug"), "images": match.get("images", []),
            "qualityProfileId": profile_id, "rootFolderPath": root,
            "monitored": True, "minimumAvailability": "released",
            "addOptions": {"searchForMovie": True},
        }
        created = _arr(cfg, "radarr", "POST", "/movie", payload)
        _arr(cfg, "radarr", "POST", "/command",
             {"name": "MoviesSearch", "movieIds": [created["id"]]})
        return {"added": created["title"], "searching": True}
    raise MediaError("type must be 'series' or 'movie'")


def queue(cfg: dict, params: dict) -> dict:
    items = []
    for service in ("sonarr", "radarr"):
        prefix = service.upper()
        if not cfg.get(f"{prefix}_URL") or not cfg.get(f"{prefix}_API_KEY"):
            continue
        data = _arr(cfg, service, "GET", "/queue?page=1&pageSize=20")
        for record in data.get("records", []):
            size = record.get("size") or 0
            left = record.get("sizeleft") or 0
            percent = round(100 * (size - left) / size) if size else 0
            items.append({
                "service": service,
                "title": record.get("title"),
                "status": record.get("status"),
                "percent": percent,
                "timeleft": record.get("timeleft"),
            })
    return {"queue": items}


def recent(cfg: dict, params: dict) -> dict:
    limit = params.get("limit") or 10
    user_id = cfg.get("JELLYFIN_USER_ID")
    if not user_id:
        me = _jellyfin(cfg, "GET", "/Users/Me")
        user_id = me["Id"]
    query = urllib.parse.urlencode({
        "SortBy": "DateCreated", "SortOrder": "Descending",
        "IncludeItemTypes": "Movie,Episode", "Recursive": "true",
        "Limit": 40,
        "Fields": "Overview,PremiereDate,SeriesName,ProductionYear",
    })
    data = _jellyfin(cfg, "GET", f"/Users/{user_id}/Items?{query}")
    items, seen_series = [], set()
    for entry in data.get("Items", []):
        if entry.get("Type") == "Episode":
            series = entry.get("SeriesName")
            if series in seen_series:
                continue
            seen_series.add(series)
            name = f"{series} - {entry.get('Name')}"
        else:
            name = entry.get("Name")
        items.append({
            "name": name,
            "type": entry.get("Type"),
            "year": entry.get("ProductionYear"),
            "overview": (entry.get("Overview") or "")[:160],
        })
        if len(items) >= limit:
            break
    return {"recent": items}


_COMMANDS = {"search": search, "add": add, "queue": queue, "recent": recent}


def run(action: str, params: dict, config_path: str = CONFIG_PATH) -> dict:
    """Run a media command. Raises MediaError on failure."""
    if action not in _COMMANDS:
        raise MediaError(f"unsupported media action: {action}")
    return _COMMANDS[action](_load_config(config_path), params or {})
