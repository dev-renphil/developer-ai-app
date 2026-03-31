import time
from copy import deepcopy
import random
from typing import List, Dict, Any


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

            changes = deepcopy(patch.get("changes", {}))
            changes["id"] = el_id
            changes["type"] = el_type

            new_element = build_new_full_element_from_ai(changes)
            elements_by_id[el_id] = new_element
            order.append(el_id)
            continue

        if el_id not in elements_by_id:
            raise ValueError(f"Element '{el_id}' not found for update")

        changes = patch.get("changes", {})
        if not isinstance(changes, dict):
            raise ValueError(f"Patch for '{el_id}' must contain a dict 'changes'")

        elements_by_id[el_id].update(changes)

    return [elements_by_id[i] for i in order if i in elements_by_id]

