from __future__ import annotations

import json
import random
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator

from .ai_element_helpers import apply_element_patches


class ZoomTranslation(BaseModel):
    x: float = 0.0
    y: float = 0.0


class Zoom(BaseModel):
    value: float = 1.0
    translation: ZoomTranslation | None = None


class Stats(BaseModel):
    open: bool = False
    panels: int = 0


class ActiveTool(BaseModel):
    type: Optional[str] = None
    locked: bool = False
    customType: Optional[str] = None
    lastActiveTool: Optional[str] = None


class FrameRendering(BaseModel):
    clip: bool = True
    name: bool = True
    enabled: bool = True
    outline: bool = True


class PasteDialog(BaseModel):
    data: Any = None
    shown: bool = False


class Roundness(BaseModel):
    type: int | str | None = None


class EndBinding(BaseModel):
    elementId: Optional[str] = None
    focus: Optional[float] = None
    gap: Optional[float] = None


class SelectedLinearElement(BaseModel):
    elementId: Optional[str] = None
    startBindingElementId: Optional[str] = None
    endBindingElementId: Optional[str] = None


class AppState(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    name: Optional[str] = None
    zoom: Zoom = Field(default_factory=Zoom)
    stats: Stats = Field(default_factory=Stats)
    theme: Optional[str] = None
    toast: Any = None
    width: float = 0.0
    height: float = 0.0
    penMode: bool = False
    scrollX: float = 0.0
    scrollY: float = 0.0
    gridSize: int = 0
    gridStep: int = 0
    openMenu: Any = None
    isLoading: bool = False
    offsetTop: int | float = 0
    openPopup: Any = None
    snapLines: list[Any] = Field(default_factory=list)
    activeTool: ActiveTool = Field(default_factory=ActiveTool)
    fileHandle: Any = None
    followedBy: dict[str, Any] = Field(default_factory=dict)
    isCropping: bool = False
    isResizing: bool = False
    isRotating: bool = False
    newElement: Any = None
    offsetLeft: int | float = 0
    openDialog: Any = None
    contextMenu: Any = None
    exportScale: int | float = 1
    openSidebar: Any = None
    pasteDialog: PasteDialog = Field(default_factory=PasteDialog)
    penDetected: bool = False
    cursorButton: Optional[str] = None
    editingFrame: Any = None
    errorMessage: Any = None
    multiElement: Any = None
    userToFollow: Any = None
    searchMatches: list[Any] = Field(default_factory=list)
    editingGroupId: Any = None
    frameRendering: FrameRendering = Field(default_factory=FrameRendering)
    zenModeEnabled: bool = False
    gridModeEnabled: bool = False
    resizingElement: Any = None
    scrolledOutside: bool = False
    viewModeEnabled: bool = False
    activeEmbeddable: Any = None
    currentChartType: Optional[str] = None
    exportBackground: bool = True
    exportEmbedScene: bool = False
    frameToHighlight: Any = None
    isBindingEnabled: bool = False
    originSnapOffset: Any = None
    selectedGroupIds: dict[str, Any] = Field(default_factory=dict)
    selectionElement: Any = None
    croppingElementId: Any = None
    hoveredElementIds: dict[str, Any] = Field(default_factory=dict)
    showWelcomeScreen: bool = False
    startBoundElement: Any = None
    suggestedBindings: list[Any] = Field(default_factory=list)
    currentItemOpacity: int = 100
    editingTextElement: Any = None
    exportWithDarkMode: bool = False
    selectedElementIds: dict[str, Any] = Field(default_factory=dict)
    showHyperlinkPopup: bool = False
    currentItemFontSize: int = 20
    elementsToHighlight: Any = None
    lastPointerDownWith: Optional[str] = None
    viewBackgroundColor: Optional[str] = None
    currentItemArrowType: Optional[str] = None
    currentItemFillStyle: Optional[str] = None
    currentItemRoughness: int | None = None
    currentItemRoundness: str | int | dict[str, Any] | None = None
    currentItemTextAlign: Optional[str] = None
    editingLinearElement: Any = None
    currentItemFontFamily: int | None = None
    pendingImageElementId: Any = None
    selectedLinearElement: SelectedLinearElement | dict[str, Any] | None = None
    shouldCacheIgnoreZoom: bool = False
    currentItemStrokeColor: Optional[str] = None
    currentItemStrokeStyle: Optional[str] = None
    currentItemStrokeWidth: int | float | None = None
    objectsSnapModeEnabled: bool = False
    currentItemEndArrowhead: Optional[str] = None
    currentHoveredFontFamily: Any = None
    currentItemStartArrowhead: Optional[str] = None
    currentItemBackgroundColor: Optional[str] = None
    previousSelectedElementIds: dict[str, Any] = Field(default_factory=dict)
    defaultSidebarDockedPreference: bool = False
    selectedElementsAreBeingDragged: bool = False


class WhiteboardElement(BaseModel):
    model_config = ConfigDict(extra="allow")

    x: float = 0.0
    y: float = 0.0
    id: Optional[str] = None
    link: Any = None
    seed: Optional[int] = None
    type: Optional[str] = None
    angle: int | float = 0
    index: Optional[str] = None
    width: int | float = 0
    height: int | float = 0
    locked: bool = False
    frameId: Any = None
    opacity: int = 100
    updated: Optional[int] = None
    version: Optional[int] = None
    groupIds: list[Any] = Field(default_factory=list)
    fillStyle: Optional[str] = "solid"
    isDeleted: bool = False
    roughness: Optional[int] = 0
    roundness: Roundness | dict[str, Any] | None = None
    strokeColor: Optional[str] = "#000000"
    strokeStyle: Optional[str] = "solid"
    strokeWidth: int | float = 2
    versionNonce: Optional[int] = None
    boundElements: list[Any] = Field(default_factory=list)
    backgroundColor: Optional[str] = "transparent"

    # line / arrow / freedraw
    points: list[Any] = Field(default_factory=list)
    startArrowhead: Optional[str] = None
    endArrowhead: Optional[str] = None
    startBinding: Any = None
    endBinding: EndBinding | dict[str, Any] | None = None
    lastCommittedPoint: Any = None
    polygon: Optional[bool] = None
    pressures: list[Any] = Field(default_factory=list)
    simulatePressure: Optional[bool] = None

    # text-specific
    fontSize: float | None = None
    fontFamily: int | None = None
    textAlign: Optional[str] = None
    verticalAlign: Optional[str] = None
    containerId: Any = None
    originalText: Optional[str] = None
    autoResize: Optional[bool] = None
    lineHeight: float | None = None
    baseline: int | None = None

    @field_validator("groupIds", "boundElements", mode="before")
    @classmethod
    def normalize_list_fields(cls, v):
        return [] if v is None else v


class Whiteboard(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    files: dict[str, Any] = Field(default_factory=dict)
    appState: AppState = Field(default_factory=AppState)
    elements: list[WhiteboardElement] = Field(default_factory=list)

    def set_whiteboard_state(self, ai_json: str | dict[str, Any]) -> None:
        if isinstance(ai_json, str):
            data = json.loads(ai_json)
        else:
            data = ai_json
        if "board" in data and isinstance(data["board"], dict):
            data = data["board"]
        if "width" in data:
            self.appState.width = float(data["width"])
        if "height" in data:
            self.appState.height = float(data["height"])
        if "grid_size" in data:
            self.appState.gridSize = int(data["grid_size"])
        elif "gridSize" in data:
            self.appState.gridSize = int(data["gridSize"])

    def get_whiteboard_state(self) -> dict[str, Any]:
        return {
            "width": self.appState.width,
            "height": self.appState.height,
            "grid_size": self.appState.gridSize,
        }

    def to_excalidraw_dict(self) -> dict[str, Any]:
        result = self.model_dump(exclude_none=False)
        # Serialize elements without null fields
        result["elements"] = [
            e.model_dump(exclude_none=True) for e in self.elements
        ]
        return result

    def get_whiteboard_elements(self, simplified: bool = True) -> list[dict[str, Any]]:
        if not simplified:
            return [e.model_dump(exclude_none=False) for e in self.elements]

        return [
            {
                "id": e.id,
                "type": e.type,
                "x": e.x,
                "y": e.y,
                "width": e.width,
                "height": e.height,
                "angle": e.angle,
                "strokeColor": e.strokeColor,
                "backgroundColor": e.backgroundColor,
            }
            for e in self.elements
        ]

    def set_whiteboard_elements(self, elements_data: list[dict[str, Any]]) -> None:
        self.elements = [WhiteboardElement.model_validate(e) for e in elements_data]

    def apply_patches_from_ai(self, patches: list[dict]) -> None:
        existing_raw = [
            el.model_dump(exclude_none=True) if hasattr(el, "model_dump") else el
            for el in self.elements
        ]
        existing_ids = [el['id'] for el in existing_raw]
        for patch in patches:
            if patch["id"] in existing_ids and patch['create'] == True:
                patch['id'] = patch['id'] + random.randint(0, 1000)
        patched_raw = apply_element_patches(existing_raw, patches)
        self.elements = [
            WhiteboardElement.model_validate(el)
            for el in patched_raw
        ]

    @classmethod
    def from_excalidraw(cls, data: dict[str, Any]) -> "Whiteboard":
        return cls.model_validate(data)
