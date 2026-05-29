import json
import logging
import math
from typing import Dict, Any, List, Optional
from sympy import Point, Line, Circle, Polygon, Segment

logger = logging.getLogger(__name__)

# Available sympy operations
# Maps operation name → the single SymPy call used.
# Excalidraw "line"/"arrow" elements are always bounded → Segment, never Line.
# Excalidraw "ellipse" (circle) → Circle.
# Excalidraw "rectangle"/"diamond" → Polygon.
SYMPY_OPERATIONS = {
    "intersection":  "Segment.intersection() / Circle.intersection()",
    "parallel":      "Segment.is_parallel()",
    "perpendicular": "Segment.is_perpendicular()",
    "angle":         "Segment.angle_between()",
    "distance":      "Point.distance() / Segment.distance()",
    "contains":      "Polygon.encloses_point() / Circle.encloses_point()",
    "area":          "Polygon.area / Circle.area",
    "perimeter":     "Polygon.perimeter / Circle.circumference",
    "tangent":       "Circle.intersection()",
    "midpoint":      "Segment.midpoint",
}


GEO_OPERATIONS = {
    "intersection_shading": "",
    "draw_triangle_orthocenter": "",
    "draw_circle_slice": "",
    "draw_intersection_section": "",
    "is_intersecting": ""
}
def check_sympy_operation_available(operation: str) -> bool:
    """
    Check if an operation is available in sympy.
    
    Args:
        operation: Operation name (e.g., "intersection", "parallel", "distance")
        
    Returns:
        True if operation is available in sympy
    """
    return operation.lower() in SYMPY_OPERATIONS


def perform_intersection(obj1: Any, obj2: Any) -> Dict[str, Any]:
    """Perform intersection operation using sympy."""
    try:
        if hasattr(obj1, 'intersection'):
            result = obj1.intersection(obj2)
            if result:
                points = []
                for item in result:
                    if isinstance(item, Point):
                        points.append({"x": float(item.x), "y": float(item.y)})
                    else:
                        # Convert other intersection types
                        points.append({"type": str(type(item).__name__), "data": str(item)})
                
                return {
                    "success": True,
                    "operation": "intersection",
                    "result": points,
                    "count": len(points),
                    "message": f"Found {len(points)} intersection point(s)"
                }
        
        return {
            "success": False,
            "operation": "intersection",
            "message": "Intersection not available for these object types"
        }
    except Exception as e:
        logger.error(f"Error performing intersection: {e}")
        return {
            "success": False,
            "operation": "intersection",
            "error": str(e)
        }


def perform_parallel_check(obj1: Any, obj2: Any) -> Dict[str, Any]:
    """Check if two segments are parallel using sympy."""
    try:
        if isinstance(obj1, Segment) and isinstance(obj2, Segment):
            is_parallel = obj1.is_parallel(obj2)
            return {
                "success": True,
                "operation": "parallel",
                "result": bool(is_parallel),
                "message": "Segments are parallel" if is_parallel else "Segments are not parallel"
            }

        return {
            "success": False,
            "operation": "parallel",
            "message": "Parallel check requires two Segment objects (Excalidraw 'line'/'arrow' elements)"
        }
    except Exception as e:
        logger.error(f"Error checking parallel: {e}")
        return {
            "success": False,
            "operation": "parallel",
            "error": str(e)
        }


def perform_distance(obj1: Any, obj2: Any) -> Dict[str, Any]:
    """Calculate distance between two objects using sympy."""
    try:
        # Helper to get center point from Circle or Polygon
        def get_center_point(obj):
            if isinstance(obj, Circle):
                return obj.center
            elif isinstance(obj, Polygon):
                # For polygons, calculate centroid (average of vertices)
                vertices = obj.vertices
                if vertices:
                    x_sum = sum(float(v.x) for v in vertices)
                    y_sum = sum(float(v.y) for v in vertices)
                    n = len(vertices)
                    return Point(x_sum / n, y_sum / n)
            elif isinstance(obj, Point):
                return obj
            return None
        
        # Point to Point
        if isinstance(obj1, Point) and isinstance(obj2, Point):
            dist = float(obj1.distance(obj2))
            return {
                "success": True,
                "operation": "distance",
                "result": dist,
                "message": f"Distance: {dist:.2f}"
            }
        
        # Circle to Circle (or Polygon representing circle) - use centers
        center1 = get_center_point(obj1)
        center2 = get_center_point(obj2)
        if center1 and center2:
            dist = float(center1.distance(center2))
            return {
                "success": True,
                "operation": "distance",
                "result": dist,
                "message": f"Distance between centers: {dist:.2f}"
            }
        
        # Point to Line
        if isinstance(obj1, Line) and isinstance(obj2, Point):
            dist = float(obj1.distance(obj2))
            return {
                "success": True,
                "operation": "distance",
                "result": dist,
                "message": f"Distance from point to line: {dist:.2f}"
            }
        elif isinstance(obj1, Point) and isinstance(obj2, Line):
            dist = float(obj2.distance(obj1))
            return {
                "success": True,
                "operation": "distance",
                "result": dist,
                "message": f"Distance from point to line: {dist:.2f}"
            }
        
        return {
            "success": False,
            "operation": "distance",
            "message": "Distance calculation not available for these object types"
        }
    except Exception as e:
        logger.error(f"Error calculating distance: {e}")
        return {
            "success": False,
            "operation": "distance",
            "error": str(e)
        }


def perform_area(obj: Any) -> Dict[str, Any]:
    """Calculate area of an object using sympy."""
    try:
        if isinstance(obj, Polygon):
            area = float(obj.area)
            return {
                "success": True,
                "operation": "area",
                "result": area,
                "message": f"Area: {area:.2f}"
            }
        elif isinstance(obj, Circle):
            area = float(obj.area)
            return {
                "success": True,
                "operation": "area",
                "result": area,
                "message": f"Area: {area:.2f}"
            }
        
        return {
            "success": False,
            "operation": "area",
            "message": "Area calculation only available for Polygon or Circle"
        }
    except Exception as e:
        logger.error(f"Error calculating area: {e}")
        return {
            "success": False,
            "operation": "area",
            "error": str(e)
        }


def perform_operation(
    operation: str,
    sympy_objects: List[Any],
    operation_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Perform a mathematical operation on sympy objects.
    
    Args:
        operation: Operation name (e.g., "intersection", "parallel", "distance")
        sympy_objects: List of sympy objects to operate on
        operation_params: Additional parameters for the operation
        
    Returns:
        Dictionary with operation result or indication that LLM should be used
    """
    operation = operation.lower().strip()
    
    # Check if operation is available in sympy
    if not check_sympy_operation_available(operation):
        return {
            "success": False,
            "operation": operation,
            "use_llm": True,
            "message": f"Operation '{operation}' not available in sympy, use LLM"
        }
    
    if not sympy_objects:
        return {
            "success": False,
            "operation": operation,
            "use_llm": True,
            "message": "No sympy objects provided - use LLM to answer"
        }
    
    # Route to appropriate operation handler
    if operation == "intersection":
        if len(sympy_objects) >= 2:
            result = perform_intersection(sympy_objects[0], sympy_objects[1])
            # If operation failed, fallback to LLM
            if not result.get("success"):
                result["use_llm"] = True
            return result
        else:
            return {
                "success": False,
                "operation": operation,
                "use_llm": True,
                "message": "Intersection requires at least 2 objects - use LLM to answer"
            }
    
    elif operation == "parallel":
        if len(sympy_objects) >= 2:
            result = perform_parallel_check(sympy_objects[0], sympy_objects[1])
            # If operation failed, fallback to LLM
            if not result.get("success"):
                result["use_llm"] = True
            return result
        else:
            return {
                "success": False,
                "operation": operation,
                "use_llm": True,
                "message": "Parallel check requires 2 objects - use LLM to answer"
            }
    
    elif operation == "distance":
        if len(sympy_objects) >= 2:
            result = perform_distance(sympy_objects[0], sympy_objects[1])
            # If operation failed, fallback to LLM
            if not result.get("success"):
                result["use_llm"] = True
            return result
        else:
            return {
                "success": False,
                "operation": operation,
                "use_llm": True,
                "message": "Distance calculation requires 2 objects - use LLM to answer"
            }
    
    elif operation == "area":
        if len(sympy_objects) >= 1:
            result = perform_area(sympy_objects[0])
            # If operation failed, fallback to LLM
            if not result.get("success"):
                result["use_llm"] = True
            return result
        else:
            return {
                "success": False,
                "operation": operation,
                "use_llm": True,
                "message": "Area calculation requires at least 1 object - use LLM to answer"
            }
    
    # For other operations, return indication to use LLM
    return {
        "success": False,
        "operation": operation,
        "use_llm": True,
        "message": f"Operation '{operation}' recognized but not yet implemented, use LLM"
    }


def detect_operation_from_message(user_message: str) -> Optional[str]:
    """
    Detect which operation the user is asking for from their message.
    
    Args:
        user_message: User's message text
        
    Returns:
        Operation name if detected, None otherwise
    """
    message_lower = user_message.lower()
    
    # Map keywords to operations
    operation_keywords = {
        "intersection": ["intersect", "intersection", "cross", "meet", "where do", "where does"],
        "parallel": ["parallel", "are parallel", "is parallel"],
        "perpendicular": ["perpendicular", "right angle", "90 degree"],
        "distance": ["distance", "how far", "length"],
        "area": ["area", "size of"],
        "perimeter": ["perimeter", "circumference"],
        "angle": ["angle", "degrees"],
        "tangent": ["tangent", "touches"],
        "contains": ["contains", "inside", "within"]
    }
    
    for operation, keywords in operation_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            return operation
    
    return None


def should_draw_result(operation: str, user_message: str) -> bool:
    """
    Determine if the operation result should be drawn on the whiteboard.
    
    Args:
        operation: Operation name
        user_message: User's message
        
    Returns:
        True if result should be drawn
    """
    message_lower = user_message.lower()
    draw_keywords = ["draw", "show", "display", "visualize", "plot", "mark"]
    
    # Some operations always benefit from drawing
    always_draw = ["intersection"]  # Intersection points should be drawn
    
    if operation in always_draw:
        return True
    
    # Check if user explicitly asks to draw
    if any(keyword in message_lower for keyword in draw_keywords):
        return True
    
    return False


def compute_sector_points(element: Dict[str, Any], angle_deg: float) -> Dict[str, Any]:
    """
    Pre-compute the arc/sector points for a pie-slice or sector shape.

    Given an ellipse/circle Excalidraw element and a sweep angle, returns the
    centre, radius, and a ready-to-use list of relative freedraw points that
    the AI can copy directly into a freedraw element to draw the sector.

    Args:
        element:   Excalidraw element dict (needs x, y, width, height).
        angle_deg: Sweep angle of the sector in degrees (0–360).

    Returns:
        Dictionary with cx, cy, r, angle_deg, and freedraw_points (relative).
    """
    try:
        cx = element["x"] + element["width"] / 2.0
        cy = element["y"] + element["height"] / 2.0
        r = min(element["width"], element["height"]) / 2.0
        angle_rad = math.radians(angle_deg)

        # Build relative arc points (origin = cx, cy)
        steps = max(36, int(angle_deg))  # at least 1 point per degree
        points = [[0.0, 0.0]]  # start at centre
        for i in range(steps + 1):
            t = (i / steps) * angle_rad
            px = r * math.cos(t)
            py = r * math.sin(t)
            points.append([round(px, 2), round(py, 2)])
        points.append([0.0, 0.0])  # close back to centre

        return {
            "success": True,
            "cx": round(cx, 2),
            "cy": round(cy, 2),
            "r": round(r, 2),
            "angle_deg": angle_deg,
            "freedraw_points": points,
        }
    except Exception as e:
        logger.error(f"Error computing sector points: {e}")
        return {"success": False, "error": str(e)}



def analyze_freedraw_with_llm(freedraw_element: Dict[str, Any], openai_client=None) -> Optional[Dict[str, Any]]:
    """
    Use LLM to analyze a complex freedraw shape and convert it to a sympy object.
    
    Args:
        freedraw_element: Excalidraw freedraw element
        openai_client: OpenAI client instance (optional)
        
    Returns:
        Dictionary with sympy object info or None if analysis fails
    """
    if not openai_client:
        return None
    
    try:
        points = freedraw_element.get("points", [])
        if len(points) < 2:
            return None
        
        # Prepare prompt for LLM
        prompt = f"""
        Analyze this freedraw shape and identify what geometric shape it represents.
        
        Freedraw data:
        - Points count: {len(points)}
        - Bounding box: x={freedraw_element.get('x')}, y={freedraw_element.get('y')}, 
          width={freedraw_element.get('width')}, height={freedraw_element.get('height')}
        - First few points: {points[:5]}
        - Last few points: {points[-5:]}
        
        Determine if this freedraw represents:
        1. A line (straight line)
        2. A circle
        3. A rectangle/square
        4. A triangle
        5. A polygon (specify number of sides if regular)
        6. Other geometric shape
        
        Return JSON with:
        {{
            "shape_type": "line|circle|rectangle|triangle|polygon|other",
            "confidence": "high|medium|low",
            "parameters": {{...}}  // shape-specific parameters
        }}
        """
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Use a fast model for this
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content.strip()
        # Clean JSON if wrapped in markdown
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()
        
        analysis = json.loads(result_text)
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing freedraw with LLM: {e}")
        return None

