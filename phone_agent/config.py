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

"""Configuration management for Phone Agent Framework."""

import os
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from pathlib import Path
import yaml


# Default configuration directory
DEFAULT_CONFIG_DIR = Path.home() / ".mai-phone"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"
DEFAULT_LOG_DIR = DEFAULT_CONFIG_DIR / "logs"


@dataclass
class ModelConfig:
    """Model configuration."""
    base_url: str = "http://localhost:8000/v1"
    name: str = "MAI-UI-8B"
    temperature: float = 0.0
    top_k: int = -1
    top_p: float = 1.0
    max_tokens: int = 2048
    history_n: int = 3


@dataclass
class DeviceConfig:
    """Device configuration."""
    serial: Optional[str] = None
    adb_server: str = "127.0.0.1:5037"


@dataclass
class ExecutionConfig:
    """Execution configuration."""
    max_steps: int = 50
    screenshot_delay: float = 0.5
    retry_attempts: int = 3
    use_accessibility_tree: bool = False
    ask_timeout: int = 120  # seconds


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    save_trajectory: bool = True
    output_dir: str = str(DEFAULT_LOG_DIR)
    save_screenshots: bool = True


@dataclass
class Config:
    """
    Main configuration for Phone Agent Framework.
    
    Attributes:
        model: Model configuration
        device: Device configuration
        execution: Execution configuration
        logging: Logging configuration
    """
    model: ModelConfig = field(default_factory=ModelConfig)
    device: DeviceConfig = field(default_factory=DeviceConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to config file. If None, uses default location.
            
        Returns:
            Config instance with loaded settings.
        """
        if config_path is None:
            config_path = DEFAULT_CONFIG_FILE
        
        # Return defaults if config file doesn't exist
        if not config_path.exists():
            return cls()
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            # Parse nested configs
            model_config = ModelConfig(**data.get("model", {}))
            device_config = DeviceConfig(**data.get("device", {}))
            execution_config = ExecutionConfig(**data.get("execution", {}))
            logging_config = LoggingConfig(**data.get("logging", {}))
            
            return cls(
                model=model_config,
                device=device_config,
                execution=execution_config,
                logging=logging_config,
            )
        except Exception as e:
            raise ValueError(f"Failed to load config from {config_path}: {e}")
    
    def save(self, config_path: Optional[Path] = None) -> None:
        """
        Save configuration to YAML file.
        
        Args:
            config_path: Path to save config. If None, uses default location.
        """
        if config_path is None:
            config_path = DEFAULT_CONFIG_FILE
        
        # Create config directory if it doesn't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict
        data = {
            "model": asdict(self.model),
            "device": asdict(self.device),
            "execution": asdict(self.execution),
            "logging": asdict(self.logging),
        }
        
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise ValueError(f"Failed to save config to {config_path}: {e}")
    
    def merge_cli_args(self, **kwargs) -> "Config":
        """
        Merge CLI arguments into config (CLI args take precedence).
        
        Args:
            **kwargs: CLI arguments to merge.
            
        Returns:
            New Config instance with merged values.
        """
        # Create a copy
        import copy
        config = copy.deepcopy(self)
        
        # Map CLI args to config fields
        arg_mapping = {
            "model_url": ("model", "base_url"),
            "model_name": ("model", "name"),
            "device_serial": ("device", "serial"),
            "max_steps": ("execution", "max_steps"),
            "debug": ("logging", "level"),
            "use_accessibility_tree": ("execution", "use_accessibility_tree"),
        }
        
        for cli_arg, (section, field) in arg_mapping.items():
            if cli_arg in kwargs and kwargs[cli_arg] is not None:
                value = kwargs[cli_arg]
                
                # Special handling for debug flag
                if cli_arg == "debug" and value:
                    value = "DEBUG"
                
                # Set the value
                section_obj = getattr(config, section)
                setattr(section_obj, field, value)
        
        return config
    
    @classmethod
    def from_env(cls) -> "Config":
        """
        Load configuration from environment variables.
        
        Environment variables:
            MAI_PHONE_MODEL_URL: Model base URL
            MAI_PHONE_MODEL_NAME: Model name
            MAI_PHONE_DEVICE_SERIAL: Device serial number
            MAI_PHONE_MAX_STEPS: Maximum execution steps
            MAI_PHONE_LOG_LEVEL: Logging level
            
        Returns:
            Config instance with values from environment.
        """
        config = cls()
        
        # Model config
        if url := os.getenv("MAI_PHONE_MODEL_URL"):
            config.model.base_url = url
        if name := os.getenv("MAI_PHONE_MODEL_NAME"):
            config.model.name = name
        
        # Device config
        if serial := os.getenv("MAI_PHONE_DEVICE_SERIAL"):
            config.device.serial = serial
        
        # Execution config
        if max_steps := os.getenv("MAI_PHONE_MAX_STEPS"):
            try:
                config.execution.max_steps = int(max_steps)
            except ValueError:
                pass
        
        # Logging config
        if log_level := os.getenv("MAI_PHONE_LOG_LEVEL"):
            config.logging.level = log_level.upper()
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert config to dictionary.
        
        Returns:
            Dictionary representation of config.
        """
        return {
            "model": asdict(self.model),
            "device": asdict(self.device),
            "execution": asdict(self.execution),
            "logging": asdict(self.logging),
        }
    
    def validate(self) -> None:
        """
        Validate configuration values.
        
        Raises:
            ValueError: If configuration is invalid.
        """
        # Validate model config
        if not self.model.base_url:
            raise ValueError("Model base_url cannot be empty")
        if self.model.temperature < 0 or self.model.temperature > 2:
            raise ValueError("Model temperature must be between 0 and 2")
        if self.model.history_n < 0:
            raise ValueError("Model history_n must be non-negative")
        
        # Validate execution config
        if self.execution.max_steps < 1:
            raise ValueError("Execution max_steps must be at least 1")
        if self.execution.screenshot_delay < 0:
            raise ValueError("Execution screenshot_delay must be non-negative")
        if self.execution.retry_attempts < 0:
            raise ValueError("Execution retry_attempts must be non-negative")
        
        # Validate logging config
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.logging.level.upper() not in valid_log_levels:
            raise ValueError(f"Logging level must be one of {valid_log_levels}")


def init_config_dir() -> Path:
    """
    Initialize configuration directory.
    
    Creates ~/.mai-phone/ directory and subdirectories if they don't exist.
    
    Returns:
        Path to config directory.
    """
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_CONFIG_DIR


def create_default_config() -> Config:
    """
    Create and save default configuration file.
    
    Returns:
        Default Config instance.
    """
    init_config_dir()
    config = Config()
    config.save()
    return config
