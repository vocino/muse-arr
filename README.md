# muse-arr

Talk to your *arr stack from the Muse app on your phone. Sonarr, Radarr,
and Jellyfin, without SSHing into the server.

Runs on a Raspberry Pi on your home LAN, via the [Muse Gadgets Linux
SDK](https://github.com/facebookincubator/muse-gadget-sdk) (Apache 2.0,
vendored in `linux/`).

## Install

Use a Pi, not the media server itself. Pairing needs Bluetooth LE, which
server blades don't have. The Pi pairs with your phone once, then drives
the *arr and Jellyfin APIs over HTTP.

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
`# --- muse-arr ---` in `src/musegadget/executor.py`; everything else we
added is `src/musegadget/media.py`, `tests/test_media.py`, and
`media.env.example`.
