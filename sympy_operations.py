import math
import logging
from typing import List, Any, Optional, Dict

from sympy import Line as SympyLine, Circle as SympyCircle, Segment, Point, Polygon as SympyPolygon, Line, Circle

logger = logging.getLogger(__name__)

# Scale: 1 px = 0.05 cm  →  100 px ≈ 5 cm (adjust to taste)
_SCALE_CM_PER_PX = 0.0265


def _find_elements(whiteboard, element_ids: List[str]) -> list:
    id_set = set(element_ids)
    return [el for el in whiteboard.elements if el.id in id_set and not el.isDeleted]


def _el_to_sympy(el):
    if el.type == "ellipse":
        cx = el.x + el.width / 2
        cy = el.y + el.height / 2
        r = min(el.width, el.height) / 2
        return SympyCircle(Point(cx, cy), r)
    if el.type in ("line", "arrow") and len(el.points) >= 2:
        x0 = el.x + el.points[0][0];  y0 = el.y + el.points[0][1]
        x1 = el.x + el.points[-1][0]; y1 = el.y + el.points[-1][1]
        return Segment(Point(x0, y0), Point(x1, y1))
    if el.type in ("rectangle", "diamond"):
        x, y, w, h = el.x, el.y, el.width, el.height
        return SympyPolygon(Point(x, y), Point(x+w, y), Point(x+w, y+h), Point(x, y+h))
    return None


def _dot_patch(element_id: str, cx: float, cy: float, color: str = "#1e1e1e") -> dict:
    return {
        "id": element_id,
        "create": True,
        "type": "ellipse",
        "changes": {
            "x": round(cx - 2, 2),
            "y": round(cy - 2, 2),
            "width": 4,
            "height": 4,
            "fillStyle": "solid",
            "backgroundColor": color,
            "strokeColor": color,
            "roughness": 0,
            "strokeWidth": 1,
        },
    }

def _compute_orthocenter(sympy_objects: List[Any]) -> Optional[Dict[str, Any]]:
    try:
        lines = [obj for obj in sympy_objects if isinstance(obj, Line)]
        if len(lines) < 3:
            return {
                "success": False,
                "error": "Need at least 3 Line objects to compute orthocenter",
            }

        l0, l1, l2 = lines[0], lines[1], lines[2]

        # Vertices: pairwise intersections
        def intersect_lines(a, b):
            pts = a.intersection(b)
            if pts and isinstance(pts[0], Point):
                return pts[0]
            return None

        v0 = intersect_lines(l1, l2)  # opposite to l0
        v1 = intersect_lines(l0, l2)  # opposite to l1
        v2 = intersect_lines(l0, l1)  # opposite to l2

        if not all([v0, v1, v2]):
            return {"success": False, "error": "Could not find all three triangle vertices"}

        alt0 = l0.perpendicular_line(v0)
        alt1 = l1.perpendicular_line(v1)

        ortho_pts = alt0.intersection(alt1)
        if not ortho_pts or not isinstance(ortho_pts[0], Point):
            return {"success": False, "error": "Could not compute orthocenter intersection"}

        ortho = ortho_pts[0]

        def foot(vertex, side):
            perp = side.perpendicular_line(vertex)
            pts = side.intersection(perp)
            return pts[0] if pts and isinstance(pts[0], Point) else None

        foot0 = foot(v0, l0)
        foot1 = foot(v1, l1)
        foot2 = foot(v2, l2)

        def pt_dict(p):
            return {"x": round(float(p.x), 4), "y": round(float(p.y), 4)} if p else None

        return {
            "success": True,
            "orthocenter": pt_dict(ortho),
            "vertices": [pt_dict(v0), pt_dict(v1), pt_dict(v2)],
            "altitude_feet": [pt_dict(foot0), pt_dict(foot1), pt_dict(foot2)],
        }
    except Exception as e:
        logger.error(f"Error computing orthocenter: {e}")
        return {"success": False, "error": str(e)}


def _compute_circle_intersection_arcs(sympy_objects: List[Any]) -> Optional[Dict[str, Any]]:
    try:
        circles = [obj for obj in sympy_objects if isinstance(obj, Circle)]
        if len(circles) < 2:
            return {
                "success": False,
                "error": "Need at least 2 Circle objects to compute lens intersection",
            }

        c1, c2 = circles[0], circles[1]
        inter = c1.intersection(c2)
        pts = [p for p in inter if isinstance(p, Point)]

        if len(pts) < 2:
            return {
                "success": False,
                "error": f"Circles have {len(pts)} intersection point(s), lens needs exactly 2",
            }

        p1, p2 = pts[0], pts[1]
        p1x, p1y = float(p1.x), float(p1.y)
        p2x, p2y = float(p2.x), float(p2.y)

        lens_min_x = min(p1x, p2x)
        lens_min_y = min(p1y, p2y)

        def arc_points(circle, from_pt, to_pt, num_steps=36):
            cx, cy, r = float(circle.center.x), float(circle.center.y), float(circle.radius)
            a_start = math.atan2(from_pt[1] - cy, from_pt[0] - cx)
            a_end = math.atan2(to_pt[1] - cy, to_pt[0] - cx)
            diff = (a_end - a_start) % (2 * math.pi)
            if diff > math.pi:
                diff -= 2 * math.pi
            result = []
            for i in range(num_steps + 1):
                angle = a_start + diff * (i / num_steps)
                result.append([round(cx + r * math.cos(angle), 2),
                                round(cy + r * math.sin(angle), 2)])
            return result

        arc1 = arc_points(c1, [p1x, p1y], [p2x, p2y])
        arc2 = arc_points(c2, [p2x, p2y], [p1x, p1y])

        combined = arc1 + arc2
        rel_points = [
            [round(x - lens_min_x, 2), round(y - lens_min_y, 2)]
            for x, y in combined
        ]

        return {
            "success": True,
            "intersection_points": [
                {"x": round(p1x, 4), "y": round(p1y, 4)},
                {"x": round(p2x, 4), "y": round(p2y, 4)},
            ],
            "lens_origin_x": round(lens_min_x, 2),
            "lens_origin_y": round(lens_min_y, 2),
            "lens_freedraw_points": rel_points,
        }
    except Exception as e:
        logger.error(f"Error computing circle intersection arcs: {e}")
        return {"success": False, "error": str(e)}

def basic_draw(whiteboard, element_ids: List[str]) -> dict:
    return {"patches": None, "text": ""}


def circle_center(whiteboard, element_ids: List[str]) -> dict:
    if not element_ids:
        element_ids = [el.id for el in whiteboard.elements if el.type == "ellipse" and not el.isDeleted and el.id]
    elements = _find_elements(whiteboard, element_ids)
    patches = []
    for el in elements:
        if el.type == "ellipse":
            cx = el.x + el.width / 2
            cy = el.y + el.height / 2
            patches.append(_dot_patch(f"center_{el.id}", cx, cy))
    return {"patches": patches, "text": ""}


def _lines_from_element(el) -> list:
    if el.type not in ("line", "arrow") or len(el.points) < 2:
        return []

    abs_pts = [[el.x + p[0], el.y + p[1]] for p in el.points]

    deduped = [abs_pts[0]]
    for p in abs_pts[1:]:
        if p != deduped[-1]:
            deduped.append(p)
    # Remove closing point if it matches the first
    if len(deduped) > 1 and deduped[-1] == deduped[0]:
        deduped = deduped[:-1]

    if len(deduped) >= 3:
        verts = [Point(p[0], p[1]) for p in deduped]
        return [SympyLine(verts[i], verts[(i + 1) % len(verts)]) for i in range(len(verts))]
    else:
        # Simple two-endpoint line
        return [SympyLine(Point(abs_pts[0][0], abs_pts[0][1]),
                          Point(abs_pts[-1][0], abs_pts[-1][1]))]


def triangle_orthocenter(whiteboard, element_ids: List[str]) -> dict:
    if not element_ids:
        element_ids = [
            el.id for el in whiteboard.elements
            if el.type in ("line", "arrow") and not el.isDeleted and el.id
        ]

    id_order = list(dict.fromkeys(element_ids))  # deduplicate, keep order
    el_map = {el.id: el for el in _find_elements(whiteboard, id_order)}
    ordered_els = [el_map[eid] for eid in id_order if eid in el_map]

    patches = []
    errors = []

    self_contained = all(
        len({tuple(p) for p in el.points}) >= 3
        for el in ordered_els
        if el.type in ("line", "arrow")
    )

    if self_contained:
        # Each element IS a triangle — compute one orthocenter per element
        for idx, el in enumerate(ordered_els):
            sides = _lines_from_element(el)
            if len(sides) < 3:
                errors.append(f"Element '{el.id}': not enough sides")
                continue
            result = _compute_orthocenter(sides)
            if result and result.get("success"):
                o = result["orthocenter"]
                patch_id = f"orthocenter_dot_{idx + 1}" if len(ordered_els) > 1 else "orthocenter_dot"
                patches.append(_dot_patch(patch_id, o["x"], o["y"], color="#e03131"))
            else:
                errors.append(f"Element '{el.id}': {result.get('error', 'unknown')}")
    else:
        # Elements are individual sides — group every 3 consecutive as one triangle
        all_lines = []
        for el in ordered_els:
            all_lines.extend(_lines_from_element(el))

        if len(all_lines) < 3:
            return {"patches": [], "text": "I need at least 3 line elements per triangle to compute the orthocenter."}

        for i in range(0, len(all_lines) - 2, 3):
            trio = all_lines[i:i + 3]
            result = _compute_orthocenter(trio)
            if result and result.get("success"):
                o = result["orthocenter"]
                patch_id = f"orthocenter_dot_{i // 3 + 1}" if len(all_lines) > 3 else "orthocenter_dot"
                patches.append(_dot_patch(patch_id, o["x"], o["y"], color="#e03131"))
            else:
                errors.append(f"Triangle {i // 3 + 1}: {result.get('error', 'unknown')}")

    if not patches:
        return {"patches": [], "text": f"Could not compute any orthocenter. {'; '.join(errors)}"}
    return {"patches": patches, "text": ""}


def _bbox_overlap_patch(el_a, el_b, pair_idx: int) -> Optional[dict]:
    ox = max(el_a.x, el_b.x)
    oy = max(el_a.y, el_b.y)
    ow = min(el_a.x + el_a.width, el_b.x + el_b.width) - ox
    oh = min(el_a.y + el_a.height, el_b.y + el_b.height) - oy
    if ow <= 0 or oh <= 0:
        return None
    return {
        "id": f"intersection_shade_{pair_idx}",
        "create": True,
        "type": "rectangle",
        "changes": {
            "x": round(ox, 2),
            "y": round(oy, 2),
            "width": round(ow, 2),
            "height": round(oh, 2),
            "fillStyle": "solid",
            "backgroundColor": "#a5d8ff",
            "strokeColor": "#a5d8ff",
            "opacity": 60,
            "roughness": 0,
            "strokeWidth": 1,
        },
    }


def intersection(whiteboard, element_ids: List[str]) -> dict:
    SUPPORTED_TYPES = ("ellipse", "rectangle", "diamond", "line")
    if not element_ids:
        return {"patches": [], "text": "Please select the elements you want to shade the intersection of."}
    elements = [el for el in _find_elements(whiteboard, element_ids) if el.type in SUPPORTED_TYPES]

    if len(elements) < 2:
        return {"patches": [], "text": "I need at least two shapes on the board to shade their intersection."}

    patches = []
    errors = []
    pair_idx = 0
    for i in range(len(elements)):
        for j in range(i + 1, len(elements)):
            el_a, el_b = elements[i], elements[j]

            if el_a.type == "ellipse" and el_b.type == "ellipse":
                c_a = SympyCircle(Point(el_a.x + el_a.width / 2, el_a.y + el_a.height / 2), min(el_a.width, el_a.height) / 2)
                c_b = SympyCircle(Point(el_b.x + el_b.width / 2, el_b.y + el_b.height / 2), min(el_b.width, el_b.height) / 2)
                result = _compute_circle_intersection_arcs([c_a, c_b])
                if result and result.get("success"):
                    patches.append({
                        "id": f"intersection_shade_{pair_idx}",
                        "create": True,
                        "type": "freedraw",
                        "changes": {
                            "x": result["lens_origin_x"],
                            "y": result["lens_origin_y"],
                            "points": result["lens_freedraw_points"],
                            "pressures": [],
                            "simulatePressure": True,
                            "fillStyle": "solid",
                            "backgroundColor": "#a5d8ff",
                            "strokeColor": "#a5d8ff",
                            "opacity": 60,
                            "roughness": 0,
                            "strokeWidth": 1,
                        },
                    })
                else:
                    errors.append(f"Pair ({i+1},{j+1}): {result.get('error', 'unknown')}")
            else:
                patch = _bbox_overlap_patch(el_a, el_b, pair_idx)
                if patch:
                    patches.append(patch)
                else:
                    errors.append(f"Pair ({i+1},{j+1}): no overlap")

            pair_idx += 1

    if not patches:
        return {"patches": [], "text": f"Could not compute any intersection. {'; '.join(errors)}"}
    return {"patches": patches, "text": ""}


def parallel(whiteboard, element_ids: List[str]) -> dict:
    elements = _find_elements(whiteboard, element_ids)
    patches = []
    for el in elements:
        if el.type in ("line", "arrow") and len(el.points) >= 2:
            x0 = round(el.x + el.points[0][0], 2)
            y0 = round(el.y + el.points[0][1], 2)
            x1 = round(el.x + el.points[-1][0], 2)
            y1 = round(el.y + el.points[-1][1], 2)
            patch = {
                "id": f"parallel_{el.id}",
                "create": True,
                "type": "line",
                "changes": {
                    "x": x0,
                    "y": y0 + 60,
                    "points": [[0, 0], [round(x1 - x0, 2), round(y1 - y0, 2)]],
                    "strokeColor": "#1e1e1e",
                    "roughness": 0,
                    "strokeWidth": 2,
                },
            }
            patches.append(patch)
    if not patches:
        return {"patches": [], "text": "Could not find any line elements to draw parallels to."}
    return {"patches": patches, "text": ""}


def perpendicular(whiteboard, element_ids: List[str]) -> dict:
    """
    For each consecutive pair of lines (0,1), (2,3), … rotate the second line
    to be perpendicular to the first, preserving its start point and length.
    If fewer than 2 lines are given, create a fresh horizontal + vertical pair.
    """
    elements = _find_elements(whiteboard, element_ids)
    line_els = [
        el for el in elements
        if el.type in ("line", "arrow") and len(el.points) >= 2
    ]

    if len(line_els) >= 2:
        patches = []
        # Process pairs: (0,1), (2,3), …
        for i in range(0, len(line_els) - 1, 2):
            el1, el2 = line_els[i], line_els[i + 1]

            dx1 = (el1.x + el1.points[-1][0]) - (el1.x + el1.points[0][0])
            dy1 = (el1.y + el1.points[-1][1]) - (el1.y + el1.points[0][1])

            perp_dx, perp_dy = -dy1, dx1
            norm = math.sqrt(perp_dx ** 2 + perp_dy ** 2)
            if norm == 0:
                continue  # skip degenerate line

            length2 = math.sqrt(
                (el2.points[-1][0] - el2.points[0][0]) ** 2 +
                (el2.points[-1][1] - el2.points[0][1]) ** 2
            )
            scale = length2 / norm
            new_dx = round(perp_dx * scale, 2)
            new_dy = round(perp_dy * scale, 2)

            start_x = round(el2.x + el2.points[0][0], 2)
            start_y = round(el2.y + el2.points[0][1], 2)

            patches.append({
                "id": el2.id,
                "changes": {
                    "x": start_x,
                    "y": start_y,
                    "points": [[0, 0], [new_dx, new_dy]],
                },
            })

        if not patches:
            return {"patches": [], "text": "All provided lines have zero length — cannot compute perpendiculars."}
        return {"patches": patches, "text": ""}

    else:
        # No lines to act on — create a fresh perpendicular pair
        existing = [el for el in whiteboard.elements if not el.isDeleted]
        if existing:
            cx = round(sum(el.x + el.width / 2 for el in existing) / len(existing), 2)
            cy = round(sum(el.y + el.height / 2 for el in existing) / len(existing), 2)
        else:
            cx, cy = 400.0, 300.0

        half = 100

        patch_h = {
            "id": "perp_line_h",
            "create": True,
            "type": "line",
            "changes": {
                "x": round(cx - half, 2),
                "y": round(cy, 2),
                "points": [[0, 0], [half * 2, 0]],
                "strokeColor": "#1e1e1e",
                "roughness": 0,
                "strokeWidth": 2,
            },
        }
        patch_v = {
            "id": "perp_line_v",
            "create": True,
            "type": "line",
            "changes": {
                "x": round(cx, 2),
                "y": round(cy - half, 2),
                "points": [[0, 0], [0, half * 2]],
                "strokeColor": "#1e1e1e",
                "roughness": 0,
                "strokeWidth": 2,
            },
        }
        return {"patches": [patch_h, patch_v], "text": ""}


def is_perpendicular(whiteboard, element_ids: List[str], params: dict | None = None) -> dict:
    elements = _find_elements(whiteboard, element_ids)
    segs = []
    for el in elements:
        if el.type in ("line", "arrow") and len(el.points) >= 2:
            x0 = el.x + el.points[0][0];  y0 = el.y + el.points[0][1]
            x1 = el.x + el.points[-1][0]; y1 = el.y + el.points[-1][1]
            segs.append(Segment(Point(x0, y0), Point(x1, y1)))

    if len(segs) < 2:
        return {"patches": [], "text": "I need at least two line elements to check if they're perpendicular."}
    try:
        results = []
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                result = segs[i].is_perpendicular(segs[j])
                verdict = "are perpendicular ✓" if result else "are NOT perpendicular ✗"
                label = f"Lines {i+1} and {j+1}" if len(segs) > 2 else "The two lines"
                results.append(f"{label} {verdict}.")
        return {"patches": [], "text": " ".join(results)}
    except Exception as e:
        logger.warning(f"[sympy_ops] is_perpendicular failed: {e}")
        return {"patches": [], "text": "Could not determine if the lines are perpendicular."}


def circle_sector(whiteboard, element_ids: List[str], params: dict | None = None) -> dict:
    """
    Draw a filled sector (pie slice) on a circle element.
    params:
      angle       – sector angle in degrees (required, e.g. 60 / 90 / 180)
      start_angle – starting angle in degrees, 0 = right/east, clockwise (default: -90 = top/12 o'clock)
    """
    params = params or {}
    angle_deg = params.get("angle") or params.get("degrees")
    if angle_deg is None:
        return {"patches": [], "text": "Please specify the sector angle in degrees (e.g. 90)."}
    try:
        angle_deg = float(angle_deg)
    except (TypeError, ValueError):
        return {"patches": [], "text": f"Invalid angle value: {angle_deg!r}"}

    if not element_ids:
        element_ids = [
            el.id for el in whiteboard.elements
            if el.type == "ellipse" and not el.isDeleted and el.id
        ]

    elements = _find_elements(whiteboard, element_ids)
    circle_els = [el for el in elements if el.type == "ellipse"]

    if not circle_els:
        return {"patches": [], "text": "I need a circle (ellipse) element to draw a sector on."}

    patches = []
    for el in circle_els:
        cx = el.x + el.width / 2
        cy = el.y + el.height / 2
        r = min(el.width, el.height) / 2

        start_deg = params.get("start_angle", -90)  # default: 12 o'clock
        start_rad = math.radians(start_deg)
        sector_rad = math.radians(angle_deg)

        # Number of arc steps (~3° per step for smooth curve)
        num_steps = max(int(angle_deg / 3), 12)

        # Build absolute points: center → arc → back to center
        abs_pts = [(cx, cy)]
        for i in range(num_steps + 1):
            a = start_rad + (sector_rad * i / num_steps)
            abs_pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        abs_pts.append((cx, cy))

        min_x = min(p[0] for p in abs_pts)
        min_y = min(p[1] for p in abs_pts)

        rel_pts = [[round(p[0] - min_x, 2), round(p[1] - min_y, 2)] for p in abs_pts]

        patch = {
            "id": f"sector_{el.id}",
            "create": True,
            "type": "freedraw",
            "changes": {
                "x": round(min_x, 2),
                "y": round(min_y, 2),
                "points": rel_pts,
                "pressures": [],
                "simulatePressure": True,
                "fillStyle": "solid",
                "backgroundColor": "#a5d8ff",
                "strokeColor": "#1971c2",
                "opacity": 80,
                "roughness": 0,
                "strokeWidth": 2,
            },
        }
        patches.append(patch)

    return {"patches": patches, "text": ""}


def is_parallel(whiteboard, element_ids: List[str]) -> dict:
    elements = _find_elements(whiteboard, element_ids)
    segs = []
    for el in elements:
        if el.type in ("line", "arrow") and len(el.points) >= 2:
            x0 = el.x + el.points[0][0];  y0 = el.y + el.points[0][1]
            x1 = el.x + el.points[-1][0]; y1 = el.y + el.points[-1][1]
            segs.append(Segment(Point(x0, y0), Point(x1, y1)))

    if len(segs) < 2:
        return {"patches": [], "text": "I need at least two line elements to check parallelism."}
    try:
        results = []
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                result = segs[i].is_parallel(segs[j])
                verdict = "are parallel ✓" if result else "are NOT parallel ✗"
                label = f"Lines {i+1} and {j+1}" if len(segs) > 2 else "The two lines"
                results.append(f"{label} {verdict}.")
        return {"patches": [], "text": " ".join(results)}
    except Exception as e:
        logger.warning(f"[sympy_ops] is_parallel failed: {e}")
        return {"patches": [], "text": "Could not determine if the lines are parallel."}


def is_intersecting(whiteboard, element_ids: List[str]) -> dict:
    elements = _find_elements(whiteboard, element_ids)
    objs = [_el_to_sympy(el) for el in elements]
    objs = [o for o in objs if o is not None]

    if len(objs) < 2:
        return {"patches": [], "text": "I need at least two elements to check intersection."}
    try:
        results = []
        for i in range(len(objs)):
            for j in range(i + 1, len(objs)):
                inter = objs[i].intersection(objs[j])
                verdict = "DO intersect ✓" if inter else "do NOT intersect ✗"
                label = f"Elements {i+1} and {j+1}" if len(objs) > 2 else "The elements"
                results.append(f"{label} {verdict}.")
        return {"patches": [], "text": " ".join(results)}
    except Exception as e:
        logger.warning(f"[sympy_ops] is_intersecting failed: {e}")
        return {"patches": [], "text": "Could not determine intersection status."}


def polygon_area(whiteboard, element_ids: List[str]) -> dict:
    elements = _find_elements(whiteboard, element_ids)
    parts = []
    s = _SCALE_CM_PER_PX
    for el in elements:
        if el.type == "ellipse":
            r_cm = round(min(el.width, el.height) / 2 * s, 2)
            area_cm2 = round(math.pi * r_cm * r_cm, 2)
            parts.append(
                f"Assuming the circle radius is {r_cm} cm, "
                f"the area is approximately {area_cm2} cm²."
            )
        elif el.type == "rectangle":
            w_cm = round(el.width * s, 2)
            h_cm = round(el.height * s, 2)
            area_cm2 = round(w_cm * h_cm, 2)
            parts.append(
                f"Assuming the rectangle is {w_cm} cm × {h_cm} cm, "
                f"the area is approximately {area_cm2} cm²."
            )
        elif el.type == "line" and el.points and len(el.points) >= 3:
            abs_pts = [(el.x + p[0], el.y + p[1]) for p in el.points]
            if abs_pts[0] == abs_pts[-1]:
                abs_pts = abs_pts[:-1]
            n = len(abs_pts)
            area_px2 = abs(sum(
                abs_pts[i][0] * abs_pts[(i + 1) % n][1] - abs_pts[(i + 1) % n][0] * abs_pts[i][1]
                for i in range(n)
            ) / 2)
            area_cm2 = round(area_px2 * s * s, 2)
            shape_label = "parallelogram" if n == 4 else f"{n}-sided polygon"
            if n >= 2:
                dx = (abs_pts[1][0] - abs_pts[0][0]) * s
                dy = (abs_pts[1][1] - abs_pts[0][1]) * s
                base_cm = round(math.sqrt(dx * dx + dy * dy), 2)
                parts.append(
                    f"Assuming the {shape_label} base is {base_cm} cm, "
                    f"the area is approximately {area_cm2} cm²."
                )
            else:
                parts.append(
                    f"The area of the {shape_label} is approximately {area_cm2} cm²."
                )
        else:
            parts.append(f'I can\'t compute the area of element "{el.id}" (type: {el.type}).')
    text = " ".join(parts) if parts else "I couldn't find any shapes to compute the area of."
    return {"patches": [], "text": text}


def circle_area(whiteboard, element_ids: List[str]) -> dict:
    elements = _find_elements(whiteboard, element_ids)
    parts = []
    s = _SCALE_CM_PER_PX
    for el in elements:
        if el.type == "ellipse":
            r_cm = round(min(el.width, el.height) / 2 * s, 2)
            area_cm2 = round(math.pi * r_cm * r_cm, 2)
            parts.append(
                f"Assuming the circle radius is {r_cm} cm, "
                f"the area is approximately {area_cm2} cm²."
            )
    text = " ".join(parts) if parts else "Could not find any circles to compute area."
    return {"patches": [], "text": text}


def _polygon_vertices(el) -> Optional[List[tuple]]:
    """Return absolute vertices for a closed line element, or None if not applicable."""
    if el.type != "line" or not el.points or len(el.points) < 3:
        return None
    pts = [(el.x + p[0], el.y + p[1]) for p in el.points]
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    return pts


def _contrast_color(hex_color: str) -> str:
    """Return a visually distinct color from hex_color that is also visible on a white canvas."""
    try:
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = "".join(c*2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        cr, cg, cb = 255 - r, 255 - g, 255 - b
        # Complement is too close to white (would be invisible on canvas) → use red
        if cr > 200 and cg > 200 and cb > 200:
            return "#e03131"
        return f"#{cr:02x}{cg:02x}{cb:02x}"
    except Exception:
        return "#e03131"


def parallelogram_height(whiteboard, element_ids: List[str]) -> dict:
    """Draw a perpendicular height line on a parallelogram and report its pixel length."""
    elements = _find_elements(whiteboard, element_ids)
    patches = []
    parts = []

    for el in elements:
        verts = _polygon_vertices(el)
        if not verts or len(verts) != 4:
            parts.append(f"Element '{el.id}' must be a 4-sided polygon.")
            continue

        a, b, c, d = verts

        def seg_len(p, q):
            return math.sqrt((q[0]-p[0])**2 + (q[1]-p[1])**2)

        len_ab = seg_len(a, b)
        len_bc = seg_len(b, c)

        if len_ab >= len_bc:
            base_p1, base_p2 = a, b
            apex = d
        else:
            base_p1, base_p2 = b, c
            apex = a

        bx = base_p2[0] - base_p1[0]
        by = base_p2[1] - base_p1[1]
        t = ((apex[0]-base_p1[0])*bx + (apex[1]-base_p1[1])*by) / (bx*bx + by*by)
        foot_x = base_p1[0] + t * bx
        foot_y = base_p1[1] + t * by

        height_px = round(math.sqrt((apex[0]-foot_x)**2 + (apex[1]-foot_y)**2), 1)
        line_color = _contrast_color(el.strokeColor or "#1e1e1e")

        height_id = f"height_{el.id}"
        existing_ids = {e.id for e in whiteboard.elements}
        if height_id in existing_ids:
            patches.append({"id": height_id, "delete": True})

        patches.append({
            "id": height_id,
            "create": True,
            "type": "line",
            "changes": {
                "x": round(apex[0], 2),
                "y": round(apex[1], 2),
                "points": [[0, 0], [round(foot_x - apex[0], 2), round(foot_y - apex[1], 2)]],
                "strokeColor": line_color,
                "strokeStyle": "dashed",
                "strokeWidth": 2,
                "fillStyle": "transparent",
                "backgroundColor": "transparent",
                "roughness": 0,
                "opacity": 100,
            },
        })

        if patches:
            height_cm = round(height_px * _SCALE_CM_PER_PX, 2)
            parts.append(
                f"Assuming the perpendicular height is {height_cm} cm."
            )
        else:
            parts.append(f"Could not draw the height of '{el.id}'.")

    return {"patches": patches, "text": " ".join(parts) if parts else ""}


def _interior_angle_at(verts: list, i: int) -> Optional[float]:
    n = len(verts)
    prev, curr, nxt = verts[(i-1) % n], verts[i], verts[(i+1) % n]
    v1 = (prev[0]-curr[0], prev[1]-curr[1])
    v2 = (nxt[0]-curr[0],  nxt[1]-curr[1])
    mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
    mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
    if mag1 * mag2 < 1e-10:
        return None
    cos_a = max(-1.0, min(1.0, (v1[0]*v2[0] + v1[1]*v2[1]) / (mag1 * mag2)))
    return round(math.degrees(math.acos(cos_a)), 1)


def angle_measure(whiteboard, element_ids: List[str], params: dict | None = None) -> dict:
    """Measure an angle.

    params:
      vertex_index (int): 1-based index of the vertex to measure on a polygon.
                          If omitted, all interior angles are returned.

    element_ids:
      - Two line/arrow elements → angle between them.
      - One polygon (line with 3+ points) → interior angle(s).
      - One simple 2-point line → angle from horizontal.
    """
    elements = _find_elements(whiteboard, element_ids)
    params = params or {}
    vertex_index = params.get("vertex_index")  # 1-based, None = all

    polygons = [e for e in elements if e.type == "line" and e.points and len(e.points) >= 3]
    lines    = [e for e in elements if e.type in ("line", "arrow") and e.points and len(e.points) == 2]

    # Two simple lines → angle between them
    if len(lines) >= 2:
        parts = []
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                la, lb = lines[i], lines[j]
                da = (la.points[-1][0] - la.points[0][0], la.points[-1][1] - la.points[0][1])
                db = (lb.points[-1][0] - lb.points[0][0], lb.points[-1][1] - lb.points[0][1])
                mag_a = math.sqrt(da[0]**2 + da[1]**2)
                mag_b = math.sqrt(db[0]**2 + db[1]**2)
                if mag_a * mag_b < 1e-10:
                    continue
                cos_a = max(-1.0, min(1.0, (da[0]*db[0] + da[1]*db[1]) / (mag_a * mag_b)))
                ang = round(math.degrees(math.acos(cos_a)), 1)
                parts.append(f"The angle between '{la.id}' and '{lb.id}' is {ang}°.")
        return {"patches": [], "text": " ".join(parts) or "Could not compute the angle."}

    # Polygon → specific or all interior angles
    if polygons:
        parts = []
        for el in polygons:
            verts = _polygon_vertices(el)
            if not verts:
                continue
            n = len(verts)
            shape = "parallelogram" if n == 4 else f"{n}-gon"
            if vertex_index is not None:
                idx = int(vertex_index) - 1  # convert to 0-based
                if not (0 <= idx < n):
                    parts.append(f"Vertex {vertex_index} does not exist on '{el.id}' ({n} vertices).")
                    continue
                ang = _interior_angle_at(verts, idx)
                parts.append(f"The angle at vertex {vertex_index} of {shape} '{el.id}' is {ang}°.")
            else:
                angles = [_interior_angle_at(verts, i) for i in range(n)]
                angles = [a for a in angles if a is not None]
                parts.append(f"Interior angles of {shape} '{el.id}': " + ", ".join(f"{a}°" for a in angles) + ".")
        return {"patches": [], "text": " ".join(parts) or "No angles found."}

    # Simple 2-point line → angle from horizontal
    if lines:
        parts = []
        for el in lines:
            dx = el.points[-1][0] - el.points[0][0]
            dy = el.points[-1][1] - el.points[0][1]
            ang = round(math.degrees(math.atan2(abs(dy), abs(dx))), 1)
            parts.append(f"Line '{el.id}' makes an angle of {ang}° with the horizontal.")
        return {"patches": [], "text": " ".join(parts)}

    return {"patches": [], "text": "Please select at least one shape to measure its angle."}
