import logging
import time
from copy import deepcopy
import random
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


_LINEAR_TYPES = {"line", "arrow"}


def _validate_element(el: Dict[str, Any]) -> None:
    """
    Raise ValueError for element shapes that would crash Excalidraw at render
    time.  Called on every newly created element before it is stored.
    """
    el_type = el.get("type", "")
    el_id = el.get("id", "<unknown>")

    # line / arrow must have at least two points
    if el_type in _LINEAR_TYPES:
        points = el.get("points", [])
        if len(points) < 2:
            raise ValueError(
                f"Element '{el_id}' (type='{el_type}') has {len(points)} point(s); "
                f"'line' and 'arrow' elements require at least 2 points: "
                f"[[x0, y0], [x1, y1]]. "
                f"Received element: {el}"
            )

    # filled dot pattern: backgroundColor must match strokeColor, not "transparent"
    # (soft warning only — don't crash, just correct it)
    if el_type == "ellipse":
        w = el.get("width", 0)
        h = el.get("height", 0)
        if w <= 8 and h <= 8 and el.get("fillStyle") == "solid":
            if el.get("backgroundColor", "transparent") == "transparent":
                el["backgroundColor"] = el.get("strokeColor", "#1e1e1e")


def build_new_full_element_from_ai(ai_element: Dict[str, Any]) -> Dict[str, Any]:
    now = int(time.time() * 1000)

    base = {
        "id": ai_element["id"],
        "type": ai_element["type"],
        "seed": random.randint(1, 2 ** 31 - 1),
        "version": 1,
        "versionNonce": random.randint(1, 2 ** 31 - 1),
        "isDeleted": False,
        "updated": now,
        "groupIds": [],
        "boundElements": [],
        "locked": False,
    }

    base.update(ai_element)

    # Normalise points for linear/freedraw elements:
    # - First point must be [0, 0]; if the LLM used absolute canvas coords,
    #   shift all points by (-first_x, -first_y) and add the offset to x/y.
    # - Recompute width/height from the normalised points.
    if base.get("type") in ("line", "arrow", "freedraw"):
        points = base.get("points") or []
        if points:
            first_x, first_y = points[0][0], points[0][1]
            if first_x != 0 or first_y != 0:
                points = [[p[0] - first_x, p[1] - first_y] for p in points]
                base["x"] = round(base.get("x", 0) + first_x, 4)
                base["y"] = round(base.get("y", 0) + first_y, 4)
                base["points"] = points
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            base["width"] = round(max(xs) - min(xs), 4)
            base["height"] = round(max(ys) - min(ys), 4)

    _validate_element(base)
    return base


def apply_element_patches(
        existing_elements: List[Dict[str, Any]],
        patches: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    elements_by_id = {str(el["id"]): deepcopy(el) for el in existing_elements}
    order = [str(el["id"]) for el in existing_elements]

    for patch in patches:
        el_id = str(patch.get("id"))
        if not el_id:
            raise ValueError("Patch missing 'id'")

        if patch.get("delete") is True:
            elements_by_id.pop(el_id, None)
            continue

        if patch.get("create") is True:
            if el_id in elements_by_id:
                raise ValueError(f"Element '{el_id}' already exists")
            el_type = patch.get("type")
            if not el_type:
                raise ValueError(f"Create patch for '{el_id}' missing 'type'")

            changes = deepcopy(patch.get("changes") or {})
            # If Gemini puts geometry at patch top-level instead of inside "changes", merge it in
            _META = {"id", "type", "create", "delete", "_skipped", "changes"}
            for k, v in patch.items():
                if k not in _META and k not in changes:
                    changes[k] = deepcopy(v)
            changes["id"] = el_id
            changes["type"] = el_type

            try:
                new_element = build_new_full_element_from_ai(changes)
            except ValueError as e:
                logger.warning(f"[PATCH] Skipping invalid element '{el_id}': {e}")
                patch["_skipped"] = True
                continue

            elements_by_id[el_id] = new_element
            order.append(el_id)
            continue

        if el_id not in elements_by_id:
            raise ValueError(f"Element '{el_id}' not found for update")

        changes = patch.get("changes", {})
        if not isinstance(changes, dict):
            raise ValueError(f"Patch for '{el_id}' must contain a dict 'changes'")

        # When text content changes, keep originalText in sync and recompute dimensions
        if "text" in changes:
            changes.setdefault("originalText", changes["text"])
            font_size = elements_by_id[el_id].get("fontSize", 20) or 20
            text_len = len(changes["text"])
            changes.setdefault("width", max(80, font_size * 0.6 * text_len))
            changes.setdefault("height", max(24, font_size * 1.4))

        elements_by_id[el_id].update(changes)

    return [elements_by_id[i] for i in order if i in elements_by_id]

