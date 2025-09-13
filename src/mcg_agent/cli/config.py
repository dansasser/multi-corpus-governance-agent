"""
CLI Configuration Module
Configuration management for the MCG Agent CLI
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

from pydantic import BaseModel, Field
from rich.console import Console

console = Console()


class CLIConfig(BaseModel):
    """CLI-specific configuration settings"""
    
    # Output settings
    verbose: bool = Field(default=False, description="Enable verbose output")
    quiet: bool = Field(default=False, description="Suppress non-essential output")
    color: bool = Field(default=True, description="Enable colored output")
    
    # Server settings
    default_host: str = Field(default="0.0.0.0", description="Default server host")
    default_port: int = Field(default=8000, description="Default server port")
    default_workers: int = Field(default=1, description="Default number of workers")
    
    # Query settings
    default_corpus: Optional[str] = Field(default=None, description="Default corpus for queries")
    default_format: str = Field(default="text", description="Default output format")
    query_timeout: int = Field(default=30, description="Query timeout in seconds")
    
    # Import/Export settings
    max_file_size: int = Field(default=100 * 1024 * 1024, description="Maximum file size for import (bytes)")
    batch_size: int = Field(default=1000, description="Batch size for data processing")
    
    # Health check settings
    health_timeout: int = Field(default=10, description="Health check timeout in seconds")
    health_retries: int = Field(default=3, description="Number of health check retries")
    
    class Config:
        env_prefix = "MCG_CLI_"
        case_sensitive = False


class CLIConfigManager:
    """Manages CLI configuration from various sources"""
    
    def __init__(self):
        self._config: Optional[CLIConfig] = None
        self._config_file_path = self._find_config_file()
    
    def _find_config_file(self) -> Optional[Path]:
        """Find CLI configuration file in standard locations"""
        possible_paths = [
            Path.cwd() / ".mcg-cli.json",
            Path.home() / ".config" / "mcg-agent" / "cli.json",
            Path.home() / ".mcg-agent" / "cli.json",
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None
    
    def load_config(self) -> CLIConfig:
        """Load configuration from environment and config file"""
        if self._config is not None:
            return self._config
        
        config_data = {}
        
        # Load from config file if it exists
        if self._config_file_path:
            try:
                import json
                with open(self._config_file_path, 'r') as f:
                    file_config = json.load(f)
                    config_data.update(file_config)
            except Exception as e:
                console.print(f"⚠️  Warning: Could not load config file {self._config_file_path}: {e}", style="yellow")
        
        # Environment variables override file config
        env_config = self._load_from_env()
        config_data.update(env_config)
        
        self._config = CLIConfig(**config_data)
        return self._config
    
    def _load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        env_config = {}
        
        # Map environment variables to config fields
        env_mappings = {
            'MCG_CLI_VERBOSE': ('verbose', bool),
            'MCG_CLI_QUIET': ('quiet', bool),
            'MCG_CLI_COLOR': ('color', bool),
            'MCG_CLI_DEFAULT_HOST': ('default_host', str),
            'MCG_CLI_DEFAULT_PORT': ('default_port', int),
            'MCG_CLI_DEFAULT_WORKERS': ('default_workers', int),
            'MCG_CLI_DEFAULT_CORPUS': ('default_corpus', str),
            'MCG_CLI_DEFAULT_FORMAT': ('default_format', str),
            'MCG_CLI_QUERY_TIMEOUT': ('query_timeout', int),
            'MCG_CLI_MAX_FILE_SIZE': ('max_file_size', int),
            'MCG_CLI_BATCH_SIZE': ('batch_size', int),
            'MCG_CLI_HEALTH_TIMEOUT': ('health_timeout', int),
            'MCG_CLI_HEALTH_RETRIES': ('health_retries', int),
        }
        
        for env_var, (config_key, config_type) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    if config_type == bool:
                        env_config[config_key] = value.lower() in ('true', '1', 'yes', 'on')
                    elif config_type == int:
                        env_config[config_key] = int(value)
                    else:
                        env_config[config_key] = value
                except ValueError as e:
                    console.print(f"⚠️  Warning: Invalid value for {env_var}: {value} ({e})", style="yellow")
        
        return env_config
    
    def save_config(self, config: CLIConfig) -> bool:
        """Save configuration to file"""
        try:
            # Create config directory if it doesn't exist
            config_dir = Path.home() / ".config" / "mcg-agent"
            config_dir.mkdir(parents=True, exist_ok=True)
            
            config_file = config_dir / "cli.json"
            
            with open(config_file, 'w') as f:
                import json
                json.dump(config.dict(), f, indent=2)
            
            console.print(f"✅ Configuration saved to {config_file}", style="green")
            return True
            
        except Exception as e:
            console.print(f"❌ Failed to save configuration: {e}", style="red")
            return False
    
    def get_config(self) -> CLIConfig:
        """Get current configuration"""
        return self.load_config()
    
    def reset_config(self) -> CLIConfig:
        """Reset configuration to defaults"""
        self._config = CLIConfig()
        return self._config
    
    def update_config(self, **kwargs) -> CLIConfig:
        """Update configuration with new values"""
        current_config = self.get_config()
        updated_data = current_config.dict()
        updated_data.update(kwargs)
        
        self._config = CLIConfig(**updated_data)
        return self._config


# Global config manager instance
config_manager = CLIConfigManager()


def get_cli_config() -> CLIConfig:
    """Get the current CLI configuration"""
    return config_manager.get_config()


def update_cli_config(**kwargs) -> CLIConfig:
    """Update CLI configuration with new values"""
    return config_manager.update_config(**kwargs)


def save_cli_config(config: CLIConfig) -> bool:
    """Save CLI configuration to file"""
    return config_manager.save_config(config)


def reset_cli_config() -> CLIConfig:
    """Reset CLI configuration to defaults"""
    return config_manager.reset_config()


# CLI configuration validation
def validate_cli_environment() -> Dict[str, Any]:
    """Validate CLI environment and return status"""
    validation_results = {
        'valid': True,
        'issues': [],
        'warnings': []
    }
    
    config = get_cli_config()
    
    # Check if required directories exist
    required_dirs = [
        Path.cwd() / "src",
        Path.cwd() / "tests",
    ]
    
    for dir_path in required_dirs:
        if not dir_path.exists():
            validation_results['warnings'].append(f"Directory not found: {dir_path}")
    
    # Check if virtual environment is active
    if not os.getenv('VIRTUAL_ENV'):
        validation_results['warnings'].append("Virtual environment not detected")
    
    # Check if package is installed
    try:
        import mcg_agent
    except ImportError:
        validation_results['issues'].append("MCG Agent package not installed")
        validation_results['valid'] = False
    
    # Check configuration values
    if config.default_port < 1 or config.default_port > 65535:
        validation_results['issues'].append(f"Invalid port number: {config.default_port}")
        validation_results['valid'] = False
    
    if config.query_timeout < 1:
        validation_results['issues'].append(f"Invalid query timeout: {config.query_timeout}")
        validation_results['valid'] = False
    
    return validation_results


__all__ = [
    'CLIConfig',
    'CLIConfigManager',
    'get_cli_config',
    'update_cli_config',
    'save_cli_config',
    'reset_cli_config',
    'validate_cli_environment'
]
