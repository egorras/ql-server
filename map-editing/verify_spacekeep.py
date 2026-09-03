"""Static checks for generated Spacekeep source geometry and metadata."""

from pathlib import Path
import math
import sys

import numpy as np
from scipy.optimize import linprog

from parse_map import brush_vertices, parse_map


NON_SOLID = {
    "common/hint",
    "common/nodraw",
    "common/trigger",
    "sfx/q3dm9fog",
    "sfx/flame1side",
    "sfx/xflame1side",
}


def contains(brush, point, tolerance=0.01):
    return all(np.dot(normal, point) - distance <= tolerance
               for normal, distance in brush["planes"])


def penetrates_box(brush, box, inset=0.25):
    """Use convex feasibility to catch even sub-grid collision slivers."""
    x0, y0, z0, x1, y1, z1 = box
    result = linprog(
        np.zeros(3),
        A_ub=np.array([normal for normal, _ in brush["planes"]]),
        b_ub=np.array([distance - inset for _, distance in brush["planes"]]),
        bounds=[
            (x0 + inset, x1 - inset),
            (y0 + inset, y1 - inset),
            (z0 + inset, z1 - inset),
        ],
        method="highs",
    )
    return result.success


def jump_arc(start_y, start_z, apex_y, apex_z, sample_y, gravity=800.0):
    time_to_apex = math.sqrt(2 * (apex_z - start_z) / gravity)
    velocity_y = (apex_y - start_y) / time_to_apex
    velocity_z = gravity * time_to_apex
    time = (sample_y - start_y) / velocity_y
    return start_z + velocity_z * time - 0.5 * gravity * time * time


def landing_y(start_y, start_z, apex_y, apex_z, landing_z, gravity=800.0):
    time_to_apex = math.sqrt(2 * (apex_z - start_z) / gravity)
    velocity_y = (apex_y - start_y) / time_to_apex
    fall_time = math.sqrt(2 * (apex_z - landing_z) / gravity)
    return start_y + velocity_y * (time_to_apex + fall_time)


def boxes_overlap(a, b):
    return all(a[i] < b[i + 3] and a[i + 3] > b[i] for i in range(3))


def main(path):
    entities = parse_map(Path(path))
    classes = [e["keys"].get("classname") for e in entities]
    assert classes.count("worldspawn") == 1
    assert "advertisement" not in classes
    assert classes.count("info_player_deathmatch") == 11
    world = next(e for e in entities if e["keys"].get("classname") == "worldspawn")
    assert world["keys"].get("message") == "Spacekeep"

    target = next(
        e for e in entities
        if e["keys"].get("classname") == "target_position"
        and e["keys"].get("targetname") == "t45"
    )
    assert target["keys"].get("origin") == "-864 106 600"
    assert sum(
        e["keys"].get("classname") == "trigger_push"
        and e["keys"].get("target") == "t45"
        for e in entities
    ) == 2

    # Check the player hull, not merely the trajectory center, at both faces of
    # the window. The same apex produces a near-symmetric pair of throws.
    for start_y, start_z in [(-872.0, 360.0), (1380.5, 159.0)]:
        for wall_y in (-120.0, -64.0):
            z = jump_arc(start_y, start_z, 106.0, 600.0, wall_y)
            assert z - 24 > 336 and z + 32 < 680, (start_y, wall_y, z)
    outbound_landing = landing_y(-872.0, 360.0, 106.0, 600.0, 152.0)
    return_landing = landing_y(1380.5, 159.0, 106.0, 600.0, 360.0)
    assert 1320 < outbound_landing < 1500, outbound_landing
    assert -920 < return_landing < -824, return_landing

    # These are inset from decorative arch edges but cover each full travel
    # volume. Linear feasibility catches thin clip or structural remnants that
    # a point grid could skip, including the one-pixel walls reported in-game.
    open_volumes = {
        "left archway": (-1520, 626, 66, -1190, 718, 304),
        "right archway": (-538, 626, 66, -208, 718, 304),
        "hall jump window": (-928, -120, 336, -800, -64, 680),
    }
    for name, volume in open_volumes.items():
        blockers = []
        for index, brush in enumerate(world["brushes"]):
            if set(brush["tex"]).issubset(NON_SOLID):
                continue
            if penetrates_box(brush, volume):
                blockers.append((index, sorted(set(brush["tex"]))))
        if blockers:
            raise AssertionError(f"{name} contains collision geometry: {blockers}")

    # Sweep a full player hull along the airborne part of the new south-to-far
    # route. This catches railings and broad clip caps between the pad and window.
    path_blockers = []
    path_candidates = []
    broad_path_bounds = (-880, -815, 120, -848, 1315, 700)
    for index, brush in enumerate(world["brushes"]):
        if set(brush["tex"]).issubset(NON_SOLID):
            continue
        vertices = brush_vertices(brush["planes"])
        if vertices is None:
            continue
        bounds = tuple(float(v) for v in (*vertices.min(0), *vertices.max(0)))
        if boxes_overlap(bounds, broad_path_bounds):
            path_candidates.append((index, brush, bounds))
    for y in np.linspace(-800, 1300, 180):
        z = jump_arc(-872.0, 360.0, 106.0, 600.0, y)
        player_box = (-880, y - 15, z - 24, -848, y + 15, z + 32)
        for index, brush, bounds in path_candidates:
            if not boxes_overlap(bounds, player_box):
                continue
            if penetrates_box(brush, player_box, inset=0.05):
                path_blockers.append((round(float(y), 1), index, sorted(set(brush["tex"]))))
    if path_blockers:
        raise AssertionError(f"Outbound jump path contains collision: {path_blockers}")

    print(
        f"Verified {path}: metadata, paired jumpers, and "
        f"{len(open_volumes)} open volumes/full outbound arc are clear"
    )


if __name__ == "__main__":
    main(sys.argv[1])
