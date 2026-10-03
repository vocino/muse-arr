# muse media gadget

A Meta Muse gadget that runs your *arr stack and Jellyfin. Install it on a
Raspberry Pi on your home LAN and manage your media server from the Muse app
on your phone — no more SSHing into the box to add a show.

Built on the Linux SDK from [Muse
Gadgets](https://github.com/facebookincubator/muse-gadget-sdk) (Apache 2.0,
vendored in `linux/`).

## Install

Run it on a Raspberry Pi on the same LAN as your media server, not on the
server itself. Pairing needs Bluetooth LE, which server blades don't have.
The Pi pairs with your phone, then drives the *arr and Jellyfin APIs over
HTTP.

On the Pi:

```sh
sudo useradd -m muse && sudo usermod -aG docker muse
bash linux/install.sh --from linux --run-as muse --sdk-token mgst_…
```

Get the SDK token at gadgets.muse.ai > Account > SDK tokens.

Copy `linux/media.env.example` to `/var/lib/musegadget/media.env` (as root,
`chmod 600`) and fill in your *arr and Jellyfin URLs and API keys. Keys:
*arr > Settings > General > Security > API Key; Jellyfin > Dashboard > API
Keys > +.

Then pair: Muse app > Settings > Devices > Developer mode on > + >
`MuseGadgetXXXXXX`. Bluetooth is only needed for pairing; after that the Pi
dials out to your Muse over an encrypted session.

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
- `linux/tests/`: mocked HTTP tests, 150 passing
- `linux/media.env.example`: config template (real keys stay on the Pi)

## Develop

```sh
cd linux && PYTHONPATH=src python3 -m pytest tests -q
```

## Provenance

`linux/` is the [Muse Gadgets Linux
SDK](https://github.com/facebookincubator/muse-gadget-sdk) (Apache 2.0),
vendored. Our changes on top are marked `# --- muse-arr ---` in
`src/musegadget/executor.py`, plus new files `src/musegadget/media.py`,
`tests/test_media.py`, and `media.env.example`.
