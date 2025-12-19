import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any
from .sympy_relationships_mapping import (
    RELATIONSHIPS_LIBRARY_AVAILABLE,
    check_relationships_library,
    identify_relationship_with_llm,
    get_sympy_methods_for_relationship,
    get_custom_functions_for_relationship,
)
logger = logging.getLogger(__name__)

possible_paths = [
    Path(__file__).parent.parent.parent,  
]
from .excalidraw_to_sympy_json_converter import (
    check_whiteboard_shape_intersections,
    analyze_excalidraw_intersections,
    find_shape_intersections,
    format_intersection_analysis_for_llm
)

def get_intersection_analysis_prompt_section(
    whiteboard_json: Dict[str, Any],
    user_message: str = "",
    check_specific_shape: str = None,
    openai_client = None
) -> str:
    """
    Generate a prompt section with intersection analysis for the LLM.
    
    FLOW:
    1. Check relationships library FIRST (fast, no LLM call)
    2. If not found, use LLM to identify relationship query
    3. Use SymPy built-in methods first, then custom functions if needed
    
    Args:
        whiteboard_json: Current whiteboard state JSON (from Excalidraw)
        user_message: User's message (to detect if relationship checking is needed)
        check_specific_shape: Optional shape ID to check specifically
        openai_client: Optional OpenAI client for LLM relationship identification
        
    Returns:
        Formatted string to include in LLM prompt, or empty string if not relevant
    """
    # STEP 1: Check relationships library FIRST (before LLM)
    relationship_info = None
    if RELATIONSHIPS_LIBRARY_AVAILABLE:
        relationship_info = check_relationships_library(user_message)
    
    if relationship_info:
        logger.info(f"[INTERSECTION_ANALYSIS] Found relationship '{relationship_info['relationship_type']}' in library")
        relationship_type = relationship_info['relationship_type']
        source = relationship_info.get('source', 'library')
    else:
        # STEP 2: Use LLM to identify relationship query (only if not in library)
        if openai_client and RELATIONSHIPS_LIBRARY_AVAILABLE:
            logger.info("[INTERSECTION_ANALYSIS] Relationship not in library, checking with LLM...")
            llm_result = identify_relationship_with_llm(user_message, openai_client)
            if llm_result:
                relationship_type = llm_result.get('relationship_type')
                source = 'llm'
                logger.info(f"[INTERSECTION_ANALYSIS] LLM identified relationship: {relationship_type}")
            else:
                relationship_type = None
                source = None
        else:
            # Fallback to keyword matching if no LLM client or library
            relationship_type = None
            source = None
            logger.debug("[INTERSECTION_ANALYSIS] No LLM client or library available, using keyword fallback")
    
    # STEP 3: Check if we should proceed with analysis
    has_shapes = False
    line_count = 0
    if isinstance(whiteboard_json, dict):
        elements = whiteboard_json.get("elements", [])
        has_shapes = len(elements) > 0
        line_count = sum(1 for e in elements if e.get("type") == "line")
    elif isinstance(whiteboard_json, list):
        has_shapes = len(whiteboard_json) > 0
        line_count = sum(1 for e in whiteboard_json if isinstance(e, dict) and e.get("type") == "line")
    
    # Determine if we should check relationships
    should_check = relationship_type is not None or check_specific_shape is not None
    
    # Also auto-check if there are 2+ lines and user mentions geometry
    if not should_check and line_count >= 2:
        message_lower = user_message.lower() if user_message else ""
        if any(word in message_lower for word in ['line', 'lines', 'parallel', 'intersect', 'angle']):
            should_check = True
            relationship_type = relationship_type or "intersect"  # Default to intersection
            logger.info(f"[INTERSECTION_ANALYSIS] Auto-detected geometry question with {line_count} lines")
    
    if not should_check and not (has_shapes and line_count >= 2):
        logger.debug(f"[INTERSECTION_ANALYSIS] Skipping analysis - should_check={should_check}, has_shapes={has_shapes}, line_count={line_count}")
        return ""  # Don't add analysis if not relevant
    
    # Log which methods will be used (SymPy built-in first)
    if relationship_type and RELATIONSHIPS_LIBRARY_AVAILABLE:
        sympy_methods = get_sympy_methods_for_relationship(relationship_type)
        custom_functions = get_custom_functions_for_relationship(relationship_type)
        logger.info(f"[INTERSECTION_ANALYSIS] Relationship '{relationship_type}' (source: {source}) - SymPy methods: {sympy_methods}, Custom: {custom_functions}")
    
    try:
        if check_specific_shape:
            result = check_whiteboard_shape_intersections(whiteboard_json, shape_id=check_specific_shape)
        else:
            # Analyze all intersections
            result = analyze_excalidraw_intersections(whiteboard_json)
        
        # Check if result has error
        if result.get('error'):
            logger.warning(f"[INTERSECTION_ANALYSIS] Analysis returned error: {result.get('error')}")
            return ""
        
        analysis_text = format_intersection_analysis_for_llm(result)
        
        if not analysis_text or "not available" in analysis_text.lower():
            logger.debug("[INTERSECTION_ANALYSIS] Analysis text is empty or indicates unavailability")
            return ""
        
        prompt_section = f"""
            GEOMETRIC ANALYSIS OF CURRENT WHITEBOARD:
            The following analysis shows relationships between shapes on the whiteboard:
            
            {analysis_text}
            
            IMPORTANT GUIDELINES FOR WHITEBOARD UPDATES:
            - If shapes are supposed to intersect, ensure they actually do in your drawing
            - If shapes should not overlap, verify they are separate
            - When adding new shapes, check if they should intersect with existing ones based on the context
            - Maintain geometric accuracy - if lines should be parallel, make them parallel
            - If shapes should form specific angles (90°, 45°, etc.), ensure those angles are correct
            - Consider the mathematical relationships described in the student's question
            """
        
        logger.info(f"[INTERSECTION_ANALYSIS] Generated analysis section ({len(prompt_section)} chars)")
        return prompt_section
    except Exception as e:
        logger.warning(f"[INTERSECTION_ANALYSIS] Error generating analysis: {e}")
        import traceback
        logger.debug(f"[INTERSECTION_ANALYSIS] Traceback: {traceback.format_exc()}")
        return ""


def analyze_whiteboard_for_llm(
    whiteboard_json: Dict[str, Any],
    analysis_type: str = "intersections"
) -> Dict[str, Any]:
    """
    Comprehensive whiteboard analysis for LLM context.
    
    Args:
        whiteboard_json: Current whiteboard state
        analysis_type: Type of analysis ('intersections', 'geometry', 'all')
        
    Returns:
        Dictionary with analysis results formatted for LLM
    """
    try:
        if analysis_type in ["intersections", "all"]:
            intersection_result = analyze_excalidraw_intersections(whiteboard_json)
            return {
                'intersections': intersection_result,
                'summary': intersection_result.get('summary', {}),
                'formatted': format_intersection_analysis_for_llm(intersection_result)
            }
        else:
            return {'error': f'Unknown analysis type: {analysis_type}'}
    except Exception as e:
        logger.error(f"[ANALYSIS] Error: {e}")
        return {'error': str(e)}


def check_specific_shape_for_llm(
    whiteboard_json: Dict[str, Any],
    shape_id: str
) -> Dict[str, Any]:
    """
    Check a specific shape's intersections and return LLM-friendly format.
    
    Args:
        whiteboard_json: Current whiteboard state
        shape_id: ID of shape to check
        
    Returns:
        Dictionary with analysis results
    """
    try:
        result = find_shape_intersections(whiteboard_json, shape_id=shape_id)
        return {
            'result': result,
            'formatted': format_intersection_analysis_for_llm(result),
            'has_intersections': result.get('summary', {}).get('total_intersections', 0) > 0
        }
    except Exception as e:
        logger.error(f"[SHAPE_CHECK] Error: {e}")
        return {'error': str(e)}
