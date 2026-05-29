import math
import logging
from typing import List, Any, Optional, Dict

from sympy import Line as SympyLine, Circle as SympyCircle, Segment, Point, Polygon as SympyPolygon, Line, Circle

logger = logging.getLogger(__name__)


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


def intersection(whiteboard, element_ids: List[str]) -> dict:
    if not element_ids:
        element_ids = [el.id for el in whiteboard.elements if el.type == "ellipse" and not el.isDeleted and el.id]
    elements = _find_elements(whiteboard, element_ids)
    circle_els = [el for el in elements if el.type == "ellipse"]

    if len(circle_els) < 2:
        return {"patches": [], "text": "I need two circle elements to shade the intersection."}

    sympy_circles = []
    for el in circle_els:
        cx = el.x + el.width / 2
        cy = el.y + el.height / 2
        r = min(el.width, el.height) / 2
        sympy_circles.append(SympyCircle(Point(cx, cy), r))

    result = _compute_circle_intersection_arcs(sympy_circles)

    if result and result.get("success"):
        patch = {
            "id": "intersection_shade",
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
        }
        return {"patches": [patch], "text": ""}
    return {"patches": [], "text": f'Could not compute intersection: {result.get("error", "unknown")}'}


def parallel(whiteboard, element_ids: List[str]) -> dict:
    elements = _find_elements(whiteboard, element_ids)
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
            return {"patches": [patch], "text": ""}
    return {"patches": [], "text": "Could not find a line element to draw a parallel to."}


def is_parallel(whiteboard, element_ids: List[str]) -> dict:
    elements = _find_elements(whiteboard, element_ids)
    segs = []
    for el in elements:
        if el.type in ("line", "arrow") and len(el.points) >= 2:
            x0 = el.x + el.points[0][0];  y0 = el.y + el.points[0][1]
            x1 = el.x + el.points[-1][0]; y1 = el.y + el.points[-1][1]
            segs.append(Segment(Point(x0, y0), Point(x1, y1)))

    if len(segs) < 2:
        return {"patches": [], "text": "I need two line elements to check parallelism."}
    try:
        result = segs[0].is_parallel(segs[1])
        verdict = "are parallel ✓" if result else "are NOT parallel ✗"
        return {"patches": [], "text": f"The two lines {verdict}."}
    except Exception as e:
        logger.warning(f"[sympy_ops] is_parallel failed: {e}")
        return {"patches": [], "text": "Could not determine if the lines are parallel."}


def is_intersecting(whiteboard, element_ids: List[str]) -> dict:
    elements = _find_elements(whiteboard, element_ids)
    objs = [_el_to_sympy(el) for el in elements]
    objs = [o for o in objs if o is not None]

    if len(objs) < 2:
        return {"patches": [], "text": "I need two elements to check intersection."}
    try:
        inter = objs[0].intersection(objs[1])
        verdict = "DO intersect ✓" if inter else "do NOT intersect ✗"
        return {"patches": [], "text": f"The elements {verdict}."}
    except Exception as e:
        logger.warning(f"[sympy_ops] is_intersecting failed: {e}")
        return {"patches": [], "text": "Could not determine intersection status."}


def circle_area(whiteboard, element_ids: List[str]) -> dict:
    elements = _find_elements(whiteboard, element_ids)
    parts = []
    for el in elements:
        if el.type == "ellipse":
            r = round(min(el.width, el.height) / 2, 2)
            area = round(math.pi * r * r, 2)
            parts.append(f'Circle "{el.id}": radius = {r}px, area ≈ {area} px².')
    text = " ".join(parts) if parts else "Could not find any circles to compute area."
    return {"patches": [], "text": text}
