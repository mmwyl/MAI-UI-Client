#!/usr/bin/env python3
# Copyright (c) 2025, Alibaba Cloud and its affiliates;
# Licensed under the Apache License, Version 2.0

"""
MAI Phone Agent - Simple CLI like Open-AutoGLM

Usage:
    python main.py --device-id 10.31.0.210:10030 --base-url http://localhost:8000/v1 --model "MAI-UI-8B" "打开抖音刷视频"
"""

import argparse
import logging
import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mai_phone_agent.device_bridge_simple import DeviceBridge
from mai_naivigation_agent import MAIUINaivigationAgent


def setup_logging(debug=False):
    """Setup logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )


def main():
    parser = argparse.ArgumentParser(description="MAI Phone Agent - Autonomous Android Control")
    parser.add_argument("instruction", help="Task instruction in natural language")
    parser.add_argument("--device-id", required=True, help="Device serial (e.g., 192.168.1.100:5555)")
    parser.add_argument("--base-url", default="http://localhost:8000/v1", help="Model API base URL")
    parser.add_argument("--model", default="MAI-UI-8B", help="Model name")
    parser.add_argument("--apikey", default=None, help="API key for model authentication (optional, defaults to EMPTY for local vLLM)")
    parser.add_argument("--max-steps", type=int, default=50, help="Maximum steps")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    setup_logging(args.debug)
    logger = logging.getLogger(__name__)
    
    print(f"🚀 MAI Phone Agent")
    print(f"📱 Device: {args.device_id}")
    print(f"🤖 Model: {args.model} @ {args.base_url}")
    print(f"📝 Task: {args.instruction}\n")
    
    try:
        # Connect to device
        print("📱 Connecting to device...")
        device = DeviceBridge(device_serial=args.device_id)
        info = device.get_device_info()
        print(f"✅ Connected: {info['model']} (Android {info['android_version']})\n")
        
        # Initialize agent
        print("🤖 Loading agent...")
        agent = MAIUINaivigationAgent(
            llm_base_url=args.base_url,
            model_name=args.model,
            api_key=args.apikey,
            runtime_conf={
                "history_n": 3,
                "temperature": 0.0,
                "top_k": -1,
                "top_p": 1.0,
                "max_tokens": 2048,
            }
        )
        print("✅ Agent loaded\n")
        
        # Execute task
        print(f"⚡ Executing task (max {args.max_steps} steps)...\n")
        
        step = 0
        done = False
        
        while not done and step < args.max_steps:
            step += 1
            print(f"=== Step {step}/{args.max_steps} ===")
            
            # Capture screenshot
            screenshot = device.capture_screenshot(format="pil")
            obs = {"screenshot": screenshot}
            
            # Get prediction
            prediction_text, action_dict = agent.predict(args.instruction, obs)
            
            # Parse action
            action_type = action_dict.get("action", "unknown")
            print(f"Action: {action_type}")
            
            if action_type == "terminate":
                status = action_dict.get("status", "success")
                done = True
                print(f"✅ Task {status}!")
                break
            
            elif action_type == "open":
                app_name = action_dict.get("text", "")
                print(f"  Opening app: {app_name}")
                # Try to launch the app
                # For simplicity, we'll use the package name mapping
                # You might need to add a proper app name to package mapping
                try:
                    device._adb_command("shell", "monkey", "-p", f"com.android.{app_name.lower()}", "1")
                except:
                    print(f"  Warning: Could not launch {app_name}, trying generic launch...")
            
            elif action_type == "click":
                coord = action_dict["coordinate"]
                # MAI-UI agent already normalizes coordinates to [0, 1] range
                x = int(coord[0] * device.screen_width)
                y = int(coord[1] * device.screen_height)
                print(f"  Tap at ({x}, {y}) - normalized: [{coord[0]:.3f}, {coord[1]:.3f}]")
                device.tap(x, y)
            
            elif action_type == "swipe":
                # Swipe has two formats:
                # 1. Direction-based: {"action": "swipe", "direction": "up/down/left/right", "coordinate": [x, y]}
                # 2. Coordinate-based: {"action": "swipe", "start": [x1, y1], "end": [x2, y2]}
                
                if "direction" in action_dict:
                    # Direction-based swipe
                    direction = action_dict["direction"]
                    coord = action_dict.get("coordinate", [0.5, 0.5])  # Default to center
                    
                    # Convert coordinate to pixels
                    center_x = int(coord[0] * device.screen_width)
                    center_y = int(coord[1] * device.screen_height)
                    
                    # Calculate swipe start and end based on direction
                    swipe_distance = min(device.screen_width, device.screen_height) // 3
                    
                    if direction == "up":
                        x1, y1 = center_x, center_y + swipe_distance // 2
                        x2, y2 = center_x, center_y - swipe_distance // 2
                    elif direction == "down":
                        x1, y1 = center_x, center_y - swipe_distance // 2
                        x2, y2 = center_x, center_y + swipe_distance // 2
                    elif direction == "left":
                        x1, y1 = center_x + swipe_distance // 2, center_y
                        x2, y2 = center_x - swipe_distance // 2, center_y
                    elif direction == "right":
                        x1, y1 = center_x - swipe_distance // 2, center_y
                        x2, y2 = center_x + swipe_distance // 2, center_y
                    else:
                        print(f"  Unknown swipe direction: {direction}")
                        continue
                    
                    print(f"  Swipe {direction} from ({x1}, {y1}) to ({x2}, {y2})")
                    device.swipe(x1, y1, x2, y2)
                    
                elif "start" in action_dict and "end" in action_dict:
                    # Coordinate-based swipe
                    start = action_dict["start"]
                    end = action_dict["end"]
                    # MAI-UI agent already normalizes coordinates to [0, 1] range
                    x1 = int(start[0] * device.screen_width)
                    y1 = int(start[1] * device.screen_height)
                    x2 = int(end[0] * device.screen_width)
                    y2 = int(end[1] * device.screen_height)
                    print(f"  Swipe from ({x1}, {y1}) to ({x2}, {y2})")
                    device.swipe(x1, y1, x2, y2)
                else:
                    print(f"  Invalid swipe action: missing direction or start/end coordinates")

            
            elif action_type == "type":
                text = action_dict["text"]
                print(f"  Type: {text}")
                device.type_text(text)
            
            elif action_type == "long_press":
                coord = action_dict["coordinate"]
                # Normalization 0-1 -> pixels
                x = int(coord[0] * device.screen_width)
                y = int(coord[1] * device.screen_height)
                print(f"  Long press at ({x}, {y})")
                device.long_press(x, y)

            elif action_type == "drag":
                start = action_dict["start_coordinate"]
                end = action_dict["end_coordinate"]
                # Normalization 0-1 -> pixels
                x1 = int(start[0] * device.screen_width)
                y1 = int(start[1] * device.screen_height)
                x2 = int(end[0] * device.screen_width)
                y2 = int(end[1] * device.screen_height)
                print(f"  Drag from ({x1}, {y1}) to ({x2}, {y2})")
                # Drag is essentially a slow swipe
                device.swipe(x1, y1, x2, y2, duration=1000)

            elif action_type == "system_button":
                button = action_dict.get("button", "back")
                print(f"  Press {button} button")
                if button == "back":
                    device.press_back()
                elif button == "home":
                    device.press_home()
                elif button == "menu" or button == "recent":
                    device.press_recent()
                elif button == "enter":
                    device._adb_command("shell", "input", "keyevent", "66") # KEYCODE_ENTER
            
            elif action_type == "wait":
                print("  Waiting...")
                import time
                time.sleep(1)
            
            elif action_type == "answer":
                text = action_dict.get("text", "")
                print(f"  Agent answer: {text}")
                # Answer usually means task is complete
                done = True
            
            else:
                print(f"  Unknown action: {action_type}")
            
            # Wait between actions
            import time
            time.sleep(0.5)
        
        if not done:
            print(f"\n⏱️  Reached max steps ({args.max_steps})")
        
        print(f"\n✅ Execution completed in {step} steps")
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    main()
