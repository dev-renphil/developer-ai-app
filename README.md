# developer_ai_app

A Flask-based AI tutoring backend that powers an interactive math whiteboard. It receives student messages and whiteboard state from the chatboard frontend, decides what to do, and responds with a text reply and updated whiteboard elements.

---

## Overview

The app exposes a `/draw` endpoint. When a student sends a message in the chatboard, the chatboard POSTs the full context to this endpoint. The app runs the message through two LLM steps and a set of deterministic SymPy geometry operations, then POSTs the response back to the chatboard.

The whiteboard uses Excalidraw format. All element manipulation produces JSON patches that are applied to the whiteboard state before being sent back.

---

## Architecture

### Request flow

```
POST /draw
  |
  +--> Validate payload
  |
  +--> Parse whiteboard state (Whiteboard.model_validate)
  |
  +--> STEP 1: describe_user_intent()
  |      - Builds prompt with topic, history, whiteboard state, pre-test details
  |      - Calls LLM (OpenAI or Anthropic depending on env config)
  |      - Returns: operation, element_ids, text reply, instruction, image_process flag
  |      - Greeting guard: forces operation=null for short greetings
  |      - Image retry: if image_process=true, retakes Step 1 with a whiteboard screenshot
  |
  +--> Decision: operation = null?
  |      YES --> Build response with text only, no whiteboard changes
  |              POST to receiving_url
  |
  +--> Decision: operation = basic_draw?
  |      YES --> STEP 2: _run_step2_llm()
  |               - Builds prompt from the instruction returned by Step 1
  |               - Calls LLM to generate Excalidraw patches
  |               - If image_process=true, includes whiteboard screenshot
  |               - Apply patches via whiteboard.apply_patches_from_ai()
  |              POST to receiving_url
  |
  +--> Any other operation (SymPy)
         - Calls the matching function in sympy_operations.py directly
         - Function computes geometry, returns patches + text
         - Apply patches via whiteboard.apply_patches_from_ai()
         POST to receiving_url
```

### Key modules

| Module | Purpose |
|---|---|
| `app.py` | Flask app, `/draw` endpoint, `describe_user_intent`, `generate_shapes` |
| `sympy_operations.py` | All deterministic geometry operations |
| `prompts.py` | Prompt builders for Step 1 and Step 2 |
| `shape.py` | Pydantic models for `Whiteboard` and `WhiteboardElement` |
| `ai_steps.py` | LLM call wrappers (OpenAI, Anthropic) |
| `ai_dtos.py` | Data transfer objects: `Step1Reply`, `ReceiveDTO` |
| `utils.py` | Image encoding, HMAC signature helpers |

---

## Endpoints

### `POST /draw`

Main endpoint used by the chatboard.

**Request body:**

```json
{
  "message": "What is the area of this shape?",
  "history": [...],
  "whiteboard_state": { "elements": [...], "appState": {} },
  "topic": "Geometry",
  "receiving_url": "https://chatboard.example.com/ai_response?ai_tutor_id=...",
  "session_id": "abc123",
  "pre_test_details": [...]
}
```

**Response:** `{ "status": "sent", "reply": "..." }` (the full reply is also POSTed to `receiving_url`).

The reply sent to `receiving_url` contains:

```json
{
  "text": "The area is approximately 42.5 cm².",
  "appState": {},
  "elements": [...]
}
```

### `POST /receive2`

Legacy endpoint with a more complex pipeline that includes vision scaffolding, explicit SymPy JSON conversion, and a multi-step LLM chain. Not used in the primary flow.

---

## Step 1 operations

Step 1 selects exactly one operation per message. The full list:

| Operation | Description |
|---|---|
| `null` | Chat reply only, no whiteboard change |
| `basic_draw` | Generic drawing via Step 2 LLM |
| `circle_area` | Area of a circle |
| `polygon_area` | Area of any closed polygon or rectangle |
| `parallelogram_height` | Draws the perpendicular height line on a parallelogram |
| `circle_center` | Marks the center point of a circle |
| `triangle_orthocenter` | Marks the orthocenter of a triangle |
| `intersection` | Shades the overlapping region of two elements |
| `is_parallel` | Checks whether lines are parallel |
| `is_perpendicular` | Checks whether lines are perpendicular |
| `is_intersecting` | Checks whether elements intersect |
| `parallel` | Draws a new line parallel to an existing one |
| `perpendicular` | Rotates a line to be perpendicular to another, or creates a fresh pair |
| `circle_sector` | Draws a filled pie-slice sector inside a circle |
| `angle_measure` | Computes interior angles of a polygon or the angle between lines |

Step 1 rules enforced in the prompt:

- Default to `null`.
- `basic_draw` is only valid when the student uses an explicit draw verb or accepts a prior offer to draw.
- Questions, explanations, and greetings always return `null`.
- If the student's first message and pre-test data show weak areas, the reply opens with a reference to those weak areas.
- If the topic is visual, the reply may end with a single offer to draw on the board, but never in the same turn as an actual draw operation.

---

## Pre-test integration

When `pre_test_details` is present in the payload, `prompts.py` formats the incorrect answers into a block injected into the Step 1 prompt. The LLM is instructed to:

- On the first message, acknowledge one weak area before addressing the student's question.
- When the ongoing topic matches a weak area, weave in a reference naturally.

The pre-test block lists each incorrectly answered question with its topic, the question text, what the student answered, and the correct answer.

---

## Unit scale

All element coordinates are in Excalidraw pixels. A fixed scale converts pixel measurements to centimetres for all area and length results:

```python
_SCALE_CM_PER_PX = 0.0265   # 100 px = 2.65 cm
```

This constant is defined at the top of `sympy_operations.py`. Changing it affects all area and height outputs globally.

---

## Environment variables

| Variable | Purpose |
|---|---|
| `OPENAI_MODEL` | Model ID for OpenAI calls |
| `ANTHROPIC_MODEL` | Model ID for Anthropic calls |
| `OPENAI_TEMPERATURE` | Sampling temperature for all LLM calls |
| `USE_AI` | Which provider to use (`openai` or `anthropic`) |
| `SECRET_KEY` | HMAC key for payload signature verification |

---

## SymPy functions reference

All functions live in `sympy_operations.py`. Each function receives a `Whiteboard` object and a list of element IDs, and returns a dict with two keys:

- `patches` - list of Excalidraw patch objects to apply to the whiteboard
- `text` - the text reply shown to the student

A patch has the shape:

```json
{ "id": "element-id", "create": true, "type": "line", "changes": { ... } }
```

For deletion:

```json
{ "id": "element-id", "delete": true }
```

---

### circle_center

Marks the geometric center of one or more circle (ellipse) elements on the whiteboard.

Computes `cx = x + width / 2`, `cy = y + height / 2` for each ellipse and places a small filled dot at that point. The dot element ID is `center_{element_id}`.

Returns patches with the dot elements. No text reply.

---

### triangle_orthocenter

Marks the orthocenter of one or more triangles.

Handles two input formats:

- A single closed line element with three or more points (the element is the full triangle).
- Three separate line or arrow elements, each representing one side.

For each triangle, it constructs the three altitude lines using SymPy's `perpendicular_line` method and finds their intersection. A red dot is placed at the orthocenter. The dot element ID is `orthocenter_dot` or `orthocenter_dot_{n}` when multiple triangles are present.

Returns patches with the dot elements. No text reply.

---

### intersection

Shades the overlapping region between pairs of elements.

Handles two cases:

- Two ellipses: uses SymPy to find the two intersection points of the circles, then traces arcs from each circle between those points to build a lens-shaped freedraw polygon.
- Any other pair (rectangle, diamond, line): falls back to a bounding-box overlap rectangle filled with a semi-transparent blue.

The shading element ID is `intersection_shade_{pair_index}`.

Returns patches with the shading elements. No text reply.

---

### circle_area

Calculates the area of one or more circle (ellipse) elements.

Takes the minimum of width and height as the diameter, converts the radius to centimetres using `_SCALE_CM_PER_PX`, and applies the formula `area = pi * r^2`.

Example reply: "Assuming the circle radius is 5.0 cm, the area is approximately 78.54 cm²."

Returns no patches.

---

### polygon_area

Calculates the area of one or more shapes: ellipses, rectangles, or closed polygons.

- Ellipse: same calculation as `circle_area`.
- Rectangle: `width * height` converted to cm².
- Closed line (polygon or parallelogram): Shoelace formula on the absolute vertex coordinates, then converted to cm². Also reports the base length of the first side in cm.

All measurements are converted using `_SCALE_CM_PER_PX` before reporting.

Example reply: "Assuming the parallelogram base is 8.5 cm, the area is approximately 42.5 cm²."

Returns no patches.

---

### parallelogram_height

Draws the perpendicular height line from the apex vertex to the base of a parallelogram, and reports the height in centimetres.

Steps:

1. Identifies the longest side as the base.
2. Projects the opposite apex vertex onto the base line using the dot product.
3. Draws a dashed line from the apex to the foot of the perpendicular.
4. If a height line for this element already exists (ID `height_{element_id}`), it is deleted first to prevent duplicates.

The line color is chosen by `_contrast_color`, which computes the complement of the shape's stroke color and falls back to red if the complement would be near-white (invisible on a white canvas).

Example reply: "Assuming the perpendicular height is 5.3 cm."

---

### is_parallel

Checks whether two or more line or arrow elements are parallel.

Converts each element to a SymPy `Segment` using its absolute start and end points, then calls `segment.is_parallel(other)` for every pair.

Example reply: "The two lines are parallel." or "The two lines are NOT parallel."

Returns no patches.

---

### is_perpendicular

Checks whether two or more line or arrow elements are perpendicular.

Same approach as `is_parallel`, using SymPy's `is_perpendicular` method.

Example reply: "The two lines are perpendicular." or "The two lines are NOT perpendicular."

Returns no patches.

---

### is_intersecting

Checks whether two or more elements intersect.

Converts each element to its SymPy equivalent (circle or polygon), then calls `.intersection()` for every pair. Reports whether the intersection set is non-empty.

Example reply: "The elements DO intersect." or "The elements do NOT intersect."

Returns no patches.

---

### parallel

Draws a new line parallel to each selected line or arrow element.

The new line has the same direction vector as the original but is offset 60 pixels downward. The new element ID is `parallel_{element_id}`.

Returns patches with the new line elements. No text reply.

---

### perpendicular

Rotates the second line in each consecutive pair to be perpendicular to the first, preserving the second line's start point and length.

If fewer than two lines are provided, creates a fresh horizontal and vertical line pair centered on the existing content (or at `(400, 300)` if the board is empty). The fresh pair uses IDs `perp_line_h` and `perp_line_v`.

Returns patches with the updated or new line elements. No text reply.

---

### circle_sector

Draws a filled pie-slice sector inside an existing circle.

Parameters passed via `operation_params` from Step 1:

- `angle` (required): sector angle in degrees.
- `start_angle` (optional): starting angle in degrees, where 0 is east and angles increase clockwise. Defaults to -90 (12 o'clock position).

Builds the sector as a closed freedraw polygon: center point, arc points sampled at roughly 3-degree intervals, back to center. The element ID is `sector_{element_id}`.

Returns patches with the sector freedraw element. No text reply.

---

### angle_measure

Measures angles on the whiteboard. Handles three cases depending on the selected elements:

- Two simple lines: computes the angle between their direction vectors using the dot product formula.
- One polygon with three or more vertices: computes all interior angles using the dot product at each vertex. If `vertex_index` is specified in `operation_params` (1-based), only that vertex is reported.
- One simple two-point line: reports the angle the line makes with the horizontal axis.

Example replies:

- "The angle between 'line-1' and 'line-2' is 45.0°."
- "Interior angles of parallelogram 'shape-1': 60.0°, 120.0°, 60.0°, 120.0°."
- "Line 'line-1' makes an angle of 30.0° with the horizontal."

Returns no patches.
