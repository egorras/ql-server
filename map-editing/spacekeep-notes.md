# spacekeep (heroskeep wall-removal edit) — status: blocked on a BSP leak

Attempt to turn the stock map `heroskeep` into a more open "spacekeep" by removing/widening
the walls between its two big symmetric side chambers and the central corridor, for more open
CA flow. Same general toolchain as the `aerospace_ca` rooftop fix (see `config/workshop-maps.md`
and `workshop-publish/`), but this one didn't get past compiling. Documenting the dead ends here
so the next attempt doesn't repeat them.

## Toolchain (same as used for aerospace_ca)

- [NetRadiant-custom](https://github.com/Garux/netradiant-custom) (Windows build), which bundles
  `q3map2.exe` — this is what does decompile (`-convert -format map`), structural compile
  (`-meta -patchmeta`), `-vis`, and `-light`.
- Use `-game quakelive` (not `-game quake3` — QL's BSP is version 47, stock Q3's compiler profile
  expects 46 and will refuse to load it).
- **Point `-fs_basepath` at the real Quake Live install**, not just the map's own assets — without
  the stock shader scripts, q3map2 can't resolve most textures during compile (doesn't affect the
  final in-game look since the client resolves shaders itself, but affects *compile-time* things:
  radiosity/light source recognition, and meta-surface merging quality; see the aerospace_ca
  writeup for what happens when you skip this).
- **QL's BSP format has an 18th lump** ("Advertisements") beyond stock Q3's 17. Any raw lump
  parsing/rebuilding (like the lightmap-transplant script written for aerospace_ca) needs to
  account for this or the client throws `R_LoadAdvertisments: funny lump size`.
- Stock maps (heroskeep included) live in `baseq3/pak00.pk3`, not a workshop item — extract with
  Python's `zipfile` module.

## What actually happened

1. Extracted `maps/heroskeep.bsp` from `pak00.pk3`, decompiled cleanly (no custom shader file —
   heroskeep is built entirely from stock textures).
2. Identified the two symmetric wall regions separating each side chamber from the center
   (roughly X≈-1290 left / X≈-530 right, Y≈300-900, Z 0-~500) via a custom top-down brush
   renderer (parses the `.map`, does half-space intersection per brush, plots with matplotlib —
   worth keeping this tool, it was very useful for orienting in a level with no visual editor
   available).
3. Deleting brushes in that region and recompiling (`-meta -patchmeta`) hit
   `ERROR: Ad cell id 93 has more than one surface.` — one of the deleted brushes belonged to an
   in-map advertisement billboard zone. Fix: strip all `classname advertisement` entities
   entirely (they're cosmetic monetization billboards, irrelevant to a private server) before
   compiling. Needs proper brace-depth-matched entity removal, not regex — these entities contain
   a nested patch definition.
4. With the ad entities stripped, compiling succeeds structurally but **leaks**:
   `Entity N, Brush 0: Entity leaked`, with a `.lin` pointfile tracing a path from deep inside one
   of the untouched rooms, through several waypoints, out to a point **~1000+ units away** near
   the octagonal room at the far end of the map — nowhere near the wall I actually edited.

## The leak: what was ruled out

- **Not a decompiler artifact.** Recompiling the *completely unmodified* decompiled map (zero
  brush edits, just the ad-entity strip) compiles clean, no leak. So the wall removal genuinely
  causes this — it's not some latent issue in the decompile like the aerospace_ca ceiling-clip
  brushes turned out to be.
- **Not about how much is removed.** A large slab (Y 180-1020, Z 0-520, ~200 brushes), a
  moderate one (Y 300-900, Z 0-380, ~35 brushes), and a tiny one (Y 390-820, Z 0-380, ~31
  brushes) all produced the *identical* leak path.
- **Not about which side.** Removing *only* the right-side wall slab (left completely untouched,
  16 brushes) leaks on its own too.
- **Restoring the likely "sealing" brush didn't help.** Found and re-inserted (verbatim, from the
  original decompiled `.map`, so guaranteed-correct winding) a couple of original ceiling/floor
  brushes near one reported leak waypoint — no change, same leak.
- **Wrapping the entire map in a large sealed outer shell didn't help**, which was the most
  surprising result. Built a proper validated hollow box (6 slabs, `common/caulk`, generous
  margin beyond the map's full bounding box, each slab's winding verified by round-tripping
  through the same half-space-intersection code used for reading brushes, confirmed to produce a
  correct 8-vertex box) enclosing the whole existing map, on the theory that any leak would hit
  this outer shell instead of escaping to the true void (this is exactly what already-working
  aerospace_ca relies on for its own outer sky/caulk shell). Recompiled: **still the identical
  leak**, and critically, the reported leak point sits *deep inside* the new shell's bounds, not
  at its boundary — meaning whatever q3map2 is actually detecting here isn't simply "reaches
  unbounded space." Left unexplained.

## Where this stands

Genuinely unresolved. The leak is real (caused by the wall removal, reproducible, not fixed by
naive approaches), but the mechanism isn't understood well enough to fix blind, and doing this
via text/scripting alone (no visual editor) has hit its limit — properly debugging a `.lin`
pointfile normally means loading it in an interactive editor (NetRadiant/GtkRadiant have a
"point file" display that draws the leak path as a 3D line you can walk along inside the level,
so you can *see* exactly which brush is missing where). That's the natural next step if this gets
picked up again, rather than more blind brush-slab deletion.

## Where the work-in-progress files are

Everything is local scratch work on the dev machine, not committed to this repo:
`C:\code\ql-server-mapwork\heroskeep\` — contains the extracted stock assets, the decompiled
`.map`, `parse_map.py` / `render_map.py` / `render_slice.py` (the brush-renderer tools, copied
from the same ones built for the aerospace_ca work), `remove_slab.py`, and `make_box_brush.py`
(the validated box-brush generator — reusable for any future "seal a hole" attempt, on this or
other maps).
