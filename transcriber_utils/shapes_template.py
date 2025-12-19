
import json
import time
import logging
from typing import Dict, Any, Optional, Tuple, List
import os
from pathlib import Path
import uuid
import random

from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

whiteboard_states = {}  

TRANSCRIBERS_DIR = Path(__file__).parent.parent / "Transcribers"
# TRANSCRIBERS_DIR = Path(__file__).parent.parent.parent / "Transcribers"

# Cache for shapes metadata to avoid reloading on every request
_shapes_cache = None
_shapes_cache_timestamp = 0
CACHE_TTL = 300  # Cache for 5 minutes

def load_shape_template(shape_name: str) -> Optional[Dict[str, Any]]:
    """
    Load a specific shape template from Transcribers directory.
    Returns the full shape data including elements and appState, or None if not found.
    """
    logger.info(f"[SHAPE_LOADER] Attempting to load shape template: {shape_name}")
    
    if not TRANSCRIBERS_DIR.exists():
        logger.warning(f"[SHAPE_LOADER] Transcribers directory not found at {TRANSCRIBERS_DIR}")
        return None
    
    shape_file = TRANSCRIBERS_DIR / f"{shape_name}.json"
    
    if not shape_file.exists():
        logger.warning(f"[SHAPE_LOADER] Shape file not found: {shape_file}")
        return None
    
    try:
        with open(shape_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        elements = data.get("elements", [])
        if not elements:
            logger.warning(f"[SHAPE_LOADER] Shape {shape_name} has no elements")
            return None
        
        logger.info(f"[SHAPE_LOADER] Successfully loaded shape {shape_name} with {len(elements)} elements")
        return {
            "elements": elements,
            "appState": data.get("appState", {}),
            "name": shape_name
        }
    except Exception as e:
        logger.error(f"[SHAPE_LOADER] Failed to load shape {shape_name}: {e}")
        return None


def get_available_shapes(use_cache: bool = True) -> Dict[str, Any]:
    """
    Load available shapes from Transcribers directory and extract key information.
    Returns a dictionary mapping shape names to their metadata.
    Uses caching to avoid reloading on every request.
    """
    global _shapes_cache, _shapes_cache_timestamp
    
    # Check cache first
    if use_cache and _shapes_cache is not None:
        cache_age = time.time() - _shapes_cache_timestamp
        if cache_age < CACHE_TTL:
            logger.debug(f"[SHAPE_LOADER] Using cached shapes (age: {cache_age:.1f}s)")
            return _shapes_cache
    
    logger.info("[SHAPE_LOADER] Loading shapes from Transcribers directory (cache miss or expired)")
    start_time = time.time()
    shapes_info = {}
    
    if not TRANSCRIBERS_DIR.exists():
        logger.warning(f"[SHAPE_LOADER] Transcribers directory not found at {TRANSCRIBERS_DIR}")
        return shapes_info
    
    try:
        json_files = list(TRANSCRIBERS_DIR.glob("*.json"))
        logger.info(f"[SHAPE_LOADER] Found {len(json_files)} JSON files in Transcribers directory")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                shape_name = json_file.stem  # filename without .json
                elements = data.get("elements", [])
                
                if elements:
                    # Extract unique element types and key properties
                    element_types = set()
                    for elem in elements:
                        elem_type = elem.get("type", "unknown")
                        element_types.add(elem_type)
                    
                    shapes_info[shape_name] = {
                        "name": shape_name,
                        "display_name": shape_name.replace("_", " ").title(),
                        "element_types": list(element_types),
                        "element_count": len(elements),
                        "has_text": any(e.get("type") == "text" for e in elements),
                        "has_shapes": any(e.get("type") in ["rectangle", "ellipse", "diamond", "arrow", "line"] for e in elements),
                    }
            except Exception as e:
                logger.warning(f"[SHAPE_LOADER] Failed to load shape {json_file.name}: {e}")
                continue
        
        load_time = time.time() - start_time
        logger.info(f"[SHAPE_LOADER] Successfully loaded metadata for {len(shapes_info)} shapes in {load_time:.2f}s")
        
        # Update cache
        _shapes_cache = shapes_info
        _shapes_cache_timestamp = time.time()
                
    except Exception as e:
        logger.error(f"[SHAPE_LOADER] Error loading shapes from Transcribers: {e}")
    
    return shapes_info


def inject_library_shapes(elements: List[Dict], detected_shapes: List[str], user_message: str = "") -> List[Dict]:
    """
    Replace or inject actual library shapes into the elements list.
    If a shape from the library is detected, use the actual library shape instead of LLM-generated one.
    """
    inject_start_time = time.time()
    logger.info(f"[SHAPE_INJECTOR] Starting shape injection for {len(detected_shapes)} detected shapes")
    logger.info(f"[SHAPE_INJECTOR] Original elements count: {len(elements)}")
    
    if not detected_shapes:
        logger.info("[SHAPE_INJECTOR] No shapes to inject")
        return elements
    
    # Note: In Excalidraw, circles are stored as ellipses with equal width/height
    shape_name_to_library = {
        "rectangle": "rectangle",
        "square": "rectangle",  # Square uses rectangle template
        "circle": "circle",  # Will be ellipse type in JSON but from circle.json
        "triangle": "triangle",
        "right_triangle": "right_triangle",
        "arrow": "arrow",
        "diamond": "diamond-arrow",  # Diamond maps to diamond-arrow.json
        "diamond-arrow": "diamond-arrow",
        "ellipse": "ellipse",
        "oval": "oval",
        "pentagon": "pentagon",
        "hexagon": "hexagon",
        "parallelogram": "parallelogram",
        "trapezium": "trapezium",
        "cube": "cube",
        "cylinder": "cylinder",
        "heart": "heart",
        "semicircle": "semi_circle",
        "quarter_circle": "quarter_circle",
        "sector": "sector",
        "quadrant": "quadrant",
        "four_quadrants": "four_quadrants",
    }
    
    # Map element types to shape names (for matching LLM-generated elements)
    # Note: "diamond" element type maps to "diamond-arrow" shape (the library file name)
    element_type_to_shape = {
        "rectangle": "rectangle",
        "ellipse": "circle",  # Ellipse from LLM might be a circle
        "diamond": "diamond-arrow",  # Diamond element type -> diamond-arrow shape
        "arrow": "arrow",
        "line": "arrow",  # Lines might be arrows
        "triangle": "triangle",
    }
    
    injected_elements = []
    replaced_count = 0
    injected_count = 0    
    used_shapes = set()
    
    for elem in elements:
        elem_type = elem.get("type", "").lower()
        should_replace = False
        library_shape_name = None
        matched_shape_name = None
        
        # Check if this element type matches a detected shape
        if elem_type in element_type_to_shape:
            potential_shape = element_type_to_shape[elem_type]
            if potential_shape in detected_shapes:
                matched_shape_name = potential_shape
                library_shape_name = shape_name_to_library.get(potential_shape)
                should_replace = True
                logger.info(f"[SHAPE_INJECTOR] Matched element type '{elem_type}' to shape '{matched_shape_name}' -> library '{library_shape_name}'")
        
        # Also check if element type directly matches a detected shape
        if not should_replace:
            for shape_name in detected_shapes:
                if shape_name in shape_name_to_library:
                    # Check if element type matches (rectangle, circle/ellipse, diamond, etc.)
                    shape_normalized = shape_name.replace("-", "_").replace("_", "")
                    elem_normalized = elem_type.replace("_", "")
                    
                    # Special handling for diamond - diamond element type should match diamond-arrow shape
                    if (elem_type == shape_name or 
                        elem_type == shape_name.replace("-", "_") or
                        (shape_name == "circle" and elem_type == "ellipse") or
                        (shape_name == "diamond-arrow" and elem_type == "diamond") or  # Diamond element -> diamond-arrow shape
                        (shape_normalized == elem_normalized)):
                        matched_shape_name = shape_name
                        library_shape_name = shape_name_to_library[shape_name]
                        should_replace = True
                        logger.info(f"[SHAPE_INJECTOR] Direct match: element type '{elem_type}' -> shape '{matched_shape_name}' -> library '{library_shape_name}'")
                        break
        
        if should_replace and library_shape_name and library_shape_name not in used_shapes:
            template = load_shape_template(library_shape_name)
            if template and template.get("elements"):
                library_elem = template["elements"][0].copy()  
                
                # Preserve position and size from LLM-generated element if they exist
                if "x" in elem:
                    library_elem["x"] = elem["x"]
                if "y" in elem:
                    library_elem["y"] = elem["y"]
                if "width" in elem:
                    library_elem["width"] = elem["width"]
                if "height" in elem:
                    library_elem["height"] = elem["height"]
                
                # Generate new IDs and ensure all required fields exist
                library_elem["id"] = str(uuid.uuid4()).replace("-", "")[:20]
                library_elem["versionNonce"] = random.randint(100000000, 999999999)
                library_elem["updated"] = int(time.time() * 1000)
                
                # Ensure all required fields are present
                if "version" not in library_elem:
                    library_elem["version"] = 1
                if "seed" not in library_elem:
                    library_elem["seed"] = random.randint(1000000, 9999999)
                if "index" not in library_elem:
                    library_elem["index"] = f"a{random.randint(1, 1000)}"
                if "opacity" not in library_elem:
                    library_elem["opacity"] = 100
                if "locked" not in library_elem:
                    library_elem["locked"] = False
                if "isDeleted" not in library_elem:
                    library_elem["isDeleted"] = False
                if "groupIds" not in library_elem:
                    library_elem["groupIds"] = []
                if "boundElements" not in library_elem:
                    library_elem["boundElements"] = []
                if "frameId" not in library_elem:
                    library_elem["frameId"] = None
                if "link" not in library_elem:
                    library_elem["link"] = None
                if "angle" not in library_elem:
                    library_elem["angle"] = 0
                
                # Preserve colors if specified
                if "strokeColor" in elem:
                    library_elem["strokeColor"] = elem["strokeColor"]
                if "backgroundColor" in elem:
                    library_elem["backgroundColor"] = elem["backgroundColor"]
                
                injected_elements.append(library_elem)
                used_shapes.add(library_shape_name)
                replaced_count += 1
                logger.info(f"[SHAPE_INJECTOR] Replaced {elem_type} with library shape: {library_shape_name}")
                continue
        
        # Keep original element if not replaced
        injected_elements.append(elem)
    
    # Second, inject any detected shapes that weren't in the original elements
    for shape_name in detected_shapes:
        if shape_name not in used_shapes and shape_name in shape_name_to_library:
            library_shape_name = shape_name_to_library[shape_name]
            template = load_shape_template(library_shape_name)
            if template and template.get("elements"):
                for lib_elem in template["elements"]:
                    new_elem = lib_elem.copy()
                    # Generate new IDs and ensure all required fields
                    new_elem["id"] = str(uuid.uuid4()).replace("-", "")[:20]
                    new_elem["versionNonce"] = random.randint(100000000, 999999999)
                    new_elem["updated"] = int(time.time() * 1000)
                    
                    # Ensure all required fields are present
                    if "version" not in new_elem:
                        new_elem["version"] = 1
                    if "seed" not in new_elem:
                        new_elem["seed"] = random.randint(1000000, 9999999)
                    if "index" not in new_elem:
                        new_elem["index"] = f"a{random.randint(1, 1000)}"
                    if "opacity" not in new_elem:
                        new_elem["opacity"] = 100
                    if "locked" not in new_elem:
                        new_elem["locked"] = False
                    if "isDeleted" not in new_elem:
                        new_elem["isDeleted"] = False
                    if "groupIds" not in new_elem:
                        new_elem["groupIds"] = []
                    if "boundElements" not in new_elem:
                        new_elem["boundElements"] = []
                    if "frameId" not in new_elem:
                        new_elem["frameId"] = None
                    if "link" not in new_elem:
                        new_elem["link"] = None
                    if "angle" not in new_elem:
                        new_elem["angle"] = 0
                    
                    # Set default position (center-ish, offset for multiple shapes)
                    if "x" not in new_elem or new_elem.get("x", 0) == 0:
                        new_elem["x"] = 200 + injected_count * 150
                    if "y" not in new_elem or new_elem.get("y", 0) == 0:
                        new_elem["y"] = 200 + injected_count * 150
                    
                    injected_elements.append(new_elem)
                    injected_count += 1
                    logger.info(f"[SHAPE_INJECTOR] Injected library shape: {library_shape_name} at ({new_elem.get('x')}, {new_elem.get('y')})")
                used_shapes.add(library_shape_name)
    
    inject_time = time.time() - inject_start_time
    logger.info(f"[SHAPE_INJECTOR] Injection complete: {replaced_count} replaced, {injected_count} injected, total elements: {len(injected_elements)} in {inject_time:.2f}s")
    return injected_elements


def detect_shapes_needed(user_message: str, update_description: str = "") -> List[str]:
    """
    Detect which shapes might be needed based on user message and update description.
    Returns a list of potential shape names that match the request.
    """
    detect_start_time = time.time()
    logger.info(f"[SHAPE_DETECTOR] Analyzing message for shape needs: '{user_message[:100] if user_message else ''}...'")
    
    # Use cached shapes for faster performance
    shapes_info = get_available_shapes(use_cache=True)
    if not shapes_info:
        logger.warning("[SHAPE_DETECTOR] No shapes available to match against")
        return []
    
    text_to_analyze = (user_message + " " + update_description).lower()
    shape_keywords = {
        "diamond-arrow": ["diamond arrow", "diamond-arrow", "diamondarrow", "diamond", "rhombus"],  # "diamond" maps to diamond-arrow
        "four_quadrants": ["four quadrants", "coordinate plane", "xy plane", "4 quadrants"],
        "quarter_circle": ["quarter circle", "quarter-circle"],
        "semicircle": ["semicircle", "semi circle", "half circle"],
        "right_triangle": ["right triangle", "right-triangle"],
        "parallelogram": ["parallelogram"],
        "trapezium": ["trapezium", "trapezoid"],
        "rectangle": ["rectangle", "rect"],
        "square": ["square"],  # Separate from rectangle
        "circle": ["circle", "round shape"],
        "triangle": ["triangle", "triangular"],
        "arrow": ["arrow", "pointer"],
        "line": ["line", "straight line"],
        "ellipse": ["ellipse"],
        "oval": ["oval"],
        "pentagon": ["pentagon"],
        "hexagon": ["hexagon"],
        "cube": ["cube", "3d box", "3d cube"],
        "cylinder": ["cylinder", "tube"],
        "heart": ["heart"],
        "quadrant": ["quadrant", "coordinate", "graph", "axes"],
    }
    
    detected_shapes = []
    matched_keywords = set() 
    sorted_shapes = sorted(shape_keywords.items(), key=lambda x: max(len(k) for k in x[1]) if x[1] else 0, reverse=True)
    
    import re
    logger.debug(f"[SHAPE_DETECTOR] Available shapes: {list(shapes_info.keys())[:10]}...")
    logger.debug(f"[SHAPE_DETECTOR] Text to analyze: '{text_to_analyze[:200]}'")
    
    for shape_name, keywords in sorted_shapes:
        if shape_name not in shapes_info:
            logger.debug(f"[SHAPE_DETECTOR] Shape '{shape_name}' not in available shapes, skipping")
            continue
            
        # Check if any keyword matches (using word boundaries for better matching)
        for keyword in keywords:
            # Use word boundary matching - keyword must appear as whole word
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            match_result = re.search(pattern, text_to_analyze)
            logger.debug(f"[SHAPE_DETECTOR] Checking '{keyword}' -> pattern '{pattern}' -> match: {bool(match_result)}")
            if match_result:
                if shape_name not in detected_shapes:
                    detected_shapes.append(shape_name)
                    matched_keywords.add(keyword)
                    logger.info(f"[SHAPE_DETECTOR] Detected potential need for shape: {shape_name} (matched keyword: '{keyword}')")
                    break  # Only match once per shape
    
    detect_time = time.time() - detect_start_time
    if detected_shapes:
        logger.info(f"[SHAPE_DETECTOR] Detected {len(detected_shapes)} potential shapes: {detected_shapes} in {detect_time:.2f}s")
    else:
        logger.info(f"[SHAPE_DETECTOR] No specific shapes detected in {detect_time:.2f}s")
    
    return list(set(detected_shapes))  


def get_shapes_prompt_section(user_message: str = "", update_description: str = "") -> str:
    """
    Generate a prompt section that includes actual shape templates for the LLM to reuse.
    Detects which shapes are needed and includes their actual element structures.
    """
    prompt_start_time = time.time()
    logger.info("[SHAPE_PROMPT] Generating shapes prompt section")
    
    # Use cached shapes for faster performance
    shapes_info = get_available_shapes(use_cache=True)
    if not shapes_info:
        logger.warning("[SHAPE_PROMPT] No shapes available, returning empty section")
        return ""
    
    # Detect which shapes might be needed (this also uses cached shapes)
    detected_shapes = detect_shapes_needed(user_message, update_description)
    
    prompt_section = """
            CRITICAL OPTIMIZATION: Pre-built shape templates are available below. USE THESE instead of creating from scratch!
            This will reduce token usage by 70-90% and ensure consistency. Copy the element structure and modify only position/size/color.
            
            """
    
    # Include actual shape templates for detected shapes
    if detected_shapes:
        logger.info(f"[SHAPE_PROMPT] Including templates for detected shapes: {detected_shapes}")
        prompt_section += "RELEVANT SHAPE TEMPLATES (Based on your request, these are likely needed):\n\n"
        
        for shape_name in detected_shapes[:5]:  # Limit to 5 most relevant
            template = load_shape_template(shape_name)
            if template:
                elements = template["elements"]
                # Create a simplified example element structure
                example_element = elements[0] if elements else {}
                # Remove position-specific fields for template
                template_element = {k: v for k, v in example_element.items() 
                                  if k not in ["x", "y", "id", "versionNonce", "updated"]}
                
                prompt_section += f"""
            Shape: {shape_name.replace('_', ' ').title()}
            Element count: {len(elements)}
            Example element structure (copy this and modify x, y, width, height, colors):
            {json.dumps(template_element, indent=2)[:500]}...
            
            """
                logger.debug(f"[SHAPE_PROMPT] Added template for {shape_name}")
    
    geometric_shapes = []
    arrows_lines = []
    special_shapes = []
    
    for shape_name, info in shapes_info.items():
        types = info["element_types"]
        if any(t in ["rectangle", "ellipse", "diamond", "circle", "triangle"] for t in types):
            geometric_shapes.append(f"- {info['display_name']} ({shape_name})")
        elif any(t in ["arrow", "line"] for t in types):
            arrows_lines.append(f"- {info['display_name']} ({shape_name})")
        else:
            special_shapes.append(f"- {info['display_name']} ({shape_name})")
    
    prompt_section += "\n ALL AVAILABLE SHAPES (you can request templates for any of these):\n\n"
    
    if geometric_shapes:
        prompt_section += "Geometric Shapes:\n" + "\n".join(geometric_shapes[:10]) + "\n\n"
    
    if arrows_lines:
        prompt_section += "Arrows and Lines:\n" + "\n".join(arrows_lines[:10]) + "\n\n"
    
    if special_shapes:
        prompt_section += "Special Shapes:\n" + "\n".join(special_shapes[:10]) + "\n\n"
    
    prompt_section += """
            USAGE INSTRUCTIONS:
            1. If you see a relevant template above, COPY its element structure
            2. Modify ONLY: x, y, width, height, strokeColor, backgroundColor, strokeWidth
            3. Generate new IDs (use UUID format) and versionNonce (random number)
            4. Keep all other properties (roughness, roundness, fillStyle, etc.) from the template
            5. This is 10x faster and uses 70% fewer tokens than generating from scratch
            
            Example: If you need a rectangle at position (100, 200) with size 300x150:
            - Copy the rectangle template element structure
            - Set x=100, y=200, width=300, height=150
            - Generate new id and versionNonce
            - Keep all other properties from template
            """
    
    prompt_time = time.time() - prompt_start_time
    logger.info(f"[SHAPE_PROMPT] Generated prompt section ({len(prompt_section)} chars) in {prompt_time:.2f}s")
    return prompt_section
