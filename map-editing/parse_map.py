"""Parse a Quake3-family .map file (classic brush format) into brushes (as vertex hulls)
and entities, for offline analysis/rendering since we have no interactive level viewer."""
import re
import sys
import numpy as np
from itertools import combinations

PLANE_RE = re.compile(
    r'\(\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\)\s*'
    r'\(\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\)\s*'
    r'\(\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\)\s+(\S+)'
)


def plane_from_points(p0, p1, p2):
    v1 = p1 - p0
    v2 = p2 - p0
    n = np.cross(v2, v1)  # Quake .map winding: this yields an outward-facing normal
    norm = np.linalg.norm(n)
    if norm < 1e-9:
        return None
    n = n / norm
    d = np.dot(n, p0)
    return n, d


def brush_vertices(planes, tol=1e-4):
    """Classic half-space intersection: try every triple of planes, keep the
    intersection point if it satisfies every plane's inequality (inside the brush)."""
    verts = []
    n = len(planes)
    for i, j, k in combinations(range(n), 3):
        n1, d1 = planes[i]
        n2, d2 = planes[j]
        n3, d3 = planes[k]
        A = np.array([n1, n2, n3])
        b = np.array([d1, d2, d3])
        try:
            if abs(np.linalg.det(A)) < 1e-9:
                continue
            pt = np.linalg.solve(A, b)
        except np.linalg.LinAlgError:
            continue
        ok = True
        for (nn, dd) in planes:
            if np.dot(nn, pt) - dd > tol:
                ok = False
                break
        if ok:
            verts.append(pt)
    if not verts:
        return None
    verts = np.array(verts)
    # dedupe
    if len(verts) > 1:
        uniq = [verts[0]]
        for v in verts[1:]:
            if not any(np.linalg.norm(v - u) < 0.5 for u in uniq):
                uniq.append(v)
        verts = np.array(uniq)
    return verts


def parse_map(path, with_spans=False):
    text = open(path, 'r', encoding='utf-8', errors='replace').read()
    entities = []
    depth = 0
    blocks = []
    start = None
    for m in re.finditer(r'[{}]', text):
        c = m.group()
        if c == '{':
            if depth == 0:
                start = m.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0 and start is not None:
                blocks.append((start, m.end()))
    for (bs, be) in blocks:
        block = text[bs:be]
        ent = {'keys': {}, 'brushes': []}
        for km in re.finditer(r'"([^"]+)"\s+"([^"]*)"', block):
            ent['keys'][km.group(1)] = km.group(2)
        inner_start = bs + block.index('{') + 1
        inner_end = bs + block.rindex('}')
        bdepth = 0
        bstart = None
        for m in re.finditer(r'[{}]', text[inner_start:inner_end]):
            c = m.group()
            abs_pos = inner_start + m.start()
            if c == '{':
                if bdepth == 0:
                    bstart = abs_pos
                bdepth += 1
            else:
                bdepth -= 1
                if bdepth == 0 and bstart is not None:
                    b_end = inner_start + m.end()
                    btext = text[bstart:b_end]
                    planes = []
                    tex = []
                    for pm in PLANE_RE.finditer(btext):
                        p0 = np.array([float(pm.group(1)), float(pm.group(2)), float(pm.group(3))])
                        p1 = np.array([float(pm.group(4)), float(pm.group(5)), float(pm.group(6))])
                        p2 = np.array([float(pm.group(7)), float(pm.group(8)), float(pm.group(9))])
                        pl = plane_from_points(p0, p1, p2)
                        if pl:
                            planes.append(pl)
                            tex.append(pm.group(10))
                    if planes:
                        bd = {'planes': planes, 'tex': tex}
                        if with_spans:
                            bd['span'] = (bstart, b_end)
                        ent['brushes'].append(bd)
        entities.append(ent)
    if with_spans:
        return entities, text
    return entities


if __name__ == '__main__':
    ents = parse_map(sys.argv[1])
    nb = sum(len(e['brushes']) for e in ents)
    print(f"{len(ents)} entities, {nb} brushes")
    for e in ents:
        if e['keys'].get('classname') != 'worldspawn':
            print(e['keys'])
