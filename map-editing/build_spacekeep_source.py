"""Create the Spacekeep source map from the stock Hero's Keep decompile.

The edit keeps the stock structure intact except for three deliberate changes:
two sealed side-chamber passages, a framed jump window in the south hall, and a
paired long-range jump route through that window.  Materials are translated to
the stock Cobalt Station palette.
"""

from pathlib import Path
import re
import sys

import numpy as np

from parse_map import brush_vertices, parse_map, plane_from_points


SOURCE = Path("src/maps/heroskeep_converted.map")
OUTPUT = Path("build/pk3root/maps/spacekeep.map")


def top_level_blocks(text):
    depth = 0
    start = None
    for match in re.finditer(r"[{}]", text):
        if match.group() == "{":
            if depth == 0:
                start = match.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0 and start is not None:
                yield start, match.end(), text[start:match.end()]


def box_brush(x0, y0, z0, x1, y1, z1, material, face_materials=None):
    """Return a validated classic-format axis-aligned brush."""
    corners = {
        (0, 0, 0): (x0, y0, z0), (1, 0, 0): (x1, y0, z0),
        (0, 1, 0): (x0, y1, z0), (0, 0, 1): (x0, y0, z1),
        (1, 1, 0): (x1, y1, z0), (1, 0, 1): (x1, y0, z1),
        (0, 1, 1): (x0, y1, z1), (1, 1, 1): (x1, y1, z1),
    }
    face_defs = [
        ("-X", (0, 0, 0), (0, 1, 0), (0, 0, 1), (-1, 0, 0)),
        ("+X", (1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 0, 0)),
        ("-Y", (0, 0, 0), (0, 0, 1), (1, 0, 0), (0, -1, 0)),
        ("+Y", (0, 1, 0), (1, 1, 0), (0, 1, 1), (0, 1, 0)),
        ("-Z", (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, -1)),
        ("+Z", (0, 0, 1), (0, 1, 1), (1, 0, 1), (0, 0, 1)),
    ]
    lines = ["\t// spacekeep generated brush", "\t{"]
    planes = []
    for name, c0, c1, c2, expected in face_defs:
        points = [np.array(corners[c], dtype=float) for c in (c0, c1, c2)]
        plane = plane_from_points(*points)
        if np.dot(plane[0], expected) < 0:
            points[1], points[2] = points[2], points[1]
            plane = plane_from_points(*points)
        assert np.dot(plane[0], expected) > 0.9
        planes.append(plane)
        texture = (face_materials or {}).get(name, material)
        p0, p1, p2 = points
        lines.append(
            f"\t\t( {p0[0]:.0f} {p0[1]:.0f} {p0[2]:.0f} ) "
            f"( {p1[0]:.0f} {p1[1]:.0f} {p1[2]:.0f} ) "
            f"( {p2[0]:.0f} {p2[1]:.0f} {p2[2]:.0f} ) "
            f"{texture} 0 0 0 0.5 0.5 0 0 0"
        )
    lines.append("\t}")
    vertices = brush_vertices(planes)
    assert vertices is not None and len(vertices) == 8
    return "\n".join(lines)


def bounds_for(brush):
    vertices = brush_vertices(brush["planes"])
    if vertices is None:
        return None
    lo, hi = vertices.min(axis=0), vertices.max(axis=0)
    return tuple(float(v) for v in (*lo, *hi))


def intersects_open_volume(bounds, volume, epsilon=0.1):
    """Return true only when a brush penetrates the interior of a volume."""
    x0, y0, z0, x1, y1, z1 = bounds
    vx0, vy0, vz0, vx1, vy1, vz1 = volume
    return (
        x1 > vx0 + epsilon and x0 < vx1 - epsilon
        and y1 > vy0 + epsilon and y0 < vy1 - epsilon
        and z1 > vz0 + epsilon and z0 < vz1 - epsilon
    )


HALL_WINDOW = (-928, -120, 336, -800, -64, 680)
SIDE_PASSAGES = (
    (-1520, 626, 66, -1190, 718, 304),
    (-538, 626, 66, -208, 718, 304),
)
JUMP_PATH_OBSTACLES = {
    # Two visible cable runs and their broad player-clip cap.
    (-1040, -536, 456, -704, -520, 464),
    (-996, -532, 448, -732, -524, 456),
    (-1020, -552, 448, -672, -504, 468),
}


def in_hall_window(bounds):
    """Select every visible or clip brush crossing the marked window."""
    return intersects_open_volume(bounds, HALL_WINDOW)


def in_side_passage(bounds):
    """Select all stock collision/decor crossing either restored archway."""
    return any(intersects_open_volume(bounds, volume) for volume in SIDE_PASSAGES)


def is_jump_path_obstacle(bounds):
    return tuple(round(value) for value in bounds) in JUMP_PATH_OBSTACLES


def direct_child_blocks(text, entity_start, entity_end):
    """Yield direct brush/patch blocks inside one top-level entity."""
    depth = 0
    start = None
    for match in re.finditer(r"[{}]", text[entity_start:entity_end]):
        absolute = entity_start + match.start()
        if match.group() == "{":
            depth += 1
            if depth == 2:
                start = absolute
        else:
            if depth == 2 and start is not None:
                yield start, entity_start + match.end(), text[start:entity_start + match.end()]
                start = None
            depth -= 1


def translate_texture(texture):
    """Map Hero's Keep surfaces onto Cobalt Station's stock material palette."""
    if texture == "skies/toxicskytim_dm7":
        return "skies/qznebula3"
    if texture.startswith("gothic_block/"):
        variants = (
            "base_wall/metalfloor_wall_cobalt_specular",
            "base_wall/bluemetalsupport2e",
            "base_wall/cobalt_chrome",
        )
        return variants[sum(texture.encode("utf-8")) % len(variants)]
    if texture.startswith("gothic_trim/"):
        if "metal" in texture or "support" in texture:
            return "base_trim/pewter_shiney"
        if "zinc" in texture:
            return "base_wall/cobalt_chrome"
        return "base_trim/dirty_pewter_big"
    if texture.startswith("gothic_door/"):
        return "base_wall/bluemetalsupport2e"
    if texture.startswith("gothic_floor/"):
        if "stepborder" in texture:
            return "gothic_floor/xstepborder8"
        if "blocks" in texture:
            return "base_floor/clang_floor3bstairtop"
        return "base_floor/clangdark"
    if texture.startswith(("gothic_ceiling/", "gothic_cath/", "gothic_wall/")):
        return "base_wall/concrete"
    if texture.startswith("gothic_light/"):
        return "base_light/border11light"
    if texture.startswith("gothic_button/"):
        return "base_wall/atech1_e"
    if texture.startswith("skin/"):
        return "base_wall/cobalt_chrome"
    if texture == "base_wall/metaltech10final":
        return "base_wall/bluemetal2_shiny"
    if texture == "base_floor/nomarkstone_1":
        return "base_floor/clangdark"
    return texture


def translate_materials(text):
    texture_re = re.compile(r"(\)\s+)([A-Za-z0-9_./-]+)(\s+[-0-9.])")
    text = texture_re.sub(
        lambda match: match.group(1) + translate_texture(match.group(2)) + match.group(3),
        text,
    )
    patch_re = re.compile(r"(patchDef2\s*\{\s*)([A-Za-z0-9_./-]+)")
    return patch_re.sub(
        lambda match: match.group(1) + translate_texture(match.group(2)),
        text,
    )


def generated_geometry():
    metal = "base_wall/metalfloor_wall_cobalt_specular"
    trim = "base_trim/pewter_shiney"
    floor = "base_floor/clangdark"
    sky = "skies/qznebula3"
    brushes = []

    # Rebuild the two removed hall slabs around 128 x 256 openings aligned with
    # the decorative side-chamber archways.
    for x0, x1, y0 in [(-1208, -1184, 448), (-544, -520, 476)]:
        brushes.extend([
            box_brush(x0, y0, -256, x1, 896, 64, metal),
            box_brush(x0, y0, 320, x1, 896, 512, metal),
            box_brush(x0, y0, 64, x1, 608, 320, metal),
            box_brush(x0, 736, 64, x1, 896, 320, metal),
        ])

    # Enclosed passage shells bridge the exterior gaps. Their solid side walls
    # specifically prevent the side-of-arch views into void seen in version one.
    for x0, x1 in [(-1536, -1184), (-544, -192)]:
        brushes.extend([
            box_brush(x0, 608, 48, x1, 736, 64, trim,
                      {"+Z": floor, "-Z": "common/caulk"}),
            box_brush(x0, 576, 64, x1, 608, 512, metal),
            box_brush(x0, 736, 64, x1, 768, 512, metal),
            box_brush(x0, 576, 320, x1, 768, 512, metal),
        ])

    # Clean 128 x 280 jump window through both leaves of the marked south wall.
    # The frame also seals the 12-unit exterior cavity between those leaves.
    brushes.extend([
        box_brush(-944, -120, 336, -928, -64, 832, trim),
        box_brush(-800, -120, 336, -784, -64, 832, trim),
        # Restore the portions of the north wall whose decompiled source
        # brushes straddled the cut and therefore had to be removed whole.
        box_brush(-976, -92, 320, -928, -64, 832, metal),
        box_brush(-800, -92, 320, -752, -64, 832, metal),
        # Some decompiled wall courses cross the cut as 128-unit-tall brushes.
        # Fill their whole removed lower remainder, not just a cosmetic lip.
        box_brush(-944, -120, 232, -784, -64, 336, metal),
        box_brush(-944, -120, 680, -784, -64, 832, metal),
    ])

    # Visible pad under the new south-hall trigger. It sits on the existing
    # armor platform and does not alter the surrounding floor collision.
    brushes.extend([
        box_brush(-912, -920, 336, -816, -824, 344, trim,
                  {"+Z": "base_light/border11light"}),
    ])
    return "\n\n".join(brushes)


def light_entity(x, y, z):
    return (
        "{\n"
        '    "classname" "light"\n'
        f'    "origin" "{x} {y} {z}"\n'
        '    "light" "260"\n'
        '    "_color" "0.48 0.68 1.0"\n'
        "}\n"
    )


def push_entity(x0, y0, z0, x1, y1, z1, target):
    return (
        "{\n"
        '    "classname" "trigger_push"\n'
        f'    "target" "{target}"\n'
        + box_brush(x0, y0, z0, x1, y1, z1, "common/trigger")
        + "\n}\n"
    )


def main(source=SOURCE, output=OUTPUT):
    source = Path(source)
    output = Path(output)
    entities, text = parse_map(source, with_spans=True)
    world = next(e for e in entities if e["keys"].get("classname") == "worldspawn")

    removals = []
    removed_brushes = 0
    for brush in world["brushes"]:
        bounds = bounds_for(brush)
        if bounds is None:
            continue
        if in_side_passage(bounds) or in_hall_window(bounds) or is_jump_path_obstacle(bounds):
            removals.append(brush["span"])
            removed_brushes += 1
    if removed_brushes != 72:
        raise RuntimeError(f"Expected to remove 72 opening/path brushes, found {removed_brushes}")

    world_start, world_end, world_block = next(top_level_blocks(text))
    if '"classname" "worldspawn"' not in world_block:
        raise RuntimeError("First top-level entity is not worldspawn")
    removed_patches = 0
    point_re = re.compile(
        r"\(\s*\(\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)"
    )
    for start, end, block in direct_child_blocks(text, world_start, world_end):
        if "patchDef2" not in block:
            continue
        points = np.array(
            [[float(x), float(y), float(z)] for x, y, z in point_re.findall(block)]
        )
        if len(points):
            point_bounds = tuple(float(v) for v in (*points.min(0), *points.max(0)))
        else:
            point_bounds = None
        if point_bounds and in_hall_window(point_bounds):
            removals.append((start, end))
            removed_patches += 1
    if removed_patches != 8:
        raise RuntimeError(f"Expected 8 window patches, found {removed_patches}")

    # Advertisements carry QL-specific surface metadata that cannot be regenerated
    # reliably by q3map2; they are cosmetic and intentionally omitted.
    ad_count = 0
    for start, end, block in top_level_blocks(text):
        if re.search(r'"classname"\s+"advertisement"', block):
            removals.append((start, end))
            ad_count += 1
    if ad_count != 5:
        raise RuntimeError(f"Expected 5 advertisement entities, found {ad_count}")

    for start, end in sorted(removals, reverse=True):
        text = text[:start] + text[end:]

    world_start, world_end, world_block = next(top_level_blocks(text))
    if '"classname" "worldspawn"' not in world_block:
        raise RuntimeError("First top-level entity is not worldspawn")
    insertion = world_end - 1
    text = text[:insertion] + "\n" + generated_geometry() + "\n" + text[insertion:]
    text += "\n".join([
        "",
        light_entity(-1440, 672, 256),
        light_entity(-288, 672, 256),
        light_entity(-864, -80, 600),
        push_entity(-912, -920, 344, -816, -824, 376, "t45"),
    ])
    text = text.replace('"message" "Hero\'s Keep"', '"message" "Spacekeep"')
    text = text.replace('"ambient" "20"', '"ambient" "25"')
    text = text.replace('"_color" "0.29 0.26 0.25"', '"_color" "0.72 0.82 1.0"')
    # Both long throws use the same apex. Outbound crosses the new window while
    # rising and lands in the far room; the stock far-room pad crosses it while
    # descending and lands on the new south platform.
    text = text.replace('"origin" "-864 844 388"', '"origin" "-864 106 600"')
    text = translate_materials(text)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")
    print(
        f"Wrote {output} ({removed_brushes} opening brushes and {removed_patches} patches removed, "
        f"{ad_count} ads removed)"
    )


if __name__ == "__main__":
    main(*(sys.argv[1:3]))
