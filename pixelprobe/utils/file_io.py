"""
File input/output utilities for PixelProbe
"""
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Optional, Union, Tuple, Any
import logging


class ArrayLoader:
    """Load array data from various file formats"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def load_numpy_array(self, file_path: Path) -> Optional[np.ndarray]:
        """
        Load array from numpy file (.npy or .npz)
        
        Args:
            file_path: Path to numpy file
            
        Returns:
            Loaded array or None if failed
        """
        try:
            if file_path.suffix == '.npy':
                array = np.load(file_path)
                self.logger.info(f"Loaded .npy array with shape {array.shape}")
                return array
            elif file_path.suffix == '.npz':
                data = np.load(file_path)
                # Get first array from npz file
                array_name = list(data.keys())[0]
                array = data[array_name]
                self.logger.info(f"Loaded .npz array '{array_name}' with shape {array.shape}")
                return array
            else:
                self.logger.error(f"Unsupported numpy format: {file_path.suffix}")
                return None
        except Exception as e:
            self.logger.error(f"Failed to load numpy array: {e}")
            return None
    
    def load_hdf5_array(self, file_path: Path, dataset_name: str = None) -> Optional[np.ndarray]:
        """
        Load array from HDF5 file
        
        Args:
            file_path: Path to HDF5 file
            dataset_name: Name of dataset to load (if None, loads first dataset)
            
        Returns:
            Loaded array or None if failed
        """
        try:
            import h5py
            
            with h5py.File(file_path, 'r') as f:
                if dataset_name is None:
                    # Get first dataset
                    dataset_name = list(f.keys())[0]
                
                array = f[dataset_name][:]
                self.logger.info(f"Loaded HDF5 dataset '{dataset_name}' with shape {array.shape}")
                return array
        except ImportError:
            self.logger.error("h5py not installed - cannot load HDF5 files")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load HDF5 array: {e}")
            return None
    
    def load_array_from_directory(self, directory: Path, item_number: int) -> Optional[np.ndarray]:
        """
        Load array from directory with item numbering
        
        Args:
            directory: Directory containing array files
            item_number: Item number to load
            
        Returns:
            Loaded array or None if failed
        """
        try:
            # Look for files with item number in name
            patterns = [
                f"item_{item_number:03d}.npy",
                f"item_{item_number}.npy", 
                f"{item_number:03d}.npy",
                f"{item_number}.npy"
            ]
            
            for pattern in patterns:
                file_path = directory / pattern
                if file_path.exists():
                    return self.load_numpy_array(file_path)
            
            self.logger.error(f"No array file found for item {item_number} in {directory}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load array from directory: {e}")
            return None


class ImageLoader:
    """Load images from various file formats"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def load_image(self, file_path: Path) -> Optional[np.ndarray]:
        """
        Load image as numpy array
        
        Args:
            file_path: Path to image file
            
        Returns:
            Image as numpy array or None if failed
        """
        try:
            image = Image.open(file_path)
            array = np.array(image)
            self.logger.info(f"Loaded image with shape {array.shape} from {file_path.name}")
            return array
        except Exception as e:
            self.logger.error(f"Failed to load image: {e}")
            return None
    
    def load_image_info(self, file_path: Path) -> Optional[dict]:
        """
        Get image information without loading full data
        
        Args:
            file_path: Path to image file
            
        Returns:
            Image info dictionary or None if failed
        """
        try:
            with Image.open(file_path) as image:
                info = {
                    'size': image.size,
                    'mode': image.mode,
                    'format': image.format,
                    'filename': file_path.name
                }
                return info
        except Exception as e:
            self.logger.error(f"Failed to get image info: {e}")
            return None 
