"""
Image interpolation processor for PixelProbe
Supports matplotlib interpolation methods for display and data resampling
"""
import numpy as np
from scipy import ndimage
from scipy.interpolate import griddata
import logging
from typing import Tuple, Optional, Union


class InterpolationProcessor:
    """Image interpolation processor with matplotlib methods only"""
    
    # Available matplotlib interpolation methods - USE FOR BOTH DISPLAY AND RESAMPLING
    INTERPOLATION_METHODS = [
        'none', 'nearest', 'bilinear', 'bicubic', 'spline16', 'spline36',
        'hanning', 'hamming', 'hermite', 'kaiser', 'quadric', 'catrom',
        'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos', 'antialiased', 'auto'
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_interpolation_methods(self) -> list:
        """Get list of available interpolation methods"""
        return self.INTERPOLATION_METHODS.copy()
    
    def is_valid_method(self, method: str) -> bool:
        """Check if method is valid"""
        return method in self.INTERPOLATION_METHODS
    
    def apply_interpolation_method(self, method: str = 'nearest') -> str:
        """
        Apply interpolation method - same for both display and resampling
        Returns the method string to be used with matplotlib
        
        Args:
            method: Interpolation method name
            
        Returns:
            Valid matplotlib interpolation method string
        """
        if not self.is_valid_method(method):
            self.logger.warning(f"Invalid method '{method}', using 'nearest'")
            return 'nearest'
            
        self.logger.info(f"Applied interpolation: {method}")
        return method
    
    # Note: For data resampling, we use matplotlib's interpolation for display
    # and let matplotlib handle the actual resampling during display
    # This keeps everything consistent with matplotlib methods only