import uuid
import random
import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def make_id() -> str:
    """Generate a unique ID for Excalidraw elements (20 characters)"""
    return uuid.uuid4().hex[:20]


def get_default_app_state() -> Dict[str, Any]:
    """Generate default appState for Excalidraw 18.0.0"""
    return {
        "name": "Untitled",
        "zoom": {"value": 1},
        "stats": {"open": False, "panels": 3},
        "theme": "light",
        "toast": None,
        "width": 1920,
        "height": 1080,
        "penMode": False,
        "scrollX": 0,
        "scrollY": 0,
        "gridSize": 20,
        "gridStep": 5,
        "openMenu": None,
        "isLoading": False,
        "offsetTop": 0,
        "openPopup": None,
        "snapLines": [],
        "activeTool": {
            "type": "selection",
            "locked": True,
            "customType": None,
            "lastActiveTool": None
        },
        "fileHandle": None,
        "followedBy": {},
        "isCropping": False,
        "isResizing": False,
        "isRotating": False,
        "newElement": None,
        "offsetLeft": 0,
        "openDialog": None,
        "contextMenu": None,
        "exportScale": 2,
        "openSidebar": None,
        "pasteDialog": {"data": None, "shown": False},
        "penDetected": False,
        "cursorButton": "up",
        "editingFrame": None,
        "errorMessage": None,
        "multiElement": None,
        "userToFollow": None,
        "searchMatches": [],
        "editingGroupId": None,
        "frameRendering": {
            "clip": True,
            "name": True,
            "enabled": True,
            "outline": True
        },
        "zenModeEnabled": False,
        "gridModeEnabled": False,
        "resizingElement": None,
        "scrolledOutside": False,
        "viewModeEnabled": False,
        "activeEmbeddable": None,
        "currentChartType": "bar",
        "exportBackground": True,
        "exportEmbedScene": False,
        "frameToHighlight": None,
        "isBindingEnabled": True,
        "originSnapOffset": None,
        "selectedGroupIds": {},
        "selectionElement": None,
        "croppingElementId": None,
        "hoveredElementIds": {},
        "showWelcomeScreen": True,
        "startBoundElement": None,
        "suggestedBindings": [],
        "currentItemOpacity": 100,
        "editingTextElement": None,
        "exportWithDarkMode": False,
        "selectedElementIds": {},
        "showHyperlinkPopup": False,
        "currentItemFontSize": 20,
        "elementsToHighlight": None,
        "lastPointerDownWith": "mouse",
        "viewBackgroundColor": "#fafafa",
        "currentItemArrowType": "round",
        "currentItemFillStyle": "solid",
        "currentItemRoughness": 1,
        "currentItemRoundness": "round",
        "currentItemTextAlign": "left",
        "editingLinearElement": None,
        "currentItemFontFamily": 5,
        "pendingImageElementId": None,
        "selectedLinearElement": None,
        "shouldCacheIgnoreZoom": False,
        "currentItemStrokeColor": "#1e1e1e",
        "currentItemStrokeStyle": "solid",
        "currentItemStrokeWidth": 2,
        "objectsSnapModeEnabled": False,
        "currentItemEndArrowhead": "arrow",
        "currentHoveredFontFamily": None,
        "currentItemStartArrowhead": None,
        "currentItemBackgroundColor": "transparent",
        "previousSelectedElementIds": {},
        "defaultSidebarDockedPreference": False,
        "selectedElementsAreBeingDragged": False
    }


def create_rectangle_element(
    x: float, y: float, width: float, height: float,
    stroke_color: str = "#000000",
    background_color: str = "transparent",
    stroke_width: int = 2,
    fill_style: str = "solid"
) -> Dict[str, Any]:
    """Create an Excalidraw rectangle element - matches exact format from working examples"""
    return {
        "x": float(x),
        "y": float(y),
        "id": make_id(),
        "link": None,
        "seed": random.randint(1000000, 999999999),
        "type": "rectangle",
        "angle": 0,
        "index": f"a{random.randint(0, 1000)}",
        "width": float(width),
        "height": float(height),
        "locked": False,
        "frameId": None,
        "opacity": 100,
        "updated": int(time.time() * 1000),
        "version": 1,
        "groupIds": [],
        "fillStyle": fill_style,
        "isDeleted": False,
        "roughness": 1,
        "roundness": {"type": 1},
        "strokeColor": stroke_color,
        "strokeStyle": "solid",
        "strokeWidth": stroke_width,
        "versionNonce": random.randint(100000000, 999999999),
        "boundElements": [],
        "backgroundColor": background_color
    }
