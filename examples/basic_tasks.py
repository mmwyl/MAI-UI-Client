#!/usr/bin/env python3
# Copyright (c) 2025, Alibaba Cloud and its affiliates;
# Licensed under the Apache License, Version 2.0

"""
Basic Phone Agent usage examples.

This script demonstrates how to use the Phone Agent Framework programmatically.
"""

from phone_agent.config import Config
from phone_agent.device_bridge import DeviceBridge
from phone_agent.integration import AgentIntegration
from phone_agent.executor import TaskExecutor
from src.mai_naivigation_agent import MAIUINaivigationAgent


def example_1_simple_task():
    """Example 1: Execute a simple task."""
    print("="*60)
    print("Example 1: Simple Task Execution")
    print("="*60)
    
    # Load configuration
    config = Config.load()
    
    # Connect to device
    print("Connecting to device...")
    device = DeviceBridge()
    print(f"Connected to: {device.get_device_info()['model']}")
    
    # Initialize agent
    print("Loading agent...")
    agent = MAIUINaivigationAgent(
        llm_base_url=config.model.base_url,
        model_name=config.model.name,
    )
    
    # Create integration and executor
    integration = AgentIntegration(agent, device)
    executor = TaskExecutor(integration, config)
    
    # Execute task
    instruction = "Open settings"
    print(f"Executing: {instruction}")
    
    result = executor.execute_task(instruction)
    
    print(f"\nResult: {result.status}")
    print(f"Steps: {result.total_steps}")
    print(f"Duration: {result.duration_seconds:.2f}s")


def example_2_custom_config():
    """Example 2: Use custom configuration."""
    print("\n" + "="*60)
    print("Example 2: Custom Configuration")
    print("="*60)
    
    # Create custom config
    config = Config()
    config.model.base_url = "http://localhost:8000/v1"
    config.model.name = "MAI-UI-8B"
    config.execution.max_steps = 30
    config.execution.screenshot_delay = 1.0
    
    print(f"Model: {config.model.name}")
    print(f"Max steps: {config.execution.max_steps}")
    
    # Rest is same as example 1...


def example_3_list_devices():
    """Example 3: List all connected devices."""
    print("\n" + "="*60)
    print("Example 3: List Devices")
    print("="*60)
    
    device = DeviceBridge()
    devices = device.list_devices()
    
    print(f"Found {len(devices)} device(s):\n")
    for dev in devices:
        print(f"  Serial: {dev['serial']}")
        print(f"  Model: {dev.get('model', 'Unknown')}")
        print(f"  Android: {dev.get('android_version', 'Unknown')}")
        print()


def example_4_device_actions():
    """Example 4: Execute device actions directly."""
    print("\n" + "="*60)
    print("Example 4: Direct Device Actions")
    print("="*60)
    
    device = DeviceBridge()
    
    # Capture screenshot
    print("Capturing screenshot...")
    screenshot = device.capture_screenshot(format="pil")
    print(f"Screenshot size: {screenshot.size}")
    
    # Execute tap
    print("Tapping at center...")
    center_x = device.screen_width // 2
    center_y = device.screen_height // 2
    device.tap(center_x, center_y)
    
    # Press back
    print("Pressing back button...")
    device.press_back()
    
    print("Done!")


def example_5_trajectory_analysis():
    """Example 5: Analyze saved trajectory."""
    import json
    from pathlib import Path
    
    print("\n" + "="*60)
    print("Example 5: Trajectory Analysis")
    print("="*60)
    
    # Find latest trajectory
    config = Config.load()
    log_dir = Path(config.logging.output_dir)
    
    if not log_dir.exists():
        print("No trajectories found")
        return
    
    # Get all task directories
    task_dirs = sorted(log_dir.glob("task_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not task_dirs:
        print("No trajectories found")
        return
    
    # Load latest trajectory
    latest_trajectory = task_dirs[0] / "trajectory.json"
    
    if not latest_trajectory.exists():
        print("No trajectory file found")
        return
    
    print(f"Loading: {latest_trajectory}")
    
    with open(latest_trajectory, "r") as f:
        data = json.load(f)
    
    print(f"\nTask: {data['instruction']}")
    print(f"Status: {data['status']}")
    print(f"Steps: {data['total_steps']}")
    print(f"Duration: {data['duration_seconds']:.2f}s")
    
    # Analyze actions
    actions = [step['action']['action'] for step in data['trajectory']]
    action_counts = {}
    for action in actions:
        action_counts[action] = action_counts.get(action, 0) + 1
    
    print("\nAction distribution:")
    for action, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {action}: {count}")


if __name__ == "__main__":
    # Run examples
    try:
        example_3_list_devices()
        # Uncomment to run other examples:
        # example_1_simple_task()
        # example_2_custom_config()
        # example_4_device_actions()
        # example_5_trajectory_analysis()
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
