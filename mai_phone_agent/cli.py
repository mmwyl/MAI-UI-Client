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

"""Command-Line Interface for Phone Agent Framework."""

import sys
import logging
from pathlib import Path
from typing import Optional

import click

from mai_phone_agent import __version__
from mai_phone_agent.config import Config, create_default_config, DEFAULT_CONFIG_FILE
from mai_phone_agent.device_bridge import DeviceBridge, DeviceNotFoundError
from mai_phone_agent.integration import AgentIntegration
from mai_phone_agent.executor import TaskExecutor


# Configure logging
def setup_logging(level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--version", is_flag=True, help="Show version and exit")
def cli(ctx, version):
    """
    MAI Phone Agent - Autonomous Android control for MAI-UI models.
    
    Control your Android phone with natural language commands.
    
    Examples:
      mai-phone "open Xiaohongshu and search nearby food"
      mai-phone "book a train ticket to Shanghai"
      mai-phone devices
      mai-phone config show
    """
    if version:
        click.echo(f"MAI Phone Agent v{__version__}")
        ctx.exit()
    
    # If no subcommand, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.argument("instruction", required=True)
@click.option("--model-url", help="Model API base URL")
@click.option("--model-name", help="Model name")
@click.option("--device-serial", "--device-id", help="Device serial number (ADB serial)", envvar="PHONE_AGENT_DEVICE_SERIAL")
@click.option("--base-url", help="Model API base URL", envvar="PHONE_AGENT_BASE_URL")
@click.option("--model", help="Model name", envvar="PHONE_AGENT_MODEL")
@click.option("--max-steps", type=int, help="Maximum execution steps")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--use-accessibility-tree", is_flag=True, help="Use accessibility tree")
def run(instruction, model_url, model_name, device_serial, max_steps, debug, use_accessibility_tree):
    """
    Execute a task on Android device.
    
    INSTRUCTION: Natural language task description
    
    Examples:
      mai-phone run "open settings and enable WiFi"
      mai-phone run "search for coffee shops on Xiaohongshu"
    """
    # Setup logging
    log_level = "DEBUG" if debug else "INFO"
    setup_logging(log_level)
    
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = Config.load()
        
        # Merge CLI arguments
        cli_args = {
            "model_url": model_url,
            "model_name": model_name,
            "device_serial": device_serial,
            "max_steps": max_steps,
            "debug": debug,
            "use_accessibility_tree": use_accessibility_tree,
        }
        config = config.merge_cli_args(**cli_args)
        
        # Validate config
        config.validate()
        
        click.echo(f"🚀 Starting task: {instruction}")
        click.echo(f"📱 Model: {config.model.name} @ {config.model.base_url}")
        
        # Connect to device
        click.echo("📱 Connecting to Android device...")
        device_bridge = DeviceBridge(device_serial=config.device.serial)
        device_info = device_bridge.get_device_info()
        click.echo(f"✅ Connected: {device_info['model']} (Android {device_info['android_version']})")
        
        # Initialize agent
        click.echo("🤖 Loading MAI-UI agent...")
        from src.mai_naivigation_agent import MAIUINaivigationAgent
        
        agent = MAIUINaivigationAgent(
            llm_base_url=config.model.base_url,
            model_name=config.model.name,
            runtime_conf={
                "history_n": config.model.history_n,
                "temperature": config.model.temperature,
                "top_k": config.model.top_k,
                "top_p": config.model.top_p,
                "max_tokens": config.model.max_tokens,
            },
        )
        
        # Create integration and executor
        integration = AgentIntegration(agent, device_bridge)
        executor = TaskExecutor(integration, config)
        
        # Execute task
        click.echo(f"⚡ Executing task (max {config.execution.max_steps} steps)...\n")
        
        result = executor.execute_task(instruction)
        
        # Display results
        click.echo("\n" + "="*60)
        if result.status == "success":
            click.secho(f"✅ Task completed successfully!", fg="green", bold=True)
        elif result.status == "timeout":
            click.secho(f"⏱️  Task timed out", fg="yellow", bold=True)
        elif result.status == "interrupted":
            click.secho(f"🛑 Task interrupted", fg="yellow", bold=True)
        else:
            click.secho(f"❌ Task failed", fg="red", bold=True)
        
        click.echo(f"📊 Steps: {result.total_steps}")
        click.echo(f"⏱️  Duration: {result.duration_seconds:.2f}s")
        
        if result.final_message:
            click.echo(f"💬 {result.final_message}")
        
        if result.error:
            click.secho(f"❌ Error: {result.error}", fg="red")
        
        # Show trajectory path
        if config.logging.save_trajectory:
            log_path = Path(config.logging.output_dir) / result.task_id / "trajectory.json"
            click.echo(f"\n📝 Trajectory saved: {log_path}")
            click.echo(f"   Replay with: mai-phone replay {log_path}")
        
        click.echo("="*60)
        
        # Exit with appropriate code
        sys.exit(0 if result.status == "success" else 1)
        
    except DeviceNotFoundError as e:
        click.secho(f"❌ {e}", fg="red")
        sys.exit(1)
    except Exception as e:
        logger.exception("Fatal error")
        click.secho(f"❌ Fatal error: {e}", fg="red")
        sys.exit(1)


@cli.command()
def devices():
    """List connected Android devices."""
    try:
        click.echo("📱 Scanning for Android devices...\n")
        
        device_bridge = DeviceBridge()
        devices_list = device_bridge.list_devices()
        
        if not devices_list:
            click.secho("No devices found.", fg="yellow")
            click.echo("\nMake sure:")
            click.echo("  1. Device is connected via USB")
            click.echo("  2. USB debugging is enabled")
            click.echo("  3. ADB drivers are installed")
            return
        
        # Display devices table
        click.echo(f"Found {len(devices_list)} device(s):\n")
        click.echo(f"{'Serial':<20} {'State':<10} {'Model':<25} {'Android':<10}")
        click.echo("-" * 70)
        
        for device in devices_list:
            serial = device['serial']
            state = device['state']
            model = device.get('model', 'Unknown')
            version = device.get('android_version', 'Unknown')
            
            # Color code by state
            if state == "device":
                state_colored = click.style(state, fg="green")
            else:
                state_colored = click.style(state, fg="yellow")
            
            click.echo(f"{serial:<20} {state_colored:<10} {model:<25} {version:<10}")
        
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg="red")
        sys.exit(1)


@cli.group()
def config():
    """Manage configuration."""
    pass


@config.command("show")
def config_show():
    """Show current configuration."""
    try:
        cfg = Config.load()
        
        click.echo("📋 Current Configuration:\n")
        click.echo("Model:")
        click.echo(f"  base_url: {cfg.model.base_url}")
        click.echo(f"  name: {cfg.model.name}")
        click.echo(f"  temperature: {cfg.model.temperature}")
        click.echo(f"  history_n: {cfg.model.history_n}")
        
        click.echo("\nDevice:")
        click.echo(f"  serial: {cfg.device.serial or 'auto-detect'}")
        click.echo(f"  adb_server: {cfg.device.adb_server}")
        
        click.echo("\nExecution:")
        click.echo(f"  max_steps: {cfg.execution.max_steps}")
        click.echo(f"  screenshot_delay: {cfg.execution.screenshot_delay}s")
        click.echo(f"  retry_attempts: {cfg.execution.retry_attempts}")
        
        click.echo("\nLogging:")
        click.echo(f"  level: {cfg.logging.level}")
        click.echo(f"  save_trajectory: {cfg.logging.save_trajectory}")
        click.echo(f"  output_dir: {cfg.logging.output_dir}")
        
        if DEFAULT_CONFIG_FILE.exists():
            click.echo(f"\n📄 Config file: {DEFAULT_CONFIG_FILE}")
        else:
            click.echo(f"\n⚠️  No config file found. Using defaults.")
            click.echo(f"   Create one with: mai-phone config init")
        
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg="red")
        sys.exit(1)


@config.command("init")
@click.option("--force", is_flag=True, help="Overwrite existing config")
def config_init(force):
    """Initialize configuration file."""
    try:
        if DEFAULT_CONFIG_FILE.exists() and not force:
            click.secho(f"Config file already exists: {DEFAULT_CONFIG_FILE}", fg="yellow")
            click.echo("Use --force to overwrite")
            return
        
        click.echo("📝 Creating default configuration...")
        cfg = create_default_config()
        
        click.secho(f"✅ Config file created: {DEFAULT_CONFIG_FILE}", fg="green")
        click.echo("\nEdit the file to customize settings.")
        
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg="red")
        sys.exit(1)


@cli.command()
def doctor():
    """Check system setup and diagnose issues."""
    click.echo("🏥 Running diagnostics...\n")
    
    all_ok = True
    
    # Check ADB
    click.echo("1. Checking ADB...")
    try:
        device_bridge = DeviceBridge()
        click.secho("   ✅ ADB is working", fg="green")
    except Exception as e:
        click.secho(f"   ❌ ADB error: {e}", fg="red")
        all_ok = False
    
    # Check devices
    click.echo("\n2. Checking devices...")
    try:
        devices_list = device_bridge.list_devices()
        if devices_list:
            click.secho(f"   ✅ Found {len(devices_list)} device(s)", fg="green")
        else:
            click.secho("   ⚠️  No devices found", fg="yellow")
            all_ok = False
    except Exception as e:
        click.secho(f"   ❌ Error: {e}", fg="red")
        all_ok = False
    
    # Check config
    click.echo("\n3. Checking configuration...")
    try:
        cfg = Config.load()
        cfg.validate()
        click.secho("   ✅ Configuration is valid", fg="green")
    except Exception as e:
        click.secho(f"   ❌ Config error: {e}", fg="red")
        all_ok = False
    
    # Check model endpoint
    click.echo("\n4. Checking model endpoint...")
    try:
        import requests
        cfg = Config.load()
        response = requests.get(f"{cfg.model.base_url}/models", timeout=5)
        if response.status_code == 200:
            click.secho(f"   ✅ Model server is reachable", fg="green")
        else:
            click.secho(f"   ⚠️  Model server returned {response.status_code}", fg="yellow")
    except Exception as e:
        click.secho(f"   ❌ Cannot reach model server: {e}", fg="red")
        click.echo(f"      Make sure vLLM server is running at {cfg.model.base_url}")
        all_ok = False
    
    # Summary
    click.echo("\n" + "="*60)
    if all_ok:
        click.secho("✅ All checks passed! System is ready.", fg="green", bold=True)
    else:
        click.secho("⚠️  Some issues found. Please fix them before running tasks.", fg="yellow", bold=True)
    click.echo("="*60)


@cli.command()
@click.argument("trajectory_file", type=click.Path(exists=True))
def replay(trajectory_file):
    """Replay a saved trajectory."""
    import json
    
    try:
        click.echo(f"📼 Replaying trajectory: {trajectory_file}\n")
        
        with open(trajectory_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        click.echo(f"Task ID: {data['task_id']}")
        click.echo(f"Instruction: {data['instruction']}")
        click.echo(f"Status: {data['status']}")
        click.echo(f"Total steps: {data['total_steps']}")
        click.echo(f"Duration: {data['duration_seconds']:.2f}s")
        click.echo("\n" + "="*60)
        
        for step in data['trajectory']:
            click.echo(f"\nStep {step['step_number']}:")
            click.echo(f"  Timestamp: {step['timestamp']}")
            if step.get('thinking'):
                click.echo(f"  Thinking: {step['thinking'][:100]}...")
            click.echo(f"  Action: {step['action']}")
            click.echo(f"  Result: {step['action_result']}")
            if step.get('error'):
                click.secho(f"  Error: {step['error']}", fg="red")
            click.echo(f"  Time: {step['execution_time_ms']:.0f}ms")
            
            input("  Press Enter for next step...")
        
        click.echo("\n" + "="*60)
        click.echo("✅ Replay complete")
        
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg="red")
        sys.exit(1)


def main():
    """Main entry point for CLI."""
    # Make 'run' the default command when instruction is provided directly
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-") and sys.argv[1] not in ["devices", "config", "doctor", "replay", "run"]:
        # Insert 'run' command
        sys.argv.insert(1, "run")
    
    cli()


if __name__ == "__main__":
    main()
