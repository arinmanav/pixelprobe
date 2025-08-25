"""
Array data handling for PixelProbe
Manages directory-based array loading with item numbering system
"""
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
import logging
import h5py


class ArrayHandler:
    """Handles array data loading from directories with item numbering"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_directory: Optional[Path] = None
        self.available_items: List[int] = []
        self.loaded_arrays: Dict[int, np.ndarray] = {}
        self.array_metadata: Dict[int, Dict[str, Any]] = {}
        self.processed_frames = {}
    
    def set_directory(self, directory: Path) -> bool:
        """
        Set the working directory and scan for available items
        
        Args:
            directory: Path to directory containing array files
            
        Returns:
            True if directory is valid and contains array files
        """
        try:
            if not directory.exists() or not directory.is_dir():
                self.logger.error(f"Invalid directory: {directory}")
                return False
            
            self.current_directory = directory
            self.available_items = self._scan_directory()
            
            if not self.available_items:
                self.logger.warning(f"No array files found in {directory}")
                return False
            
            self.logger.info(f"Found {len(self.available_items)} items in {directory}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting directory: {e}")
            return False
    
    def _scan_directory(self) -> List[int]:
        """
        Scan directory for array files and extract item numbers
        
        Returns:
            List of available item numbers
        """
        if not self.current_directory:
            return []
        
        item_numbers = set()
        
        # Common array file patterns
        patterns = [
            "item_*.npy", "item_*.npz", "item_*.h5", "item_*.hdf5",
            "*.npy", "*.npz", "*.h5", "*.hdf5"
        ]
        
        for pattern in patterns:
            for file_path in self.current_directory.glob(pattern):
                item_num = self._extract_item_number(file_path)
                if item_num is not None:
                    item_numbers.add(item_num)
        
        return sorted(list(item_numbers))
    
    def _extract_item_number(self, file_path: Path) -> Optional[int]:
        """
        Extract item number from filename
        
        Args:
            file_path: Path to array file
            
        Returns:
            Item number or None if not found
        """
        try:
            filename = file_path.stem
            
            # Try different naming patterns
            patterns = [
                r'item_(\d+)',  # item_001.npy
                r'(\d+)',       # 001.npy
            ]
            
            import re
            for pattern in patterns:
                match = re.search(pattern, filename)
                if match:
                    return int(match.group(1))
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Could not extract item number from {file_path}: {e}")
            return None
    
    def get_available_items(self) -> List[int]:
        """Get list of available item numbers"""
        return self.available_items.copy()
    
    def load_item(self, item_number: int, force_reload: bool = False) -> Optional[np.ndarray]:
        """
        Load array data for specific item number
        
        Args:
            item_number: Item number to load
            force_reload: Force reload even if already cached
            
        Returns:
            Numpy array or None if loading failed
        """
        try:
            
            # Check cache first
            if not force_reload and item_number in self.loaded_arrays:
                self.logger.debug(f"Using cached array for item {item_number}")
                return self.loaded_arrays[item_number]
            
            if item_number not in self.available_items:
                self.logger.error(f"Item {item_number} not available")
                return None
            
            # Find the file for this item
            file_path = self._find_item_file(item_number)
            if not file_path:
                self.logger.error(f"Could not find file for item {item_number}")
                return None
            
            # Load based on file extension
            array_data = self._load_array_file(file_path)
            if array_data is not None:
                # Cache the loaded array
                self.loaded_arrays[item_number] = array_data
                self.array_metadata[item_number] = {
                    'file_path': str(file_path),
                    'shape': array_data.shape,
                    'dtype': str(array_data.dtype),
                    'file_size': file_path.stat().st_size
                }
                self.logger.info(f"Loaded item {item_number}: shape {array_data.shape}")
            
            return array_data
            
        except Exception as e:
            self.logger.error(f"Error loading item {item_number}: {e}")
            return None
    
    def _find_item_file(self, item_number: int) -> Optional[Path]:
        """Find the file path for a specific item number"""
        if not self.current_directory:
            return None
        
        # Try different naming patterns
        patterns = [
            f"item_{item_number:03d}.npy",
            f"item_{item_number:03d}.npz",
            f"item_{item_number:03d}.h5",
            f"item_{item_number:03d}.hdf5",
            f"item_{item_number}.npy",
            f"item_{item_number}.npz",
            f"item_{item_number}.h5",
            f"item_{item_number}.hdf5",
            f"{item_number:03d}.npy",
            f"{item_number:03d}.npz",
            f"{item_number:03d}.h5",
            f"{item_number:03d}.hdf5",
            f"{item_number}.npy",
            f"{item_number}.npz",
            f"{item_number}.h5",
            f"{item_number}.hdf5"
        ]
        
        for pattern in patterns:
            file_path = self.current_directory / pattern
            if file_path.exists():
                return file_path
        
        return None
    
    def _load_array_file(self, file_path: Path) -> Optional[np.ndarray]:
        """Load array from file based on extension"""
        try:
            suffix = file_path.suffix.lower()
            
            if suffix == '.npy':
                return np.load(file_path)
            
            elif suffix == '.npz':
                data = np.load(file_path)
                # Get first array from npz file
                array_name = list(data.keys())[0]
                return data[array_name]
            
            elif suffix in ['.h5', '.hdf5']:
                with h5py.File(file_path, 'r') as f:
                    # Get first dataset
                    dataset_name = list(f.keys())[0]
                    return f[dataset_name][:]
            
            else:
                self.logger.error(f"Unsupported file format: {suffix}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error loading {file_path}: {e}")
            return None
    
    def load_multiple_items(self, item_numbers: List[int]) -> Dict[int, np.ndarray]:
        """
        Load multiple items at once
        
        Args:
            item_numbers: List of item numbers to load
            
        Returns:
            Dictionary mapping item numbers to arrays
        """
        results = {}
        for item_num in item_numbers:
            array_data = self.load_item(item_num)
            if array_data is not None:
                results[item_num] = array_data
        
        return results
    
    def average_items(self, item_numbers: List[int]) -> Optional[np.ndarray]:
        """
        Load and average multiple items
        
        Args:
            item_numbers: List of item numbers to average
            
        Returns:
            Averaged array or None if failed
        """
        try:
            arrays = []
            for item_num in item_numbers:
                array_data = self.load_item(item_num)
                if array_data is not None:
                    arrays.append(array_data)
                else:
                    self.logger.warning(f"Could not load item {item_num} for averaging")
            
            if not arrays:
                self.logger.error("No arrays loaded for averaging")
                return None
            
            # Check that all arrays have the same shape
            shapes = [arr.shape for arr in arrays]
            if not all(shape == shapes[0] for shape in shapes):
                self.logger.error("Arrays have different shapes, cannot average")
                return None
            
            # Calculate average
            averaged = np.mean(arrays, axis=0)
            self.logger.info(f"Averaged {len(arrays)} items")
            
            return averaged
            
        except Exception as e:
            self.logger.error(f"Error averaging items: {e}")
            return None
    
    def get_item_metadata(self, item_number: int) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific item"""
        return self.array_metadata.get(item_number)
    
    def clear_cache(self):
        """Clear cached arrays to free memory"""
        self.loaded_arrays.clear()
        self.array_metadata.clear()
        self.logger.info("Cleared array cache")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached arrays"""
        total_memory = 0
        for array in self.loaded_arrays.values():
            total_memory += array.nbytes
        
        return {
            'cached_items': len(self.loaded_arrays),
            'total_memory_mb': total_memory / (1024 * 1024),
            'available_items': len(self.available_items)
        }