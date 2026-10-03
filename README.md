# muse-arr

Talk to your *arr stack from the Muse app on your phone. Sonarr, Radarr,
and Jellyfin, without SSHing into the server.

Runs on any always-on Linux box on your home LAN, via the [Muse Gadgets
Linux SDK](https://github.com/facebookincubator/muse-gadget-sdk) (Apache
2.0, vendored in `linux/`).

## How it works

Muse is Meta's AI assistant; it lives in an app on your phone. A Muse
gadget is a small computer on your home network that Muse can send commands
to.

This gadget sits on your LAN and does two things:

1. It talks to Sonarr, Radarr, and Jellyfin over plain HTTP, using the same
   APIs their web UIs use.
2. It holds an encrypted session to Muse over the internet, so your phone
   reaches your media stack through it.

You ask Muse for a movie. Muse tells the gadget. The gadget tells Radarr.
Radarr grabs it. No SSH, no web UI.

Bluetooth is only for pairing: your phone needs to be next to the gadget
once, to prove the box is yours. After that it's all internet.

## Install

New to Muse? [muse.ai/join](https://muse.ai/join) takes an invite code in
Settings within 48 hours of signing up: 1 billion bonus tokens for you, the
same for the referrer. Mine is:

```
O638HY
```

Install it on the machine running your *arr stack, or on a separate box.
The only hard requirement is Bluetooth LE, which pairing needs. No
Bluetooth on the server? Either plug in a USB Bluetooth adapter, or put it
on a Raspberry Pi (any 3B+ or newer) on the same LAN. The media commands
are plain HTTP, so the gadget drives your stack over the network either
way.

```sh
git clone https://github.com/vocino/muse-arr.git
cd muse-arr
sudo useradd -m muse && sudo usermod -aG docker muse
bash linux/install.sh --from linux --run-as muse --sdk-token mgst_…
```

SDK token: gadgets.muse.ai > Account > SDK tokens.

```sh
sudo cp linux/media.env.example /var/lib/musegadget/media.env
sudo chmod 600 /var/lib/musegadget/media.env
# fill in your *arr and Jellyfin URLs and API keys
```

API keys: Sonarr/Radarr > Settings > General > Security. Jellyfin >
Dashboard > API Keys > +.

Pair in the Muse app: Settings > Devices > Developer mode on > + >
`MuseGadgetXXXXXX`.

Check it's alive: `sudo journalctl -u musegadget -f` and look for
`registered with the Muse`.

## Where to install

| Your setup | Install the gadget... |
|---|---|
| Ubuntu/Debian server | Directly on it (`apt` and `systemd` work; add a USB Bluetooth adapter if it has no BLE) |
| Raspberry Pi | Directly on it (Bluetooth built in) |
| Synology NAS | On a Pi on the LAN (DSM has no `apt`/`systemd`, and dropped Bluetooth support) |
| Unraid | On a Pi on the LAN (no `apt`/`systemd`/Bluetooth) |
| TrueNAS Scale | On a Pi on the LAN (appliance OS; host changes get wiped) |
| Windows | On a Pi on the LAN (the SDK is Linux-only) |

The media commands are plain HTTP, so any gadget on the LAN works. Point
`media.env` at your server's LAN IP and ports (`http://<server-ip>:8989`,
and so on).

### Keep it local

- Never expose Sonarr/Radarr/Jellyfin to the internet. LAN or VPN only.
- Turn on authentication in each app; don't rely on LAN obscurity.
- API keys are secrets: they live in `/var/lib/musegadget/media.env`
  (root, `chmod 600`), never in git. Rotate on any leak.

## Use

- "Find the show Severance"
- "Add it and start downloading"
- "What's downloading right now?"
- "What's new on Jellyfin?"

## Commands

| Command | What it does |
|---|---|
| `media.search` | Search Sonarr/Radarr by title |
| `media.add` | Add a series/movie by id, monitor it, start a search |
| `media.queue` | Merged Sonarr/Radarr download queue |
| `media.recent` | Recently added on Jellyfin |
| `homelab.docker` | `ps` lists containers, `restart` bounces one |

## What's inside

- `linux/src/musegadget/media.py`: the media commands (stdlib only)
- `linux/src/musegadget/executor.py`: command specs and dispatch
- `linux/tests/`: mocked HTTP tests
- `linux/media.env.example`: config template (keys stay on the Pi)

## Develop

```sh
cd linux && PYTHONPATH=src python3 -m pytest tests -q
```

## Provenance

`linux/` is the Muse Gadgets Linux SDK, vendored. Our changes are marked
`# --- muse-arr ---` in `linux/src/musegadget/executor.py`; everything else
we added is `linux/src/musegadget/media.py`, `linux/tests/test_media.py`,
and `linux/media.env.example`.
