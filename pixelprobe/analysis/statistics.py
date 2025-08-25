"""
Statistical analysis tools for PixelProbe
"""
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import logging
from typing import Dict, Any, Tuple, Optional


class StatisticalAnalyzer:
    """Statistical analysis for image data"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def basic_statistics(self, image: np.ndarray) -> Dict[str, Any]:
        """Calculate basic statistical measures for an image"""
        try:
            print(f"DEBUG: Image shape: {image.shape}, dtype: {image.dtype}")  # Debug
            print(f"DEBUG: Image range: {np.min(image)} to {np.max(image)}")   # Debug
            
            if len(image.shape) == 2:
                # Grayscale image
                stats_dict = {
                    'mean': float(np.mean(image)),
                    'std': float(np.std(image)),
                    'min': float(np.min(image)),
                    'max': float(np.max(image)),
                    'median': float(np.median(image)),
                    'mode': float(stats.mode(image.flatten(), keepdims=True)[0][0]),
                    'variance': float(np.var(image)),
                    'range': float(np.max(image) - np.min(image)),
                    'skewness': float(stats.skew(image.flatten())),
                    'kurtosis': float(stats.kurtosis(image.flatten())),
                    'entropy': self.calculate_entropy(image),
                    'shape': image.shape,
                    'width': image.shape[1],
                    'height': image.shape[0], 
                    'total_pixels': image.shape[0] * image.shape[1],
                    'dtype': str(image.dtype),
                    'channels': 1,
                    'bit_depth': 8
                }
            else:
                # Color image - convert to grayscale for main stats
                if image.shape[2] == 3:
                    gray = 0.299 * image[:, :, 0] + 0.587 * image[:, :, 1] + 0.114 * image[:, :, 2]
                else:
                    gray = np.mean(image, axis=2)
                    
                stats_dict = {
                    'shape': image.shape,
                    'width': image.shape[1],
                    'height': image.shape[0],
                    'total_pixels': image.shape[0] * image.shape[1],
                    'dtype': str(image.dtype),
                    'channels': image.shape[2],
                    'bit_depth': 8,
                    # Main stats from grayscale conversion
                    'mean': float(np.mean(gray)),
                    'std': float(np.std(gray)),
                    'min': float(np.min(gray)),
                    'max': float(np.max(gray)),
                    'median': float(np.median(gray)),
                    'variance': float(np.var(gray)),
                    'range': float(np.max(gray) - np.min(gray)),
                    'skewness': float(stats.skew(gray.flatten())),
                    'kurtosis': float(stats.kurtosis(gray.flatten())),
                    'entropy': self.calculate_entropy(gray),
                    'by_channel': {}
                }
                    
                # Per-channel statistics
                channels = ['Red', 'Green', 'Blue'] if image.shape[2] == 3 else [f'Channel {i}' for i in range(image.shape[2])]
                for i, channel_name in enumerate(channels):
                    channel_data = image[:, :, i]
                    stats_dict['by_channel'][channel_name] = {
                        'mean': float(np.mean(channel_data)),
                        'std': float(np.std(channel_data)),
                        'min': float(np.min(channel_data)),
                        'max': float(np.max(channel_data)),
                        'median': float(np.median(channel_data)),
                        'entropy': self.calculate_entropy(channel_data)
                    }
            
            print(f"DEBUG: Calculated mean: {stats_dict.get('mean', 'None')}")  # Debug
            self.logger.info("Calculated basic image statistics")
            return stats_dict
            
        except Exception as e:
            self.logger.error(f"Failed to calculate statistics: {e}")
            import traceback
            traceback.print_exc()  # Debug
            return {}

    
    def calculate_entropy(self, image: np.ndarray) -> float:
        """Calculate Shannon entropy of image"""
        try:
            # Calculate histogram
            hist, _ = np.histogram(image.flatten(), bins=256, range=(0, 255))
            
            # Normalize histogram to get probabilities
            hist = hist.astype(float)
            hist = hist[hist > 0]  # Remove zero entries
            hist = hist / np.sum(hist)
            
            # Calculate entropy
            entropy = -np.sum(hist * np.log2(hist))
            return float(entropy)
        except Exception as e:
            self.logger.error(f"Failed to calculate entropy: {e}")
            return 0.0
    
    def image_quality_metrics(self, image: np.ndarray) -> Dict[str, float]:
        """
        Calculate image quality metrics
        
        Args:
            image: Input image array
            
        Returns:
            Dictionary of quality metrics
        """
        try:
            metrics = {}
            
            if len(image.shape) == 2:
                # Grayscale image
                metrics['contrast'] = self.calculate_contrast(image)
                metrics['sharpness'] = self.calculate_sharpness(image)
                metrics['brightness'] = float(np.mean(image))
                metrics['noise_estimate'] = self.estimate_noise(image)
            else:
                # Color image - average across channels
                contrasts = []
                sharpnesses = []
                noise_estimates = []
                
                for i in range(image.shape[2]):
                    channel = image[:, :, i]
                    contrasts.append(self.calculate_contrast(channel))
                    sharpnesses.append(self.calculate_sharpness(channel))
                    noise_estimates.append(self.estimate_noise(channel))
                
                metrics['contrast'] = float(np.mean(contrasts))
                metrics['sharpness'] = float(np.mean(sharpnesses))
                metrics['brightness'] = float(np.mean(image))
                metrics['noise_estimate'] = float(np.mean(noise_estimates))
            
            self.logger.info("Calculated image quality metrics")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to calculate quality metrics: {e}")
            return {}
    
    def calculate_contrast(self, image: np.ndarray) -> float:
        """Calculate RMS contrast"""
        try:
            mean_intensity = np.mean(image)
            contrast = np.sqrt(np.mean((image - mean_intensity) ** 2))
            return float(contrast)
        except Exception as e:
            self.logger.error(f"Failed to calculate contrast: {e}")
            return 0.0
    
    def calculate_sharpness(self, image: np.ndarray) -> float:
        """Calculate sharpness using Laplacian variance"""
        try:
            from scipy import ndimage
            laplacian = ndimage.laplace(image.astype(float))
            sharpness = np.var(laplacian)
            return float(sharpness)
        except Exception as e:
            self.logger.error(f"Failed to calculate sharpness: {e}")
            return 0.0
    
    def estimate_noise(self, image: np.ndarray) -> float:
        """Estimate noise level using robust median estimator"""
        try:
            from scipy import ndimage
            # Use Laplacian to detect edges/noise
            laplacian = ndimage.laplace(image.astype(float))
            # Robust noise estimation
            noise_estimate = np.median(np.abs(laplacian)) / 0.6745
            return float(noise_estimate)
        except Exception as e:
            self.logger.error(f"Failed to estimate noise: {e}")
            return 0.0
    
    def generate_histogram_data(self, image: np.ndarray) -> Dict[str, Any]:
        """Generate histogram data for plotting - fixed to handle any data range"""
        try:
            # Get actual data range
            img_min = float(np.min(image))
            img_max = float(np.max(image))
            
            print(f"DEBUG: Histogram range {img_min} to {img_max}")  # Debug
            
            if len(image.shape) == 2:
                # Grayscale histogram
                hist, bins = np.histogram(image.flatten(), bins=256, range=(img_min, img_max))
                return {
                    'type': 'grayscale',
                    'histogram': hist,
                    'bins': bins,
                    'data': image.flatten()
                }
            else:
                # Color histogram
                colors = ['red', 'green', 'blue']
                histograms = {}
                
                for i, color in enumerate(colors[:image.shape[2]]):
                    channel_data = image[:, :, i]
                    ch_min = float(np.min(channel_data))
                    ch_max = float(np.max(channel_data))
                    hist, bins = np.histogram(channel_data.flatten(), bins=256, range=(ch_min, ch_max))
                    histograms[color] = {'hist': hist, 'bins': bins}
                
                return {
                    'type': 'color',
                    'histograms': histograms,
                    'shape': image.shape
                }
        except Exception as e:
            self.logger.error(f"Failed to generate histogram data: {e}")
            return {}

