# Copyright (c) 2025, Alibaba Cloud and its affiliates;
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions for Phone Agent Framework."""

import base64
import io
import json
import re
from typing import Dict, Any, Tuple, Optional
from PIL import Image


def pil_to_base64(image: Image.Image) -> str:
    """
    Convert PIL Image to base64 string.
    
    Args:
        image: PIL Image object.
        
    Returns:
        Base64 encoded string.
    """
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def base64_to_pil(b64_string: str) -> Image.Image:
    """
    Convert base64 string to PIL Image.
    
    Args:
        b64_string: Base64 encoded image string.
        
    Returns:
        PIL Image object.
    """
    img_bytes = base64.b64decode(b64_string)
    return Image.open(io.BytesIO(img_bytes))


def bytes_to_pil(img_bytes: bytes) -> Image.Image:
    """
    Convert bytes to PIL Image.
    
    Args:
        img_bytes: Image bytes.
        
    Returns:
        PIL Image object.
    """
    return Image.open(io.BytesIO(img_bytes))


def pil_to_bytes(image: Image.Image, format: str = "PNG") -> bytes:
    """
    Convert PIL Image to bytes.
    
    Args:
        image: PIL Image object.
        format: Image format (PNG, JPEG, etc.).
        
    Returns:
        Image bytes.
    """
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    return buffered.getvalue()


def parse_tagged_text(text: str) -> Dict[str, Any]:
    """
    Parse text containing XML-style tags to extract thinking and tool_call content.
    
    Args:
        text: Text containing <thinking> and <tool_call> tags.
        
    Returns:
        Dictionary with keys:
            - "thinking": Content inside <thinking> tags (str or None)
            - "tool_call": Parsed JSON content inside <tool_call> tags (dict or None)
            
    Raises:
        ValueError: If tool_call content is not valid JSON.
    """
    result = {
        "thinking": None,
        "tool_call": None,
    }
    
    # Extract thinking
    thinking_match = re.search(r"<thinking>(.*?)</thinking>", text, re.DOTALL)
    if thinking_match:
        result["thinking"] = thinking_match.group(1).strip()
    
    # Extract tool_call
    tool_call_match = re.search(r"<tool_call>(.*?)</tool_call>", text, re.DOTALL)
    if tool_call_match:
        tool_call_str = tool_call_match.group(1).strip()
        try:
            result["tool_call"] = json.loads(tool_call_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in tool_call tag: {e}\nContent: {tool_call_str}")
    
    return result


def normalize_coordinate(coord: float, max_value: int) -> int:
    """
    Convert normalized coordinate [0, 1] to pixel coordinate.
    
    Args:
        coord: Normalized coordinate in range [0, 1].
        max_value: Maximum pixel value (screen width or height).
        
    Returns:
        Pixel coordinate as integer.
    """
    return int(coord * max_value)


def denormalize_coordinate(pixel: int, max_value: int) -> float:
    """
    Convert pixel coordinate to normalized [0, 1] coordinate.
    
    Args:
        pixel: Pixel coordinate.
        max_value: Maximum pixel value (screen width or height).
        
    Returns:
        Normalized coordinate in range [0, 1].
    """
    return pixel / max_value


def validate_action(action: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate action dictionary structure.
    
    Args:
        action: Action dictionary to validate.
        
    Returns:
        Tuple of (is_valid, error_message).
    """
    if not isinstance(action, dict):
        return False, "Action must be a dictionary"
    
    if "action" not in action:
        return False, "Action must have 'action' key"
    
    action_type = action["action"]
    
    # Valid action types
    valid_actions = [
        "tap", "swipe", "type", "long_press",
        "back", "home", "recent",
        "FINISH", "ask_user", "mcp_call"
    ]
    
    if action_type not in valid_actions:
        return False, f"Invalid action type: {action_type}. Must be one of {valid_actions}"
    
    # Validate parameters for each action type
    if action_type == "tap":
        if "coordinate" not in action:
            return False, "tap action requires 'coordinate' field"
        coord = action["coordinate"]
        if not isinstance(coord, (list, tuple)) or len(coord) != 2:
            return False, "coordinate must be [x, y] list"
        if not all(isinstance(c, (int, float)) for c in coord):
            return False, "coordinate values must be numeric"
    
    elif action_type == "swipe":
        if "start" not in action or "end" not in action:
            return False, "swipe action requires 'start' and 'end' fields"
        for field in ["start", "end"]:
            coord = action[field]
            if not isinstance(coord, (list, tuple)) or len(coord) != 2:
                return False, f"{field} must be [x, y] list"
    
    elif action_type == "type":
        if "text" not in action:
            return False, "type action requires 'text' field"
        if not isinstance(action["text"], str):
            return False, "text must be a string"
    
    elif action_type == "long_press":
        if "coordinate" not in action:
            return False, "long_press action requires 'coordinate' field"
    
    elif action_type == "ask_user":
        if "question" not in action:
            return False, "ask_user action requires 'question' field"
    
    elif action_type == "mcp_call":
        if "tool" not in action or "args" not in action:
            return False, "mcp_call action requires 'tool' and 'args' fields"
    
    return True, None


def format_error_message(error: Exception, context: Optional[str] = None) -> str:
    """
    Format error message with context for user display.
    
    Args:
        error: Exception object.
        context: Optional context string.
        
    Returns:
        Formatted error message.
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    if context:
        return f"[{error_type}] {context}: {error_msg}"
    return f"[{error_type}] {error_msg}"


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to maximum length with ellipsis.
    
    Args:
        text: Text to truncate.
        max_length: Maximum length.
        
    Returns:
        Truncated text.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
