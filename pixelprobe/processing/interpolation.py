"""
Image interpolation processor for PixelProbe
Supports matplotlib interpolation methods for display and actual data resampling
"""
import numpy as np
from scipy import ndimage
from scipy.interpolate import griddata, interp2d
import logging
from typing import Tuple, Optional, Union


class InterpolationProcessor:
    """Image interpolation processor with both display and data modification support"""
    
    # Available matplotlib interpolation methods - USE FOR BOTH DISPLAY AND RESAMPLING
    INTERPOLATION_METHODS = [
        'none', 'nearest', 'bilinear', 'bicubic', 'spline16', 'spline36',
        'hanning', 'hamming', 'hermite', 'kaiser', 'quadric', 'catrom',
        'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos', 'antialiased', 'auto'
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def interpolate_pixel_data(self, image_data: np.ndarray, method: str) -> np.ndarray:
        """
        Apply interpolation to actual pixel data (not just display)
        
        Args:
            image_data: Input image array
            method: Interpolation method
            
        Returns:
            Interpolated image array
        """
        
        if method == 'none' or method == 'nearest':
            # No interpolation or nearest neighbor - return copy of original
            return image_data.copy()
        
        try:
            # Map matplotlib methods to scipy equivalents for data processing
            scipy_order_map = {
                'bilinear': 1,      # Linear interpolation
                'bicubic': 3,       # Cubic interpolation
                'spline16': 3,      # Spline approximation
                'spline36': 3,      # Spline approximation
                'quadric': 2,       # Quadratic interpolation
                'gaussian': 1,      # Gaussian with linear order
                'auto': 1           # Default to linear
            }
            
            # Handle color vs grayscale images
            if len(image_data.shape) == 3:
                # Color image - process each channel separately
                result = np.zeros_like(image_data, dtype=np.float64)
                
                for channel in range(image_data.shape[2]):
                    channel_data = image_data[:, :, channel].astype(np.float64)
                    result[:, :, channel] = self._apply_scipy_interpolation(channel_data, method, scipy_order_map)
                
                # Convert back to original dtype
                return result.astype(image_data.dtype)
            
            else:
                # Grayscale image
                float_data = image_data.astype(np.float64)
                result = self._apply_scipy_interpolation(float_data, method, scipy_order_map)
                return result.astype(image_data.dtype)
                
        except Exception as e:
            self.logger.error(f"Data interpolation failed: {e}")
            # Return original data if interpolation fails
            return image_data.copy()

    def _apply_scipy_interpolation(self, data: np.ndarray, method: str, scipy_order_map: dict) -> np.ndarray:
        """Apply scipy-based interpolation to 2D data"""
        
        # For methods that have direct scipy equivalents
        if method in scipy_order_map:
            order = scipy_order_map[method]
            # Apply zoom of 1.0 with the specified order (this smooths the data)
            return ndimage.zoom(data, 1.0, order=order, mode='reflect')
        
        # For special methods, use specific scipy functions
        elif method in ['hanning', 'hamming', 'hermite', 'kaiser', 'bessel', 'mitchell', 'sinc', 'lanczos']:
            # For advanced methods, use a smoothing filter approach
            return self._apply_advanced_interpolation(data, method)
        
        else:
            # Fallback to linear interpolation
            return ndimage.zoom(data, 1.0, order=1, mode='reflect')

    def _apply_advanced_interpolation(self, data: np.ndarray, method: str) -> np.ndarray:
        """Apply advanced interpolation methods using scipy filters"""
        
        # Create a small smoothing kernel based on the method
        if method == 'gaussian':
            return ndimage.gaussian_filter(data, sigma=0.5, mode='reflect')
        
        elif method in ['hanning', 'hamming']:
            # Apply a gentle smoothing filter
            return ndimage.uniform_filter(data, size=2, mode='reflect')
        
        elif method in ['sinc', 'lanczos']:
            # Higher quality interpolation using spline filter
            return ndimage.spline_filter(data, order=3, mode='reflect')
        
        elif method in ['hermite', 'kaiser', 'bessel', 'mitchell']:
            # Medium quality smoothing
            return ndimage.gaussian_filter(data, sigma=0.7, mode='reflect')
        
        else:
            # Default smoothing
            return ndimage.gaussian_filter(data, sigma=0.5, mode='reflect')

    def interpolate_roi_pixels(self, image_data: np.ndarray, roi_mask: np.ndarray, method: str) -> np.ndarray:
        """
        Apply interpolation only to pixels specified by ROI mask
        
        Args:
            image_data: Input image array
            roi_mask: Boolean mask indicating which pixels to interpolate
            method: Interpolation method
            
        Returns:
            Image with interpolation applied only to ROI pixels
        """
        
        # Create result copy
        result = image_data.copy()
        
        if not np.any(roi_mask):
            return result
        
        # Get ROI region coordinates
        y_indices, x_indices = np.where(roi_mask)
        
        if len(y_indices) == 0:
            return result
        
        # Extract ROI bounding box for processing
        y_min, y_max = np.min(y_indices), np.max(y_indices) + 1
        x_min, x_max = np.min(x_indices), np.max(x_indices) + 1
        
        # Process the ROI region
        if len(image_data.shape) == 3:
            # Color image
            for channel in range(image_data.shape[2]):
                roi_region = image_data[y_min:y_max, x_min:x_max, channel].astype(np.float64)
                roi_mask_region = roi_mask[y_min:y_max, x_min:x_max]
                
                # Apply interpolation to the region
                interpolated_region = self._apply_scipy_interpolation(roi_region, method, {
                    'bilinear': 1, 'bicubic': 3, 'spline16': 3, 'spline36': 3,
                    'quadric': 2, 'gaussian': 1, 'auto': 1
                })
                
                # Only update pixels that are in the ROI
                result[y_min:y_max, x_min:x_max, channel] = np.where(
                    roi_mask_region, 
                    interpolated_region, 
                    result[y_min:y_max, x_min:x_max, channel]
                )
        
        else:
            # Grayscale image
            roi_region = image_data[y_min:y_max, x_min:x_max].astype(np.float64)
            roi_mask_region = roi_mask[y_min:y_max, x_min:x_max]
            
            # Apply interpolation to the region
            interpolated_region = self._apply_scipy_interpolation(roi_region, method, {
                'bilinear': 1, 'bicubic': 3, 'spline16': 3, 'spline36': 3,
                'quadric': 2, 'gaussian': 1, 'auto': 1
            })
            
            # Only update pixels that are in the ROI
            result[y_min:y_max, x_min:x_max] = np.where(
                roi_mask_region, 
                interpolated_region, 
                result[y_min:y_max, x_min:x_max]
            )
        
        return result.astype(image_data.dtype)
        
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
    
    def interpolate_pixel_data(self, image_data: np.ndarray, method: str) -> np.ndarray:
        """
        Apply interpolation to actual pixel data (not just display)
        
        Args:
            image_data: Input image array
            method: Interpolation method
            
        Returns:
            Interpolated image array
        """
        
        if method == 'none' or method == 'nearest':
            # No interpolation or nearest neighbor - return copy of original
            return image_data.copy()
        
        try:
            # Map matplotlib methods to scipy equivalents for data processing
            scipy_order_map = {
                'bilinear': 1,      # Linear interpolation
                'bicubic': 3,       # Cubic interpolation
                'spline16': 3,      # Spline approximation
                'spline36': 3,      # Spline approximation
                'quadric': 2,       # Quadratic interpolation
                'gaussian': 1,      # Gaussian with linear order
                'auto': 1           # Default to linear
            }
            
            # Handle color vs grayscale images
            if len(image_data.shape) == 3:
                # Color image - process each channel separately
                result = np.zeros_like(image_data, dtype=np.float64)
                
                for channel in range(image_data.shape[2]):
                    channel_data = image_data[:, :, channel].astype(np.float64)
                    result[:, :, channel] = self._apply_scipy_interpolation(channel_data, method, scipy_order_map)
                
                # Convert back to original dtype
                return result.astype(image_data.dtype)
            
            else:
                # Grayscale image
                float_data = image_data.astype(np.float64)
                result = self._apply_scipy_interpolation(float_data, method, scipy_order_map)
                return result.astype(image_data.dtype)
                
        except Exception as e:
            self.logger.error(f"Data interpolation failed: {e}")
            # Return original data if interpolation fails
            return image_data.copy()
    
    def _apply_scipy_interpolation(self, data: np.ndarray, method: str, scipy_order_map: dict) -> np.ndarray:
        """Apply scipy-based interpolation to 2D data"""
        
        # For methods that have direct scipy equivalents
        if method in scipy_order_map:
            order = scipy_order_map[method]
            # Apply zoom of 1.0 with the specified order (this smooths the data)
            return ndimage.zoom(data, 1.0, order=order, mode='reflect')
        
        # For special methods, use specific scipy functions
        elif method in ['hanning', 'hamming', 'hermite', 'kaiser', 'bessel', 'mitchell', 'sinc', 'lanczos']:
            # For advanced methods, use a smoothing filter approach
            return self._apply_advanced_interpolation(data, method)
        
        else:
            # Fallback to linear interpolation
            return ndimage.zoom(data, 1.0, order=1, mode='reflect')
    
    def _apply_advanced_interpolation(self, data: np.ndarray, method: str) -> np.ndarray:
        """Apply advanced interpolation methods using scipy filters"""
        
        # Create a small smoothing kernel based on the method
        if method == 'gaussian':
            return ndimage.gaussian_filter(data, sigma=0.5, mode='reflect')
        
        elif method in ['hanning', 'hamming']:
            # Apply a gentle smoothing filter
            return ndimage.uniform_filter(data, size=2, mode='reflect')
        
        elif method in ['sinc', 'lanczos']:
            # Higher quality interpolation using spline filter
            return ndimage.spline_filter(data, order=3, mode='reflect')
        
        elif method in ['hermite', 'kaiser', 'bessel', 'mitchell']:
            # Medium quality smoothing
            return ndimage.gaussian_filter(data, sigma=0.7, mode='reflect')
        
        else:
            # Default smoothing
            return ndimage.gaussian_filter(data, sigma=0.5, mode='reflect')
    
    def interpolate_roi_pixels(self, image_data: np.ndarray, roi_mask: np.ndarray, method: str) -> np.ndarray:
        """
        Apply interpolation only to pixels specified by ROI mask
        
        Args:
            image_data: Input image array
            roi_mask: Boolean mask indicating which pixels to interpolate
            method: Interpolation method
            
        Returns:
            Image with interpolation applied only to ROI pixels
        """
        
        # Create result copy
        result = image_data.copy()
        
        if not np.any(roi_mask):
            return result
        
        # Get ROI region coordinates
        y_indices, x_indices = np.where(roi_mask)
        
        if len(y_indices) == 0:
            return result
        
        # Extract ROI bounding box for processing
        y_min, y_max = np.min(y_indices), np.max(y_indices) + 1
        x_min, x_max = np.min(x_indices), np.max(x_indices) + 1
        
        # Process the ROI region
        if len(image_data.shape) == 3:
            # Color image
            for channel in range(image_data.shape[2]):
                roi_region = image_data[y_min:y_max, x_min:x_max, channel].astype(np.float64)
                roi_mask_region = roi_mask[y_min:y_max, x_min:x_max]
                
                # Apply interpolation to the region
                interpolated_region = self._apply_scipy_interpolation(roi_region, method, {
                    'bilinear': 1, 'bicubic': 3, 'spline16': 3, 'spline36': 3,
                    'quadric': 2, 'gaussian': 1, 'auto': 1
                })
                
                # Only update pixels that are in the ROI
                result[y_min:y_max, x_min:x_max, channel] = np.where(
                    roi_mask_region, 
                    interpolated_region, 
                    result[y_min:y_max, x_min:x_max, channel]
                )
        
        else:
            # Grayscale image
            roi_region = image_data[y_min:y_max, x_min:x_max].astype(np.float64)
            roi_mask_region = roi_mask[y_min:y_max, x_min:x_max]
            
            # Apply interpolation to the region
            interpolated_region = self._apply_scipy_interpolation(roi_region, method, {
                'bilinear': 1, 'bicubic': 3, 'spline16': 3, 'spline36': 3,
                'quadric': 2, 'gaussian': 1, 'auto': 1
            })
            
            # Only update pixels that are in the ROI
            result[y_min:y_max, x_min:x_max] = np.where(
                roi_mask_region, 
                interpolated_region, 
                result[y_min:y_max, x_min:x_max]
            )
        
        return result.astype(image_data.dtype)