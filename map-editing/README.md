# Spacekeep map workspace

This directory contains the reproducible source and build tooling for the `spacekeep`
Quake Live map edit. The map starts from the stock `heroskeep` BSP, adds sealed lateral
connectors across the exterior gaps, and adds a paired long jump through a framed hall
window. It uses stock Quake Live materials so the test PK3 does not redistribute
base-game textures.

Run `./build.ps1` from PowerShell to decompile the stock map (when needed), compile BSP,
VIS, lighting and bot navigation, and create `build/spacekeep_test.pk3`. The defaults expect
Quake Live under Steam's standard Windows path and NetRadiant Custom under
`C:\tools\netradiant-custom`; both paths can be overridden with script parameters.

For a local test, copy the PK3 into Quake Live's `baseq3` directory, start the game, open
the console, and run `map spacekeep ca`.

See `spacekeep-notes.md` for the history of the earlier wall-removal attempt.
