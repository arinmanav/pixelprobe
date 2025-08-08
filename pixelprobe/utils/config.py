"""
Configuration management for PixeProbe
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load configuration from .env file
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Dictionary of configuration values
    """
    # Load environment variables
    if config_path:
        load_dotenv(config_path)
    else:
        load_dotenv()
    
    return {
        # Debug settings
        'debug': os.getenv('DEBUG', 'false').lower() == 'true',
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        
        # GUI settings
        'theme': os.getenv('THEME', 'dark'),
        'window_size': os.getenv('DEFAULT_WINDOW_SIZE', '1200x800'),
        'ctk_theme': os.getenv('CUSTOMTKINTER_THEME', 'blue'),
        
        # Paths
        'data_dir': Path(os.getenv('DATA_DIR', './data')),
        'models_dir': Path(os.getenv('MODELS_DIR', './data/models')),
        'temp_dir': Path(os.getenv('TEMP_DIR', './temp')),
        
        # Plotting
        'matplotlib_backend': os.getenv('MATPLOTLIB_BACKEND', 'TkAgg'),
        'plot_dpi': int(os.getenv('PLOT_DPI', '100')),
        'figure_size': tuple(map(float, os.getenv('FIGURE_SIZE', '10,8').split(','))),
    }


def ensure_directories(config: Dict[str, Any]) -> None:
    """Create necessary directories if they don't exist"""
    for key in ['data_dir', 'models_dir', 'temp_dir']:
        path = config[key]
        path.mkdir(parents=True, exist_ok=True) 
