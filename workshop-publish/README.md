# Publishing a map to Steam Workshop

The only way to get new/fixed map content onto a real player's Quake Live client is
Steam Workshop — see the top-level README's "Known limitation" section and
`config/workshop-maps.md` for why. This runs from a Windows/Linux x86_64 machine with
SteamCMD, **not** from the dedicated server (ARM64, can't run SteamCMD at all).

## One-time setup

1. Get [SteamCMD](https://developer.valvesoftware.com/wiki/SteamCMD).
2. Log in once interactively so it caches the session next to the binary:
   ```
   steamcmd.exe +login <your_steam_username> +quit
   ```
   Handle the password / Steam Guard prompt yourself here. Later runs of `publish.sh`
   reuse this cached login (no password needed) as long as they point at the same
   SteamCMD install.

## Publishing

```sh
STEAMCMD=/c/path/to/steamcmd.exe STEAM_USER=<your_steam_username> \
  ./publish.sh <pk3 path> "<title>" "<description>" [existing published_file_id]
```

- Omit the last argument to create a **new** item — the item is created **private**
  (`visibility 2` in `item.vdf.template`); flip it to public/friends-only yourself on
  the Workshop page once you're happy with it. SteamCMD prints the new item's
  published file ID on success — add it to `config/workshop.txt`.
- Pass an existing published file ID as the last argument to push an update to an item
  this script (or you) already created.

The script pulls the pk3's first top-level `levelshots/*.jpg` as the preview image
automatically — no separate preview file needed.

**Preview must be under 1MB.** SteamCMD silently fails workshop_build_item with
`Size limit exceeded for preview file ... File must be less than 1 MB` if it isn't — this bit
the spacekeep publish, whose levelshot was a raw stock `pak00.pk3` JPEG (~1.6MB) copied over from
`heroskeep`. The content upload itself still succeeds and the item gets created, so a failed
preview upload leaves a real (but preview-less/incomplete) item behind — re-run against that
item's published_file_id with a resized preview rather than creating a second item. Fix: downscale/
recompress the jpg (e.g. Pillow `Image.thumbnail((1024,1024))` + `quality=85`) before it goes into
the pk3, or swap the pk3's levelshot for the resized copy before publishing.

## Why not just overwrite an existing Workshop item's pk3 locally?

Don't. See `config/workshop-maps.md` — every player's client already has the *real*
item cached with the original checksum; a byte-different file at that same identity
fails client-side pure-server validation for everyone. Always publish fixes as a new
(or your own already-published) item instead.
