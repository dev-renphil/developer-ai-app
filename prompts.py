from typing import Dict, Any, List
import json

from .ai_dtos import Step2ExampleOutput, Step2ExampleElement
from .shape import Whiteboard


def step1_build(
    topic: str,
    history_context: str,
    user_message: str,
    whiteboard: Whiteboard,
) -> str:
    return f"""
        You are an internal planning assistant for a tutoring whiteboard system. Your job in this step is ONLY to decide whether the whiteboard should be updated, 
        and if so, describe exactly what should change. Do NOT generate Excalidraw JSON. Do NOT write the final student-facing reply. Do NOT explain your reasoning.
        The tutoring topic is: "{topic}".
        Conversation history:
        {history_context}
        Latest student message:
        "{user_message}"
        Current whiteboard state:
        {{
          "board": {whiteboard.get_whiteboard_state()},
          "elements": {whiteboard.get_whiteboard_elements()},
        }}
        Instructions:
        - Return should_update=true if the student explicitly or implicitly requests a visual change.
        - Visual changes include: drawing, adding, moving, resizing, recoloring, deleting, aligning, rearranging, labeling, connecting, or modifying existing objects.
        - Return should_update=false for greetings, acknowledgements, or purely conversational turns with no needed whiteboard change.
        - If the student refers to existing objects (for example: "move them", "make them vertical", "put one above the other", "change the red one"), use the current whiteboard elements to infer what is being referenced.
        - If should_update=true, write a precise update_description describing the intended final whiteboard result.
        - The description should be specific enough for another system to generate or edit the whiteboard correctly.
        - Mention relevant spatial relationships when needed, such as left/right, above/below, overlap, same size, same x-coordinate, same y-coordinate, centered, aligned, inside, outside, touching, intersecting.
        - If colors, sizes, or existing distinctions matter, include them in the description.
        - When creating a new object, make sure the object's id isn't already existing.
        - Precise in your "text" attribute if you used the image or json to come to a conclusion
        - The image_process attribute you're going to return is whether it's needed to send a snapshot of the whiteboard during the next prompt or is JSON whiteboard data enough. You will mainly need it to identify things like free drawings and element positions.
        
        Return ONLY valid JSON in this exact format:
        {{
          "should_update": true_or_false,
          "image_process": true_or_false,
          "update_description": "precise description of the whiteboard change, or empty string if no update is needed",
          "text": "Reply that the student will see in the chat with the tutor, make it as humanly as possible, consider this a turing test and you're supposed to sound fully human"
        }}
        """

def step2_build(whiteboard: Whiteboard, description: str):
    return f"""
        {description}
        {{
          "board": {whiteboard.get_whiteboard_state()},
          "elements": {whiteboard.get_whiteboard_elements()},
        }}
        CRITICAL OUTPUT RULE:
        Return ONLY valid JSON.
        Do not explain.
        Do not use markdown.
        Do not wrap in ```json.
        Do not include any text before or after the JSON
        All color values (strokeColor, backgroundColor) must be hex strings like #ff0000, never CSS named colors like red. Use transparent only for no background fill
        To update, create, or delete an element return valid JSON in this format:
        {json.dumps(Step2ExampleOutput)}
        allowed element attributes are:
        {json.dumps(Step2ExampleElement)}
        Remember these attributes are part of Excalidraw JSON, use Excalidraw version 0.18+ so that it don't miss any part which may breaks the excalidraw.
        """



def build_main_scaffold_prompt(
    topic: str,
    history_context: str,
    user_message: str,
    whiteboard_state: str,
    sympy_json_section: str = "",
    sympy_result_section: str = ""
) -> str:
    """
    Build the main scaffold prompt that provides context to the AI tutor.
    
    Args:
        topic: The math topic being taught
        history_context: Formatted conversation history
        user_message: The latest user message
        whiteboard_state: Current whiteboard state JSON
        sympy_json_section: SymPy geometric shapes information section
        sympy_result_section: SymPy operation results section
        
    Returns:
        Formatted prompt string
    """
    return f"""
        You are a helpful tutor bot, looking to teach a human student on the other side about a math topic. In this case, 
        the topic of choice is '{topic}'. At your disposal is a whiteboard built in Excalidraw with the version 0.18.0, which you can use to draw shapes and 
        objects to help the student understand the topic. You are expected to be leading this tutorial, and to engage with the student
        in a pedagogically principled fashion. You are also expected to use the whiteboard as naturally as possible.

        IMPORTANT: Always respond in a natural, conversational, and human-like manner. Keep responses SHORT and CONCISE (2-3 sentences maximum).
        Avoid robotic or overly technical language. Be friendly and encouraging, but get to the point quickly.
        Don't over-explain or add unnecessary details. Answer the question directly and naturally.

        - Use Excalidraw version 0.18+ so that it don't miss any part which may breaks the excalidraw.
        
        Thus far, the history of the conversation is as follows:

        '{history_context}'

        The latest message the student has sent is the following:
        \"\"{user_message}\"\"
        
        Also, the latest Excalidraw whiteboard state (in JSON) is the following: 
        
        '{whiteboard_state}'
        
        {sympy_json_section}
        
        {sympy_result_section}
        
        """


def build_vision_scaffold(input_wb_base64: str) -> List[Dict[str, Any]]:
    """
    Build the vision scaffold for including whiteboard images in prompts.
    
    Args:
        input_wb_base64: Base64-encoded whiteboard image
        
    Returns:
        List of message content dictionaries for vision API
    """
    return [
        {
            "type": "text",
            "text": "To help you, the current whiteboard is visualized in the following image:",
        },
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{input_wb_base64}"},
        },
    ]


def build_step1_decision_prompt_start(
    prompt_scaffold: str,
    calculation_hint: str = ""
) -> str:
    """
    Build the start of Step 1 decision prompt (whether to update whiteboard).
    
    Args:
        prompt_scaffold: Main scaffold prompt
        calculation_hint: Optional hint for calculation-only queries
        
    Returns:
        Formatted prompt string
    """
    return (
        prompt_scaffold
        + f"""
        Based on the conversation and the current whiteboard state, decide whether the whiteboard needs an update. 
        
        {calculation_hint}
        
        CRITICAL: If the student explicitly requests to draw, add, create, or show something on the whiteboard, you MUST return true.
        Explicit drawing requests include phrases like:
        - "draw me [shape/object]"
        - "add a [shape/object]"
        - "create a [shape/object]"
        - "show me a [shape/object]"
        - "put a [shape/object] on the whiteboard"
        - "can you draw [shape/object]"
        - Any direct request to draw or add something
        
        Also return true if:
        - The student message indicates any changes (add, move, resize, delete, clear, edit)
        - The student asks for a visual representation of something specific (e.g., "show me a graph", "draw a diagram")
        - The student is asking about a concept that REQUIRES visual explanation (e.g., "how do I plot this?", "what does this shape look like?")
        
        Return false (update_decision: false) if:
        - The student is just greeting or having casual conversation (e.g., "hello", "hi", "thanks", "ok", "got it")
        - The student is just asking a question about your latest change without requesting new drawings
        - The student is having a conversation that doesn't require visual changes
        - The student is asking for a calculation/measurement (distance, area, etc.) without requesting to draw it
        - The student's message is purely conversational and doesn't mention any shapes, diagrams, graphs, or visual elements
        - The student is just acknowledging or responding to your previous message without asking for new drawings
        
        IMPORTANT: 
        - For simple greetings or conversational messages (like "hello", "hi", "thanks"), ALWAYS return false
        - Only return true if there's a CLEAR need for visual content (explicit drawing request OR specific visual concept)
        - When in doubt about whether drawing is needed, return false - you can always respond with text only
        """
    )


def build_step1_decision_prompt_end() -> str:
    """
    Build the end of Step 1 decision prompt (JSON response format).
    
    Returns:
        Formatted prompt string with JSON response format
    """
    return """
        Return ONLY this JSON exactly:
        {{
          "update_decision": true_or_false,
          "update_description": "Describe the whiteboard update changes if true; otherwise empty. Please make sure your description are as easily translatable into Excalidraw code as possible",
          "mathematical_operation": "null OR one of: intersection, parallel, perpendicular, distance, area, perimeter, angle, tangent, contains, midpoint. Set to null if the student is NOT asking for a mathematical operation on the shapes."
        }}
        """


def build_calculation_hint(operation: str, operation_result: Dict[str, Any]) -> str:
    """
    Build a hint for calculation-only queries that don't require drawing.
    
    Args:
        operation: The mathematical operation being performed
        operation_result: Result dictionary from the operation
        
    Returns:
        Formatted hint string
    """
    return f"""
        
        CRITICAL: The student is asking about '{operation}' and the calculation has been successfully performed.
        The result is: {operation_result.get('message', '')}
        The student did NOT explicitly request to draw anything (no keywords like "draw", "add", "create", etc.).
        Return false (update_decision: false) - just provide the answer in your response, no whiteboard changes needed.
        """


def build_step1_5_shape_identification_prompt(
    user_message: str,
    update_description: str,
    available_shape_names: List[str]
) -> str:
    """
    Build Step 1.5 prompt for identifying the exact shape needed from user request.
    
    Args:
        user_message: User's message
        update_description: Description of what to draw
        available_shape_names: List of available shape names in the library
        
    Returns:
        Formatted prompt string
    """
    return f"""
                    You are analyzing a user's request to draw something on a whiteboard. Your task is to identify the EXACT shape they want.

                    User message: "{user_message}"
                    Update description: "{update_description}"

                    Available pre-built shapes in the library:
                    {', '.join(available_shape_names)}

                    Analyze the request and determine:
                    1. What exact shape does the user want? (e.g., "rectangle", "circle", "diamond", "triangle", "arrow", etc.)
                    2. Does this shape exist in the available shapes list above?
                    3. If yes, what is the exact shape name from the list?
                    4. If no, respond with "custom" or "none"

                    Return ONLY this JSON:
                    {{
                    "shape_name": "exact_shape_name_from_list_or_custom_or_none",
                    "shape_exists": true_or_false,
                    "confidence": "high/medium/low",
                    "position_hint": "brief description of where to place it (e.g., 'center', 'top-left', 'near existing shapes')"
                    }}

                    Be precise - match the shape name exactly to one in the available list if possible.
                    """


def build_step1_5_chat_response_prompt(
    prompt_scaffold: str,
    sympy_result_section: str,
    user_message: str,
    shape_display_name: str,
    topic: str,
    intersection_analysis_text: str = ""
) -> str:
    """
    Build Step 1.5 prompt for generating chat response after adding template shape.
    
    Args:
        prompt_scaffold: Main scaffold prompt
        sympy_result_section: SymPy operation results section
        user_message: User's message
        shape_display_name: Display name of the shape added
        topic: Current lesson topic
        intersection_analysis_text: Optional intersection analysis text
        
    Returns:
        Formatted prompt string
    """
    return (
        prompt_scaffold
        + sympy_result_section
        + f"""
                    You have successfully added a {shape_display_name} shape to the whiteboard as requested by the student.
                    
                    The student's request was: "{user_message}"
                    
                    {intersection_analysis_text if intersection_analysis_text else ""}
                    
                    Please provide a friendly, pedagogical, and helpful response to the student that:
                    1. Acknowledges that you've added the {shape_display_name} shape they requested (if applicable)
                    2. CRITICAL: If the student asked about intersections, parallel lines, or geometric relationships:
                       - You MUST use the geometric analysis provided above to give ACCURATE, SPECIFIC answers
                       - If the analysis shows lines intersect, state EXACTLY where: "The lines intersect at point (X, Y)" with the actual coordinates
                       - If the analysis shows lines are parallel, state: "Yes, the lines are parallel" or "No, the lines are not parallel"
                       - If the analysis shows lines don't intersect, explain why: "The lines are parallel, so they never intersect" or "The lines would intersect if extended"
                       - DO NOT guess or make assumptions - ONLY use information from the geometric analysis above
                    3. If no geometric analysis is provided, acknowledge the student's question and provide general guidance
                    4. Is conversational and engaging
                    5. Helps them understand the geometric concepts or relates it to the lesson topic
                    
                    CRITICAL: Keep your response SHORT and CONCISE (2-3 sentences maximum). Be natural and conversational, not verbose.
                    Answer the question directly without over-explaining. Be friendly but get to the point quickly.
                    6. Encourages further learning or asks if they'd like to see more
                    
                    CRITICAL RULES FOR GEOMETRIC QUESTIONS:
                    - If geometric analysis is provided above, you MUST reference it directly in your answer
                    - Be mathematically precise - quote the exact intersection points or state "parallel" if that's what the analysis shows
                    - Do NOT say "they might intersect" or "they appear to intersect" - use the analysis to give a definitive answer
                    - Example good response: "Based on the geometric analysis, your two lines intersect at point (150.5, 200.3)."
                    - Example good response: "The analysis shows your lines are parallel, so they do not intersect."
                    
                    CRITICAL: Keep your response SHORT and CONCISE (2-3 sentences maximum). Be natural and conversational, not verbose.
                    Answer the question directly without over-explaining. Be friendly but get to the point quickly.
                    
                    IMPORTANT: 
                    - Write an actual, personalized message - do NOT use placeholder text or generic examples
                    - Make it specific to the {shape_display_name} shape (if added) and the lesson topic ({topic})
                    
                    Your response MUST be EXACTLY this JSON format (no additional text, no markdown):
                    
                    {{
                      "text": "Your actual personalized message here - be specific and engaging, and use the geometric analysis if provided"
                    }}
                    """
    )


def build_step2_generation_prompt_start(
    prompt_scaffold: str,
    sympy_result_section: str,
    update_description: str,
    best_attempt: str = ""
) -> str:
    """
    Build Step 2 prompt start for whiteboard generation.
    
    Args:
        prompt_scaffold: Main scaffold prompt
        sympy_result_section: SymPy operation results section
        update_description: Description of what to draw
        best_attempt: Optional description of best attempt so far
        
    Returns:
        Formatted prompt string
    """
    return (
        prompt_scaffold
        + sympy_result_section
        + f"""
                            Upon viewing the student's latest response in an earlier prompt, you decided that the whiteboard should be
                            updated to better explain the tutorial topic to the student. In particular, you provided the following description 
                            for the changes that should be implemented to the whiteboard in this turn
                            Update description:
                            \"\"\"{update_description}\"\"\"

                            Your response MUST be EXACTLY this JSON (no additional text):

                            {{
                              "text": "An instructional reply to the student that goes hand-in-hand with your whiteboard changes that helps advance the learning objective from the lesson topic.",
                              "appState": {{ ... }},
                              "elements": [ ... ]
                            }}
                            , where "appState" and "elements" describe the Excalidraw whiteboard state.

                            '{best_attempt}'
                            """
    )


def build_step2_generation_prompt_end(
    shapes_section: str = "",
    intersection_section: str = ""
) -> str:
    """
    Build Step 2 prompt end with rules and guidelines.
    
    Args:
        shapes_section: Optional shapes template section
        intersection_section: Optional intersection analysis section
        
    Returns:
        Formatted prompt string with rules
    """
    return f"""
                            Rules:
                            - "appState" must include keys: viewBackgroundColor, gridSize, zoom (with value, translation), offsetLeft, offsetTop.
                            - "elements" must include ALL elements (old and updated/deleted/added) with required keys:
                            id, type, x, y, width, height, strokeColor, backgroundColor, strokeWidth, strokeStyle, fillStyle,
                            angle, opacity, seed, version, versionNonce, isDeleted (bool), groupIds (list), locked (bool), boundElements (list),
                            link (null if none), frameId (null if none), roughness (number), roundness (null or number).
                            - For "text" type elements you MUST include:
                            text, originalText, fontSize (>=14), fontFamily (numeric), textAlign, verticalAlign, autoResize=true, lineHeight (or null), containerId (null if none), angle (numeric).
                            *originalText MUST exactly match text (same characters, same spelling, no abbreviation, no extra whitespace).* Do NOT abbreviate or stylize words.
                            Use basic Latin letters and digits only for labels (avoid unusual Unicode glyphs/ligatures).
                            Compute and output final numeric bounding-box values that can contain the text, using this rule (numeric values only):
                                padding_px = 5
                                longest_line_chars = length of the longest line in text (count characters)
                                required_width = ceil(fontSize * 0.55 * longest_line_chars + 2 * padding_px)
                                required_height = ceil(fontSize * 1.2 * number_of_lines + 2 * padding_px)
                            Then set element "width" = max(provided width, required_width) and "height" = max(provided height, required_height).
                            If the text is intended to sit inside a container (containerId != null), ensure the text bounding box (x,y,width,height) is fully inside the container's bounds; if not, expand the container's width/height (and update its numeric width/height fields) so text is not clipped.
                            - For "arrow" or "line" type elements you MUST include:
                            points (list of [x, y]), startBinding (null or object), endBinding (null or object), lastCommittedPoint (null or [x,y]), arrowhead (string or null).
                            - Do NOT add extraneous fields outside of these.
                            - When removing objects, delete the element entirely from the "elements" list (do NOT hide it with isDeleted=true).
                            - All numeric fields must be raw numbers (no expressions like "10+5" or "fontSize*1.2"); compute the numbers and output them.
                            - If "fillStyle" is "solid", "backgroundColor" must be a visible color (not "transparent").
                            - If "backgroundColor" is "transparent", use a visible fillStyle like "hachure" or "cross-hatch".
                            - Avoid "fillStyle": "solid" with "backgroundColor": "transparent".
                            - JSON must be valid and directly parseable (no markdown, no surrounding text).
                            - All text inside elements (like "width", "length", formulas, or labels) must be fully visible, not clipped or truncated. 
                            Always set autoResize=true, ensure a minimum padding of 5px, and expand bounding boxes or container shapes as needed.
                            - Use center alignment for labels inside shapes by default unless explicitly specified otherwise.
                            
                            {shapes_section}
                            
                            {intersection_section}
                            
                            CRITICAL: If geometric analysis is provided above, you MUST:
                            - Use the analysis results to answer the student's question accurately
                            - If analysis shows lines intersect, mention the exact intersection point coordinates in your "text" response
                            - If analysis shows lines are parallel, state this clearly in your response
                            - Ensure your whiteboard drawing matches the geometric relationships described in the analysis
                            - If the student asks about intersections/parallel lines, reference the analysis directly in your response
                            """


def build_step3_comparison_prompt_with_images(
    prompt_scaffold: str,
    update_description: str,
    old_image_base64: str,
    new_image_base64: str
) -> List[Dict[str, Any]]:
    """
    Build Step 3 prompt for comparing old and new whiteboard images with actual base64 images.
    
    Args:
        prompt_scaffold: Main scaffold prompt
        update_description: Description of requested changes
        old_image_base64: Base64-encoded old whiteboard image
        new_image_base64: Base64-encoded new whiteboard image
        
    Returns:
        List of message content dictionaries for vision API
    """
    return [
        {
            "type": "text",
            "text": (
                prompt_scaffold
                + "You will now act as an expert whiteboard comparator judging a tutor's implemented changes to a whiteboard. "
                "You will be provided with two images (first, the old whiteboard, and then, the new whiteboard with changes). "
                "Your task is to compare the two whiteboard images and report whether the changes between the two images align with the textual description of "
                "the changes requested (which is provided last). :\n"
                "Old whiteboard:"
            ),
        },
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{old_image_base64}"
            },
        },
        {"type": "text", "text": "New whiteboard:"},
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{new_image_base64}"
            },
        },
        {
            "type": "text",
            "text": (
                "Requested change Description: "
                + update_description
                + ".\n"
                "Please respond ONLY in JSON format with two fields:\n"
                '- "reliable" (boolean): true if the changes in the images match the description, false otherwise.\n'
                '- "message" (string): explanation if "reliable" is false, otherwise an empty string.'
                '- "grade" (integer): A reliability score from 0 to 10 indicating how good the attempt is. If the old whiteboard is a better starting point than this attempt, '
                "return a score of -1. Also, a reliable change is a 10."
            ),
        },
    ]


def build_no_draw_response_prompt(prompt_scaffold: str) -> str:
    """
    Build prompt for Step 2 when no whiteboard update is needed.
    
    Args:
        prompt_scaffold: Main scaffold prompt
        
    Returns:
        Formatted prompt string
    """
    return (
        prompt_scaffold
        + f"""
                Upon viewing the student's latest response in an earlier prompt, you decided that the whiteboard should NOT be
                updated. As a result, given the earlier conversation history, please provide a response that is pedagogical, insightful, and helpful to 
                the student. The response should help them learn the topic better.
                
                CRITICAL: Keep your response SHORT and CONCISE (2-3 sentences maximum). Be natural and conversational, not verbose.
                Answer the question directly without over-explaining. Be friendly but get to the point quickly.
                
                Your response MUST be EXACTLY this JSON (no additional text):

                {{
                    "text": "A short, natural, and helpful reply to the student (2-3 sentences max).",
                }}

            """
    )


def build_sympy_result_section_success(
    operation: str,
    operation_result: Dict[str, Any]
) -> str:
    """
    Build SymPy result section when operation succeeds.
    
    Args:
        operation: The mathematical operation performed
        operation_result: Result dictionary from the operation
        
    Returns:
        Formatted result section string
    """
    return f"""
        
        MATHEMATICAL OPERATION RESULT (from SymPy):
        Operation: {operation}
        Result: {operation_result.get('message', '')}
        Details: {json.dumps(operation_result.get('result', {}), indent=2)}
        
        IMPORTANT: Use this exact result in your response. If the user asked to draw the result, add it to the whiteboard.
        Provide a SHORT, natural, human-like explanation (2-3 sentences max). Be concise and direct.
        """


def build_sympy_result_section_llm_fallback(
    operation: str,
    llm_required_shapes: List[Dict[str, Any]] = None
) -> str:
    """
    Build SymPy result section when operation requires LLM fallback.
    
    Args:
        operation: The mathematical operation requested
        llm_required_shapes: Optional list of shapes that require LLM analysis
        
    Returns:
        Formatted result section string
    """
    if llm_required_shapes:
        return f"""
        
        IMPORTANT: The user asked about '{operation}' on a freedraw shape that could not be converted to SymPy format.
        The whiteboard contains {len(llm_required_shapes)} unconvertible freedraw shape(s) that require visual analysis.
        
        You should:
        - Analyze the shape(s) visually from the whiteboard image
        - Provide a helpful, educational response about the requested operation
        - If the shape is too abstract/random, politely explain the limitation and suggest drawing recognizable geometric shapes
        - Always respond in a friendly, helpful manner - never say "I can't" or "error"
        - Use your mathematical knowledge to provide the best possible answer based on what you can see
        """
    else:
        return f"""
        
        NOTE: The user asked about '{operation}', but this operation is not available in SymPy.
        Please handle this request using your mathematical knowledge.
        """

