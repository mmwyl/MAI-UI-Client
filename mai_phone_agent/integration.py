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

"""Agent Integration Layer for Phone Agent Framework.

This module provides the glue between MAI-UI agents and the device bridge,
handling observation formatting, action parsing, and coordinate transformation.
"""

import logging
from typing import Dict, Any, Tuple, Optional
from PIL import Image

from mai_phone_agent.device_bridge import DeviceBridge
from mai_phone_agent.utils import (
    parse_tagged_text,
    normalize_coordinate,
    validate_action,
    format_error_message,
)


logger = logging.getLogger(__name__)


class AgentIntegrationError(Exception):
    """Base exception for agent integration errors."""
    pass


class ActionParseError(AgentIntegrationError):
    """Raised when action parsing fails."""
    pass


class ActionValidationError(AgentIntegrationError):
    """Raised when action validation fails."""
    pass


class AgentIntegration:
    """
    Integration layer between MAI-UI agents and device bridge.
    
    Handles:
    - Observation formatting for agent input
    - Action parsing and validation from agent output
    - Coordinate transformation (normalized to pixels)
    - Error mapping and user-friendly messages
    
    Attributes:
        agent: MAI-UI agent instance (MAIUINaivigationAgent or MAIGroundingAgent)
        device_bridge: DeviceBridge instance for device control
        screen_width: Device screen width in pixels
        screen_height: Device screen height in pixels
    """
    
    def __init__(self, agent: Any, device_bridge: DeviceBridge):
        """
        Initialize Agent Integration.
        
        Args:
            agent: MAI-UI agent instance with predict() method.
            device_bridge: DeviceBridge instance.
            
        Raises:
            ValueError: If agent doesn't have predict() method.
        """
        if not hasattr(agent, "predict"):
            raise ValueError("Agent must have predict() method")
        
        self.agent = agent
        self.device_bridge = device_bridge
        self.screen_width = device_bridge.screen_width
        self.screen_height = device_bridge.screen_height
        
        logger.info(
            f"Initialized AgentIntegration with screen size: "
            f"{self.screen_width}x{self.screen_height}"
        )
    
    def format_observation(
        self,
        screenshot: Any,
        include_metadata: bool = False,
        step_count: Optional[int] = None,
        max_steps: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Format observation for agent input.
        
        Args:
            screenshot: Screenshot as PIL Image or bytes.
            include_metadata: Whether to include execution metadata.
            step_count: Current step number (if include_metadata=True).
            max_steps: Maximum steps (if include_metadata=True).
            
        Returns:
            Observation dictionary compatible with agent.predict().
        """
        obs = {"screenshot": screenshot}
        
        if include_metadata and step_count is not None and max_steps is not None:
            obs["step_count"] = step_count
            obs["max_steps"] = max_steps
        
        return obs
    
    def parse_prediction(self, prediction_text: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Parse agent prediction into thinking and action.
        
        Args:
            prediction_text: Raw prediction text from agent.
            
        Returns:
            Tuple of (thinking, action_dict).
            
        Raises:
            ActionParseError: If parsing fails.
        """
        try:
            parsed = parse_tagged_text(prediction_text)
            thinking = parsed.get("thinking")
            action = parsed.get("tool_call")
            
            if action is None:
                raise ActionParseError(
                    "No tool_call found in prediction. "
                    "Agent must output <tool_call>{...}</tool_call> tags."
                )
            
            return thinking, action
            
        except ValueError as e:
            raise ActionParseError(f"Failed to parse prediction: {e}")
    
    def validate_and_transform_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate action and transform coordinates from normalized to pixels.
        
        Args:
            action: Action dictionary from agent.
            
        Returns:
            Transformed action with pixel coordinates.
            
        Raises:
            ActionValidationError: If action is invalid.
        """
        # Validate action structure
        is_valid, error_msg = validate_action(action)
        if not is_valid:
            raise ActionValidationError(error_msg)
        
        # Transform coordinates for actions that need it
        action_type = action["action"]
        transformed_action = action.copy()
        
        if action_type == "tap":
            coord = action["coordinate"]
            transformed_action["coordinate"] = self._transform_coordinate(coord)
        
        elif action_type == "swipe":
            start = action["start"]
            end = action["end"]
            transformed_action["start"] = self._transform_coordinate(start)
            transformed_action["end"] = self._transform_coordinate(end)
        
        elif action_type == "long_press":
            coord = action["coordinate"]
            transformed_action["coordinate"] = self._transform_coordinate(coord)
        
        return transformed_action
    
    def _transform_coordinate(self, normalized_coord: list) -> Tuple[int, int]:
        """
        Transform normalized [0, 1] coordinate to pixel coordinate.
        
        Args:
            normalized_coord: [x, y] in range [0, 1].
            
        Returns:
            Tuple of (pixel_x, pixel_y).
            
        Raises:
            ActionValidationError: If coordinates are out of range.
        """
        x_norm, y_norm = normalized_coord
        
        # Validate range
        if not (0 <= x_norm <= 1 and 0 <= y_norm <= 1):
            raise ActionValidationError(
                f"Coordinates must be in [0, 1] range. Got: [{x_norm}, {y_norm}]"
            )
        
        # Transform to pixels
        pixel_x = normalize_coordinate(x_norm, self.screen_width)
        pixel_y = normalize_coordinate(y_norm, self.screen_height)
        
        # Ensure within bounds
        pixel_x = max(0, min(pixel_x, self.screen_width - 1))
        pixel_y = max(0, min(pixel_y, self.screen_height - 1))
        
        return (pixel_x, pixel_y)
    
    def execute_action(self, action: Dict[str, Any]) -> None:
        """
        Execute action on device.
        
        Args:
            action: Validated and transformed action dictionary.
            
        Raises:
            ActionExecutionError: If action execution fails.
        """
        import time
        
        action_type = action["action"]
        
        try:
            # 点击类动作
            if action_type in ["tap", "click"]:
                x, y = action["coordinate"]
                self.device_bridge.tap(x, y)
                logger.info(f"Executed {action_type} at ({x}, {y})")
            
            elif action_type == "double_click":
                x, y = action["coordinate"]
                self.device_bridge.tap(x, y)
                time.sleep(0.1)
                self.device_bridge.tap(x, y)
                logger.info(f"Executed double_click at ({x}, {y})")
            
            elif action_type == "long_press":
                x, y = action["coordinate"]
                duration = action.get("duration", 1000)
                self.device_bridge.long_press(x, y, duration)
                logger.info(f"Executed long press at ({x}, {y})")
            
            # 滑动和拖拽
            elif action_type == "swipe":
                if "start" in action and "end" in action:
                    x1, y1 = action["start"]
                    x2, y2 = action["end"]
                else:
                    # Direction-based swipe - 需要在调用前转换
                    logger.warning("Direction-based swipe not handled in integration layer")
                    return
                duration = action.get("duration", 300)
                self.device_bridge.swipe(x1, y1, x2, y2, duration)
                logger.info(f"Executed swipe from ({x1}, {y1}) to ({x2}, {y2})")
            
            elif action_type == "drag":
                x1, y1 = action["start_coordinate"]
                x2, y2 = action["end_coordinate"]
                self.device_bridge.swipe(x1, y1, x2, y2, 1000)  # Drag 是慢速 swipe
                logger.info(f"Executed drag from ({x1}, {y1}) to ({x2}, {y2})")
            
            # 多指手势
            elif action_type == "pinch":
                x, y = action["coordinate"]
                direction = action.get("direction", "out")
                offset = 100
                if direction == "out":  # 放大
                    self.device_bridge._adb_command("shell", "input", "swipe", 
                        str(x), str(y), str(x - offset), str(y - offset), "300")
                    self.device_bridge._adb_command("shell", "input", "swipe", 
                        str(x), str(y), str(x + offset), str(y + offset), "300")
                else:  # 缩小
                    self.device_bridge._adb_command("shell", "input", "swipe", 
                        str(x - offset), str(y - offset), str(x), str(y), "300")
                    self.device_bridge._adb_command("shell", "input", "swipe", 
                        str(x + offset), str(y + offset), str(x), str(y), "300")
                logger.info(f"Executed pinch {direction} at ({x}, {y})")
            
            elif action_type == "rotate":
                x, y = action["coordinate"]
                direction = action.get("direction", "clockwise")
                offset = 80
                if direction == "clockwise":
                    self.device_bridge._adb_command("shell", "input", "swipe", 
                        str(x - offset), str(y), str(x), str(y - offset), "300")
                    self.device_bridge._adb_command("shell", "input", "swipe", 
                        str(x + offset), str(y), str(x), str(y + offset), "300")
                else:
                    self.device_bridge._adb_command("shell", "input", "swipe", 
                        str(x), str(y - offset), str(x - offset), str(y), "300")
                    self.device_bridge._adb_command("shell", "input", "swipe", 
                        str(x), str(y + offset), str(x + offset), str(y), "300")
                logger.info(f"Executed rotate {direction} at ({x}, {y})")
            
            # 输入
            elif action_type == "type":
                text = action["text"]
                result = self.device_bridge.type_text(text)
                # 兼容新旧返回值格式
                if isinstance(result, tuple):
                    success, error_msg = result
                    if not success:
                        logger.warning(f"Type text failed: {error_msg}")
                logger.info(f"Typed text: {text[:50]}...")
            
            # 系统按钮
            elif action_type == "system_button":
                button = action.get("button", "back")
                if button == "back":
                    self.device_bridge.press_back()
                elif button == "home":
                    self.device_bridge.press_home()
                elif button in ["menu", "recent"]:
                    self.device_bridge.press_recent()
                elif button == "enter":
                    self.device_bridge._adb_command("shell", "input", "keyevent", "66")
                logger.info(f"Pressed {button} button")
            
            elif action_type == "back":
                self.device_bridge.press_back()
                logger.info("Pressed back button")
            
            elif action_type == "home":
                self.device_bridge.press_home()
                logger.info("Pressed home button")
            
            elif action_type == "recent":
                self.device_bridge.press_recent()
                logger.info("Pressed recent apps button")
            
            # 等待和记录
            elif action_type == "wait":
                duration = action.get("duration", 2)
                duration = min(max(1, int(duration)), 60)  # 限制 1-60 秒
                time.sleep(duration)
                logger.info(f"Waited {duration} seconds")
            
            elif action_type == "note":
                note_text = action.get("text", "")
                logger.info(f"Note: {note_text}")
                # note 动作不执行设备操作，仅记录
            
            # 应用控制
            elif action_type == "open":
                app_name = action.get("text", "")
                # 这个通常由 executor 处理，因为需要应用映射
                logger.info(f"Open app: {app_name}")
            
            # 任务控制 - 由 executor 处理
            elif action_type in ["FINISH", "terminate", "answer", "ask_user", "mcp_call"]:
                logger.debug(f"Action {action_type} handled by executor")
            
            else:
                raise ActionValidationError(f"Unknown action type: {action_type}")
                
        except Exception as e:
            error_msg = format_error_message(e, f"executing {action_type}")
            logger.error(error_msg)
            raise
    
    def predict_and_execute(
        self,
        instruction: str,
        observation: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any], Optional[str]]:
        """
        Full pipeline: predict action from observation and execute it.
        
        Args:
            instruction: Task instruction for agent.
            observation: Observation dictionary.
            
        Returns:
            Tuple of (prediction_text, action_dict, thinking).
            
        Raises:
            AgentIntegrationError: If prediction or execution fails.
        """
        try:
            # Get prediction from agent
            logger.debug("Calling agent.predict()...")
            prediction_text, action_dict = self.agent.predict(instruction, observation)
            
            # Parse prediction
            thinking, parsed_action = self.parse_prediction(prediction_text)
            
            # Validate and transform action
            transformed_action = self.validate_and_transform_action(parsed_action)
            
            # Execute action (if not a special action)
            if transformed_action["action"] not in ["FINISH", "ask_user", "mcp_call"]:
                self.execute_action(transformed_action)
            
            return prediction_text, transformed_action, thinking
            
        except ActionParseError as e:
            logger.error(f"Action parse error: {e}")
            raise
        except ActionValidationError as e:
            logger.error(f"Action validation error: {e}")
            raise
        except Exception as e:
            error_msg = format_error_message(e, "predict_and_execute")
            logger.error(error_msg)
            raise AgentIntegrationError(error_msg)
    
    def map_error_to_user_message(self, error: Exception) -> str:
        """
        Map technical error to user-friendly message.
        
        Args:
            error: Exception object.
            
        Returns:
            User-friendly error message with suggestions.
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Device connection errors
        if "DeviceDisconnected" in error_type or "connection" in error_msg.lower():
            return (
                "❌ Device disconnected. Please check USB connection.\n"
                "Suggestions:\n"
                "  1. Replug USB cable\n"
                "  2. Run `mai-phone devices` to verify connection\n"
                "  3. Restart ADB server: `adb kill-server && adb start-server`"
            )
        
        # Model/agent errors
        if "timeout" in error_msg.lower() or "connection refused" in error_msg.lower():
            return (
                "❌ Model is not responding. Check if model server is running.\n"
                "Suggestions:\n"
                "  1. Verify model URL in config\n"
                "  2. Run `mai-phone doctor` to diagnose\n"
                "  3. Check vLLM server logs"
            )
        
        # Action validation errors
        if "ActionValidation" in error_type:
            return (
                f"❌ Invalid action from agent: {error_msg}\n"
                "This is likely a model issue. The agent predicted an invalid action."
            )
        
        # Generic error
        return f"❌ Error: {error_msg}"
