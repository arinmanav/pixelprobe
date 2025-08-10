"""
File dialog utilities for PixelProbe
"""
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, List, Tuple
import logging


class FileDialogs:
    """File dialog utilities for loading data and images"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def select_directory(self, title: str = "Select Directory") -> Optional[Path]:
        """
        Open directory selection dialog
        
        Args:
            title: Dialog window title
            
        Returns:
            Selected directory path or None if cancelled
        """
        try:
            directory = filedialog.askdirectory(title=title)
            if directory:
                return Path(directory)
            return None
        except Exception as e:
            self.logger.error(f"Error selecting directory: {e}")
            messagebox.showerror("Error", f"Failed to select directory: {e}")
            return None
    
    def select_image_file(self, title: str = "Select Image File") -> Optional[Path]:
        """
        Open image file selection dialog
        
        Args:
            title: Dialog window title
            
        Returns:
            Selected image file path or None if cancelled
        """
        try:
            filetypes = [
                ("Image files", "*.png *.jpg *.jpeg *.tiff *.bmp *.gif"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("TIFF files", "*.tiff *.tif"),
                ("All files", "*.*")
            ]
            
            filename = filedialog.askopenfilename(
                title=title,
                filetypes=filetypes
            )
            
            if filename:
                return Path(filename)
            return None
        except Exception as e:
            self.logger.error(f"Error selecting image file: {e}")
            messagebox.showerror("Error", f"Failed to select image file: {e}")
            return None
    
    def select_array_file(self, title: str = "Select Array Data File") -> Optional[Path]:
        """
        Open array data file selection dialog
        
        Args:
            title: Dialog window title
            
        Returns:
            Selected array file path or None if cancelled
        """
        try:
            filetypes = [
                ("Array files", "*.npy *.npz *.h5 *.hdf5"),
                ("NumPy files", "*.npy *.npz"),
                ("HDF5 files", "*.h5 *.hdf5"),
                ("All files", "*.*")
            ]
            
            filename = filedialog.askopenfilename(
                title=title,
                filetypes=filetypes
            )
            
            if filename:
                return Path(filename)
            return None
        except Exception as e:
            self.logger.error(f"Error selecting array file: {e}")
            messagebox.showerror("Error", f"Failed to select array file: {e}")
            return None 
