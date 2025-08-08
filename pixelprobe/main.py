"""
PixelProbe - Main Application Entry Point
"""

import sys
import logging
from pathlib import Path
from typing import Optional

from pixelprobe.utils.logging_setup import setup_logging
from pixelprobe.utils.config import load_config
from pixelprobe.gui.main_window import PixelProbeApp


def main(config_path: Optional[Path] = None) -> int:
    """
    Main application entry point
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Exit code (0 for success)
    """
    try:
        # Load configuration first
        config = load_config(config_path)
        
        # Setup logging with config
        setup_logging(level=config['log_level'])
        logger = logging.getLogger(__name__)
        
        logger.info("Starting PixelProbe Image Analysis Laboratory")
        
        # Create and run application
        app = PixelProbeApp(config=config)
        app.run()
        
        logger.info("Application closed successfully")
        return 0
        
    except Exception as e:
        # Use basic logging if setup_logging fails
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Application failed to start: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
