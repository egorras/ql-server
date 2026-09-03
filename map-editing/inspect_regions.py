"""Print world brushes whose hulls intersect one or more axis-aligned regions."""

from pathlib import Path
import sys

from parse_map import brush_vertices, parse_map


REGIONS = {
    "left": (-1600, -1200, 400, 950, -100, 700),
    "right": (-550, -150, 400, 950, -100, 700),
    # Window marked in hall_section_original.png. This is the south wall of the
    # small main-hall vestibule, well away from the Y=896 barrier.
    "hall_window": (-1000, -720, -160, 32, 0, 720),
}


def intersects(bounds, region):
    return all(bounds[i] <= region[i + 1] and bounds[i + 1] >= region[i]
               for i in (0, 2, 4))


def main(path):
    entities = parse_map(path)
    world = next(e for e in entities if e["keys"].get("classname") == "worldspawn")
    for index, brush in enumerate(world["brushes"]):
        vertices = brush_vertices(brush["planes"])
        if vertices is None:
            continue
        lo = vertices.min(axis=0)
        hi = vertices.max(axis=0)
        bounds = (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])
        hits = [name for name, region in REGIONS.items() if intersects(bounds, region)]
        if not hits:
            continue
        textures = ",".join(sorted(set(brush["tex"])))
        print(f"{index:4} {'/'.join(hits):5} "
              f"x={lo[0]:7.1f}..{hi[0]:7.1f} y={lo[1]:7.1f}..{hi[1]:7.1f} "
              f"z={lo[2]:7.1f}..{hi[2]:7.1f} {textures}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
