"""
Main window for PixelProbe application
"""
import customtkinter as ctk
import logging
import numpy as np
from typing import Dict, Any, Optional
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from pixelprobe.utils.config import load_config, ensure_directories
from pixelprobe.gui.dialogs.file_dialogs import FileDialogs
from pixelprobe.utils.file_io import ArrayLoader, ImageLoader
from pixelprobe.processing.denoising import AdvancedDenoiseProcessor
from pixelprobe.analysis.statistics import StatisticalAnalyzer
from pixelprobe.core.array_handler import ArrayHandler


class PixelProbeApp:
    """Main application window for PixelProbe"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the PixelProbe application"""
        self.logger = logging.getLogger(__name__)
        self.config = config or load_config()
        
        # Initialize file handling
        self.file_dialogs = FileDialogs()
        self.array_loader = ArrayLoader()
        self.image_loader = ImageLoader()
        self.array_handler = ArrayHandler()

        # Current loaded data
        self.current_array = None
        self.current_image = None
        self.current_items = []  # List of loaded item numbers
        self.current_operation = None  # 'single', 'multiple', or 'average'        

        # Ensure required directories exist
        ensure_directories(self.config)
        
        # Configure CustomTkinter appearance
        ctk.set_appearance_mode(self.config['theme'])
        ctk.set_default_color_theme(self.config['ctk_theme'])
        
        # Initialize main window
        self.root = ctk.CTk()
        self.setup_window()
        self.create_widgets()

        # Initialize processing
        self.denoiser = AdvancedDenoiseProcessor()

        # Initialize analysis
        self.analyzer = StatisticalAnalyzer()
        
        self.logger.info("PixelProbe application initialized")    
    
    def setup_window(self):
        """Configure the main window properties"""
        self.root.title("PixelProbe")
        
        # Set window size from config
        width, height = map(int, self.config['window_size'].split('x'))
        self.root.geometry(f"{width}x{height}")
        
        # Center window on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Configure grid weights for responsive design
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Set minimum window size
        self.root.minsize(800, 600)
        
        self.logger.debug(f"Window configured: {width}x{height}")

    def display_image(self, image_array, title="Loaded Image"):
        """Display image in the main content area"""
        try:
            self.subplot.clear()
            
            if len(image_array.shape) == 2:
                # Grayscale image
                self.subplot.imshow(image_array, cmap='gray')
            else:
                # Color image
                self.subplot.imshow(image_array)
                
            self.subplot.set_title(title)
            self.subplot.axis('off')
            self.canvas.draw()
            
            self.logger.info(f"Displayed image with shape {image_array.shape}")
        except Exception as e:
            self.logger.error(f"Failed to display image: {e}")
            self.update_status("Failed to display image")

    def show_denoise_options(self):
        """Show denoising method selection dialog"""
        import tkinter as tk
        from tkinter import ttk
        
        # Create options window
        options_window = tk.Toplevel(self.root)
        options_window.title("Denoising Options")
        options_window.geometry("900x600")
        options_window.transient(self.root)
        options_window.grab_set()
        
        # Main frame with padding
        main_frame = tk.Frame(options_window, padx=30, pady=30)
        main_frame.pack(fill='both', expand=True)
        
        # Title with larger font
        title_label = tk.Label(main_frame, text="Select Denoising Method:", 
                            font=("Arial", 18, "bold"))
        title_label.pack(pady=(0, 30))
        
        method_var = tk.StringVar(value="adaptive")
        methods = [
            ("Adaptive (Recommended)", "adaptive", "Automatically selects best method"),
            ("Gaussian Filter (Simple)", "gaus", "Basic blur filter - fast and simple"),
            ("Median Filter (Simple)", "med", "Removes salt-and-pepper noise"),
            ("Mean Filter (Simple)", "mean", "Simple averaging filter"),
            ("Non-Local Means (Advanced)", "nlm", "Excellent for texture preservation"),
            ("Total Variation (Advanced)", "tv", "Best for smooth images"),
            ("Bilateral Filter (Advanced)", "bilateral", "Edge-preserving smoothing"),
        ]
        
        # Create radio buttons with larger fonts
        for text, value, description in methods:
            # Frame for each method
            method_frame = tk.Frame(main_frame)
            method_frame.pack(fill='x', pady=8)
            
            # Radio button
            radio = tk.Radiobutton(method_frame, text=text, variable=method_var, value=value,
                                font=("Arial", 14, "bold"))
            radio.pack(anchor='w')
            
            # Description
            desc_label = tk.Label(method_frame, text=f"   • {description}",
                                font=("Arial", 12), fg="gray")
            desc_label.pack(anchor='w', padx=(30, 0), pady=(2, 0))
        
        # Buttons font
        button_frame = tk.Frame(main_frame)
        button_frame.pack(pady=40)
        
        def apply_denoising():
            method = method_var.get()
            options_window.destroy()
            self.apply_selected_denoising(method)
        
        # Large, prominent buttons
        apply_btn = tk.Button(button_frame, text="Apply Denoising", command=apply_denoising,
                            font=("Arial", 14, "bold"), bg='#4CAF50', fg='white',
                            padx=40, pady=15)
        apply_btn.pack(side='left', padx=20)
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=options_window.destroy,
                            font=("Arial", 14, "bold"), bg='#f44336', fg='white',
                            padx=40, pady=15)
        cancel_btn.pack(side='left', padx=20)
        
        # Center the window
        options_window.update_idletasks()
        x = (options_window.winfo_screenwidth() // 2) - (900 // 2)
        y = (options_window.winfo_screenheight() // 2) - (600 // 2)
        options_window.geometry(f"900x600+{x}+{y}")

    def apply_selected_denoising(self, method):
        """Apply the selected denoising method"""
        if self.current_image is None:
            self.update_status("No image loaded")
            return
        
        self.update_status(f"Applying {method} denoising...")
        
        try:
            denoised_image = self.denoiser.pixel_level_denoising(self.current_image, method=method)
            self.display_image(denoised_image, f"Denoised Image ({method.upper()})")
            self.current_image = denoised_image
            self.update_status(f"Applied {method} denoising successfully")
            
        except Exception as e:
            self.logger.error(f"Denoising failed: {e}")
            self.update_status(f"Denoising failed: {str(e)}")

    def create_widgets(self):
        """Create and arrange the main interface widgets"""
        # Create sidebar frame
        self.sidebar_frame = ctk.CTkFrame(self.root, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)
        
        # Sidebar title
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="PixelProbe",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Load buttons
        self.load_data_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Load Data",
            command=self.load_data_action
        )
        self.load_data_btn.grid(row=1, column=0, padx=20, pady=10)
        
        self.load_image_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Load Image", 
            command=self.load_image_action
        )
        self.load_image_btn.grid(row=2, column=0, padx=20, pady=10)
        
        # Processing section
        self.processing_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Processing",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.processing_label.grid(row=3, column=0, padx=20, pady=(20, 10))
        
        self.denoise_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Denoise",
            command=self.denoise_action
        )
        self.denoise_btn.grid(row=4, column=0, padx=20, pady=5)
        
        self.segment_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Segment",
            command=self.segment_action
        )
        self.segment_btn.grid(row=5, column=0, padx=20, pady=5)
        
        # Analysis section
        self.analysis_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Analysis",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.analysis_label.grid(row=6, column=0, padx=20, pady=(20, 10))
        
        self.plot_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Plot Data",
            command=self.plot_action
        )
        self.plot_btn.grid(row=7, column=0, padx=20, pady=5)
        
        self.stats_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Statistics", 
            command=self.stats_action
        )
        self.stats_btn.grid(row=8, column=0, padx=20, pady=5)
        
        # Theme toggle
        self.theme_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Toggle Theme",
            command=self.toggle_theme
        )
        self.theme_btn.grid(row=11, column=0, padx=20, pady=10)
        
        # Main content area
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=(20, 20), pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Welcome message
        self.welcome_label = ctk.CTkLabel(
            self.main_frame,
            text="Welcome to PixelProbe",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.welcome_label.grid(row=0, column=0, padx=20, pady=20)
        

        # Content area for displaying images/plots
        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # Create matplotlib figure for image display
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.subplot = self.figure.add_subplot(111)
        self.subplot.set_title("No image loaded")
        self.subplot.axis('off')

        # Create canvas widget
        self.canvas = FigureCanvasTkAgg(self.figure, self.content_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Status bar
        self.status_label = ctk.CTkLabel(
            self.root,
            text="Ready",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 10))
        
        self.logger.debug("Main interface widgets created")
    
    def load_data_action(self):
        """Handle load data button click"""
        self.logger.info("Load data action triggered")
        self.update_status("Selecting data directory...")
        
        # Get directory from user
        directory = self.file_dialogs.select_directory("Select Array Data Directory")
        if not directory:
            self.update_status("Data loading cancelled")
            return
        
        # Set directory in array handler
        if not self.array_handler.set_directory(directory):
            self.update_status("No valid array files found in directory")
            return
        
        self.update_status(f"Found {len(self.array_handler.get_available_items())} items")
        
        # Show array selection dialog
        self._show_array_selection_dialog()
    
    def _show_array_selection_dialog(self):
        """Show dialog for selecting array items"""
        from pixelprobe.gui.dialogs.array_dialogs import ArraySelectionDialog
        
        dialog = ArraySelectionDialog(self.root, self.array_handler)
        result = dialog.show()
        
        if result is None:
            self.update_status("Array selection cancelled")
            return
        
        selected_items, operation = result
        self.current_items = selected_items
        self.current_operation = operation
        
        # Load arrays based on operation
        self._load_selected_arrays(selected_items, operation)
    
    def _load_selected_arrays(self, selected_items, operation):
        """Load the selected arrays"""
        try:
            self.update_status(f"Loading {len(selected_items)} items...")
            
            if operation == "single":
                # Load single item
                item_num = selected_items[0]
                array_data = self.array_handler.load_item(item_num)
                
                if array_data is not None:
                    self.current_array = array_data
                    self.current_image = self._array_to_display_image(array_data)
                    self.display_image(self.current_image, f"Array Item {item_num}")
                    self.update_status(f"Loaded item {item_num} - Shape: {array_data.shape}")
                else:
                    self.update_status(f"Failed to load item {item_num}")
            
            elif operation == "multiple":
                # Load multiple items - display first one
                arrays = self.array_handler.load_multiple_items(selected_items)
                
                if arrays:
                    # Display first array
                    first_item = selected_items[0]
                    self.current_array = arrays[first_item]
                    self.current_image = self._array_to_display_image(self.current_array)
                    self.display_image(self.current_image, f"Items {selected_items[0]}-{selected_items[-1]} (showing {first_item})")
                    
                    # Store all arrays for later use
                    self._loaded_arrays = arrays
                    self.update_status(f"Loaded {len(arrays)} items - Showing item {first_item}")
                else:
                    self.update_status("Failed to load items")
            
            elif operation == "average":
                # Average items
                averaged_array = self.array_handler.average_items(selected_items)
                
                if averaged_array is not None:
                    self.current_array = averaged_array
                    self.current_image = self._array_to_display_image(averaged_array)
                    self.display_image(self.current_image, f"Averaged Items {selected_items[0]}-{selected_items[-1]}")
                    self.update_status(f"Averaged {len(selected_items)} items - Shape: {averaged_array.shape}")
                else:
                    self.update_status("Failed to average items")
            
        except Exception as e:
            self.logger.error(f"Error loading arrays: {e}")
            self.update_status(f"Error loading arrays: {str(e)}")
    
    def _array_to_display_image(self, array_data):
        """Convert array data to displayable image format"""
        try:
            # Handle different array dimensions
            if len(array_data.shape) == 2:
                # 2D array - grayscale
                # Normalize to 0-255 range
                normalized = ((array_data - array_data.min()) / 
                            (array_data.max() - array_data.min()) * 255).astype(np.uint8)
                return normalized
            
            elif len(array_data.shape) == 3:
                if array_data.shape[2] == 3:
                    # RGB image
                    normalized = ((array_data - array_data.min()) / 
                                (array_data.max() - array_data.min()) * 255).astype(np.uint8)
                    return normalized
                else:
                    # 3D array - take first slice
                    slice_data = array_data[:, :, 0]
                    normalized = ((slice_data - slice_data.min()) / 
                                (slice_data.max() - slice_data.min()) * 255).astype(np.uint8)
                    return normalized
            
            else:
                # Higher dimension - take 2D slice
                while len(array_data.shape) > 2:
                    array_data = array_data[..., 0]
                
                normalized = ((array_data - array_data.min()) / 
                            (array_data.max() - array_data.min()) * 255).astype(np.uint8)
                return normalized
                
        except Exception as e:
            self.logger.error(f"Error converting array to image: {e}")
            # Return a simple placeholder
            return np.zeros((100, 100), dtype=np.uint8)

    def load_image_action(self):
        """Handle load image button click"""
        self.logger.info("Load image action triggered")
        self.update_status("Selecting image file...")
        
        # Get image file from user
        image_path = self.file_dialogs.select_image_file("Select Image File")
        if image_path:
            # Load the image
            self.current_image = self.image_loader.load_image(image_path)
            if self.current_image is not None:
                # Display the image
                self.display_image(self.current_image, f"Image: {image_path.name}")
                self.update_status(f"Loaded image: {image_path.name} - Shape: {self.current_image.shape}")
                self.logger.info(f"Successfully loaded and displayed image: {image_path}")
            else:
                self.update_status("Failed to load image")
        else:
            self.update_status("Image loading cancelled")
        
    def denoise_action(self):
        """Handle denoise button click - show options dialog"""
        self.logger.info("Denoise action triggered")
        
        if self.current_image is None:
            self.update_status_persistent("No image loaded - please load an image or array data first")
            return
        
        # Show denoising options dialog
        self.show_denoise_options()
    
    def update_status_persistent(self, message: str):
        """Update status with a persistent message that stays longer"""
        self.status_label.configure(text=message)
        self.root.update_idletasks()
        
        # Clear the message after 8 seconds
        self.root.after(8000, lambda: self.update_status("Ready"))
        
    def show_statistics_window(self, basic_stats, quality_metrics):
        """Display statistics in a professional window"""
        import tkinter as tk
        from tkinter import ttk
        
        # Create statistics window
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Image Statistics and Analysis")
        stats_window.geometry("800x600")
        stats_window.transient(self.root)
        
        # Center the window
        stats_window.update_idletasks()
        x = (stats_window.winfo_screenwidth() // 2) - (800 // 2)
        y = (stats_window.winfo_screenheight() // 2) - (600 // 2)
        stats_window.geometry(f"800x600+{x}+{y}")
        
        # Create notebook for tabs
        notebook = ttk.Notebook(stats_window)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Basic Statistics Tab
        basic_frame = ttk.Frame(notebook)
        notebook.add(basic_frame, text="Basic Statistics")
        
        # Create scrollable text widget for basic stats
        basic_text = tk.Text(basic_frame, font=("Consolas", 12), wrap='word')
        basic_scrollbar = tk.Scrollbar(basic_frame, orient="vertical", command=basic_text.yview)
        basic_text.configure(yscrollcommand=basic_scrollbar.set)
        
        basic_text.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        basic_scrollbar.pack(side="right", fill="y")
        
        # Format and display basic statistics
        stats_text = self.format_statistics_text(basic_stats, quality_metrics)
        basic_text.insert('1.0', stats_text)
        basic_text.config(state='disabled')  # Make read-only
        
        # Quality Metrics Tab
        quality_frame = ttk.Frame(notebook)
        notebook.add(quality_frame, text="Quality Metrics")
        
        # Quality metrics display
        quality_text = tk.Text(quality_frame, font=("Consolas", 14), wrap='word')
        quality_scroll = tk.Scrollbar(quality_frame, orient="vertical", command=quality_text.yview)
        quality_text.configure(yscrollcommand=quality_scroll.set)
        
        quality_text.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        quality_scroll.pack(side="right", fill="y")
        
        # Format quality metrics
        quality_text_content = f"""
    IMAGE QUALITY ANALYSIS
    {'='*50}

    🔍 SHARPNESS: {quality_metrics.get('sharpness', 0):.2f}
    Higher values indicate sharper images

    📊 CONTRAST: {quality_metrics.get('contrast', 0):.2f}
    RMS contrast measure (higher = more contrast)

    💡 BRIGHTNESS: {quality_metrics.get('brightness', 0):.2f}
    Average pixel intensity (0-255)

    🔇 NOISE ESTIMATE: {quality_metrics.get('noise_estimate', 0):.4f}
    Estimated noise level (lower = cleaner)

    {'='*50}
    QUALITY ASSESSMENT:

    Sharpness: {'Excellent' if quality_metrics.get('sharpness', 0) > 1000 else 'Good' if quality_metrics.get('sharpness', 0) > 500 else 'Poor'}
    Contrast: {'High' if quality_metrics.get('contrast', 0) > 50 else 'Medium' if quality_metrics.get('contrast', 0) > 25 else 'Low'}
    Noise Level: {'Low' if quality_metrics.get('noise_estimate', 0) < 2 else 'Medium' if quality_metrics.get('noise_estimate', 0) < 5 else 'High'}
    """
        
        quality_text.insert('1.0', quality_text_content)
        quality_text.config(state='disabled')
        
        # Histogram Tab
        histogram_frame = ttk.Frame(notebook)
        notebook.add(histogram_frame, text="Histogram")
        
        # Add histogram plot
        self.create_histogram_plot(histogram_frame)
        
        # Close button
        button_frame = tk.Frame(stats_window)
        button_frame.pack(pady=10)
        
        close_btn = tk.Button(button_frame, text="Close", command=stats_window.destroy,
                            font=("Arial", 12), bg='#2196F3', fg='white',
                            padx=30, pady=8)
        close_btn.pack()

    def format_statistics_text(self, basic_stats, quality_metrics):
        """Format statistics into readable text"""
        if not basic_stats:
            return "No statistics available"
        
        text = f"""
    IMAGE STATISTICS REPORT
    {'='*60}

    📐 IMAGE DIMENSIONS
    Shape: {basic_stats.get('shape', 'N/A')}
    Data Type: {basic_stats.get('dtype', 'N/A')}
    Channels: {basic_stats.get('channels', 'N/A')}

    📊 BASIC STATISTICS
    """
        
        if basic_stats.get('channels') == 1:
            # Grayscale image
            text += f"""
    Mean: {basic_stats.get('mean', 0):.2f}
    Standard Deviation: {basic_stats.get('std', 0):.2f}
    Minimum: {basic_stats.get('min', 0):.2f}
    Maximum: {basic_stats.get('max', 0):.2f}
    Median: {basic_stats.get('median', 0):.2f}
    Mode: {basic_stats.get('mode', 0):.2f}
    Variance: {basic_stats.get('variance', 0):.2f}
    Skewness: {basic_stats.get('skewness', 0):.4f}
    Kurtosis: {basic_stats.get('kurtosis', 0):.4f}
    Entropy: {basic_stats.get('entropy', 0):.4f} bits
    """
        else:
            # Color image
            text += f"""
    🌈 OVERALL STATISTICS
    Mean: {basic_stats.get('overall', {}).get('mean', 0):.2f}
    Standard Deviation: {basic_stats.get('overall', {}).get('std', 0):.2f}
    Minimum: {basic_stats.get('overall', {}).get('min', 0):.2f}
    Maximum: {basic_stats.get('overall', {}).get('max', 0):.2f}

    📈 BY CHANNEL
    """
            for channel, stats in basic_stats.get('by_channel', {}).items():
                text += f"""
    {channel} Channel:
        Mean: {stats.get('mean', 0):.2f}
        Std Dev: {stats.get('std', 0):.2f}
        Min: {stats.get('min', 0):.2f}
        Max: {stats.get('max', 0):.2f}
        Entropy: {stats.get('entropy', 0):.4f} bits
    """
        
        return text

    def create_histogram_plot(self, parent_frame):
        """Create histogram plot in the statistics window"""
        try:
            # Generate histogram data
            hist_data = self.analyzer.generate_histogram_data(self.current_image)
            
            # Create matplotlib figure
            fig = Figure(figsize=(10, 6), dpi=80)
            
            if hist_data.get('type') == 'grayscale':
                # Grayscale histogram
                ax = fig.add_subplot(111)
                ax.hist(hist_data['data'], bins=256, range=(0, 255), color='gray', alpha=0.7)
                ax.set_title('Grayscale Histogram', fontsize=14, fontweight='bold')
                ax.set_xlabel('Pixel Intensity')
                ax.set_ylabel('Frequency')
                ax.grid(True, alpha=0.3)
                
            else:
                # Color histogram
                ax = fig.add_subplot(111)
                colors = ['red', 'green', 'blue']
                
                for color in colors:
                    if color in hist_data.get('histograms', {}):
                        hist_info = hist_data['histograms'][color]
                        ax.plot(hist_info['bins'][:-1], hist_info['hist'], 
                            color=color, alpha=0.7, linewidth=2, label=color.capitalize())
                
                ax.set_title('RGB Histogram', fontsize=14, fontweight='bold')
                ax.set_xlabel('Pixel Intensity')
                ax.set_ylabel('Frequency')
                ax.legend()
                ax.grid(True, alpha=0.3)
            
            fig.tight_layout()
            
            # Add to GUI
            canvas = FigureCanvasTkAgg(fig, parent_frame)
            canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
            canvas.draw()
            
        except Exception as e:
            self.logger.error(f"Failed to create histogram plot: {e}")
            error_label = tk.Label(parent_frame, text="Failed to generate histogram", 
                                font=("Arial", 12), fg="red")
            error_label.pack(pady=50)

    def segment_action(self):
        """Handle segment button click"""
        self.logger.info("Segment action triggered")
        self.update_status("Segmentation not yet implemented")
    
    def plot_action(self):
        """Handle plot button click"""
        self.logger.info("Plot action triggered")
        self.update_status("Plotting not yet implemented")
    
    def stats_action(self):
        """Handle statistics button click"""
        self.logger.info("Statistics action triggered")
        
        if self.current_image is None:
            self.update_status_persistent("No image loaded - please load an image or array data first")
            return
        
        self.update_status("Calculating image statistics...")
        
        try:
            # Calculate statistics
            basic_stats = self.analyzer.basic_statistics(self.current_image)
            quality_metrics = self.analyzer.image_quality_metrics(self.current_image)
            
            # Show statistics in a new window
            self.show_statistics_window(basic_stats, quality_metrics)
            
            self.update_status("Statistics calculated successfully")
            self.logger.info("Statistics window displayed")
            
        except Exception as e:
            self.logger.error(f"Statistics calculation failed: {e}")
            self.update_status("Statistics calculation failed")
    
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        current_mode = ctk.get_appearance_mode()
        new_mode = "Light" if current_mode == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        self.update_status(f"Theme changed to {new_mode}")
        self.logger.info(f"Theme toggled to {new_mode}")
    
    def update_status(self, message: str):
        """Update the status bar message"""
        self.status_label.configure(text=message)
        self.root.update_idletasks()
    
    def run(self):
        """Start the application main loop"""
        self.logger.info("Starting PixelProbe main loop")
        self.root.mainloop()
        self.logger.info("PixelProbe application closed")