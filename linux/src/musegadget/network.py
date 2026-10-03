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

"""Connectivity checks used during setup."""

from __future__ import annotations

import shutil
import socket
import subprocess

from musegadget.muse_api import API_BASE

CURRENT_CONNECTION_LABEL = "Use current connection"


def is_online(timeout: float = 5.0) -> bool:
    """True if the Muse API host accepts a TCP connection."""
    host = API_BASE.split("://", 1)[-1].split("/", 1)[0]
    try:
        with socket.create_connection((host, 443), timeout=timeout):
            return True
    except OSError:
        return False


def active_wifi_ssid() -> str | None:
    """SSID of the active Wi-Fi connection, via NetworkManager if present."""
    if not shutil.which("nmcli"):
        return None
    try:
        out = subprocess.run(
            ["nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi", "list", "--rescan", "no"],
            capture_output=True, text=True, timeout=5, check=False,
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    for line in out.splitlines():
        active, _, ssid = line.partition(":")
        if active == "yes" and ssid:
            return ssid.replace("\\:", ":")
    return None


def current_connection_entry() -> dict:
    """The single scan entry offered when the device is already online.

    It is marked open so the apps skip the password field. The device ignores
    whatever credentials come back. Using the real SSID lets the app preselect
    it when the phone is on the same network.
    """
    return {
        "ssid": active_wifi_ssid() or CURRENT_CONNECTION_LABEL,
        "rssi": -40,
        "secure": False,
    }
