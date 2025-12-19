import logging
import math
from typing import Dict, Any, List, Optional
from sympy import Point, Line, Circle, Polygon, Segment

logger = logging.getLogger(__name__)

from .excalidraw_to_sympy_json_converter import (
    excalidraw_line_to_sympy,
    excalidraw_rectangle_to_sympy,
    excalidraw_ellipse_to_sympy,
    excalidraw_polygon_to_sympy
)

def sympy_object_to_json(obj) -> Dict[str, Any]:
    """
    Convert a sympy object to a JSON-serializable dictionary.
    
    Args:
        obj: SymPy object (Point, Line, Circle, Polygon, Segment)
        
    Returns:
        Dictionary representation of the sympy object
    """
    if isinstance(obj, Point):
        return {
            "type": "Point",
            "x": float(obj.x),
            "y": float(obj.y)
        }
    
    elif isinstance(obj, Line):
        return {
            "type": "Line",
            "p1": sympy_object_to_json(obj.p1),
            "p2": sympy_object_to_json(obj.p2)
        }
    
    elif isinstance(obj, Segment):
        return {
            "type": "Segment",
            "p1": sympy_object_to_json(obj.p1),
            "p2": sympy_object_to_json(obj.p2)
        }
    
    elif isinstance(obj, Circle):
        return {
            "type": "Circle",
            "center": sympy_object_to_json(obj.center),
            "radius": float(obj.radius)
        }
    
    elif isinstance(obj, Polygon):
        vertices = [sympy_object_to_json(v) for v in obj.vertices]
        return {
            "type": "Polygon",
            "vertices": vertices
        }
    
    else:
        logger.warning(f"Unknown sympy object type: {type(obj)}")
        return {"type": "Unknown", "data": str(obj)}


def _is_approximately_line(points: List[Point], tolerance: float = 5.0) -> bool:
    """
    Check if points form an approximately straight line.
    
    Args:
        points: List of Point objects
        tolerance: Maximum distance from line to consider it approximately linear
        
    Returns:
        True if points are approximately collinear
    """
    if len(points) < 3:
        return True  # 2 points always form a line
    
    # Create a line from first to last point
    line = Line(points[0], points[-1])
    
    # Check if all intermediate points are close to the line
    for point in points[1:-1]:
        distance = float(line.distance(point))
        if distance > tolerance:
            return False
    
    return True


def _is_approximately_circle(points: List[Point], tolerance: float = 0.15) -> bool:
    """
    Check if points form an approximately circular shape.
    
    Args:
        points: List of Point objects
        tolerance: Maximum relative error in radius to consider it a circle
        
    Returns:
        True if points form an approximately circular shape
    """
    if len(points) < 8:
        return False 
    
    # Calculate center as average of all points
    center_x = sum(float(p.x) for p in points) / len(points)
    center_y = sum(float(p.y) for p in points) / len(points)
    center = Point(center_x, center_y)
    
    # Calculate distances from center
    distances = [float(center.distance(p)) for p in points]
    if not distances:
        return False
    
    avg_radius = sum(distances) / len(distances)
    if avg_radius < 1.0:  # Too small to be meaningful
        return False
    
    # Check if all distances are approximately equal
    for dist in distances:
        relative_error = abs(dist - avg_radius) / avg_radius
        if relative_error > tolerance:
            return False
    
    return True


def _fit_circle(points: List[Point]) -> tuple:
    """
    Fit a circle to a set of points.
    
    Args:
        points: List of Point objects
        
    Returns:
        Tuple of (center Point, radius float) or (None, None) if fitting fails
    """
    if len(points) < 3:
        return None, None
    
    try:
        # Simple circle fitting: use average center and average radius
        center_x = sum(float(p.x) for p in points) / len(points)
        center_y = sum(float(p.y) for p in points) / len(points)
        center = Point(center_x, center_y)
        
        # Calculate average radius
        distances = [float(center.distance(p)) for p in points]
        radius = sum(distances) / len(distances)
        
        return center, radius
    except Exception as e:
        logger.warning(f"Error fitting circle: {e}")
        return None, None


def convert_whiteboard_to_sympy_json(whiteboard_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert whiteboard JSON (Excalidraw format) to sympy-readable JSON.
    
    Args:
        whiteboard_json: Excalidraw whiteboard JSON with 'elements' array
        
    Returns:
        Dictionary with sympy objects in JSON format:
        {
            "shapes": [
                {"type": "Line", "p1": {...}, "p2": {...}},
                {"type": "Circle", "center": {...}, "radius": 5.0},
                ...
            ],
            "metadata": {
                "total_shapes": 3,
                "conversion_timestamp": "..."
            }
        }
        
    Note: This function never raises exceptions - all errors are caught and returned in metadata.
    """
    try:
        if not whiteboard_json:
            return {"shapes": [], "metadata": {"total_shapes": 0, "conversion_errors": [], "llm_required_shapes": []}}
        
        elements = whiteboard_json.get("elements", [])
        if not isinstance(elements, list):
            return {"shapes": [], "metadata": {"total_shapes": 0, "conversion_errors": [], "llm_required_shapes": []}}
        
        sympy_shapes = []
        conversion_errors = []
        llm_required_shapes = []  # Shapes that need LLM analysis
        
        for i, element in enumerate(elements):
            if not isinstance(element, dict):
                continue
            
            elem_type = element.get("type", "").lower()
            sympy_obj = None
            
            try:
                # Convert based on element type
                if elem_type == "line":
                    if excalidraw_line_to_sympy:
                        sympy_obj = excalidraw_line_to_sympy(element)
                    else:
                        # Fallback: try to extract points manually
                        points = element.get("points", [])
                        if len(points) >= 2:
                            x0 = float(element.get("x", 0))
                            y0 = float(element.get("y", 0))
                            p1 = Point(x0 + float(points[0][0]), y0 + float(points[0][1]))
                            p2 = Point(x0 + float(points[-1][0]), y0 + float(points[-1][1]))
                            # Check if points are distinct (SymPy requires two unique points)
                            if abs(float(p2.x - p1.x)) > 1e-6 or abs(float(p2.y - p1.y)) > 1e-6:
                                sympy_obj = Line(p1, p2)
                            else:
                                # Points are too close, skip conversion
                                conversion_errors.append(f"Element {i} (type: {elem_type}) has identical start/end points")
                                continue
                
                elif elem_type == "rectangle":
                    if excalidraw_rectangle_to_sympy:
                        sympy_obj = excalidraw_rectangle_to_sympy(element)
                    else:
                        # Fallback: manual conversion
                        x = float(element.get("x", 0))
                        y = float(element.get("y", 0))
                        w = float(element.get("width", 0))
                        h = float(element.get("height", 0))
                        p1 = Point(x, y)
                        p2 = Point(x + w, y)
                        p3 = Point(x + w, y + h)
                        p4 = Point(x, y + h)
                        sympy_obj = Polygon(p1, p2, p3, p4)
                
                elif elem_type == "ellipse":
                    x = float(element.get("x", 0))
                    y = float(element.get("y", 0))
                    w = float(element.get("width", 0))
                    h = float(element.get("height", 0))
                    
                    # Check if it's a circle (width == height)
                    if abs(w - h) < 0.01:
                        # Try the function first
                        if excalidraw_ellipse_to_sympy:
                            sympy_obj = excalidraw_ellipse_to_sympy(element)
                        
                        # Fallback: create circle manually
                        if not sympy_obj:
                            center = Point(x + w/2, y + h/2)
                            radius = w / 2
                            sympy_obj = Circle(center, radius)
                    else:
                        # Approximate ellipse as polygon with 32 points
                        center_x = x + w / 2
                        center_y = y + h / 2
                        a = w / 2  # semi-major axis
                        b = h / 2  # semi-minor axis
                        vertices = []
                        for j in range(32):
                            angle = 2 * math.pi * j / 32
                            px = center_x + a * math.cos(angle)
                            py = center_y + b * math.sin(angle)
                            vertices.append(Point(px, py))
                        if len(vertices) >= 3:
                            sympy_obj = Polygon(*vertices)
                
                elif elem_type == "diamond":
                    # Diamond: calculate vertices from bounding box
                    x = float(element.get("x", 0))
                    y = float(element.get("y", 0))
                    w = float(element.get("width", 0))
                    h = float(element.get("height", 0))
                    
                    # Diamond vertices: top, right, bottom, left
                    center_x = x + w / 2
                    center_y = y + h / 2
                    p1 = Point(center_x, y)  # top
                    p2 = Point(x + w, center_y)  # right
                    p3 = Point(center_x, y + h)  # bottom
                    p4 = Point(x, center_y)  # left
                    sympy_obj = Polygon(p1, p2, p3, p4)
                
                elif elem_type == "arrow":
                    # Arrow: convert to Line using points or start/end positions
                    points = element.get("points", [])
                    if len(points) >= 2:
                        x0 = float(element.get("x", 0))
                        y0 = float(element.get("y", 0))
                        # Get first and last points
                        first_point = points[0]
                        last_point = points[-1]
                        p1 = Point(x0 + float(first_point[0]), y0 + float(first_point[1]))
                        p2 = Point(x0 + float(last_point[0]), y0 + float(last_point[1]))
                        # Check if points are distinct (SymPy requires two unique points)
                        if abs(float(p2.x - p1.x)) > 1e-6 or abs(float(p2.y - p1.y)) > 1e-6:
                            sympy_obj = Line(p1, p2)
                        else:
                            # Points are too close, skip conversion
                            conversion_errors.append(f"Element {i} (type: {elem_type}) has identical start/end points")
                            continue
                    else:
                        # Fallback: use width/height as line
                        x = float(element.get("x", 0))
                        y = float(element.get("y", 0))
                        w = float(element.get("width", 0))
                        h = float(element.get("height", 0))
                        p1 = Point(x, y)
                        p2 = Point(x + w, y + h)
                        # Check if points are distinct (SymPy requires two unique points)
                        if abs(float(p2.x - p1.x)) > 1e-6 or abs(float(p2.y - p1.y)) > 1e-6:
                            sympy_obj = Line(p1, p2)
                        else:
                            # Points are too close, skip conversion
                            conversion_errors.append(f"Element {i} (type: {elem_type}) has zero width/height")
                            continue
                
                elif elem_type == "freedraw":
                    # Freedraw: convert based on shape complexity
                    points = element.get("points", [])
                    if len(points) < 2:
                        conversion_errors.append(f"Element {i} (type: {elem_type}) has insufficient points")
                        continue
                    
                    x0 = float(element.get("x", 0))
                    y0 = float(element.get("y", 0))
                    
                    # Convert relative points to absolute
                    abs_points = []
                    for rel_point in points:
                        if len(rel_point) >= 2:
                            px = x0 + float(rel_point[0])
                            py = y0 + float(rel_point[1])
                            abs_points.append(Point(px, py))
                    
                    if len(abs_points) < 2:
                        conversion_errors.append(f"Element {i} (type: {elem_type}) could not extract valid points")
                        continue
                    
                    # Check if it's a simple line (most points are collinear)
                    if len(abs_points) == 2:
                        # Simple line - check if points are distinct
                        p1, p2 = abs_points[0], abs_points[1]
                        if abs(float(p2.x - p1.x)) > 1e-6 or abs(float(p2.y - p1.y)) > 1e-6:
                            sympy_obj = Line(p1, p2)
                        else:
                            conversion_errors.append(f"Element {i} (type: {elem_type}) has identical start/end points")
                            continue
                    elif _is_approximately_line(abs_points):
                        # Approximate as line from first to last point - check if points are distinct
                        p1, p2 = abs_points[0], abs_points[-1]
                        if abs(float(p2.x - p1.x)) > 1e-6 or abs(float(p2.y - p1.y)) > 1e-6:
                            sympy_obj = Line(p1, p2)
                        else:
                            conversion_errors.append(f"Element {i} (type: {elem_type}) has identical start/end points")
                            continue
                    elif _is_approximately_circle(abs_points):
                        # Approximate as circle
                        center, radius = _fit_circle(abs_points)
                        if center and radius:
                            sympy_obj = Circle(center, radius)
                        else:
                            # Fallback to polygon
                            sympy_obj = Polygon(*abs_points) if len(abs_points) >= 3 else None
                    else:
                        # Convert to polygon with all points
                        if len(abs_points) >= 3:
                            try:
                                # Check if it's closed (first and last points are close)
                                first = abs_points[0]
                                last = abs_points[-1]
                                if abs(float(first.x - last.x)) < 1.0 and abs(float(first.y - last.y)) < 1.0:
                                    # Closed shape - use all points
                                    sympy_obj = Polygon(*abs_points)
                                else:
                                    # Open shape - close it by adding first point at end
                                    sympy_obj = Polygon(*(abs_points + [abs_points[0]]))
                            except Exception as poly_error:
                                # Polygon creation failed (e.g., invalid geometry, collinear points)
                                logger.debug(f"Could not create Polygon from freedraw element {i}: {poly_error}")
                                sympy_obj = None
                        else:
                            # Too few points, convert to line - check if points are distinct
                            if len(abs_points) == 2:
                                p1, p2 = abs_points[0], abs_points[-1]
                                if abs(float(p2.x - p1.x)) > 1e-6 or abs(float(p2.y - p1.y)) > 1e-6:
                                    sympy_obj = Line(p1, p2)
                                else:
                                    conversion_errors.append(f"Element {i} (type: {elem_type}) has identical start/end points")
                                    continue
                            else:
                                sympy_obj = None
                
                # Convert sympy object to JSON
                if sympy_obj:
                    try:
                        shape_json = sympy_object_to_json(sympy_obj)
                        shape_json["element_id"] = element.get("id", f"element_{i}")
                        shape_json["element_type"] = elem_type
                        sympy_shapes.append(shape_json)
                    except Exception as json_error:
                        # JSON conversion failed - mark for LLM analysis
                        logger.debug(f"Could not convert sympy object to JSON for element {i}: {json_error}")
                        conversion_errors.append(f"Element {i} (type: {elem_type}) - JSON conversion failed")
                        # Still add to llm_required_shapes if it's a freedraw
                        if elem_type == "freedraw":
                            freedraw_data = {
                                "element_id": element.get("id", f"element_{i}"),
                                "element_type": elem_type,
                                "points_count": len(element.get("points", [])),
                                "bounds": {
                                    "x": element.get("x"),
                                    "y": element.get("y"),
                                    "width": element.get("width"),
                                    "height": element.get("height")
                                },
                                "requires_llm": True,
                                "reason": "JSON conversion failed"
                            }
                            llm_required_shapes.append(freedraw_data)
                else:
                    # Shape couldn't be converted - mark for LLM analysis if it's a freedraw
                    if elem_type == "freedraw":
                        conversion_errors.append(f"Element {i} (type: {elem_type}) - complex/random freedraw, use LLM for analysis")
                        # Store freedraw data for LLM analysis
                        freedraw_data = {
                            "element_id": element.get("id", f"element_{i}"),
                            "element_type": elem_type,
                            "points_count": len(element.get("points", [])),
                            "bounds": {
                                "x": element.get("x"),
                                "y": element.get("y"),
                                "width": element.get("width"),
                                "height": element.get("height")
                            },
                            "requires_llm": True,
                            "reason": "Could not be converted to geometric shape"
                        }
                        llm_required_shapes.append(freedraw_data)
                    else:
                        conversion_errors.append(f"Element {i} (type: {elem_type}) could not be converted")
            
            except Exception as e:
                logger.warning(f"Error converting element {i} to sympy: {e}")
                conversion_errors.append(f"Element {i}: {str(e)}")
                # If it's a freedraw that failed, still try to add it to llm_required_shapes
                try:
                    elem_type = element.get("type", "").lower() if isinstance(element, dict) else "unknown"
                    if elem_type == "freedraw":
                        freedraw_data = {
                            "element_id": element.get("id", f"element_{i}") if isinstance(element, dict) else f"element_{i}",
                            "element_type": elem_type,
                            "points_count": len(element.get("points", [])) if isinstance(element, dict) else 0,
                            "bounds": {
                                "x": element.get("x") if isinstance(element, dict) else 0,
                                "y": element.get("y") if isinstance(element, dict) else 0,
                                "width": element.get("width") if isinstance(element, dict) else 0,
                                "height": element.get("height") if isinstance(element, dict) else 0
                            },
                            "requires_llm": True,
                            "reason": f"Conversion error: {str(e)}"
                        }
                        llm_required_shapes.append(freedraw_data)
                except Exception as inner_error:
                    logger.debug(f"Error adding failed freedraw to llm_required_shapes: {inner_error}")
        
        result = {
            "shapes": sympy_shapes,
            "metadata": {
                "total_shapes": len(sympy_shapes),
                "total_elements": len(elements),
                "conversion_errors": conversion_errors,
                "llm_required_shapes": llm_required_shapes
            }
        }
        
        logger.info(f"Converted {len(sympy_shapes)} shapes to sympy JSON (from {len(elements)} elements)")
        return result
    
    except Exception as e:
        # Top-level error handler - ensures function never crashes
        logger.error(f"Critical error in convert_whiteboard_to_sympy_json: {e}", exc_info=True)
        return {
            "shapes": [],
            "metadata": {
                "total_shapes": 0,
                "total_elements": 0,
                "conversion_errors": [f"Critical conversion error: {str(e)}"],
                "llm_required_shapes": []
            }
        }


def sympy_json_to_objects(sympy_json: Dict[str, Any]) -> List[Any]:
    """
    Convert sympy JSON back to sympy objects.
    
    Args:
        sympy_json: JSON representation of sympy objects (from convert_whiteboard_to_sympy_json)
        
    Returns:
        List of sympy objects (Point, Line, Circle, Polygon, etc.)
    """
    if not sympy_json or "shapes" not in sympy_json:
        return []
    
    shapes = sympy_json.get("shapes", [])
    sympy_objects = []
    
    for shape in shapes:
        try:
            shape_type = shape.get("type")
            
            if shape_type == "Point":
                obj = Point(shape["x"], shape["y"])
            
            elif shape_type == "Line":
                p1_data = shape["p1"]
                p2_data = shape["p2"]
                p1 = Point(p1_data["x"], p1_data["y"])
                p2 = Point(p2_data["x"], p2_data["y"])
                obj = Line(p1, p2)
            
            elif shape_type == "Segment":
                p1_data = shape["p1"]
                p2_data = shape["p2"]
                p1 = Point(p1_data["x"], p1_data["y"])
                p2 = Point(p2_data["x"], p2_data["y"])
                obj = Segment(p1, p2)
            
            elif shape_type == "Circle":
                center_data = shape["center"]
                center = Point(center_data["x"], center_data["y"])
                radius = float(shape["radius"])
                obj = Circle(center, radius)
            
            elif shape_type == "Polygon":
                vertices_data = shape["vertices"]
                vertices = [Point(v["x"], v["y"]) for v in vertices_data]
                obj = Polygon(*vertices)
            
            else:
                logger.warning(f"Unknown shape type in sympy JSON: {shape_type}")
                continue
            
            sympy_objects.append(obj)
        
        except Exception as e:
            logger.warning(f"Error converting shape to sympy object: {e}")
            continue
    
    logger.info(f"Converted {len(sympy_objects)} shapes from sympy JSON to sympy objects")
    return sympy_objects

