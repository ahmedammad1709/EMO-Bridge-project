#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EMO Bridge Application
Main entry point for the EMO Bridge desktop application.
"""

import os
import sys
import yaml
from pathlib import Path

# Add the parent directory to sys.path to allow importing from sibling packages
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.gui import EMOBridgeApp


def load_config():
    """
    Load configuration from config.yaml or create default if not exists
    """
    config_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / 'config' / 'config.yaml'
    
    # Default configuration
    default_config = {
        'gemini_api_key': '',
        'enable_mqtt': False,
        'mqtt_broker': 'localhost',
        'mqtt_port': 1883,
        'mqtt_topic': 'emo/bridge',
        'voice_rate': 180,  # Default speech rate
        'voice_volume': 1.0  # Default volume (0.0 to 1.0)
    }
    
    # Create config directory if it doesn't exist
    config_path.parent.mkdir(exist_ok=True)
    
    # If config file doesn't exist, create it with default values
    if not config_path.exists():
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        return default_config
    
    # Load existing config
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Update with any missing default keys
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
        
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return default_config


def main():
    """
    Main entry point for the application
    """
    # Load configuration
    config = load_config()
    
    # Start the GUI application
    app = EMOBridgeApp(config)
    app.run()


if __name__ == "__main__":
    main()