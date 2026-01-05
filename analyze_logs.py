#!/usr/bin/env python3
# Copyright (c) 2025, Alibaba Cloud and its affiliates;
# Licensed under the Apache License, Version 2.0

"""
日志分析工具 - 用于复盘Agent执行过程

Usage:
    python analyze_logs.py logs/session_20260105_195000
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Any


def load_session_logs(session_dir: Path) -> Dict[str, Any]:
    """加载会话日志"""
    session_dir = Path(session_dir)
    
    if not session_dir.exists():
        raise FileNotFoundError(f"Session directory not found: {session_dir}")
    
    # 加载任务信息
    task_info_file = session_dir / "task_info.json"
    if task_info_file.exists():
        with open(task_info_file, "r", encoding="utf-8") as f:
            task_info = json.load(f)
    else:
        task_info = {}
    
    # 加载执行日志
    execution_log_file = session_dir / "execution_log.json"
    if execution_log_file.exists():
        with open(execution_log_file, "r", encoding="utf-8") as f:
            execution_log = json.load(f)
    else:
        # 尝试加载单独的步骤日志
        execution_log = []
        step_files = sorted(session_dir.glob("step_*_log.json"))
        for step_file in step_files:
            with open(step_file, "r", encoding="utf-8") as f:
                execution_log.append(json.load(f))
    
    return {
        "task_info": task_info,
        "execution_log": execution_log,
        "session_dir": session_dir
    }


def extract_thinking(raw_prediction: str) -> str:
    """从原始预测中提取thinking内容"""
    import re
    match = re.search(r"<thinking>(.*?)</thinking>", raw_prediction, re.DOTALL)
    if match:
        return match.group(1).strip()
    return "N/A"


def analyze_session(session_data: Dict[str, Any]) -> None:
    """分析会话并生成报告"""
    task_info = session_data["task_info"]
    execution_log = session_data["execution_log"]
    session_dir = session_data["session_dir"]
    
    print("=" * 80)
    print("📊 Agent 执行复盘分析报告")
    print("=" * 80)
    print()
    
    # 任务信息
    print("📝 任务信息:")
    print(f"  时间: {task_info.get('timestamp', 'N/A')}")
    print(f"  指令: {task_info.get('instruction', 'N/A')}")
    print(f"  设备: {task_info.get('device_id', 'N/A')}")
    print(f"  模型: {task_info.get('model', 'N/A')}")
    print(f"  总步数: {len(execution_log)}")
    print()
    
    # 逐步分析
    print("🔍 逐步执行分析:")
    print("-" * 80)
    
    for step_data in execution_log:
        step = step_data.get("step", 0)
        action = step_data.get("action", {})
        raw_prediction = step_data.get("raw_prediction", "")
        screenshot_file = step_data.get("screenshot_file", "")
        
        action_type = action.get("action", "unknown")
        
        print(f"\n【步骤 {step}】")
        print(f"  动作类型: {action_type}")
        
        # 显示动作详情
        if action_type == "click":
            coord = action.get("coordinate", [])
            print(f"  点击坐标: {coord}")
        elif action_type == "type":
            text = action.get("text", "")
            print(f"  输入文本: {text}")
        elif action_type == "open":
            app_name = action.get("text", "")
            print(f"  打开应用: {app_name}")
        elif action_type == "swipe":
            direction = action.get("direction", "")
            print(f"  滑动方向: {direction}")
        elif action_type in ["terminate", "answer"]:
            text = action.get("text", "") or action.get("status", "")
            print(f"  结果: {text}")
        
        # 提取并显示thinking过程
        thinking = extract_thinking(raw_prediction)
        if thinking != "N/A":
            print(f"  思考过程:")
            for line in thinking.split("\n"):
                if line.strip():
                    print(f"    {line.strip()}")
        
        # 截图文件
        if screenshot_file:
            screenshot_path = session_dir / screenshot_file
            if screenshot_path.exists():
                print(f"  截图: {screenshot_path}")
    
    print()
    print("-" * 80)
    print()
    
    # 动作统计
    print("📈 动作统计:")
    action_counts = {}
    for step_data in execution_log:
        action_type = step_data.get("action", {}).get("action", "unknown")
        action_counts[action_type] = action_counts.get(action_type, 0) + 1
    
    for action_type, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {action_type}: {count} 次")
    
    print()
    print("=" * 80)
    print(f"📂 完整日志目录: {session_dir}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="分析Agent执行日志")
    parser.add_argument("session_dir", help="会话日志目录路径")
    parser.add_argument("--export", help="导出分析报告到文件")
    
    args = parser.parse_args()
    
    try:
        session_data = load_session_logs(args.session_dir)
        analyze_session(session_data)
        
        if args.export:
            # TODO: 实现导出功能
            print(f"\n💾 导出功能待实现: {args.export}")
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
