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

from __future__ import annotations

import io
import json

import pytest

from musegadget import media
from musegadget.media import MediaError


CFG = {
    "SONARR_URL": "http://blade:8989",
    "SONARR_API_KEY": "sonarr-key",
    "RADARR_URL": "http://blade:7878",
    "RADARR_API_KEY": "radarr-key",
    "JELLYFIN_URL": "http://blade:8096",
    "JELLYFIN_API_KEY": "jellyfin-key",
}

SERIES_LOOKUP = [
    {"title": "Severance", "year": 2022, "tvdbId": 369638,
     "titleSlug": "severance", "images": [], "seasons": [],
     "overview": "A thriller about work-life balance taken literally."},
]

MOVIE_LOOKUP = [
    {"title": "Dune", "year": 2021, "tmdbId": 438631,
     "titleSlug": "dune-438631", "images": [], "overview": "Spice must flow."},
]


class _Resp:
    def __init__(self, payload):
        self._buf = io.BytesIO(json.dumps(payload).encode())

    def read(self, *a):
        return self._buf.read(*a)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _fake_http(monkeypatch, routes):
    """routes: list of (method, path_prefix, payload). Returns captured requests."""
    captured = []

    def fake_urlopen(req, timeout=None):
        captured.append((req.method, req.full_url,
                         json.loads(req.data.decode()) if req.data else None))
        for method, prefix, payload in routes:
            if req.method == method and prefix in req.full_url:
                if isinstance(payload, Exception):
                    raise payload
                return _Resp(payload)
        raise AssertionError(f"unexpected request: {req.method} {req.full_url}")

    monkeypatch.setattr(media.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(media, "_load_config", lambda path=media.CONFIG_PATH: dict(CFG))
    return captured


def test_search_series(monkeypatch):
    _fake_http(monkeypatch, [("GET", "/series/lookup", SERIES_LOOKUP)])
    out = media.run("search", {"query": "Severance"})
    assert out["results"][0]["tvdbId"] == 369638


def test_search_movie(monkeypatch):
    _fake_http(monkeypatch, [("GET", "/movie/lookup", MOVIE_LOOKUP)])
    out = media.run("search", {"query": "Dune", "type": "movie"})
    assert out["results"][0]["tmdbId"] == 438631


def test_search_needs_query(monkeypatch):
    monkeypatch.setattr(media, "_load_config", lambda path=media.CONFIG_PATH: dict(CFG))
    with pytest.raises(MediaError):
        media.run("search", {})


def test_add_series_posts_and_triggers_search(monkeypatch):
    captured = _fake_http(monkeypatch, [
        ("GET", "/series/lookup", SERIES_LOOKUP),
        ("GET", "/qualityprofile", [{"id": 6}]),
        ("GET", "/rootfolder", [{"path": "/media/tv"}]),
        ("POST", "/api/v3/series", {"id": 42, "title": "Severance"}),
        ("POST", "/api/v3/command", {}),
    ])
    out = media.run("add", {"id": 369638, "title": "Severance"})
    assert out == {"added": "Severance", "searching": True}
    posts = [c for c in captured if c[0] == "POST"]
    add_body = next(b for m, u, b in posts if u.endswith("/api/v3/series"))
    assert add_body["qualityProfileId"] == 6
    assert add_body["rootFolderPath"] == "/media/tv"
    assert add_body["addOptions"] == {"searchForMissingEpisodes": True}
    cmd_body = next(b for m, u, b in posts if u.endswith("/api/v3/command"))
    assert cmd_body == {"name": "SeriesSearch", "seriesId": 42}


def test_add_movie(monkeypatch):
    captured = _fake_http(monkeypatch, [
        ("GET", "/movie/lookup", MOVIE_LOOKUP),
        ("GET", "/qualityprofile", [{"id": 6}]),
        ("GET", "/rootfolder", [{"path": "/media/movies"}]),
        ("POST", "/api/v3/movie", {"id": 7, "title": "Dune"}),
        ("POST", "/api/v3/command", {}),
    ])
    out = media.run("add", {"id": 438631, "title": "Dune", "type": "movie"})
    assert out == {"added": "Dune", "searching": True}
    cmd_body = next(b for m, u, b in captured if u.endswith("/api/v3/command"))
    assert cmd_body == {"name": "MoviesSearch", "movieIds": [7]}


def test_add_rejects_unknown_id(monkeypatch):
    _fake_http(monkeypatch, [("GET", "/series/lookup", SERIES_LOOKUP)])
    with pytest.raises(MediaError, match="no series lookup result"):
        media.run("add", {"id": 1, "title": "Severance"})


def test_queue_merges_services(monkeypatch):
    _fake_http(monkeypatch, [
        ("GET", "blade:8989/api/v3/queue",
         {"records": [{"title": "Show.S01E01", "status": "downloading",
                        "size": 1000, "sizeleft": 250, "timeleft": "00:10:00"}]}),
        ("GET", "blade:7878/api/v3/queue",
         {"records": [{"title": "Movie.2021", "status": "queued",
                        "size": 2000, "sizeleft": 2000, "timeleft": None}]}),
    ])
    out = media.run("queue", {})
    assert [(i["service"], i["title"], i["percent"]) for i in out["queue"]] == [
        ("sonarr", "Show.S01E01", 75), ("radarr", "Movie.2021", 0)]


def test_recent_dedupes_episodes_by_series(monkeypatch):
    _fake_http(monkeypatch, [
        ("GET", "/Users/Me", {"Id": "user1"}),
        ("GET", "/Users/user1/Items", {"Items": [
            {"Name": "Episode 2", "Type": "Episode", "SeriesName": "Severance",
             "ProductionYear": 2022, "Overview": "x"},
            {"Name": "Episode 1", "Type": "Episode", "SeriesName": "Severance",
             "ProductionYear": 2022, "Overview": "x"},
            {"Name": "Dune", "Type": "Movie", "ProductionYear": 2021, "Overview": "y"},
        ]}),
    ])
    out = media.run("recent", {})
    assert [i["name"] for i in out["recent"]] == ["Severance - Episode 2", "Dune"]


def test_missing_config_is_a_clean_error(monkeypatch):
    monkeypatch.setattr(media, "_load_config", lambda path=media.CONFIG_PATH: {})
    result = media.run("queue", {})
    assert result == {"queue": []}
    with pytest.raises(MediaError, match="not configured"):
        media.run("search", {"query": "x"})


def test_unknown_action(monkeypatch):
    monkeypatch.setattr(media, "_load_config", lambda path=media.CONFIG_PATH: dict(CFG))
    with pytest.raises(MediaError, match="unsupported media action"):
        media.run("nope", {})
