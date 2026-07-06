import json
import random
import time
import math
import logging
from typing import Dict, Any, List, Callable, Optional
from sympy import Point, Polygon, Circle, RegularPolygon, Triangle, Segment, Line
from sympy import symbols, lambdify, sin

from .sympy_base_value_function import make_id, get_default_app_state

logger = logging.getLogger(__name__)

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


def create_ellipse_element(
    x: float, y: float, width: float, height: float,
    stroke_color: str = "#000000",
    background_color: str = "transparent",
    stroke_width: int = 2,
    fill_style: str = "solid"
) -> Dict[str, Any]:
    """Create an Excalidraw ellipse element - matches exact format from working examples"""
    return {
        "x": float(x),
        "y": float(y),
        "id": make_id(),
        "link": None,
        "seed": random.randint(1000000, 999999999),
        "type": "ellipse",
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
        "roundness": None,  # Can be null or {"type": 2}, using null to match some examples
        "strokeColor": stroke_color,
        "strokeStyle": "solid",
        "strokeWidth": stroke_width,
        "versionNonce": random.randint(100000000, 999999999),
        "boundElements": [],
        "backgroundColor": background_color
    }


def create_line_element(
    points: List[List[float]],
    x: float, y: float, width: float, height: float,
    stroke_color: str = "#000000",
    stroke_width: int = 2,
    closed: bool = False,
    background_color: str = "#ced4da"
) -> Dict[str, Any]:
    """Create an Excalidraw line/polyline element - matches exact format from working examples"""
    # Match the exact field order from the working example
    element = {
        "x": float(x),
        "y": float(y),
        "id": make_id(),
        "link": None,
        "seed": random.randint(1000000, 999999999),
        "type": "line",
        "angle": 0,
        "index": f"b{random.randint(0, 1000)}",
        "width": float(width),
        "height": float(height),
        "locked": False,
        "points": points,
        "frameId": None,
        "opacity": 100,
        "polygon": closed,  # True for closed shapes, False for open lines
        "updated": int(time.time() * 1000),
        "version": 1,
        "groupIds": [],
        "fillStyle": "solid",
        "isDeleted": False,
        "roughness": 1,
        "roundness": None,
        "endBinding": None,
        "strokeColor": stroke_color,
        "strokeStyle": "solid",
        "strokeWidth": stroke_width,
        "endArrowhead": None,
        "startBinding": None,
        "versionNonce": random.randint(100000000, 999999999),
        "boundElements": [],
        "startArrowhead": None,
        "backgroundColor": background_color,
        "lastCommittedPoint": None
    }
    return element


def create_diamond_element(
    x: float, y: float, width: float, height: float,
    stroke_color: str = "#000000",
    background_color: str = "transparent",
    stroke_width: int = 2
) -> Dict[str, Any]:
    """Create an Excalidraw diamond element"""
    return {
        "id": make_id(),
        "type": "diamond",
        "x": float(x),
        "y": float(y),
        "width": float(width),
        "height": float(height),
        "angle": 0,
        "strokeColor": stroke_color,
        "backgroundColor": background_color,
        "fillStyle": "solid",
        "strokeWidth": stroke_width,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": None,
        "seed": random.randint(1000000, 999999999),
        "version": 1,
        "versionNonce": random.randint(100000000, 999999999),
        "isDeleted": False,
        "boundElements": [],
        "updated": int(time.time() * 1000),
        "link": None,
        "locked": False,
        "frameId": None,
        "index": f"a{random.randint(0, 1000)}"
    }


def sympy_rectangle_to_excalidraw(rect: Polygon, **kwargs) -> Dict[str, Any]:
    """Convert SymPy Polygon (rectangle) to Excalidraw rectangle element"""
    # Get bounding box
    vertices = list(rect.vertices)
    x_coords = [float(v.x) for v in vertices]
    y_coords = [float(v.y) for v in vertices]
    
    x = min(x_coords)
    y = min(y_coords)
    width = max(x_coords) - x
    height = max(y_coords) - y
    
    return create_rectangle_element(x, y, width, height, **kwargs)


def sympy_polygon_to_excalidraw(polygon: Polygon, **kwargs) -> Dict[str, Any]:
    """Convert SymPy Polygon to Excalidraw line element (closed polygon)"""
    vertices = list(polygon.vertices)
    
    # Convert to float coordinates
    coords = [(float(v.x), float(v.y)) for v in vertices]
    
    # Calculate bounding box
    x_coords = [c[0] for c in coords]
    y_coords = [c[1] for c in coords]
    
    x0 = min(x_coords)
    y0 = min(y_coords)
    width = max(x_coords) - x0
    height = max(y_coords) - y0
    
    # Convert to relative points (relative to first point)
    rel_points = [[float(c[0] - x0), float(c[1] - y0)] for c in coords]
    # Close the polygon
    rel_points.append(rel_points[0])
    
    # Extract supported parameters from kwargs
    background_color = kwargs.pop('background_color', "#ced4da")
    stroke_color = kwargs.pop('stroke_color', "#000000")
    stroke_width = kwargs.pop('stroke_width', 2)
    # Remove unsupported kwargs (like fill_style) that create_line_element doesn't accept
    kwargs.pop('fill_style', None)
    
    return create_line_element(rel_points, x0, y0, width, height, closed=True, 
                              background_color=background_color, 
                              stroke_color=stroke_color, 
                              stroke_width=stroke_width)


def sympy_circle_to_excalidraw(circle: Circle, **kwargs) -> Dict[str, Any]:
    """Convert SymPy Circle to Excalidraw ellipse element"""
    center = circle.center
    radius = float(circle.radius)
    
    x = float(center.x) - radius
    y = float(center.y) - radius
    width = 2 * radius
    height = 2 * radius
    
    return create_ellipse_element(x, y, width, height, **kwargs)


def sympy_triangle_to_excalidraw(triangle: Triangle, **kwargs) -> Dict[str, Any]:
    """Convert SymPy Triangle to Excalidraw line element (closed triangle)"""
    vertices = list(triangle.vertices)
    
    # Convert to float coordinates
    coords = [(float(v.x), float(v.y)) for v in vertices]
    
    # Calculate bounding box
    x_coords = [c[0] for c in coords]
    y_coords = [c[1] for c in coords]
    
    x0 = min(x_coords)
    y0 = min(y_coords)
    width = max(x_coords) - x0
    height = max(y_coords) - y0
    
    # Convert to relative points
    rel_points = [[float(c[0] - x0), float(c[1] - y0)] for c in coords]
    # Close the triangle
    rel_points.append(rel_points[0])
    
    # Extract supported parameters from kwargs
    background_color = kwargs.pop('background_color', "#ced4da")
    stroke_color = kwargs.pop('stroke_color', "#000000")
    stroke_width = kwargs.pop('stroke_width', 2)
    # Remove unsupported kwargs (like fill_style) that create_line_element doesn't accept
    kwargs.pop('fill_style', None)
    
    return create_line_element(rel_points, x0, y0, width, height, closed=True,
                              background_color=background_color,
                              stroke_color=stroke_color,
                              stroke_width=stroke_width)


def sympy_regular_polygon_to_excalidraw(polygon: RegularPolygon, **kwargs) -> Dict[str, Any]:
    """Convert SymPy RegularPolygon to Excalidraw line element"""
    vertices = list(polygon.vertices)
    
    # Convert to float coordinates
    coords = [(float(v.x), float(v.y)) for v in vertices]
    
    # Calculate bounding box
    x_coords = [c[0] for c in coords]
    y_coords = [c[1] for c in coords]
    
    x0 = min(x_coords)
    y0 = min(y_coords)
    width = max(x_coords) - x0
    height = max(y_coords) - y0
    
    # Convert to relative points
    rel_points = [[float(c[0] - x0), float(c[1] - y0)] for c in coords]
    # Close the polygon
    rel_points.append(rel_points[0])
    
    # Extract supported parameters from kwargs
    background_color = kwargs.pop('background_color', "#ced4da")
    stroke_color = kwargs.pop('stroke_color', "#000000")
    stroke_width = kwargs.pop('stroke_width', 2)
    # Remove unsupported kwargs (like fill_style) that create_line_element doesn't accept
    kwargs.pop('fill_style', None)
    
    return create_line_element(rel_points, x0, y0, width, height, closed=True,
                              background_color=background_color,
                              stroke_color=stroke_color,
                              stroke_width=stroke_width)


def clamp_coordinate(value: float, min_val: float = -10000, max_val: float = 10000) -> float:
    """Clamp coordinate to safe range for Excalidraw"""
    return max(min_val, min(max_val, value))


def create_coordinate_axes(
    origin_x: float = 400, origin_y: float = 400,
    x_range: float = 200, y_range: float = 200,
    stroke_color: str = "#666666",
    stroke_width: int = 1
) -> List[Dict[str, Any]]:
    """
    Create coordinate axes (x and y axes with arrows).
    Reuses create_line_element for the axes.
    Coordinates are clamped to safe ranges.
    """
    elements = []
    
    # Ensure origin is in safe range
    origin_x = clamp_coordinate(origin_x, 100, 1900)
    origin_y = clamp_coordinate(origin_y, 100, 1900)
    
    # X-axis (horizontal line with arrow) - limit range
    x_range = min(x_range, 300)  # Limit to reasonable size
    x_axis_points = [[0, 0], [x_range * 2, 0]]
    x_start = clamp_coordinate(origin_x - x_range, 50, 1950)
    x_axis = create_line_element(
        x_axis_points, x_start, origin_y, x_range * 2, 0,
        stroke_color=stroke_color, stroke_width=stroke_width, closed=False
    )
    # Add arrowhead at the end
    x_axis["endArrowhead"] = "arrow"
    elements.append(x_axis)
    
    # Y-axis (vertical line with arrow) - limit range
    y_range = min(y_range, 300)  # Limit to reasonable size
    y_axis_points = [[0, 0], [0, -y_range * 2]]
    y_start = clamp_coordinate(origin_y - y_range, 50, 1950)
    y_axis = create_line_element(
        y_axis_points, origin_x, y_start, 0, y_range * 2,
        stroke_color=stroke_color, stroke_width=stroke_width, closed=False
    )
    # Add arrowhead at the end
    y_axis["endArrowhead"] = "arrow"
    elements.append(y_axis)
    
    return elements


def function_to_points(
    func: Callable, x_min: float, x_max: float, num_points: int = 100,
    y_scale: float = 1.0, y_offset: float = 0.0
) -> List[Point]:
    """
    Convert a function to a list of SymPy Points for plotting.
    Reuses Point creation. Coordinates are clamped to safe ranges.
    """
    points = []
    step = (x_max - x_min) / (num_points - 1)
    
    for i in range(num_points):
        x = x_min + i * step
        try:
            y = func(x) * y_scale + y_offset
            # Clamp coordinates to safe ranges
            x = clamp_coordinate(x, -5000, 5000)
            y = clamp_coordinate(y, -5000, 5000)
            points.append(Point(x, y))
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
    
    return points


def sympy_function_to_excalidraw(
    func_expr, x_min: float, x_max: float,
    origin_x: float = 400, origin_y: float = 400,
    x_scale: float = 1.0, y_scale: float = 1.0,
    num_points: int = 100,
    stroke_color: str = "#1e1e1e",
    stroke_width: int = 2,
    **kwargs
) -> Dict[str, Any]:
    """
    Convert a SymPy function expression to Excalidraw line element.
    Reuses sympy_polygon_to_excalidraw for the curve.
    Coordinates are normalized to safe ranges.
    """
    x = symbols('x')
    
    # Limit input range to reasonable values
    x_min = clamp_coordinate(x_min, -500, 500)
    x_max = clamp_coordinate(x_max, -500, 500)
    origin_x = clamp_coordinate(origin_x, 200, 1800)
    origin_y = clamp_coordinate(origin_y, 200, 1800)
    
    # Convert SymPy expression to a callable function
    try:
        func = lambdify(x, func_expr, 'numpy')
    except:
        # Fallback for simple expressions
        func = lambda x_val: float(func_expr.subs(x, x_val))
    
    # Generate points with proper coordinate transformation
    # Transform: math x -> Excalidraw x, math y -> Excalidraw y (flipped)
    points_list = []
    step = (x_max - x_min) / (num_points - 1) if num_points > 1 else 1
    
    for i in range(num_points):
        math_x = x_min + i * step
        try:
            math_y = func(math_x)
            # Transform to Excalidraw coordinates
            excal_x = origin_x + (math_x * x_scale)
            excal_y = origin_y - (math_y * y_scale)  # Flip y-axis
            # Clamp to safe ranges
            excal_x = clamp_coordinate(excal_x, 50, 1950)
            excal_y = clamp_coordinate(excal_y, 50, 1950)
            points_list.append(Point(excal_x, excal_y))
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
    
    if len(points_list) < 2:
        raise ValueError("Not enough points to create a line")
    
    # Create polygon from points
    curve_polygon = Polygon(*points_list)
    
    # Extract background_color if provided
    background_color = kwargs.pop('background_color', "transparent")
    stroke_color = kwargs.pop('stroke_color', stroke_color)
    stroke_width = kwargs.pop('stroke_width', stroke_width)
    kwargs.pop('fill_style', None)
    
    # Convert to line element (not closed for function graphs)
    vertices = list(curve_polygon.vertices)
    coords = [(float(v.x), float(v.y)) for v in vertices]
    
    x_coords = [c[0] for c in coords]
    y_coords = [c[1] for c in coords]
    
    x0 = clamp_coordinate(min(x_coords), 50, 1950)
    y0 = clamp_coordinate(min(y_coords), 50, 1950)
    width = clamp_coordinate(max(x_coords) - x0, 0, 2000)
    height = clamp_coordinate(max(y_coords) - y0, 0, 2000)
    
    rel_points = [[float(c[0] - x0), float(c[1] - y0)] for c in coords]
    
    return create_line_element(rel_points, x0, y0, width, height, closed=False,
                              background_color=background_color,
                              stroke_color=stroke_color,
                              stroke_width=stroke_width)


def create_point_marker(
    x: float, y: float,
    size: float = 6.0,
    stroke_color: str = "#ff0000",
    background_color: str = "#ff0000",
    **kwargs
) -> Dict[str, Any]:
    """
    Create a point marker (small filled circle).
    Reuses create_ellipse_element. Coordinates are clamped.
    """
    x = clamp_coordinate(x, 50, 1950)
    y = clamp_coordinate(y, 50, 1950)
    size = min(size, 20)  # Limit size
    
    return create_ellipse_element(
        x - size/2, y - size/2, size, size,
        stroke_color=stroke_color,
        background_color=background_color,
        stroke_width=1,
        fill_style="solid",
        **kwargs
    )


def linear_equation_to_excalidraw(
    slope: float, intercept: float,
    x_min: float, x_max: float,
    origin_x: float = 400, origin_y: float = 400,
    x_scale: float = 1.0, y_scale: float = 1.0,
    stroke_color: str = "#1e1e1e",
    stroke_width: int = 2,
    **kwargs
) -> Dict[str, Any]:
    """
    Convert a linear equation (y = mx + b) to Excalidraw line.
    Reuses create_line_element. Coordinates are clamped to safe ranges.
    """
    # Limit input range
    x_min = clamp_coordinate(x_min, -200, 200)
    x_max = clamp_coordinate(x_max, -200, 200)
    origin_x = clamp_coordinate(origin_x, 200, 1800)
    origin_y = clamp_coordinate(origin_y, 200, 1800)
    
    # Calculate two points on the line (in math coordinates)
    y1 = slope * x_min + intercept
    y2 = slope * x_max + intercept
    
    # Transform to Excalidraw coordinates
    x1_transformed = origin_x + (x_min * x_scale)
    y1_transformed = origin_y - (y1 * y_scale)  # Flip y-axis
    x2_transformed = origin_x + (x_max * x_scale)
    y2_transformed = origin_y - (y2 * y_scale)  # Flip y-axis
    
    # Clamp coordinates
    x1_transformed = clamp_coordinate(x1_transformed, 50, 1950)
    y1_transformed = clamp_coordinate(y1_transformed, 50, 1950)
    x2_transformed = clamp_coordinate(x2_transformed, 50, 1950)
    y2_transformed = clamp_coordinate(y2_transformed, 50, 1950)
    
    # Create line element
    dx = x2_transformed - x1_transformed
    dy = y2_transformed - y1_transformed
    points = [[0, 0], [dx, dy]]
    
    width = clamp_coordinate(abs(dx), 0, 2000)
    height = clamp_coordinate(abs(dy), 0, 2000)
    
    background_color = kwargs.pop('background_color', "transparent")
    stroke_color = kwargs.pop('stroke_color', stroke_color)
    stroke_width = kwargs.pop('stroke_width', stroke_width)
    kwargs.pop('fill_style', None)
    
    return create_line_element(points, x1_transformed, y1_transformed,
                              width, height,
                              closed=False, background_color=background_color,
                              stroke_color=stroke_color, stroke_width=stroke_width)


def quadratic_equation_to_excalidraw(
    a: float, b: float, c: float,
    x_min: float, x_max: float,
    origin_x: float = 400, origin_y: float = 400,
    x_scale: float = 1.0, y_scale: float = 1.0,
    num_points: int = 100,
    stroke_color: str = "#1e1e1e",
    stroke_width: int = 2,
    **kwargs
) -> Dict[str, Any]:
    """
    Convert a quadratic equation (y = ax² + bx + c) to Excalidraw curve.
    Reuses sympy_function_to_excalidraw.
    """
    x = symbols('x')
    func_expr = a * x**2 + b * x + c
    
    return sympy_function_to_excalidraw(
        func_expr, x_min, x_max, origin_x, origin_y,
        x_scale, y_scale, num_points, stroke_color, stroke_width, **kwargs
    )


def create_excalidraw_scene(elements: List[Dict[str, Any]], app_state: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Create a complete Excalidraw scene JSON compatible with whiteboard.
    Returns format: {"elements": [...], "appState": {...}}
    This matches the exact format used by the whiteboard component.
    """
    if app_state is None:
        app_state = get_default_app_state()
    
    # Match the exact format from working JSON files
    return {
        "elements": elements,
        "appState": app_state
    }


def generate_algebra_examples() -> Dict[str, Any]:
    """
    Generate common algebra visualizations using SymPy.
    Reuses existing conversion functions to avoid redundant code.
    Uses safe coordinate ranges to avoid Excalidraw size limits.
    """
    elements = []
    
    # Coordinate system setup - use safe ranges
    origin_x, origin_y = 600, 500
    x_scale, y_scale = 0.5, 0.5  # Smaller scale for safety
    
    # 1. Coordinate axes - smaller range
    axes = create_coordinate_axes(origin_x, origin_y, 150, 150, "#666666", 1)
    elements.extend(axes)
    
    # 2. Linear equation: y = 2x + 1 - smaller range
    try:
        linear1 = linear_equation_to_excalidraw(
            slope=2, intercept=1,
            x_min=-100, x_max=100,
            origin_x=origin_x, origin_y=origin_y,
            x_scale=x_scale, y_scale=y_scale,
            stroke_color="#0066cc", stroke_width=2
        )
        elements.append(linear1)
    except Exception as e:
        print(f"Skipping linear1: {e}")
    
    # 3. Linear equation: y = -x + 3 - smaller range
    try:
        linear2 = linear_equation_to_excalidraw(
            slope=-1, intercept=3,
            x_min=-100, x_max=100,
            origin_x=origin_x, origin_y=origin_y,
            x_scale=x_scale, y_scale=y_scale,
            stroke_color="#cc6600", stroke_width=2
        )
        elements.append(linear2)
    except Exception as e:
        print(f"Skipping linear2: {e}")
    
    # 4. Quadratic equation: y = x² - 4 - smaller range
    try:
        quadratic1 = quadratic_equation_to_excalidraw(
            a=1, b=0, c=-4,
            x_min=-80, x_max=80,
            origin_x=origin_x, origin_y=origin_y,
            x_scale=x_scale, y_scale=y_scale,
            num_points=80,
            stroke_color="#009900", stroke_width=2
        )
        elements.append(quadratic1)
    except Exception as e:
        print(f"Skipping quadratic1: {e}")
    
    # 5. Quadratic equation: y = -0.5x² + 2x - smaller range
    try:
        quadratic2 = quadratic_equation_to_excalidraw(
            a=-0.5, b=2, c=0,
            x_min=-80, x_max=80,
            origin_x=origin_x, origin_y=origin_y,
            x_scale=x_scale, y_scale=y_scale,
            num_points=80,
            stroke_color="#990099", stroke_width=2
        )
        elements.append(quadratic2)
    except Exception as e:
        print(f"Skipping quadratic2: {e}")
    
    # 6. Point at (0, 1) - solution to y = 2x + 1
    try:
        point1 = create_point_marker(
            origin_x, origin_y - y_scale * 1,
            size=8, stroke_color="#ff0000", background_color="#ff0000"
        )
        elements.append(point1)
    except Exception as e:
        print(f"Skipping point1: {e}")
    
    # 7. Point at (2, 5) - on line y = 2x + 1
    try:
        point2 = create_point_marker(
            origin_x + x_scale * 2, origin_y - y_scale * 5,
            size=8, stroke_color="#ff6600", background_color="#ff6600"
        )
        elements.append(point2)
    except Exception as e:
        print(f"Skipping point2: {e}")
    
    # 8. Exponential function: y = 2^x - very small range
    x = symbols('x')
    exp_func = 2**x
    try:
        exponential = sympy_function_to_excalidraw(
            exp_func, x_min=-50, x_max=30,
            origin_x=origin_x, origin_y=origin_y,
            x_scale=x_scale, y_scale=y_scale * 0.05,  # Very small scale
            num_points=60,
            stroke_color="#cc0066", stroke_width=2
        )
        elements.append(exponential)
    except Exception as e:
        print(f"Skipping exponential: {e}")
    
    # 9. Sine function: y = sin(x) - smaller range
    x = symbols('x')
    sin_func = sin(x)
    try:
        sine = sympy_function_to_excalidraw(
            sin_func, x_min=-100, x_max=100,
            origin_x=origin_x, origin_y=origin_y,
            x_scale=x_scale * 2, y_scale=y_scale * 20,  # Adjusted scale
            num_points=100,
            stroke_color="#0066cc", stroke_width=2
        )
        elements.append(sine)
    except Exception as e:
        print(f"Skipping sine: {e}")
    
    # 10. Polynomial: y = x³ - 3x - smaller range
    x = symbols('x')
    poly_func = x**3 - 3*x
    try:
        polynomial = sympy_function_to_excalidraw(
            poly_func, x_min=-60, x_max=60,
            origin_x=origin_x, origin_y=origin_y,
            x_scale=x_scale, y_scale=y_scale * 0.05,
            num_points=80,
            stroke_color="#009999", stroke_width=2
        )
        elements.append(polynomial)
    except Exception as e:
        print(f"Skipping polynomial: {e}")
    
    # Create the complete Excalidraw scene
    scene = create_excalidraw_scene(elements)
    
    return scene


def generate_common_shapes() -> Dict[str, Any]:
    """
    Generate common shapes using SymPy and convert them to Excalidraw JSON format.
    Returns a complete Excalidraw scene with multiple shapes.
    """
    elements = []
    
    # 1. Rectangle (using SymPy Polygon)
    rect = Polygon(Point(100, 100), Point(300, 100), Point(300, 250), Point(100, 250))
    elements.append(sympy_rectangle_to_excalidraw(
        rect,
        stroke_color="#1e1e1e",
        background_color="transparent",
        stroke_width=2
    ))
    
    # 2. Square (using SymPy Polygon with equal sides)
    square = Polygon(Point(350, 100), Point(500, 100), Point(500, 250), Point(350, 250))
    elements.append(sympy_rectangle_to_excalidraw(
        square,
        stroke_color="#1e1e1e",
        background_color="#e7f5ff",
        stroke_width=2,
        fill_style="solid"
    ))
    
    # 3. Circle (using SymPy Circle)
    circle = Circle(Point(150, 350), 75)
    elements.append(sympy_circle_to_excalidraw(
        circle,
        stroke_color="#1e1e1e",
        background_color="#fff3bf",
        stroke_width=2,
        fill_style="solid"
    ))
    
    # 4. Triangle (using SymPy Triangle)
    triangle = Triangle(Point(300, 350), Point(450, 350), Point(375, 450))
    elements.append(sympy_triangle_to_excalidraw(
        triangle,
        stroke_color="#1e1e1e",
        stroke_width=2
    ))
    
    # 5. Regular Pentagon (using SymPy RegularPolygon)
    pentagon = RegularPolygon(Point(550, 200), 5, 80)
    elements.append(sympy_regular_polygon_to_excalidraw(
        pentagon,
        stroke_color="#1e1e1e",
        background_color="#d0f0c0",
        stroke_width=2,
        fill_style="solid"
    ))
    
    # 6. Regular Hexagon (using SymPy RegularPolygon)
    hexagon = RegularPolygon(Point(550, 400), 6, 80)
    elements.append(sympy_regular_polygon_to_excalidraw(
        hexagon,
        stroke_color="#1e1e1e",
        background_color="#ffe0e0",
        stroke_width=2,
        fill_style="solid"
    ))
    
    # 7. Custom Polygon (using SymPy Polygon)
    custom_poly = Polygon(Point(100, 500), Point(200, 550), Point(250, 600), 
                          Point(200, 650), Point(100, 650), Point(50, 600))
    elements.append(sympy_polygon_to_excalidraw(
        custom_poly,
        stroke_color="#1e1e1e",
        stroke_width=2
    ))
    
    # 8. Diamond (using SymPy Polygon for diamond shape)
    diamond = Polygon(Point(350, 500), Point(400, 550), Point(350, 600), Point(300, 550))
    elements.append(sympy_polygon_to_excalidraw(
        diamond,
        stroke_color="#1e1e1e",
        background_color="#f0e6ff",
        stroke_width=2,
        fill_style="solid"
    ))
    
    # 9. Ellipse (using SymPy Circle with different radius, then we'll adjust)
    # For a true ellipse, we'll use a polygon approximation
    ellipse_center = Point(550, 600)
    ellipse_points = []
    a, b = 100, 60  # semi-major and semi-minor axes
    for i in range(32):  # 32 points for smooth ellipse
        angle = 2 * math.pi * i / 32
        x = float(ellipse_center.x) + a * math.cos(angle)
        y = float(ellipse_center.y) + b * math.sin(angle)
        ellipse_points.append(Point(x, y))
    ellipse = Polygon(*ellipse_points)
    elements.append(sympy_polygon_to_excalidraw(
        ellipse,
        stroke_color="#1e1e1e",
        background_color="#fff9e6",
        stroke_width=2,
        fill_style="solid"
    ))
    
    # 10. Right Triangle (using SymPy Triangle)
    right_triangle = Triangle(Point(100, 700), Point(250, 700), Point(100, 800))
    elements.append(sympy_triangle_to_excalidraw(
        right_triangle,
        stroke_color="#1e1e1e",
        background_color="#e6f3ff",
        stroke_width=2,
        fill_style="solid"
    ))
    
    # Create the complete Excalidraw scene
    scene = create_excalidraw_scene(elements)
    
    return scene


def validate_excalidraw_json(scene: Dict[str, Any]) -> bool:
    """Validate that the JSON structure matches whiteboard requirements"""
    errors = []
    
    # Check top-level structure
    if "elements" not in scene:
        errors.append("Missing 'elements' key")
    if "appState" not in scene:
        errors.append("Missing 'appState' key")
    
    if "elements" in scene:
        if not isinstance(scene["elements"], list):
            errors.append("'elements' must be a list")
        else:
            # Validate each element
            for i, elem in enumerate(scene["elements"]):
                if not isinstance(elem, dict):
                    errors.append(f"Element {i} is not a dictionary")
                    continue
                
                # Required fields for all elements
                required_fields = ["id", "type", "x", "y", "width", "height"]
                for field in required_fields:
                    if field not in elem:
                        errors.append(f"Element {i} missing required field: {field}")
                
                # Type-specific validations
                if elem.get("type") == "line":
                    if "points" not in elem:
                        errors.append(f"Element {i} (line) missing 'points' field")
                    if not isinstance(elem.get("points"), list):
                        errors.append(f"Element {i} (line) 'points' must be a list")
                
                # Check data types
                if "id" in elem and not isinstance(elem["id"], str):
                    errors.append(f"Element {i} 'id' must be a string")
                if "type" in elem and not isinstance(elem["type"], str):
                    errors.append(f"Element {i} 'type' must be a string")
    
    if errors:
        print("Validation errors found:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True


def save_to_json(scene: Dict[str, Any], filename: str = "excalidraw_shapes.json"):
    """Save Excalidraw scene to JSON file"""
    # Validate before saving
    if not validate_excalidraw_json(scene):
        print("⚠ Warning: JSON validation failed, but saving anyway...")
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(scene, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved Excalidraw scene to {filename}")
    print(f"  Total elements: {len(scene['elements'])}")


def print_json_output(scene: Dict[str, Any]):
    """Print the JSON in a format that can be easily copied"""
    print("\n" + "=" * 80)
    print("EXCALIDRAW JSON OUTPUT (Copy the JSON below):")
    print("=" * 80)
    json_str = json.dumps(scene, indent=2, ensure_ascii=False)
    print(json_str)
    print("=" * 80)
    print(f"Total elements: {len(scene['elements'])}")
    print("=" * 80)


def main(include_algebra: bool = True, include_shapes: bool = True):
    """
    Main function to generate shapes and algebra examples.
    
    Args:
        include_algebra: If True, include algebra visualizations
        include_shapes: If True, include geometric shapes
    """
    all_elements = []
    
    if include_shapes:
        print("Generating common shapes using SymPy...")
        print("-" * 50)
        shapes_scene = generate_common_shapes()
        all_elements.extend(shapes_scene['elements'])
        print(f"Generated {len(shapes_scene['elements'])} geometric shapes")
    
    if include_algebra:
        print("\nGenerating algebra visualizations using SymPy...")
        print("-" * 50)
        algebra_scene = generate_algebra_examples()
        all_elements.extend(algebra_scene['elements'])
        print(f"Generated {len(algebra_scene['elements'])} algebra elements")
    
    # Create combined scene
    scene = create_excalidraw_scene(all_elements)
    
    # Print summary
    print(f"\nTotal elements generated: {len(scene['elements'])}")
    print("Element types:")
    type_counts = {}
    for elem in scene['elements']:
        elem_type = elem.get('type', 'unknown')
        type_counts[elem_type] = type_counts.get(elem_type, 0) + 1
    for elem_type, count in sorted(type_counts.items()):
        print(f"  - {elem_type}: {count}")
    
    # Validate JSON structure
    if validate_excalidraw_json(scene):
        print("✓ JSON structure validated successfully")
    else:
        print("⚠ Warning: JSON validation found issues")
    
    # Print the JSON output directly
    print_json_output(scene)
    
    # Also try to save to file (may not work in Colab)
    try:
        save_to_json(scene, "excalidraw_shapes.json")
    except Exception as e:
        print(f"Note: Could not save to file (this is OK in Colab): {e}")
    
    print("\n" + "=" * 50)
    print("To use this JSON in your whiteboard:")
    print("1. Copy the JSON output above")
    print("2. Use it with your whiteboard's updateScene API:")
    print("   excalidrawAPI.updateScene({")
    print("     elements: scene.elements,")
    print("     appState: scene.appState,")
    print("     commitToHistory: false")
    print("   })")
    print("=" * 50)
    
    return scene


if __name__ == "__main__":
    # Run the main function with both shapes and algebra
    # You can customize: main(include_algebra=True, include_shapes=False) for only algebra
    scene = main(include_algebra=True, include_shapes=True)
    
    # Also print JSON at the end for easy access
    print("\n" + "=" * 80)
    print("FINAL JSON OUTPUT (for easy copying):")
    print("=" * 80)
    print(json.dumps(scene, indent=2, ensure_ascii=False))
    print("=" * 80)
    
    # You can also access individual shapes programmatically:
    # Example: Get just the rectangle
    # rect = Polygon(Point(0, 0), Point(100, 0), Point(100, 50), Point(0, 50))
    # rect_element = sympy_rectangle_to_excalidraw(rect)
    # print(json.dumps(rect_element, indent=2))


# REVERSE CONVERSION: Excalidraw JSON -> SymPy Objects

def excalidraw_line_to_sympy(line_element: Dict[str, Any]) -> Optional[Line]:
    """
    Convert an Excalidraw line element back to a SymPy Line object.
    
    Args:
        line_element: Excalidraw line element from JSON
        
    Returns:
        SymPy Line object or None if conversion fails
    """
    if line_element.get("type") != "line":
        return None
    
    try:
        # Get starting position
        x0 = float(line_element.get("x", 0))
        y0 = float(line_element.get("y", 0))
        
        # Get points (relative to starting position)
        points = line_element.get("points", [])
        if len(points) < 2:
            return None
        
        # Calculate absolute end point
        # First point is always [0, 0] relative to start
        # Last point gives the relative end position
        end_point = points[-1]
        dx = float(end_point[0])
        dy = float(end_point[1])
        
        # Absolute coordinates
        x1 = x0 + dx
        y1 = y0 + dy
        
        # Check if points are distinct (SymPy requires two unique points)
        if abs(x1 - x0) < 1e-6 and abs(y1 - y0) < 1e-6:
            # Points are too close or identical, skip conversion
            return None
        
        # Create SymPy Line from two points
        p1 = Point(x0, y0)
        p2 = Point(x1, y1)
        
        return Line(p1, p2)
    except (ValueError, TypeError, KeyError) as e:
        print(f"Error converting line to SymPy: {e}")
        return None


def excalidraw_json_to_sympy_lines(excalidraw_json: Dict[str, Any]) -> List[Line]:
    """
    Extract all line elements from Excalidraw JSON and convert to SymPy Line objects.
    
    Args:
        excalidraw_json: Excalidraw JSON (can be full scene or just elements array)
        
    Returns:
        List of SymPy Line objects
    """
    lines = []
    
    # Handle both full scene format and elements-only format
    if "elements" in excalidraw_json:
        elements = excalidraw_json["elements"]
    elif isinstance(excalidraw_json, list):
        elements = excalidraw_json
    else:
        return lines
    
    for element in elements:
        if element.get("type") == "line":
            sympy_line = excalidraw_line_to_sympy(element)
            if sympy_line is not None:
                lines.append(sympy_line)
    
    return lines


def check_line_intersection(line1: Line, line2: Line) -> Dict[str, Any]:
    """
    Check if two SymPy Line objects intersect and find intersection point.
    
    Args:
        line1: First SymPy Line object
        line2: Second SymPy Line object
        
    Returns:
        Dictionary with:
        - 'intersect': bool - whether lines intersect
        - 'point': Point or None - intersection point if exists
        - 'parallel': bool - whether lines are parallel
        - 'coincident': bool - whether lines are coincident (same line)
    """
    try:
        # Check if lines are parallel
        if line1.is_parallel(line2):
            # Check if they are coincident (same line)
            if line1.contains(line2.p1) or line2.contains(line1.p1):
                return {
                    'intersect': True,
                    'point': None,  # Infinite points
                    'parallel': True,
                    'coincident': True,
                    'message': 'Lines are coincident (same line)'
                }
            else:
                return {
                    'intersect': False,
                    'point': None,
                    'parallel': True,
                    'coincident': False,
                    'message': 'Lines are parallel and do not intersect'
                }
        
        # Find intersection point
        intersection = line1.intersection(line2)
        
        if intersection:
            point = intersection[0]
            return {
                'intersect': True,
                'point': point,
                'parallel': False,
                'coincident': False,
                'message': f'Lines intersect at ({float(point.x):.2f}, {float(point.y):.2f})'
            }
        else:
            return {
                'intersect': False,
                'point': None,
                'parallel': False,
                'coincident': False,
                'message': 'Lines do not intersect'
            }
    except Exception as e:
        return {
            'intersect': False,
            'point': None,
            'parallel': False,
            'coincident': False,
            'error': str(e),
            'message': f'Error checking intersection: {e}'
        }


def analyze_excalidraw_intersections(excalidraw_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze all line intersections in an Excalidraw JSON.
    
    Args:
        excalidraw_json: Excalidraw JSON (can be full scene or just elements array)
        
    Returns:
        Dictionary with:
        - 'total_lines': number of lines found
        - 'intersections': list of intersection results
        - 'summary': summary statistics
    """
    # Convert to SymPy lines
    lines = excalidraw_json_to_sympy_lines(excalidraw_json)
    
    if len(lines) < 2:
        return {
            'total_lines': len(lines),
            'intersections': [],
            'summary': f'Not enough lines to check intersections (found {len(lines)} line(s))'
        }
    
    intersections = []
    intersection_count = 0
    parallel_count = 0
    coincident_count = 0
    
    # Check all pairs of lines
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            result = check_line_intersection(lines[i], lines[j])
            result['line1_index'] = i
            result['line2_index'] = j
            intersections.append(result)
            
            if result['intersect']:
                intersection_count += 1
            if result['parallel']:
                parallel_count += 1
            if result.get('coincident'):
                coincident_count += 1
    
    return {
        'total_lines': len(lines),
        'total_pairs': len(intersections),
        'intersections': intersections,
        'summary': {
            'intersecting_pairs': intersection_count,
            'parallel_pairs': parallel_count,
            'coincident_pairs': coincident_count,
            'non_intersecting_pairs': len(intersections) - intersection_count
        }
    }


def find_line_intersections_from_json(json_file_path: str = None, json_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Main function to load Excalidraw JSON and find all line intersections.
    
    Args:
        json_file_path: Path to Excalidraw JSON file (optional)
        json_data: Excalidraw JSON data as dictionary (optional)
        
    Returns:
        Analysis results dictionary
        
    Example:
        # From file:
        result = find_line_intersections_from_json("excalidraw.json")
        
        # From data:
        with open("excalidraw.json") as f:
            data = json.load(f)
        result = find_line_intersections_from_json(json_data=data)
    """
    if json_data is None:
        if json_file_path is None:
            raise ValueError("Either json_file_path or json_data must be provided")
        
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    
    return analyze_excalidraw_intersections(json_data)

def excalidraw_rectangle_to_sympy(rect_element: Dict[str, Any]) -> Optional[Polygon]:
    """Convert Excalidraw rectangle to SymPy Polygon."""
    if rect_element.get("type") != "rectangle":
        return None
    try:
        x = float(rect_element.get("x", 0))
        y = float(rect_element.get("y", 0))
        w = float(rect_element.get("width", 0))
        h = float(rect_element.get("height", 0))
        
        p1 = Point(x, y)
        p2 = Point(x + w, y)
        p3 = Point(x + w, y + h)
        p4 = Point(x, y + h)
        
        return Polygon(p1, p2, p3, p4)
    except Exception as e:
        print(f"Error converting rectangle: {e}")
        return None


def excalidraw_ellipse_to_sympy(ellipse_element: Dict[str, Any]) -> Optional[Circle]:
    """Convert Excalidraw ellipse to SymPy Circle (if it's actually a circle)."""
    if ellipse_element.get("type") != "ellipse":
        return None
    try:
        x = float(ellipse_element.get("x", 0))
        y = float(ellipse_element.get("y", 0))
        w = float(ellipse_element.get("width", 0))
        h = float(ellipse_element.get("height", 0))
        
        # Check if it's actually a circle (width == height)
        if abs(w - h) < 0.01:
            center_x = x + w / 2
            center_y = y + h / 2
            radius = w / 2
            return Circle(Point(center_x, center_y), radius)
        return None
    except Exception as e:
        print(f"Error converting ellipse: {e}")
        return None


def excalidraw_polygon_to_sympy(poly_element: Dict[str, Any]) -> Optional[Polygon]:
    """Convert Excalidraw polygon/line to SymPy Polygon."""
    if poly_element.get("type") != "line":
        return None
    try:
        x0 = float(poly_element.get("x", 0))
        y0 = float(poly_element.get("y", 0))
        points = poly_element.get("points", [])
        
        if len(points) < 3:
            return None
        
        # Convert relative points to absolute
        abs_points = []
        for rel_point in points:
            if len(rel_point) >= 2:
                px = x0 + float(rel_point[0])
                py = y0 + float(rel_point[1])
                abs_points.append(Point(px, py))
        
        if len(abs_points) < 3:
            return None
        
        return Polygon(*abs_points)
    except Exception as e:
        print(f"Error converting polygon: {e}")
        return None


def calculate_distance(point1: Point, point2: Point) -> float:
    """Calculate distance between two points."""
    return float(point1.distance(point2))


def calculate_line_length(line: Line) -> float:
    """Calculate length of a line segment."""
    return float(line.length)


def calculate_angle_between_lines(line1: Line, line2: Line) -> Dict[str, Any]:
    """Calculate angle between two lines in degrees."""
    try:
        angle_rad = float(line1.angle_between(line2))
        angle_deg = math.degrees(angle_rad)
        
        # Check if perpendicular (90 degrees)
        is_perpendicular = abs(angle_deg - 90) < 0.1 or abs(angle_deg - 270) < 0.1
        
        return {
            'angle_radians': angle_rad,
            'angle_degrees': angle_deg,
            'is_perpendicular': is_perpendicular,
            'is_parallel': line1.is_parallel(line2)
        }
    except Exception as e:
        return {'error': str(e)}


def check_point_on_line(point: Point, line: Line, tolerance: float = 0.1) -> bool:
    """Check if a point lies on a line (within tolerance)."""
    try:
        return line.distance(point) < tolerance
    except:
        return False


def check_point_in_polygon(point: Point, polygon: Polygon) -> bool:
    """Check if a point is inside a polygon."""
    try:
        return polygon.encloses_point(point)
    except:
        return False


def calculate_polygon_area(polygon: Polygon) -> float:
    """Calculate area of a polygon."""
    try:
        return float(polygon.area)
    except:
        return 0.0


def calculate_polygon_perimeter(polygon: Polygon) -> float:
    """Calculate perimeter of a polygon."""
    try:
        return float(polygon.perimeter)
    except:
        return 0.0


def detect_rectangle(polygon: Polygon, tolerance: float = 0.1) -> Dict[str, Any]:
    """Detect if a polygon is a rectangle and return properties."""
    try:
        if len(polygon.vertices) != 4:
            return {'is_rectangle': False, 'message': 'Not a quadrilateral'}
        
        # Check if opposite sides are parallel and equal
        vertices = list(polygon.vertices)
        sides = []
        for i in range(4):
            side = Segment(vertices[i], vertices[(i + 1) % 4])
            sides.append(side)
        
        # Check if opposite sides are parallel
        parallel1 = sides[0].is_parallel(sides[2])
        parallel2 = sides[1].is_parallel(sides[3])
        
        if parallel1 and parallel2:
            # Check if adjacent sides are perpendicular
            perp1 = sides[0].is_perpendicular(sides[1])
            
            # Check if it's a square (all sides equal)
            lengths = [float(s.length) for s in sides]
            is_square = all(abs(l - lengths[0]) < tolerance for l in lengths) and perp1
            
            area = calculate_polygon_area(polygon)
            perimeter = calculate_polygon_perimeter(polygon)
            
            return {
                'is_rectangle': True,
                'is_square': is_square,
                'area': area,
                'perimeter': perimeter,
                'side_lengths': lengths,
                'diagonal': float(vertices[0].distance(vertices[2]))
            }
        
        return {'is_rectangle': False, 'message': 'Opposite sides not parallel'}
    except Exception as e:
        return {'is_rectangle': False, 'error': str(e)}


def detect_triangle(polygon: Polygon) -> Dict[str, Any]:
    """Detect if a polygon is a triangle and return properties."""
    try:
        if len(polygon.vertices) != 3:
            return {'is_triangle': False, 'message': 'Not a triangle'}
        
        vertices = list(polygon.vertices)
        triangle = Triangle(*vertices)
        
        # Calculate properties
        area = float(triangle.area)
        perimeter = float(triangle.perimeter)
        
        # Get side lengths
        sides = [float(vertices[i].distance(vertices[(i + 1) % 3])) for i in range(3)]
        
        # Determine triangle type
        sides_sorted = sorted(sides)
        is_equilateral = all(abs(s - sides[0]) < 0.1 for s in sides)
        is_isosceles = (abs(sides[0] - sides[1]) < 0.1 or 
                       abs(sides[1] - sides[2]) < 0.1 or 
                       abs(sides[0] - sides[2]) < 0.1)
        
        # Check for right triangle (Pythagorean theorem)
        a, b, c = sides_sorted
        is_right = abs(a**2 + b**2 - c**2) < 0.1
        
        # Get angles
        angles = [float(triangle.angles[vertex]) for vertex in triangle.vertices]
        angles_deg = [math.degrees(a) for a in angles]
        
        return {
            'is_triangle': True,
            'area': area,
            'perimeter': perimeter,
            'side_lengths': sides,
            'angles_degrees': angles_deg,
            'is_equilateral': is_equilateral,
            'is_isosceles': is_isosceles,
            'is_right': is_right,
            'triangle_type': _classify_triangle(is_equilateral, is_isosceles, is_right)
        }
    except Exception as e:
        return {'is_triangle': False, 'error': str(e)}


def _classify_triangle(equilateral: bool, isosceles: bool, right: bool) -> str:
    """Classify triangle type."""
    if equilateral:
        return "equilateral"
    elif right and isosceles:
        return "right isosceles"
    elif right:
        return "right"
    elif isosceles:
        return "isosceles"
    else:
        return "scalene"


def calculate_circle_properties(circle: Circle) -> Dict[str, Any]:
    """Calculate circle properties."""
    try:
        radius = float(circle.radius)
        center = circle.center
        
        return {
            'center': (float(center.x), float(center.y)),
            'radius': radius,
            'diameter': 2 * radius,
            'area': float(circle.area),
            'circumference': float(circle.circumference)
        }
    except Exception as e:
        return {'error': str(e)}


def find_midpoint(point1: Point, point2: Point) -> Point:
    """Find midpoint between two points."""
    return Point((point1.x + point2.x) / 2, (point1.y + point2.y) / 2)


def calculate_slope(line: Line) -> Optional[float]:
    """Calculate slope of a line (m in y = mx + b)."""
    try:
        p1, p2 = line.p1, line.p2
        dx = float(p2.x - p1.x)
        if abs(dx) < 0.0001:  # Vertical line
            return None
        return float((p2.y - p1.y) / dx)
    except:
        return None


def get_line_equation(line: Line) -> Dict[str, Any]:
    """Get equation of line in y = mx + b format."""
    try:
        slope = calculate_slope(line)
        if slope is None:
            # Vertical line: x = c
            x_intercept = float(line.p1.x)
            return {
                'form': 'vertical',
                'equation': f'x = {x_intercept:.2f}',
                'x_intercept': x_intercept
            }
        
        # Calculate y-intercept
        p1 = line.p1
        y_intercept = float(p1.y - slope * p1.x)
        
        return {
            'form': 'slope_intercept',
            'slope': slope,
            'y_intercept': y_intercept,
            'equation': f'y = {slope:.2f}x + {y_intercept:.2f}' if y_intercept >= 0 else f'y = {slope:.2f}x - {abs(y_intercept):.2f}'
        }
    except Exception as e:
        return {'error': str(e)}


def find_shape_intersections(
    excalidraw_json: Dict[str, Any],
    shape_id: str = None,
    shape_index: int = None,
    shape_type: str = None
) -> Dict[str, Any]:
    """
    Find all intersections for a specific shape in the whiteboard.
    
    Args:
        excalidraw_json: Excalidraw JSON data
        shape_id: ID of the shape to check (from element['id'])
        shape_index: Index of the shape in elements array (alternative to shape_id)
        shape_type: Type of shape to check ('line', 'rectangle', 'ellipse', etc.)
        
    Returns:
        Dictionary with intersection results for the specified shape
        
    Example:
        # Find intersections for a shape by ID
        result = find_shape_intersections(json_data, shape_id="abc123")
        
        # Find intersections for first rectangle
        result = find_shape_intersections(json_data, shape_type="rectangle", shape_index=0)
    """
    # Get elements
    if "elements" in excalidraw_json:
        elements = excalidraw_json["elements"]
    elif isinstance(excalidraw_json, list):
        elements = excalidraw_json
    else:
        return {'error': 'Invalid JSON format'}
    
    # Find the target shape
    target_element = None
    target_index = None
    
    if shape_id:
        for i, elem in enumerate(elements):
            if elem.get("id") == shape_id:
                target_element = elem
                target_index = i
                break
    elif shape_index is not None:
        if 0 <= shape_index < len(elements):
            target_element = elements[shape_index]
            target_index = shape_index
    elif shape_type:
        for i, elem in enumerate(elements):
            if elem.get("type") == shape_type:
                target_element = elem
                target_index = i
                break
    
    if not target_element:
        return {'error': 'Shape not found', 'shape_id': shape_id, 'shape_index': shape_index}
    
    target_type = target_element.get("type")
    results = {
        'target_shape': {
            'id': target_element.get("id"),
            'type': target_type,
            'index': target_index
        },
        'intersections': [],
        'summary': {
            'total_intersections': 0,
            'intersecting_shapes': []
        }
    }
    
    # Convert target shape to SymPy
    target_sympy = None
    if target_type == "line":
        target_sympy = excalidraw_line_to_sympy(target_element)
    elif target_type == "rectangle":
        target_sympy = excalidraw_rectangle_to_sympy(target_element)
    elif target_type == "ellipse":
        target_sympy = excalidraw_ellipse_to_sympy(target_element)
    
    if not target_sympy:
        return {'error': f'Could not convert shape type {target_type} to SymPy'}
    
    # Check intersections with all other shapes
    for i, other_element in enumerate(elements):
        if i == target_index:
            continue
        
        other_type = other_element.get("type")
        intersection_result = None
        
        # Convert other shape to SymPy
        other_sympy = None
        if other_type == "line":
            other_sympy = excalidraw_line_to_sympy(other_element)
        elif other_type == "rectangle":
            other_sympy = excalidraw_rectangle_to_sympy(other_element)
        elif other_type == "ellipse":
            other_sympy = excalidraw_ellipse_to_sympy(other_element)
        
        if not other_sympy:
            continue
        
        # Check intersection based on shape types
        if target_type == "line" and other_type == "line":
            intersection_result = check_line_intersection(target_sympy, other_sympy)
        
        elif target_type == "line" and other_type == "rectangle":
            intersection_result = check_line_polygon_intersection(target_sympy, other_sympy)
        
        elif target_type == "line" and other_type == "ellipse":
            intersection_result = check_line_circle_intersection(target_sympy, other_sympy)
        
        elif target_type == "rectangle" and other_type == "line":
            intersection_result = check_line_polygon_intersection(other_sympy, target_sympy)
        
        elif target_type == "rectangle" and other_type == "rectangle":
            intersection_result = check_polygon_polygon_intersection(target_sympy, other_sympy)
        
        elif target_type == "rectangle" and other_type == "ellipse":
            intersection_result = check_polygon_circle_intersection(target_sympy, other_sympy)
        
        elif target_type == "ellipse" and other_type == "line":
            intersection_result = check_line_circle_intersection(other_sympy, target_sympy)
        
        elif target_type == "ellipse" and other_type == "rectangle":
            intersection_result = check_polygon_circle_intersection(other_sympy, target_sympy)
        
        elif target_type == "ellipse" and other_type == "ellipse":
            intersection_result = check_circle_circle_intersection(target_sympy, other_sympy)
        
        if intersection_result:
            intersection_result['other_shape'] = {
                'id': other_element.get("id"),
                'type': other_type,
                'index': i
            }
            results['intersections'].append(intersection_result)
            
            if intersection_result.get('intersect'):
                results['summary']['total_intersections'] += 1
                results['summary']['intersecting_shapes'].append({
                    'id': other_element.get("id"),
                    'type': other_type,
                    'index': i
                })
    
    return results


def check_line_polygon_intersection(line: Line, polygon: Polygon) -> Dict[str, Any]:
    """Check if a line intersects with a polygon (rectangle or any polygon)."""
    try:
        # Get polygon edges
        vertices = list(polygon.vertices)
        intersections = []
        
        # Check intersection with each edge
        for i in range(len(vertices)):
            edge = Segment(vertices[i], vertices[(i + 1) % len(vertices)])
            edge_line = Line(edge.p1, edge.p2)
            
            line_intersection = check_line_intersection(line, edge_line)
            if line_intersection.get('intersect') and line_intersection.get('point'):
                point = line_intersection['point']
                # Check if point is on the edge segment
                if edge.contains(point):
                    intersections.append(point)
        
        # Also check if line endpoints are inside polygon
        p1_inside = check_point_in_polygon(line.p1, polygon)
        p2_inside = check_point_in_polygon(line.p2, polygon)
        
        has_intersection = len(intersections) > 0 or p1_inside or p2_inside
        
        return {
            'intersect': has_intersection,
            'points': intersections,
            'point_count': len(intersections),
            'line_start_inside': p1_inside,
            'line_end_inside': p2_inside,
            'message': f'Line intersects polygon at {len(intersections)} point(s)' if has_intersection else 'Line does not intersect polygon'
        }
    except Exception as e:
        return {'intersect': False, 'error': str(e), 'message': f'Error checking intersection: {e}'}


def check_line_circle_intersection(line: Line, circle: Circle) -> Dict[str, Any]:
    """Check if a line intersects with a circle."""
    try:
        intersections = circle.intersection(line)
        
        if intersections:
            points = [Point(p.x, p.y) if not isinstance(p, Point) else p for p in intersections]
            return {
                'intersect': True,
                'points': points,
                'point_count': len(points),
                'message': f'Line intersects circle at {len(points)} point(s)',
                'tangent': len(points) == 1  # Tangent if one intersection
            }
        else:
            # Check distance from center to line
            center = circle.center
            distance = line.distance(center)
            radius = float(circle.radius)
            
            if abs(distance - radius) < 0.01:
                return {
                    'intersect': True,
                    'points': [],
                    'point_count': 1,
                    'tangent': True,
                    'message': 'Line is tangent to circle'
                }
            
            return {
                'intersect': False,
                'points': [],
                'point_count': 0,
                'distance_from_center': float(distance),
                'radius': radius,
                'message': 'Line does not intersect circle'
            }
    except Exception as e:
        return {'intersect': False, 'error': str(e), 'message': f'Error checking intersection: {e}'}


def check_polygon_polygon_intersection(poly1: Polygon, poly2: Polygon) -> Dict[str, Any]:
    """Check if two polygons intersect."""
    try:
        # Check if any vertex of poly1 is inside poly2
        vertices1_inside = [check_point_in_polygon(v, poly2) for v in poly1.vertices]
        vertices2_inside = [check_point_in_polygon(v, poly1) for v in poly2.vertices]
        
        # Check edge intersections
        edge_intersections = []
        vertices1 = list(poly1.vertices)
        vertices2 = list(poly2.vertices)
        
        for i in range(len(vertices1)):
            edge1 = Segment(vertices1[i], vertices1[(i + 1) % len(vertices1)])
            edge1_line = Line(edge1.p1, edge1.p2)
            
            for j in range(len(vertices2)):
                edge2 = Segment(vertices2[j], vertices2[(j + 1) % len(vertices2)])
                edge2_line = Line(edge2.p1, edge2.p2)
                
                intersection = check_line_intersection(edge1_line, edge2_line)
                if intersection.get('intersect') and intersection.get('point'):
                    point = intersection['point']
                    if edge1.contains(point) and edge2.contains(point):
                        edge_intersections.append(point)
        
        has_intersection = (any(vertices1_inside) or any(vertices2_inside) or 
                           len(edge_intersections) > 0)
        
        return {
            'intersect': has_intersection,
            'poly1_vertices_inside_poly2': sum(vertices1_inside),
            'poly2_vertices_inside_poly1': sum(vertices2_inside),
            'edge_intersection_points': edge_intersections,
            'edge_intersection_count': len(edge_intersections),
            'overlap': any(vertices1_inside) and any(vertices2_inside),
            'message': 'Polygons intersect' if has_intersection else 'Polygons do not intersect'
        }
    except Exception as e:
        return {'intersect': False, 'error': str(e), 'message': f'Error checking intersection: {e}'}


def check_polygon_circle_intersection(polygon: Polygon, circle: Circle) -> Dict[str, Any]:
    """Check if a polygon intersects with a circle."""
    try:
        # Check if any vertex is inside circle
        vertices_inside = []
        center = circle.center
        radius = float(circle.radius)
        
        for vertex in polygon.vertices:
            dist = float(vertex.distance(center))
            if dist <= radius:
                vertices_inside.append(vertex)
        
        # Check if circle center is inside polygon
        center_inside = check_point_in_polygon(center, polygon)
        
        # Check edge intersections with circle
        edge_intersections = []
        vertices = list(polygon.vertices)
        
        for i in range(len(vertices)):
            edge = Segment(vertices[i], vertices[(i + 1) % len(vertices)])
            edge_line = Line(edge.p1, edge.p2)
            
            circle_intersection = check_line_circle_intersection(edge_line, circle)
            if circle_intersection.get('intersect') and circle_intersection.get('points'):
                for point in circle_intersection['points']:
                    if edge.contains(point):
                        edge_intersections.append(point)
        
        has_intersection = (len(vertices_inside) > 0 or center_inside or 
                           len(edge_intersections) > 0)
        
        return {
            'intersect': has_intersection,
            'vertices_inside_circle': len(vertices_inside),
            'circle_center_inside_polygon': center_inside,
            'edge_intersection_points': edge_intersections,
            'edge_intersection_count': len(edge_intersections),
            'message': 'Polygon intersects circle' if has_intersection else 'Polygon does not intersect circle'
        }
    except Exception as e:
        return {'intersect': False, 'error': str(e), 'message': f'Error checking intersection: {e}'}


def check_circle_circle_intersection(circle1: Circle, circle2: Circle) -> Dict[str, Any]:
    """Check if two circles intersect."""
    try:
        center1 = circle1.center
        center2 = circle2.center
        radius1 = float(circle1.radius)
        radius2 = float(circle2.radius)
        
        distance = float(center1.distance(center2))
        sum_radii = radius1 + radius2
        diff_radii = abs(radius1 - radius2)
        
        # Circles intersect if distance <= sum of radii and distance >= |r1 - r2|
        if distance > sum_radii:
            return {
                'intersect': False,
                'distance': distance,
                'sum_radii': sum_radii,
                'message': 'Circles are separate (no intersection)'
            }
        elif distance < diff_radii:
            return {
                'intersect': False,
                'distance': distance,
                'diff_radii': diff_radii,
                'message': 'One circle is inside the other (no intersection)'
            }
        elif abs(distance - sum_radii) < 0.01:
            return {
                'intersect': True,
                'points': 1,
                'tangent': True,
                'distance': distance,
                'message': 'Circles are tangent (touch at one point)'
            }
        elif abs(distance - diff_radii) < 0.01:
            return {
                'intersect': True,
                'points': 1,
                'tangent': True,
                'distance': distance,
                'message': 'Circles are internally tangent'
            }
        else:
            # Calculate intersection points
            intersections = circle1.intersection(circle2)
            return {
                'intersect': True,
                'points': len(intersections) if intersections else 2,
                'tangent': False,
                'distance': distance,
                'intersection_points': intersections if intersections else [],
                'message': f'Circles intersect at {len(intersections) if intersections else 2} point(s)'
            }
    except Exception as e:
        return {'intersect': False, 'error': str(e), 'message': f'Error checking intersection: {e}'}


def check_shape_intersections_simple(
    excalidraw_json: Dict[str, Any],
    shape_identifier: str = None
) -> Dict[str, Any]:
    """
    Simple function to check intersections for a shape.
    Can identify shape by ID, or will check first shape if no ID provided.
    
    Args:
        excalidraw_json: Excalidraw JSON from whiteboard
        shape_identifier: Shape ID (optional - if not provided, checks first shape)
        
    Returns:
        Dictionary with intersection results
        
    Example:
        # Check intersections for a specific shape by ID
        result = check_shape_intersections_simple(json_data, "abc123")
        
        # Check first shape in the whiteboard
        result = check_shape_intersections_simple(json_data)
    """
    if shape_identifier:
        return find_shape_intersections(excalidraw_json, shape_id=shape_identifier)
    else:
        # Check first shape
        return find_shape_intersections(excalidraw_json, shape_index=0)


def analyze_excalidraw_geometry(excalidraw_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive geometric analysis of Excalidraw JSON.
    Analyzes all shapes and their relationships.
    """
    results = {
        'lines': [],
        'rectangles': [],
        'circles': [],
        'polygons': [],
        'distances': [],
        'angles': [],
        'intersections': [],
        'summary': {}
    }
    
    # Handle both full scene format and elements-only format
    if "elements" in excalidraw_json:
        elements = excalidraw_json["elements"]
    elif isinstance(excalidraw_json, list):
        elements = excalidraw_json
    else:
        return results
    
    # Extract and convert shapes
    lines = []
    rectangles = []
    circles = []
    polygons = []
    
    for element in elements:
        elem_type = element.get("type")
        
        if elem_type == "line":
            line = excalidraw_line_to_sympy(element)
            if line:
                lines.append(line)
                # Also check if it's a closed polygon
                if element.get("polygon", False):
                    poly = excalidraw_polygon_to_sympy(element)
                    if poly:
                        polygons.append(poly)
        
        elif elem_type == "rectangle":
            rect = excalidraw_rectangle_to_sympy(element)
            if rect:
                rectangles.append(rect)
                polygons.append(rect)
        
        elif elem_type == "ellipse":
            circle = excalidraw_ellipse_to_sympy(element)
            if circle:
                circles.append(circle)
    
    # Analyze lines
    for i, line in enumerate(lines):
        line_info = {
            'index': i,
            'length': calculate_line_length(line),
            'equation': get_line_equation(line),
            'slope': calculate_slope(line)
        }
        results['lines'].append(line_info)
    
    # Analyze rectangles
    for i, rect in enumerate(rectangles):
        rect_info = detect_rectangle(rect)
        rect_info['index'] = i
        rect_info['area'] = calculate_polygon_area(rect)
        rect_info['perimeter'] = calculate_polygon_perimeter(rect)
        results['rectangles'].append(rect_info)
    
    # Analyze circles
    for i, circle in enumerate(circles):
        circle_info = calculate_circle_properties(circle)
        circle_info['index'] = i
        results['circles'].append(circle_info)
    
    # Analyze polygons (triangles, etc.)
    for i, poly in enumerate(polygons):
        if len(poly.vertices) == 3:
            tri_info = detect_triangle(poly)
            tri_info['index'] = i
            results['polygons'].append(tri_info)
        else:
            poly_info = {
                'index': i,
                'vertices': len(poly.vertices),
                'area': calculate_polygon_area(poly),
                'perimeter': calculate_polygon_perimeter(poly)
            }
            results['polygons'].append(poly_info)
    
    # Calculate angles between lines
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            angle_info = calculate_angle_between_lines(lines[i], lines[j])
            angle_info['line1_index'] = i
            angle_info['line2_index'] = j
            results['angles'].append(angle_info)
    
    # Find intersections
    intersection_results = analyze_excalidraw_intersections(excalidraw_json)
    results['intersections'] = intersection_results['intersections']
    
    # Summary
    results['summary'] = {
        'total_lines': len(lines),
        'total_rectangles': len(rectangles),
        'total_circles': len(circles),
        'total_polygons': len(polygons),
        'total_intersections': intersection_results['summary']['intersecting_pairs'],
        'parallel_lines': sum(1 for a in results['angles'] if a.get('is_parallel', False)),
        'perpendicular_lines': sum(1 for a in results['angles'] if a.get('is_perpendicular', False))
    }
    
    return results



def format_intersection_analysis_for_llm(intersection_result: Dict[str, Any]) -> str:
    """
    Format intersection analysis results in a way that's useful for LLM prompts.
    Returns a human-readable string describing the intersections.
    """
    if 'error' in intersection_result:
        return f"Error analyzing intersections: {intersection_result['error']}"
    
    if 'target_shape' in intersection_result:
        # Single shape analysis
        target = intersection_result['target_shape']
        summary = intersection_result.get('summary', {})
        total = summary.get('total_intersections', 0)
        
        if total == 0:
            return f"Shape {target['type']} (ID: {target['id'][:8]}...) has no intersections with other shapes."
        
        result_text = f"Shape {target['type']} (ID: {target['id'][:8]}...) intersects with {total} other shape(s):\n"
        
        for intersection in intersection_result.get('intersections', []):
            if intersection.get('intersect'):
                other = intersection.get('other_shape', {})
                result_text += f"  - {other.get('type')} (ID: {other.get('id', 'unknown')[:8]}...): {intersection.get('message', 'intersects')}\n"
                if intersection.get('points'):
                    points = intersection['points']
                    if isinstance(points, list) and len(points) > 0:
                        if isinstance(points[0], Point):
                            result_text += f"    Intersection points: {[(float(p.x), float(p.y)) for p in points[:3]]}\n"
                        else:
                            result_text += f"    Intersection points: {points[:3]}\n"
        
        return result_text
    else:
        # All shapes analysis
        summary = intersection_result.get('summary', {})
        total_lines = intersection_result.get('total_lines', 0)
        intersecting_pairs = summary.get('intersecting_pairs', 0)
        
        if total_lines < 2:
            return f"Not enough shapes to check intersections (found {total_lines} line(s))."
        
        result_text = f"Whiteboard Analysis: {total_lines} lines found, {intersecting_pairs} intersecting pair(s).\n"
        
        for intersection in intersection_result.get('intersections', [])[:10]:  # Limit to first 10
            if intersection.get('intersect'):
                result_text += f"  - Lines {intersection.get('line1_index')} and {intersection.get('line2_index')}: {intersection.get('message', 'intersect')}\n"
        
        return result_text


def get_intersection_analysis_prompt_section(
    whiteboard_json: Dict[str, Any],
    user_message: str = "",
    check_specific_shape: str = None
) -> str:
    """
    Generate a prompt section with intersection analysis for the LLM.
    Similar to get_shapes_prompt_section but for geometric analysis.
    
    Args:
        whiteboard_json: Current whiteboard state JSON
        user_message: User's message (to detect if intersection checking is needed)
        check_specific_shape: Optional shape ID to check specifically
        
    Returns:
        Formatted string to include in LLM prompt
    """
    # Check if user is asking about intersections
    intersection_keywords = [
        'intersect', 'intersection', 'cross', 'overlap', 'touch', 'meet',
        'parallel', 'perpendicular', 'angle', 'geometry', 'relationship'
    ]
    
    message_lower = user_message.lower()
    should_check = any(keyword in message_lower for keyword in intersection_keywords)
    
    if not should_check and not check_specific_shape:
        return ""  # Don't add analysis if not relevant
    
    try:
        if check_specific_shape:
            result = check_whiteboard_shape_intersections(whiteboard_json, shape_id=check_specific_shape)
        else:
            result = analyze_excalidraw_intersections(whiteboard_json)
        
        analysis_text = format_intersection_analysis_for_llm(result)
        
        prompt_section = f"""
            GEOMETRIC ANALYSIS OF CURRENT WHITEBOARD:
            The following analysis shows relationships between shapes on the whiteboard:
            
            {analysis_text}
            
            IMPORTANT: When updating the whiteboard, consider these geometric relationships:
            - If shapes are supposed to intersect, ensure they actually do
            - If shapes should not overlap, verify they are separate
            - When adding new shapes, check if they should intersect with existing ones
            - Maintain geometric accuracy in your drawings
            """
        
        return prompt_section
    except Exception as e:
        logger.warning(f"[INTERSECTION_ANALYSIS] Error generating analysis: {e}")
        return ""


def check_whiteboard_shape_intersections(
    whiteboard_json: Dict[str, Any],
    shape_id: str = None
) -> Dict[str, Any]:
    if shape_id:
        # Check specific shape
        return find_shape_intersections(whiteboard_json, shape_id=shape_id)
    else:
        # Return analysis for all shapes
        return analyze_excalidraw_intersections(whiteboard_json)

