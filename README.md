# AI Flask Application

A Flask-based AI tutoring webhook service with advanced whiteboard processing, SymPy mathematical operations, and built-in JSON transcribers for geometric shape recognition and manipulation.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Setup](#setup)
- [API Endpoints](#api-endpoints)
- [SymPy Integration](#sympy-integration)
- [Built-in JSON Transcribers](#built-in-json-transcribers)
- [SymPy Operations](#sympy-operations)
- [SymPy JSON Conversion](#sympy-json-conversion)
- [Architecture](#architecture)
- [Environment Variables](#environment-variables)
- [Usage Examples](#usage-examples)
- [Development Guidelines](#development-guidelines)

## Overview

The AI Flask application is a sophisticated webhook service that processes whiteboard content, performs mathematical operations using SymPy, and provides intelligent responses through OpenAI's GPT models. It supports:

- **Geometric Shape Recognition**: Converts Excalidraw whiteboard elements to SymPy objects
- **Mathematical Operations**: Performs geometric calculations (intersection, distance, area, etc.)
- **LLM Fallback(Optional)**: Gracefully handles unsupported operations using OpenAI
- **Shape Templates**: Pre-built shape library for efficient whiteboard generation
- **Intersection Analysis**: Advanced analysis of shape intersections

## Features

### 1. Whiteboard Processing

- Converts Excalidraw JSON format to SymPy-readable format
- Handles multiple shape types: lines, rectangles, ellipses, diamonds, arrows, and freedraw
- Preserves all whiteboard elements including complex freedraw shapes
- Normalizes freedraw elements to ensure proper rendering after page refresh

### 2. SymPy Mathematical Operations

- **Intersection**: Find intersection points between shapes
- **Parallel Check**: Determine if lines are parallel
- **Distance Calculation**: Calculate distances between points, lines, circles, and polygons
- **Area Calculation**: Compute area of polygons and circles
- **Perpendicular Check**: Check if lines are perpendicular
- **Angle Calculation**: Find angles between lines
- **Contains Check**: Determine if a point is inside a shape
- **Perimeter Calculation**: Calculate perimeter/circumference
- **Tangent Check**: Check if shapes are tangent
- **Midpoint Calculation**: Find midpoint between points

### 3. Built-in JSON Transcribers

- **Shape Template Library**: Pre-built templates for common shapes
- **Shape Detection**: Automatically detects which shapes are needed from user requests
- **Template Injection**: Injects shape templates into LLM prompts for efficient generation
- **Shape Metadata**: Provides detailed metadata about available shapes

### 4. LLM Integration

- **Multi-step Decision Making**: Step 1 decides whether to draw, Step 1.5 identifies shapes, Step 2 generates content
- **Visual Analysis**: Uses OpenAI Vision API to analyze whiteboard images
- **Contextual Responses**: Provides human-like, conversational responses
- **Operation Detection**: LLM intelligently detects mathematical operations from user queries
- **Fallback Handling**: Gracefully handles unsupported operations and shapes

### 5. Error Handling & Monitoring

- **TrustCall Integration**: Comprehensive monitoring and metrics
- **Graceful Degradation**: Handles errors without breaking the system
- **Detailed Logging**: Extensive logging for debugging and monitoring
- **Unconvertible Shape Handling**: Tracks shapes that require LLM analysis

## Setup

### Prerequisites

- Python 3.10+
- Virtual environment (recommended)
- OpenAI API key

### Installation

1. **Create and activate virtual environment:**

```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

2. **Install requirements:**

```bash
pip install -r requirements.txt
```

3. **Create `.env` file:**

```bash
cp .env.example .env  # If example exists
# Or create .env manually with required variables
```

4. **Run the application:**

```bash
flask run
# Or with specific host/port:
flask run --host=0.0.0.0 --port=5000
```

## API Endpoints

### POST `/receive`

Main webhook endpoint for processing AI tutoring requests.

**Request Body:**

```json
{
  "message": "User's message",
  "history": [
    {
      "user_id": "user123",
      "text": "Previous message",
      "timestamp": "2024-01-01T00:00:00"
    }
  ],
  "whiteboard_state": {
    "elements": [...],
    "appState": {...}
  },
  "session_id": "session123",
  "receiving_url": "http://backend/api/whiteboards/ai-prompt/?whiteboard_id=123&ai_tutor_id=456",
  "topic": "Geometry"
}
```

**Response:**

```json
{
  "text": "AI response text",
  "whiteboard_update": {
    "elements": [...],
    "appState": {...}
  }
}
```

### GET `/health_check`

Health check endpoint for monitoring.

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00"
}
```

### GET `/trustcall/metrics`

TrustCall monitoring metrics endpoint.

**Response:**

```json
{
  "timestamp": "2024-01-01T00:00:00",
  "webhook_metrics": {...},
  "ai_metrics": {...},
  "whiteboard_metrics": {...}
}
```

## SymPy Integration

### Overview

The application integrates SymPy for symbolic mathematics, allowing geometric operations on whiteboard shapes. Shapes are converted from Excalidraw format to SymPy objects, enabling mathematical analysis.

### Supported Shape Types

| Excalidraw Type | SymPy Object                   | Notes                                         |
| --------------- | ------------------------------ | --------------------------------------------- |
| `line`          | `Line`                         | Two-point line                                |
| `rectangle`     | `Polygon`                      | 4-vertex polygon                              |
| `ellipse`       | `Circle` or `Polygon`          | Circle if width≈height, else 32-point polygon |
| `diamond`       | `Polygon`                      | 4-vertex diamond shape                        |
| `arrow`         | `Line`                         | Line from first to last point                 |
| `freedraw`      | `Line`, `Circle`, or `Polygon` | Analyzed based on shape complexity            |

### Conversion Process

1. **Element Extraction**: Extracts elements from Excalidraw JSON
2. **Type Detection**: Identifies element type (line, rectangle, etc.)
3. **SymPy Conversion**: Converts to appropriate SymPy object
4. **JSON Serialization**: Converts SymPy objects to JSON for storage
5. **Metadata Tracking**: Tracks conversion errors and LLM-required shapes

## Built-in JSON Transcribers

### Shape Template Library

Located in `transcriber_utils/shapes_template.py`, this module provides:

- **Pre-built Shape Templates**: 34+ shape templates for common geometric shapes
- **Template Loading**: Efficient loading and caching of shape templates
- **Shape Detection**: Detects which shapes are needed from user messages
- **Template Injection**: Injects relevant templates into LLM prompts

### Key Functions

#### `get_available_shapes(use_cache=True)`

Returns metadata about all available shapes.

```python
from ai_flask.transcriber_utils.shapes_template import get_available_shapes

shapes = get_available_shapes()
# Returns: {
#   "shape_name": {
#     "display_name": "Shape Name",
#     "element_types": ["rectangle", "ellipse"],
#     "element_count": 2
#   }
# }
```

#### `load_shape_template(shape_name)`

Loads a specific shape template.

```python
from ai_flask.transcriber_utils.shapes_template import load_shape_template

template = load_shape_template("rectangle")
# Returns: {
#   "elements": [...],
#   "metadata": {...}
# }
```

#### `detect_shapes_needed(user_message, update_description="")`

Detects which shapes are needed from a user message.

```python
from ai_flask.transcriber_utils.shapes_template import detect_shapes_needed

shapes = detect_shapes_needed("Draw a rectangle and a circle")
# Returns: ["rectangle", "circle"]
```

#### `get_shapes_prompt_section(user_message="", update_description="")`

Generates a prompt section with relevant shape templates.

```python
from ai_flask.transcriber_utils.shapes_template import get_shapes_prompt_section

prompt_section = get_shapes_prompt_section("Draw a triangle")
# Returns formatted prompt with triangle template
```

## SymPy Operations

### Available Operations

Located in `transcriber_utils/sympy_operations.py`.

| Operation       | Description                 | Supported Objects            | Status          |
| --------------- | --------------------------- | ---------------------------- | --------------- |
| `intersection`  | Find intersection points    | Line, Circle, Polygon        | ✅ Implemented  |
| `parallel`      | Check if lines are parallel | Line, Segment                | ✅ Implemented  |
| `distance`      | Calculate distance          | Point, Line, Circle, Polygon | ✅ Implemented  |
| `area`          | Calculate area              | Polygon, Circle              | ✅ Implemented  |
| `perpendicular` | Check if perpendicular      | Line, Segment                | 🔄 LLM Fallback |
| `angle`         | Find angle between lines    | Line                         | 🔄 LLM Fallback |
| `perimeter`     | Calculate perimeter         | Polygon, Circle              | 🔄 LLM Fallback |
| `tangent`       | Check if tangent            | Circle                       | 🔄 LLM Fallback |
| `contains`      | Check if point inside shape | Polygon, Line, Circle        | 🔄 LLM Fallback |
| `midpoint`      | Find midpoint               | Point                        | 🔄 LLM Fallback |

### Usage

#### `check_sympy_operation_available(operation: str) -> bool`

Check if an operation is available in SymPy.

```python
from ai_flask.transcriber_utils.sympy_operations import check_sympy_operation_available

is_available = check_sympy_operation_available("intersection")
# Returns: True
```

#### `perform_operation(operation: str, sympy_objects: List[Any], operation_params: Optional[Dict] = None) -> Dict[str, Any]`

Perform a mathematical operation on SymPy objects.

```python
from ai_flask.transcriber_utils.sympy_operations import perform_operation
from sympy import Point, Line

# Create SymPy objects
p1 = Point(0, 0)
p2 = Point(1, 1)
line1 = Line(p1, p2)

p3 = Point(0, 1)
p4 = Point(1, 0)
line2 = Line(p3, p4)

# Perform intersection
result = perform_operation("intersection", [line1, line2])
# Returns: {
#   "success": True,
#   "operation": "intersection",
#   "result": [{"x": 0.5, "y": 0.5}],
#   "message": "Found 1 intersection point(s)"
# }
```

#### `should_draw_result(operation: str, user_message: str) -> bool`

Determine if operation result should be drawn on whiteboard.

```python
from ai_flask.transcriber_utils.sympy_operations import should_draw_result

should_draw = should_draw_result("intersection", "draw the intersection point")
# Returns: True
```

### Operation Details

#### Intersection

Finds intersection points between two shapes.

```python
result = perform_operation("intersection", [line1, line2])
# Result includes intersection points as {"x": float, "y": float}
```

#### Parallel Check

Checks if two lines are parallel.

```python
result = perform_operation("parallel", [line1, line2])
# Result: {"result": True/False, "message": "Lines are parallel" or "Lines are not parallel"}
```

#### Distance Calculation

Calculates distance between shapes. For polygons and circles, uses centroids.

```python
result = perform_operation("distance", [point1, point2])
# Result: {"result": float, "message": "Distance is X units"}
```

#### Area Calculation

Calculates area of polygons and circles.

```python
result = perform_operation("area", [polygon])
# Result: {"result": float, "message": "Area is X square units"}
```

## SymPy JSON Conversion

### Overview

The SymPy JSON conversion system converts Excalidraw whiteboard elements to SymPy objects and stores them in a JSON format that can be converted back to SymPy objects.

### Key Functions

Located in `transcriber_utils/sympy_json_converter.py`.

#### `convert_whiteboard_to_sympy_json(whiteboard_json: Dict[str, Any]) -> Dict[str, Any]`

Converts Excalidraw whiteboard JSON to SymPy-readable JSON format.

```python
from ai_flask.transcriber_utils.sympy_json_converter import convert_whiteboard_to_sympy_json

whiteboard_json = {
    "elements": [
        {
            "type": "line",
            "x": 0,
            "y": 0,
            "points": [[0, 0], [100, 100]]
        }
    ]
}

sympy_json = convert_whiteboard_to_sympy_json(whiteboard_json)
# Returns: {
#   "shapes": [
#     {
#       "type": "Line",
#       "p1": {"type": "Point", "x": 0.0, "y": 0.0},
#       "p2": {"type": "Point", "x": 100.0, "y": 100.0},
#       "element_id": "element_0",
#       "element_type": "line"
#     }
#   ],
#   "metadata": {
#     "total_shapes": 1,
#     "total_elements": 1,
#     "conversion_errors": [],
#     "llm_required_shapes": []
#   }
# }
```

#### `sympy_json_to_objects(sympy_json: Dict[str, Any]) -> List[Any]`

Converts SymPy JSON back to SymPy objects.

```python
from ai_flask.transcriber_utils.sympy_json_converter import sympy_json_to_objects

sympy_objects = sympy_json_to_objects(sympy_json)
# Returns: [Line(Point(0, 0), Point(100, 100))]
```

### JSON Format

#### Point

```json
{
  "type": "Point",
  "x": 0.0,
  "y": 0.0
}
```

#### Line

```json
{
  "type": "Line",
  "p1": { "type": "Point", "x": 0.0, "y": 0.0 },
  "p2": { "type": "Point", "x": 100.0, "y": 100.0 }
}
```

#### Circle

```json
{
  "type": "Circle",
  "center": { "type": "Point", "x": 50.0, "y": 50.0 },
  "radius": 25.0
}
```

#### Polygon

```json
{
  "type": "Polygon",
  "vertices": [
    { "type": "Point", "x": 0.0, "y": 0.0 },
    { "type": "Point", "x": 100.0, "y": 0.0 },
    { "type": "Point", "x": 100.0, "y": 100.0 },
    { "type": "Point", "x": 0.0, "y": 100.0 }
  ]
}
```

### Freedraw Handling

Freedraw elements are analyzed and converted based on shape complexity:

1. **Simple Line** (2 points): Converted to `Line`
2. **Approximately Line**: Converted to `Line` (first to last point)
3. **Approximately Circle**: Converted to `Circle` (fitted)
4. **Complex Shape**: Converted to `Polygon` (all points)
5. **Unconvertible**: Added to `llm_required_shapes` for LLM analysis

### Error Handling

The conversion process includes comprehensive error handling:

- **Invalid Elements**: Logged and added to `conversion_errors`
- **Unconvertible Shapes**: Added to `llm_required_shapes` for LLM fallback
- **Critical Errors**: Returns empty structure with error metadata
- **Never Crashes**: All exceptions are caught and handled gracefully

## Architecture

### Request Flow

```
1. Webhook receives request
   ↓
2. Extract whiteboard state and user message
   ↓
3. Convert whiteboard to SymPy JSON (if available)
   ↓
4. Convert SymPy JSON to SymPy objects
   ↓
5. Step 1: LLM decides if whiteboard update is needed
   ↓
6. LLM detects mathematical operation (if any)
   ↓
7. Perform SymPy operation (if available)
   ↓
8. Step 1.5: Identify shapes needed (if drawing)
   ↓
9. Step 2: Generate whiteboard content (if needed)
   ↓
10. Return response with text and/or whiteboard update
```

### Module Structure

```
ai_flask/
├── app.py                          # Main Flask application
├── transcriber_utils/
│   ├── shapes_template.py          # Shape template library
│   ├── sympy_json_converter.py     # SymPy JSON conversion
│   ├── sympy_operations.py         # Mathematical operations
│   ├── intersection_analysis.py    # Intersection analysis
│   ├── sympy_relationships_mapping.py    # Relationship detection
│   └── excalidraw_to_sympy_json_converter.py            # Excalidraw to SymPy converters
├── utils.py                        # Utility functions
├── trustcall_config.py             # TrustCall monitoring
└── requirements.txt                # Dependencies
```

## Environment Variables

Create a `.env` file in the `ai_flask` directory with the following variables:

### Required Variables

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL_STEP1=gpt-4.1
OPENAI_MODEL_STEP2=gpt-4.1
OPENAI_TEMPERATURE=0.7

# Backend Configuration
BACKEND_BASE_URL=http://localhost:8000
WHITEBOARD_PREVIEW_API_SUFFIX=/api/whiteboards/excalidraw_preview/

# Conversation Configuration
LOOKBACK_LEN=50  # Number of messages to include in context
```

### Optional Variables

```bash
# TrustCall Configuration (if using monitoring)
TRUSTCALL_ENABLED=true
TRUSTCALL_API_KEY=your_trustcall_key
```

## Usage Examples

### Example 1: Intersection Operation

**User Request:** "Find the intersection of these two lines"

**Process:**

1. LLM detects `mathematical_operation: "intersection"`
2. System converts whiteboard elements to SymPy objects
3. `perform_operation("intersection", [line1, line2])` is called
4. Result: `{"success": True, "result": [{"x": 0.5, "y": 0.5}]}`
5. LLM responds with intersection point coordinates

### Example 2: Distance Calculation

**User Request:** "What is the distance between these two points?"

**Process:**

1. LLM detects `mathematical_operation: "distance"`
2. System performs distance calculation using SymPy
3. Result: `{"success": True, "result": 141.42, "message": "Distance is 141.42 units"}`
4. LLM provides human-like response with the distance

### Example 3: Unsupported Operation

**User Request:** "What is the volume of this shape?"

**Process:**

1. LLM detects `mathematical_operation: "volume"` (not in SymPy operations)
2. System sets `use_llm: True`
3. LLM handles the request using its knowledge
4. LLM provides helpful response explaining volume calculation

### Example 4: Freedraw Shape Analysis

**User Request:** "What is the area of this shape?" (pointing to a freedraw shape)

**Process:**

1. Freedraw shape couldn't be converted to SymPy (in `llm_required_shapes`)
2. System detects unconvertible shapes
3. Sets `use_llm: True` immediately
4. LLM analyzes shape visually from whiteboard image
5. LLM provides helpful response or suggests drawing recognizable shapes

## Development Guidelines

### Adding New SymPy Operations

1. **Add to `SYMPY_OPERATIONS` dictionary** in `sympy_operations.py`:

```python
SYMPY_OPERATIONS = {
    "new_operation": ["SymPy.method()"],
    # ... existing operations
}
```

2. **Implement the operation function**:

```python
def perform_new_operation(obj1: Any, obj2: Any) -> Dict[str, Any]:
    try:
        # Implementation
        return {
            "success": True,
            "operation": "new_operation",
            "result": result,
            "message": "Operation completed"
        }
    except Exception as e:
        return {
            "success": False,
            "operation": "new_operation",
            "use_llm": True,
            "message": str(e)
        }
```

3. **Add to `perform_operation` function**:

```python
def perform_operation(operation: str, sympy_objects: List[Any], ...):
    # ... existing code
    elif operation == "new_operation":
        return perform_new_operation(sympy_objects[0], sympy_objects[1])
```

### Adding New Shape Types

1. **Add conversion logic** in `sympy_json_converter.py`:

```python
elif elem_type == "new_shape":
    # Conversion logic
    sympy_obj = NewShape(...)
```

2. **Add to `sympy_object_to_json`** if needed:

```python
elif isinstance(obj, NewShape):
    return {
        "type": "NewShape",
        # ... properties
    }
```

3. **Add to `sympy_json_to_objects`**:

```python
elif shape_type == "NewShape":
    obj = NewShape(...)
```

### Error Handling Best Practices

1. **Always catch exceptions** in conversion functions
2. **Log errors** with appropriate log levels
3. **Return structured error responses** with `use_llm: True` for fallback
4. **Never crash** - always return a valid response structure
5. **Track errors** in metadata for debugging

### Testing

1. **Test SymPy operations** with various shape combinations
2. **Test freedraw conversion** with different shape complexities
3. **Test error handling** with invalid inputs
4. **Test LLM fallback** for unsupported operations
5. **Test whiteboard persistence** after page refresh

## Troubleshooting

### Common Issues

1. **SymPy conversion fails**: Check element structure, ensure points are valid
2. **Operations return `use_llm: True`**: Operation may not be implemented, check `SYMPY_OPERATIONS`
3. **Freedraw shapes not rendering**: Check normalization in `save_whiteboard_content`
4. **LLM not detecting operations**: Check Step 1 prompt and `mathematical_operation` field

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```
