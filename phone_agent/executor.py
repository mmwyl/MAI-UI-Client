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

"""Autonomous Task Executor for Phone Agent Framework.

This module implements the main execution loop that orchestrates multi-step
task execution by repeatedly invoking the agent and executing predicted actions.
"""

import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict

from phone_agent.device_bridge import DeviceBridge
from phone_agent.integration import AgentIntegration, ActionParseError, ActionValidationError
from phone_agent.config import Config
from phone_agent.utils import pil_to_base64, truncate_text


logger = logging.getLogger(__name__)


@dataclass
class ExecutionStep:
    """Single step in task execution trajectory."""
    step_number: int
    timestamp: str
    screenshot_b64: Optional[str]
    thinking: Optional[str]
    action: Dict[str, Any]
    action_result: str  # "success", "failed", or "skipped"
    error: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class ExecutionResult:
    """Result of task execution."""
    task_id: str
    instruction: str
    status: str  # "success", "failed", "timeout", "interrupted"
    total_steps: int
    duration_seconds: float
    trajectory: List[ExecutionStep]
    final_message: Optional[str] = None
    error: Optional[str] = None


class TaskExecutor:
    """
    Autonomous task executor for multi-step Android automation.
    
    Orchestrates the execution loop:
    1. Capture observation (screenshot)
    2. Agent predicts next action
    3. Execute action on device
    4. Check termination conditions
    5. Repeat until FINISH or max steps
    
    Attributes:
        agent_integration: AgentIntegration instance
        config: Configuration object
        trajectory: List of execution steps
    """
    
    def __init__(
        self,
        agent_integration: AgentIntegration,
        config: Config,
        user_prompt_handler: Optional[Callable[[str], str]] = None,
    ):
        """
        Initialize Task Executor.
        
        Args:
            agent_integration: AgentIntegration instance.
            config: Configuration object.
            user_prompt_handler: Optional callback for ask_user actions.
        """
        self.agent_integration = agent_integration
        self.config = config
        self.user_prompt_handler = user_prompt_handler or self._default_user_prompt
        self.trajectory: List[ExecutionStep] = []
        self.task_id: str = ""
        
        logger.info("Initialized TaskExecutor")
    
    def execute_task(self, instruction: str) -> ExecutionResult:
        """
        Execute a complete task autonomously.
        
        Args:
            instruction: Natural language task instruction.
            
        Returns:
            ExecutionResult with status and trajectory.
        """
        self.task_id = self._generate_task_id()
        self.trajectory = []
        start_time = time.time()
        
        logger.info(f"Starting task execution: {instruction}")
        logger.info(f"Task ID: {self.task_id}")
        
        # Reset agent trajectory
        self.agent_integration.agent.reset()
        
        try:
            # Main execution loop
            done = False
            step_count = 0
            max_steps = self.config.execution.max_steps
            
            while not done and step_count < max_steps:
                step_count += 1
                logger.info(f"=== Step {step_count}/{max_steps} ===")
                
                try:
                    # Execute single step
                    action_result, should_finish = self._execute_step(
                        instruction, step_count, max_steps
                    )
                    
                    if should_finish:
                        done = True
                        logger.info("Task completed: FINISH action received")
                    
                    # Delay between actions
                    if not done and step_count < max_steps:
                        time.sleep(self.config.execution.screenshot_delay)
                
                except KeyboardInterrupt:
                    logger.warning("Task interrupted by user (Ctrl+C)")
                    duration = time.time() - start_time
                    return self._create_result(
                        instruction, "interrupted", step_count, duration,
                        final_message="Task interrupted by user"
                    )
                
                except Exception as e:
                    logger.error(f"Step {step_count} failed: {e}")
                    
                    # Try to retry if configured
                    if self._should_retry(e):
                        logger.info("Retrying step...")
                        continue
                    else:
                        # Fatal error, abort task
                        duration = time.time() - start_time
                        return self._create_result(
                            instruction, "failed", step_count, duration,
                            error=str(e)
                        )
            
            # Task completed
            duration = time.time() - start_time
            
            if done:
                status = "success"
                final_message = "Task completed successfully"
            else:
                status = "timeout"
                final_message = f"Reached maximum steps ({max_steps}) without completion"
            
            logger.info(f"Task finished: {status} in {duration:.2f}s with {step_count} steps")
            
            result = self._create_result(
                instruction, status, step_count, duration, final_message=final_message
            )
            
            # Save trajectory
            self._save_trajectory(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Fatal error during task execution: {e}")
            duration = time.time() - start_time
            return self._create_result(
                instruction, "failed", 0, duration, error=str(e)
            )
    
    def _execute_step(
        self, instruction: str, step_number: int, max_steps: int
    ) -> tuple[str, bool]:
        """
        Execute a single step of the task.
        
        Args:
            instruction: Task instruction.
            step_number: Current step number.
            max_steps: Maximum steps allowed.
            
        Returns:
            Tuple of (action_result, should_finish).
        """
        step_start_time = time.time()
        
        # 1. Capture observation
        logger.debug("Capturing screenshot...")
        screenshot = self.agent_integration.device_bridge.capture_screenshot(format="pil")
        
        observation = self.agent_integration.format_observation(
            screenshot,
            include_metadata=True,
            step_count=step_number,
            max_steps=max_steps,
        )
        
        # 2. Get prediction from agent
        logger.debug("Getting agent prediction...")
        try:
            prediction_text, action, thinking = self.agent_integration.predict_and_execute(
                instruction, observation
            )
        except (ActionParseError, ActionValidationError) as e:
            # Record failed step
            self._record_step(
                step_number, screenshot, None, {}, "failed", error=str(e),
                execution_time_ms=(time.time() - step_start_time) * 1000
            )
            raise
        
        logger.info(f"Agent thinking: {truncate_text(thinking or 'N/A', 100)}")
        logger.info(f"Agent action: {action['action']}")
        
        # 3. Handle special actions
        should_finish = False
        action_result = "success"
        
        if action["action"] == "FINISH":
            should_finish = True
            action_result = "success"
        
        elif action["action"] == "ask_user":
            # Handle user interaction
            question = action.get("question", "Agent needs input")
            logger.info(f"Agent asks: {question}")
            
            try:
                user_response = self.user_prompt_handler(question)
                logger.info(f"User response: {user_response}")
                # TODO: Inject response into next observation
                action_result = "success"
            except Exception as e:
                logger.error(f"User prompt failed: {e}")
                action_result = "failed"
                raise
        
        elif action["action"] == "mcp_call":
            # Handle MCP tool call (placeholder)
            tool_name = action.get("tool", "unknown")
            logger.info(f"MCP call: {tool_name}")
            logger.warning("MCP tool calls not yet implemented")
            action_result = "skipped"
        
        # 4. Record step
        execution_time_ms = (time.time() - step_start_time) * 1000
        self._record_step(
            step_number, screenshot, thinking, action, action_result,
            execution_time_ms=execution_time_ms
        )
        
        return action_result, should_finish
    
    def _record_step(
        self,
        step_number: int,
        screenshot: Any,
        thinking: Optional[str],
        action: Dict[str, Any],
        result: str,
        error: Optional[str] = None,
        execution_time_ms: float = 0.0,
    ) -> None:
        """Record execution step in trajectory."""
        # Convert screenshot to base64 for storage
        screenshot_b64 = None
        if screenshot and self.config.logging.save_screenshots:
            try:
                screenshot_b64 = pil_to_base64(screenshot)
            except Exception as e:
                logger.warning(f"Failed to encode screenshot: {e}")
        
        step = ExecutionStep(
            step_number=step_number,
            timestamp=datetime.now().isoformat(),
            screenshot_b64=screenshot_b64,
            thinking=thinking,
            action=action,
            action_result=result,
            error=error,
            execution_time_ms=execution_time_ms,
        )
        
        self.trajectory.append(step)
    
    def _should_retry(self, error: Exception) -> bool:
        """Determine if error is retryable."""
        # For now, don't retry any errors
        # TODO: Implement retry logic for specific error types
        return False
    
    def _default_user_prompt(self, question: str) -> str:
        """Default user prompt handler (CLI input)."""
        print(f"\n🤖 Agent asks: {question}")
        response = input("Your response: ")
        return response
    
    def _generate_task_id(self) -> str:
        """Generate unique task ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"task_{timestamp}_{unique_id}"
    
    def _create_result(
        self,
        instruction: str,
        status: str,
        total_steps: int,
        duration: float,
        final_message: Optional[str] = None,
        error: Optional[str] = None,
    ) -> ExecutionResult:
        """Create execution result object."""
        return ExecutionResult(
            task_id=self.task_id,
            instruction=instruction,
            status=status,
            total_steps=total_steps,
            duration_seconds=duration,
            trajectory=self.trajectory,
            final_message=final_message,
            error=error,
        )
    
    def _save_trajectory(self, result: ExecutionResult) -> None:
        """Save trajectory to JSON file."""
        if not self.config.logging.save_trajectory:
            return
        
        try:
            # Create log directory
            log_dir = Path(self.config.logging.output_dir) / self.task_id
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Convert result to dict
            result_dict = {
                "task_id": result.task_id,
                "instruction": result.instruction,
                "status": result.status,
                "total_steps": result.total_steps,
                "duration_seconds": result.duration_seconds,
                "final_message": result.final_message,
                "error": result.error,
                "trajectory": [asdict(step) for step in result.trajectory],
            }
            
            # Save to JSON
            trajectory_file = log_dir / "trajectory.json"
            with open(trajectory_file, "w", encoding="utf-8") as f:
                json.dump(result_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved trajectory to: {trajectory_file}")
            
        except Exception as e:
            logger.error(f"Failed to save trajectory: {e}")
