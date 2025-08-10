"""
Main window for PixelProbe application
"""
import customtkinter as ctk
import logging
from typing import Dict, Any, Optional
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from pixelprobe.utils.config import load_config, ensure_directories
from pixelprobe.gui.dialogs.file_dialogs import FileDialogs
from pixelprobe.utils.file_io import ArrayLoader, ImageLoader
from pixelprobe.processing.denoising import AdvancedDenoiseProcessor


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

        # Current loaded data
        self.current_array = None
        self.current_image = None        

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
        directory = self.file_dialogs.select_directory("Select Data Directory")
        if directory:
            self.update_status(f"Selected directory: {directory.name}")
            self.logger.info(f"Data directory selected: {directory}")
        else:
            self.update_status("Data loading cancelled")

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
            self.update_status_persistent("No image loaded - please load an image first")
            return
        
        # Show denoising options dialog
        self.show_denoise_options()

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
        self.update_status("Statistics not yet implemented")
    
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
