"""
Advanced image denoising algorithms for PixelProbe
"""
import numpy as np
from scipy import ndimage
from skimage import filters, restoration, morphology
import logging


class AdvancedDenoiseProcessor:
    """Advanced image denoising algorithms for pixel-level operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def non_local_means(self, image: np.ndarray, h: float = 0.1, fast_mode: bool = True) -> np.ndarray:
        """Non-local means denoising - excellent for texture preservation"""
        try:
            if len(image.shape) == 2:
                result = restoration.denoise_nl_means(
                    image, h=h, fast_mode=fast_mode, patch_size=5, patch_distance=6
                )
            else:
                result = restoration.denoise_nl_means(
                    image, h=h, fast_mode=fast_mode, 
                    patch_size=5, patch_distance=6, channel_axis=-1
                )
            
            if image.dtype == np.uint8:
                result = (np.clip(result, 0, 1) * 255).astype(np.uint8)
            
            self.logger.info(f"Applied non-local means denoising with h={h}")
            return result
        except Exception as e:
            self.logger.error(f"Non-local means denoising failed: {e}")
            return image
        
    def gaussian_filter(self, image: np.ndarray, sigma: float = 1.0) -> np.ndarray:
        """Simple Gaussian filter for basic denoising"""
        try:
            if len(image.shape) == 2:
                result = ndimage.gaussian_filter(image, sigma=sigma)
            else:
                result = np.zeros_like(image)
                for i in range(image.shape[2]):
                    result[:, :, i] = ndimage.gaussian_filter(image[:, :, i], sigma=sigma)
            
            self.logger.info(f"Applied Gaussian filter with sigma={sigma}")
            return result
        except Exception as e:
            self.logger.error(f"Gaussian filter failed: {e}")
            return image

    def median_filter(self, image: np.ndarray, size: int = 3) -> np.ndarray:
        """Simple median filter for salt-and-pepper noise"""
        try:
            if len(image.shape) == 2:
                result = ndimage.median_filter(image, size=size)
            else:
                result = np.zeros_like(image)
                for i in range(image.shape[2]):
                    result[:, :, i] = ndimage.median_filter(image[:, :, i], size=size)
            
            self.logger.info(f"Applied median filter with size={size}")
            return result
        except Exception as e:
            self.logger.error(f"Median filter failed: {e}")
            return image

    def mean_filter(self, image: np.ndarray, size: int = 3) -> np.ndarray:
        """Simple mean filter for basic noise reduction"""
        try:
            kernel = np.ones((size, size)) / (size * size)
            
            if len(image.shape) == 2:
                result = ndimage.convolve(image, kernel, mode='reflect')
            else:
                result = np.zeros_like(image)
                for i in range(image.shape[2]):
                    result[:, :, i] = ndimage.convolve(image[:, :, i], kernel, mode='reflect')
            
            self.logger.info(f"Applied mean filter with size={size}")
            return result
        except Exception as e:
            self.logger.error(f"Mean filter failed: {e}")
            return image
    
    def total_variation_denoising(self, image: np.ndarray, weight: float = 0.1) -> np.ndarray:
        """Total Variation denoising - excellent for piecewise smooth images"""
        try:
            if len(image.shape) == 2:
                result = restoration.denoise_tv_chambolle(image, weight=weight)
            else:
                result = restoration.denoise_tv_chambolle(image, weight=weight, channel_axis=-1)
            
            if image.dtype == np.uint8:
                result = (np.clip(result, 0, 1) * 255).astype(np.uint8)
            
            self.logger.info(f"Applied TV denoising with weight={weight}")
            return result
        except Exception as e:
            self.logger.error(f"TV denoising failed: {e}")
            return image
    
    def bilateral_filter(self, image: np.ndarray, sigma_color: float = 0.1, sigma_spatial: float = 1.0) -> np.ndarray:
        """Advanced bilateral filter with parameter control"""
        try:
            if len(image.shape) == 2:
                result = restoration.denoise_bilateral(
                    image, sigma_color=sigma_color, sigma_spatial=sigma_spatial
                )
            else:
                result = restoration.denoise_bilateral(
                    image, sigma_color=sigma_color, sigma_spatial=sigma_spatial, 
                    channel_axis=-1
                )
            
            if image.dtype == np.uint8:
                result = (np.clip(result, 0, 1) * 255).astype(np.uint8)
            
            self.logger.info(f"Applied bilateral filter")
            return result
        except Exception as e:
            self.logger.error(f"Bilateral filter failed: {e}")
            return image
    
    def adaptive_denoising(self, image: np.ndarray, noise_level: str = "medium") -> np.ndarray:
        """Adaptive denoising that combines multiple methods"""
        try:
            if len(image.shape) == 2:
                estimated_sigma = restoration.estimate_sigma(image)
            else:
                estimated_sigma = np.mean([
                    restoration.estimate_sigma(image[:, :, i]) 
                    for i in range(image.shape[2])
                ])
            
            self.logger.info(f"Estimated noise sigma: {estimated_sigma:.4f}")
            
            if noise_level == "low" or estimated_sigma < 0.05:
                result = self.bilateral_filter(image)
            elif noise_level == "medium" or estimated_sigma < 0.15:
                result = self.non_local_means(image, h=estimated_sigma * 0.8)
            else:
                tv_result = self.total_variation_denoising(image, weight=0.2)
                result = self.non_local_means(tv_result, h=estimated_sigma * 1.2)
            
            self.logger.info(f"Applied adaptive denoising for {noise_level} noise level")
            return result
        except Exception as e:
            self.logger.error(f"Adaptive denoising failed: {e}")
            return image
    
    def pixel_level_denoising(self, image: np.ndarray, method: str = "adaptive") -> np.ndarray:
        """Pixel-level denoising with automatic method selection"""
        method_map = {
            "adaptive": self.adaptive_denoising,
            "gaus": self.gaussian_filter,
            "med": self.median_filter,
            "mean": self.mean_filter,
            "nlm": lambda img: self.non_local_means(img, h=0.1),
            "tv": lambda img: self.total_variation_denoising(img, weight=0.1),
            "bilateral": self.bilateral_filter,
        }
        
        if method in method_map:
            return method_map[method](image)
        else:
            self.logger.warning(f"Unknown method {method}, using adaptive")
            return self.adaptive_denoising(image)