# AGENTS.md

## Code Map

- .github: project configuration
- linux/: vendored Muse Gadgets Linux SDK (see Provenance in README.md)
- linux/src/musegadget/media.py, linux/tests/test_media.py, linux/media.env.example: our media commands
- linux/src/musegadget/executor.py, linux/tests/test_executor.py: upstream plus our `# --- muse-arr ---` sections
- linux/.upstream-sha: the upstream commit our vendor is synced to

## Vendor sync

`linux/` tracks facebookincubator/muse-gadget-sdk. `.github/workflows/vendor-sync.yml`
runs weekly: it diffs upstream `linux/` between `linux/.upstream-sha` and upstream
main, then `git apply`s that diff onto our tree. Our changes live in separate hunks
under `# --- muse-arr ---` markers, so upstream's diff applies cleanly in the common
case. On a clean apply it updates the pin, runs tests and shellcheck, and opens a PR
(never pushes to main). On conflict it opens an issue for manual resolution: apply what
fits, keep our markers, update the pin, run tests.
