from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

RELATIONSHIPS_LIBRARY_AVAILABLE = True
RELATIONSHIP_LIBRARY = {
    # Intersection relationships
    "intersect": {
        "keywords": ["intersect", "intersection", "cross", "meet", "touch", "overlap"],
        "relationship_type": "intersection",
        "sympy_methods": ["Line.intersection()", "Circle.intersection()"],
        "custom_functions": ["check_line_intersection", "check_line_circle_intersection", 
                            "check_polygon_polygon_intersection", "check_circle_circle_intersection"],
        "description": "Checks if shapes intersect and finds intersection points"
    },
    
    # Parallel relationships
    "parallel": {
        "keywords": ["parallel", "never meet", "same direction", "same slope"],
        "relationship_type": "parallel",
        "sympy_methods": ["Line.is_parallel()", "Segment.is_parallel()"],
        "custom_functions": ["check_line_intersection"],  # Returns parallel status
        "description": "Checks if lines are parallel"
    },
    
    # Perpendicular relationships
    "perpendicular": {
        "keywords": ["perpendicular", "right angle", "90 degrees", "orthogonal"],
        "relationship_type": "perpendicular",
        "sympy_methods": ["Segment.is_perpendicular()", "Line.angle_between()"],
        "custom_functions": ["calculate_angle_between_lines"],
        "description": "Checks if lines are perpendicular (90° angle)"
    },
    
    # Angle relationships
    "angle": {
        "keywords": ["angle", "degrees", "radians", "between lines"],
        "relationship_type": "angle",
        "sympy_methods": ["Line.angle_between()"],
        "custom_functions": ["calculate_angle_between_lines"],
        "description": "Calculates angle between lines"
    },
    
    # Distance relationships
    "distance": {
        "keywords": ["distance", "how far", "length", "apart"],
        "relationship_type": "distance",
        "sympy_methods": ["Point.distance()", "Line.distance()"],
        "custom_functions": ["calculate_distance", "calculate_line_length"],
        "description": "Calculates distance between points or from point to line"
    },
    
    # Containment relationships
    "contains": {
        "keywords": ["inside", "contains", "within", "enclosed", "inside polygon"],
        "relationship_type": "containment",
        "sympy_methods": ["Polygon.encloses_point()", "Line.contains()", "Circle.contains()"],
        "custom_functions": ["check_point_in_polygon", "check_point_on_line"],
        "description": "Checks if point is inside polygon or on line"
    },
    
    # Coincident relationships
    "coincident": {
        "keywords": ["coincident", "same line", "overlap", "identical"],
        "relationship_type": "coincident",
        "sympy_methods": ["Line.contains()"],
        "custom_functions": ["check_line_intersection"],  # Returns coincident status
        "description": "Checks if lines are coincident (same line)"
    },
    
    # Tangent relationships
    "tangent": {
        "keywords": ["tangent", "touches", "touching"],
        "relationship_type": "tangent",
        "sympy_methods": ["Circle.intersection()"],  # Returns 1 point if tangent
        "custom_functions": ["check_line_circle_intersection", "check_circle_circle_intersection"],
        "description": "Checks if line/circle is tangent to circle"
    },
    
    # Area relationships
    "area": {
        "keywords": ["area", "size", "surface"],
        "relationship_type": "area",
        "sympy_methods": ["Polygon.area", "Circle.area"],
        "custom_functions": ["calculate_polygon_area", "calculate_circle_properties"],
        "description": "Calculates area of shapes"
    },
    
    # Perimeter relationships
    "perimeter": {
        "keywords": ["perimeter", "circumference", "boundary length"],
        "relationship_type": "perimeter",
        "sympy_methods": ["Polygon.perimeter"],
        "custom_functions": ["calculate_polygon_perimeter"],
        "description": "Calculates perimeter of polygons"
    },
    
    # Shape detection
    "shape_type": {
        "keywords": ["what shape", "type of", "is it a", "detect", "rectangle", "triangle", "square"],
        "relationship_type": "shape_detection",
        "sympy_methods": ["Polygon.vertices", "Polygon.area"],
        "custom_functions": ["detect_rectangle", "detect_triangle"],
        "description": "Detects type of shape (rectangle, triangle, etc.)"
    },
    
    # Midpoint relationships
    "midpoint": {
        "keywords": ["midpoint", "center point", "middle"],
        "relationship_type": "midpoint",
        "sympy_methods": ["Point.midpoint()"],  # If available, else custom
        "custom_functions": ["find_midpoint"],
        "description": "Finds midpoint between two points"
    },
    
    # Slope relationships
    "slope": {
        "keywords": ["slope", "gradient", "steepness"],
        "relationship_type": "slope",
        "sympy_methods": [],  # SymPy doesn't have direct slope, need custom
        "custom_functions": ["calculate_slope", "get_line_equation"],
        "description": "Calculates slope of a line"
    }
}


def check_relationships_library(user_message: str) -> Optional[Dict[str, Any]]:
    """
    Check relationships library FIRST before calling LLM.
    Returns relationship info if found, None otherwise.
    
    Args:
        user_message: User's query message
        
    Returns:
        Dictionary with relationship info if found, None if not in library
    """
    if not user_message:
        return None
    
    message_lower = user_message.lower()
    
    # Check each relationship pattern
    for relationship_key, relationship_info in RELATIONSHIP_LIBRARY.items():
        keywords = relationship_info["keywords"]
        
        # Check if any keyword matches
        if any(keyword in message_lower for keyword in keywords):
            logger.info(f"[RELATIONSHIPS_LIBRARY] Found relationship '{relationship_key}' in library")
            return {
                "relationship_type": relationship_key,
                "relationship_info": relationship_info,
                "matched_keywords": [kw for kw in keywords if kw in message_lower],
                "source": "library"  # Indicates found in library, not LLM
            }
    
    logger.debug(f"[RELATIONSHIPS_LIBRARY] No relationship found in library for: '{user_message[:50]}...'")
    return None


def get_sympy_methods_for_relationship(relationship_type: str) -> List[str]:
    """
    Get list of SymPy built-in methods for a relationship type.
    
    Args:
        relationship_type: Type of relationship (e.g., "intersect", "parallel")
        
    Returns:
        List of SymPy method names
    """
    if relationship_type in RELATIONSHIP_LIBRARY:
        return RELATIONSHIP_LIBRARY[relationship_type].get("sympy_methods", [])
    return []


def get_custom_functions_for_relationship(relationship_type: str) -> List[str]:
    """
    Get list of custom functions for a relationship type (used if SymPy doesn't have it).
    
    Args:
        relationship_type: Type of relationship
        
    Returns:
        List of custom function names
    """
    if relationship_type in RELATIONSHIP_LIBRARY:
        return RELATIONSHIP_LIBRARY[relationship_type].get("custom_functions", [])
    return []


def identify_relationship_with_llm(
    user_message: str,
    openai_client,
    model: str = "gpt-4o-mini",
    temperature: float = 0.3
) -> Optional[Dict[str, Any]]:
    """
    Use LLM to identify relationship query if not found in library.
    This is called ONLY if check_relationships_library() returns None.
    
    Args:
        user_message: User's query
        openai_client: OpenAI client instance
        model: Model to use
        temperature: Temperature for LLM
        
    Returns:
        Dictionary with relationship info, or None if not a relationship query
    """
    prompt = f"""
        You are analyzing a student's question about geometric shapes on a whiteboard.

        Student's question: "{user_message}"

        Determine if this is a question about geometric RELATIONSHIPS between shapes (like intersections, parallel lines, angles, distances, etc.) or if it's a request to DRAW/ADD/MODIFY shapes.

        Common relationship questions include:
        - "Do these lines intersect?"
        - "Are the lines parallel?"
        - "What's the angle between these lines?"
        - "How far apart are these points?"
        - "Is this point inside the rectangle?"
        - "What's the area of this shape?"

        If it's a RELATIONSHIP question, respond with JSON:
        {{
            "is_relationship_query": true,
            "relationship_type": "intersect|parallel|perpendicular|angle|distance|contains|area|perimeter|etc",
            "confidence": "high|medium|low",
            "reasoning": "brief explanation"
        }}

        If it's NOT a relationship question (e.g., "draw a circle", "add a line"), respond with:
        {{
            "is_relationship_query": false,
            "reasoning": "brief explanation"
        }}

        Respond ONLY with valid JSON, no additional text.
        """
    
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Clean JSON if wrapped in markdown
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
        
        import json
        result = json.loads(response_text)
        
        if result.get("is_relationship_query"):
            logger.info(f"[RELATIONSHIPS_LLM] Identified relationship: {result.get('relationship_type')}")
            return {
                "relationship_type": result.get("relationship_type"),
                "confidence": result.get("confidence", "medium"),
                "source": "llm" 
            }
        else:
            logger.debug(f"[RELATIONSHIPS_LLM] Not a relationship query: {result.get('reasoning')}")
            return None
            
    except Exception as e:
        logger.warning(f"[RELATIONSHIPS_LLM] Error identifying relationship: {e}")
        return None


def get_relationship_analysis_function(relationship_type: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Get the appropriate function to use for a relationship type.
    Returns (sympy_method, custom_function) - use sympy_method first if available.
    
    Args:
        relationship_type: Type of relationship
        
    Returns:
        Tuple of (sympy_method_name, custom_function_name)
    """
    if relationship_type not in RELATIONSHIP_LIBRARY:
        return (None, None)
    
    info = RELATIONSHIP_LIBRARY[relationship_type]
    sympy_methods = info.get("sympy_methods", [])
    custom_functions = info.get("custom_functions", [])
    
    # Return first available sympy method and custom function
    sympy_method = sympy_methods[0] if sympy_methods else None
    custom_function = custom_functions[0] if custom_functions else None
    
    return (sympy_method, custom_function)


# Export main functions
__all__ = [
    "check_relationships_library",
    "identify_relationship_with_llm",
    "get_sympy_methods_for_relationship",
    "get_custom_functions_for_relationship",
    "get_relationship_analysis_function",
    "RELATIONSHIP_LIBRARY",
    "RELATIONSHIPS_LIBRARY_AVAILABLE"
]

