# ql-server

Quake Live dedicated server, running natively on this ARM64 box via [box64](https://github.com/ptitSeb/box64) (no Docker, no Pterodactyl/LGSM — both would need SteamCMD's 32-bit bootstrap, which can't run on this CPU; see below).

## Why it's built this way

This VPS is ARM64 (Ampere/Neoverse N1). The QLDS game server binary is 64-bit x86 and runs fine under box64. SteamCMD's *installer* binary, however, is 32-bit x86, and this CPU has no AArch32 (32-bit ARM) execution mode at all, so box86 can't run here — meaning SteamCMD itself can't run on this box, at any level of emulation.

The workaround: `.github/workflows/fetch-qlds.yml` runs SteamCMD on a real x86_64 GitHub Actions runner (free) to download the QLDS files, and uploads them as a build artifact. `deploy.sh` pulls the latest artifact down here and runs it via box64.

## One-time host setup (already done on this box)

- box64 built from source with `-DARM_DYNAREC=ON` and installed to `/usr/local/bin/box64`, registered with binfmt.

## Usage

**Update/install the game server files** (re-run whenever you want to pick up a Quake Live update):
```sh
gh workflow run fetch-qlds.yml
gh run watch                # wait for it to finish
./deploy.sh                 # pulls the artifact, applies config/, (re)starts the systemd service
```

**Day-to-day**:
```sh
sudo systemctl status qlds
sudo systemctl restart qlds
journalctl -u qlds -f
```

## Config

- `config/server.cfg` — hostname, map pool, rcon/stats passwords. **Change the placeholder `CHANGE_ME_*` passwords before exposing the server.**
- `config/access.txt` — admin/mod/ban list. One line per SteamID64: `76561198072786081|admin`.
- Edit these, then re-run `./deploy.sh` to apply (it overwrites `baseq3/server.cfg` and `baseq3/access.txt` from these files on every deploy).

## Stats integration

`zmq_stats_enable` is on in `config/server.cfg`, publishing live match events over ZMQ on port `27961` (TCP) — point your existing stats web app at `<this-host>:27961` with the password you set in `zmq_stats_password`.

## Known limitation: Steam Workshop maps

The server authenticates to Steam anonymously (via SteamCMD), which is enough to download the QLDS binaries but *not* enough for the running server's own Steam session (`SteamAPI_Init` fails, `ISteamUGC` is null) — so it can't freshly sync Workshop content itself; it just trusts whatever's already on disk under `steamapps/workshop/content/282440/<id>/` as "in cache". That's fine for items already subscribed once (see `config/workshop.txt`), but it also means **there's no download path of any kind to a connecting client** for content the server has that a client doesn't (this build has zero download-related cvars — checked via `cvarlist download`). Steam Workshop sync (handled by each *player's* own Steam client, not this server) is the only distribution channel. See `config/workshop-maps.md` for the details and gotchas (e.g. never overwrite an existing Workshop item's pk3 locally — breaks it for every player whose client already has the original cached) and `workshop-publish/` for publishing a custom/fixed map as a new Workshop item.

## Firewall

Open UDP `27960` (game) and TCP `27961`/`28960` (stats/rcon, if you want remote access to those) in whatever firewall/security list applies — this repo doesn't manage that.
