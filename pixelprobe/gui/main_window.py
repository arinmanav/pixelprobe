"""
Main window for PixelProbe application - Updated with ROI functionality
"""
import customtkinter as ctk
import logging
import numpy as np
from typing import Dict, Any, Optional, Tuple
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
import matplotlib.patches as patches
from pixelprobe.gui.dialogs.plotting_dialog import create_plotting_dialog
from tkinter import messagebox

from pixelprobe.utils.config import load_config, ensure_directories
from pixelprobe.gui.dialogs.file_dialogs import FileDialogs
from pixelprobe.utils.file_io import ArrayLoader, ImageLoader
from pixelprobe.processing.denoising import AdvancedDenoiseProcessor
from pixelprobe.analysis.statistics import StatisticalAnalyzer
from pixelprobe.core.array_handler import ArrayHandler
from pixelprobe.gui.roi_selector import ROISelector, ROIType, ROI
from pixelprobe.processing.interpolation import InterpolationProcessor


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

        # ROI functionality
        self.roi_selector = None
        self.roi_mode_active = False
        self.roi_interpolation_active = False  # Track if ROI-specific interpolation is active
        self.camera_roll = None  # Will be created when needed

        # Cleanup tracking
        self.scheduled_callbacks = []
        self.is_closing = False

        # Ensure required directories exist
        ensure_directories(self.config)
        
        # Configure CustomTkinter appearance
        ctk.set_appearance_mode(self.config['theme'])
        ctk.set_default_color_theme(self.config['ctk_theme'])
        
        # Initialize main window
        self.root = ctk.CTk()
        self.setup_window()
        
        # Initialize analysis BEFORE create_widgets() is called AFTER all these variables are set up
        
        # Initialize processing
        self.denoiser = AdvancedDenoiseProcessor()
        self.interpolator = InterpolationProcessor()  # NEW PROCESSOR
        
        # Current interpolation settings - SIMPLIFIED
        self.current_display_interpolation = 'nearest'  # Single setting for all interpolation
        self.current_title = "Image"  # Track current image title

        # NEW: Colormap and display settings - MUST BE BEFORE create_widgets()
        self.current_colormap = 'gray'  # Default colormap
        self.show_colorbar = True  # Whether to show colorbar
        self.colorbar_range_mode = 'auto'  # 'auto' or 'manual'
        self.colorbar_vmin = None  # Manual minimum value
        self.colorbar_vmax = None  # Manual maximum value
        self.current_colorbar = None  # Store current colorbar object for removal

        # NEW: Enhanced colorbar customization settings
        self.colorbar_tick_fontsize = 10  # Font size for colorbar tick labels
        self.colorbar_label = ""  # Colorbar label text
        self.colorbar_label_fontsize = 12  # Font size for colorbar label

        # NEW: Export settings
        self.export_format = "png"  # Default export format
        self.export_dpi = 300  # Default DPI for exports
        self.export_bbox_inches = "tight"  # Bounding box setting for exports

        # UI references for inline controls (will be set in create_widgets)
        self.colormap_dropdown = None
        self.colorbar_checkbox = None
        self.range_mode_dropdown = None
        self.min_value_entry = None
        self.max_value_entry = None
        
        # NEW: UI references for colorbar customization
        self.colorbar_label_entry = None
        self.colorbar_tick_font_entry = None
        self.colorbar_label_font_entry = None
        
        # NEW: UI references for export controls
        self.export_format_dropdown = None
        self.export_dpi_dropdown = None
        self.export_current_btn = None
        self.export_interval_btn = None

        # NOW create widgets (after all variables are initialized)
        self.create_widgets()

        # Initialize analysis
        self.analyzer = StatisticalAnalyzer()
        
        self.logger.info("PixelProbe application initialized")

    def setup_window(self):
        """Configure the main window properties"""
        self.root.title("PixelProbe")
        
        # Set window size from config with taller default
        width, height = map(int, self.config['window_size'].split('x'))
        # Make window taller to accommodate the extended sidebar
        height = max(height, 900)  # Ensure minimum height of 900px
        width = max(width, 1300)   # Ensure minimum width of 1300px
        
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
        self.root.minsize(1200, 850)  # Increased minimum size
        
        # FIXED: Add proper close handling
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.logger.debug(f"Window configured: {width}x{height}")

    def create_widgets(self):
        """Create and arrange the main interface widgets with scrollable sidebar"""
        
        # Create main sidebar container (fixed width)
        self.sidebar_container = ctk.CTkFrame(self.root, width=250, corner_radius=0)
        self.sidebar_container.grid(row=0, column=0, sticky="nsew")
        self.sidebar_container.grid_propagate(False)  # Maintain fixed width
        self.sidebar_container.grid_columnconfigure(0, weight=1)
        self.sidebar_container.grid_rowconfigure(0, weight=1)
        
        # Create scrollable frame inside the container
        self.sidebar_frame = ctk.CTkScrollableFrame(
            self.sidebar_container, 
            width=230,  # Slightly smaller to account for scrollbar
            corner_radius=0
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Sidebar title
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="PixelProbe",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.pack(pady=(20, 10), padx=20)
        
        # Load buttons
        self.load_data_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Load Data",
            command=self.load_data_action,
            width=200
        )
        self.load_data_btn.pack(pady=5, padx=20)
        
        self.load_image_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Load Image", 
            command=self.load_image_action,
            width=200
        )
        self.load_image_btn.pack(pady=5, padx=20)
        
        # Processing section
        self.processing_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Processing",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.processing_label.pack(pady=(20, 10), padx=20)
        
        self.denoise_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Denoise",
            command=self.denoise_action,
            width=200
        )
        self.denoise_btn.pack(pady=2, padx=20)
        
        self.segment_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Segment",
            command=self.segment_action,
            width=200
        )
        self.segment_btn.pack(pady=2, padx=20)

        self.interpolation_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Interpolation",
            command=self.interpolation_action,
            width=200
        )
        self.interpolation_btn.pack(pady=2, padx=20)
        
        # ENHANCED Display section with colorbar customization
        self.display_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Display",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.display_label.pack(pady=(20, 10), padx=20)
        
        # Create frame for display controls
        self.display_controls_frame = ctk.CTkFrame(self.sidebar_frame)
        self.display_controls_frame.pack(fill="x", padx=15, pady=5)
        
        # Colormap dropdown
        ctk.CTkLabel(
            self.display_controls_frame,
            text="Colormap:",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=10, pady=(10, 2))
        
        self.colormap_dropdown = ctk.CTkOptionMenu(
            self.display_controls_frame,
            values=["gray", "viridis", "plasma", "inferno", "magma", "hot", "cool", "spring", 
                    "summer", "autumn", "winter", "bone", "copper", "pink", "jet", "hsv", 
                    "rainbow", "coolwarm", "bwr", "seismic", "cividis", "turbo"],
            command=self.on_colormap_change,
            width=180
        )
        self.colormap_dropdown.set(self.current_colormap)
        self.colormap_dropdown.pack(padx=10, pady=(0, 8))
        
        # Colorbar toggle
        self.colorbar_checkbox = ctk.CTkCheckBox(
            self.display_controls_frame,
            text="Show Colorbar",
            command=self.on_colorbar_toggle,
            font=ctk.CTkFont(size=12)
        )
        self.colorbar_checkbox.select() if self.show_colorbar else self.colorbar_checkbox.deselect()
        self.colorbar_checkbox.pack(anchor="w", padx=10, pady=3)
        
        # NEW: Colorbar customization section - IMPROVED SPACING
        colorbar_custom_frame = ctk.CTkFrame(self.display_controls_frame)
        colorbar_custom_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(
            colorbar_custom_frame,
            text="Colorbar Settings:",
            font=ctk.CTkFont(size=11, weight="bold")
        ).pack(anchor="w", padx=5, pady=(5, 2))
        
        # Colorbar label
        label_frame = ctk.CTkFrame(colorbar_custom_frame)
        label_frame.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(label_frame, text="Label:", width=45, font=ctk.CTkFont(size=10)).pack(side="left", padx=2)
        self.colorbar_label_entry = ctk.CTkEntry(
            label_frame, 
            placeholder_text="Enter colorbar label",
            width=120,
            height=24,
            font=ctk.CTkFont(size=10)
        )
        self.colorbar_label_entry.pack(side="left", padx=2)
        self.colorbar_label_entry.bind('<Return>', self.on_colorbar_label_change)
        self.colorbar_label_entry.bind('<FocusOut>', self.on_colorbar_label_change)
        
        # IMPROVED: Font sizes - separate rows for better spacing
        tick_font_frame = ctk.CTkFrame(colorbar_custom_frame)
        tick_font_frame.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(tick_font_frame, text="Tick Font Size:", width=80, font=ctk.CTkFont(size=10)).pack(side="left", padx=2)
        self.colorbar_tick_font_entry = ctk.CTkEntry(
            tick_font_frame,
            width=60,  # INCREASED from 40 to 60
            height=24,
            font=ctk.CTkFont(size=10)
        )
        self.colorbar_tick_font_entry.insert(0, str(self.colorbar_tick_fontsize))
        self.colorbar_tick_font_entry.pack(side="left", padx=2)
        self.colorbar_tick_font_entry.bind('<Return>', self.on_colorbar_font_change)
        self.colorbar_tick_font_entry.bind('<FocusOut>', self.on_colorbar_font_change)
        
        # Label font size - separate row for more space
        label_font_frame = ctk.CTkFrame(colorbar_custom_frame)
        label_font_frame.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(label_font_frame, text="Label Font Size:", width=80, font=ctk.CTkFont(size=10)).pack(side="left", padx=2)
        self.colorbar_label_font_entry = ctk.CTkEntry(
            label_font_frame,
            width=60,  # INCREASED from 40 to 60
            height=24,
            font=ctk.CTkFont(size=10)
        )
        self.colorbar_label_font_entry.insert(0, str(self.colorbar_label_fontsize))
        self.colorbar_label_font_entry.pack(side="left", padx=2)
        self.colorbar_label_font_entry.bind('<Return>', self.on_colorbar_font_change)
        self.colorbar_label_font_entry.bind('<FocusOut>', self.on_colorbar_font_change)
        
        # Range mode selection
        ctk.CTkLabel(
            self.display_controls_frame,
            text="Range Mode:",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=10, pady=(8, 2))
        
        self.range_mode_dropdown = ctk.CTkOptionMenu(
            self.display_controls_frame,
            values=["auto", "manual"],
            command=self.on_range_mode_change,
            width=180
        )
        self.range_mode_dropdown.set(self.colorbar_range_mode)
        self.range_mode_dropdown.pack(padx=10, pady=(0, 5))
        
        # Manual range inputs (initially disabled for auto mode)
        range_frame = ctk.CTkFrame(self.display_controls_frame)
        range_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Min value
        min_frame = ctk.CTkFrame(range_frame)
        min_frame.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(min_frame, text="Min:", width=35, font=ctk.CTkFont(size=11)).pack(side="left")
        self.min_value_entry = ctk.CTkEntry(min_frame, width=120, height=28, font=ctk.CTkFont(size=11))
        self.min_value_entry.pack(side="left", padx=5)
        self.min_value_entry.bind('<Return>', self.on_manual_range_change)
        self.min_value_entry.bind('<FocusOut>', self.on_manual_range_change)
        
        # Max value
        max_frame = ctk.CTkFrame(range_frame)
        max_frame.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(max_frame, text="Max:", width=35, font=ctk.CTkFont(size=11)).pack(side="left")
        self.max_value_entry = ctk.CTkEntry(max_frame, width=120, height=28, font=ctk.CTkFont(size=11))
        self.max_value_entry.pack(side="left", padx=5)
        self.max_value_entry.bind('<Return>', self.on_manual_range_change)
        self.max_value_entry.bind('<FocusOut>', self.on_manual_range_change)
        
        # Set initial state for range inputs
        if self.colorbar_range_mode == 'auto':
            self.min_value_entry.configure(state="disabled")
            self.max_value_entry.configure(state="disabled")
        
        # NEW: Export section
        self.export_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Export",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.export_label.pack(pady=(20, 10), padx=20)
        
        # Create frame for export controls
        self.export_controls_frame = ctk.CTkFrame(self.sidebar_frame)
        self.export_controls_frame.pack(fill="x", padx=15, pady=5)
        
        # Export format selection
        format_frame = ctk.CTkFrame(self.export_controls_frame)
        format_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            format_frame,
            text="Format:",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=5, pady=2)
        
        self.export_format_dropdown = ctk.CTkOptionMenu(
            format_frame,
            values=["png", "pdf", "svg", "jpg", "tiff"],
            command=self.on_export_format_change,
            width=160
        )
        self.export_format_dropdown.set(self.export_format)
        self.export_format_dropdown.pack(padx=5, pady=2)
        
        # DPI selection
        dpi_frame = ctk.CTkFrame(self.export_controls_frame)
        dpi_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            dpi_frame,
            text="DPI:",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=5, pady=2)
        
        self.export_dpi_dropdown = ctk.CTkOptionMenu(
            dpi_frame,
            values=["150", "300", "600", "1200"],
            command=self.on_export_dpi_change,
            width=160
        )
        self.export_dpi_dropdown.set(str(self.export_dpi))
        self.export_dpi_dropdown.pack(padx=5, pady=2)
        
        # Export buttons
        export_buttons_frame = ctk.CTkFrame(self.export_controls_frame)
        export_buttons_frame.pack(fill="x", padx=10, pady=10)
        
        self.export_current_btn = ctk.CTkButton(
            export_buttons_frame,
            text="Export Current Frame",
            command=self.export_current_frame,
            width=170,
            height=32,
            font=ctk.CTkFont(size=11)
        )
        self.export_current_btn.pack(pady=3)
        
        self.export_interval_btn = ctk.CTkButton(
            export_buttons_frame,
            text="Export Frame Interval",
            command=self.export_frame_interval,
            width=170,
            height=32,
            font=ctk.CTkFont(size=11)
        )
        self.export_interval_btn.pack(pady=3)
        
        # ROI Section
        self.roi_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="ROI Selection",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.roi_label.pack(pady=(20, 10), padx=20)
        
        # ROI mode toggle
        self.roi_mode_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Enable ROI Mode",
            command=self.toggle_roi_mode,
            fg_color="gray",
            width=200
        )
        self.roi_mode_btn.pack(pady=5, padx=20)
        
        # ROI selection buttons frame
        self.roi_buttons_frame = ctk.CTkFrame(self.sidebar_frame)
        self.roi_buttons_frame.pack(fill="x", padx=15, pady=5)
        
        self.roi_rect_btn = ctk.CTkButton(
            self.roi_buttons_frame,
            text="Rectangle",
            command=self.set_rectangle_roi,
            state="disabled",
            width=85
        )
        self.roi_rect_btn.pack(side="left", padx=5, pady=5)
        
        self.roi_point_btn = ctk.CTkButton(
            self.roi_buttons_frame,
            text="Point",
            command=self.set_point_roi,
            state="disabled",
            width=85
        )
        self.roi_point_btn.pack(side="right", padx=5, pady=5)
        
        # ROI clear button
        self.roi_clear_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Clear ROIs",
            command=self.clear_rois,
            state="disabled",
            width=200,
            fg_color="red",
            hover_color="darkred"
        )
        self.roi_clear_btn.pack(pady=5, padx=20)
        
        # Analysis section
        self.analysis_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Analysis",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.analysis_label.pack(pady=(20, 10), padx=20)
        
        self.plot_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Plot Data",
            command=self.plot_action,
            width=200
        )
        self.plot_btn.pack(pady=5, padx=20)
        
        self.stats_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Statistics", 
            command=self.stats_action,
            width=200
        )
        self.stats_btn.pack(pady=5, padx=20)
        
        # Theme toggle
        self.theme_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Toggle Theme",
            command=self.toggle_theme,
            width=200
        )
        self.theme_btn.pack(pady=15, padx=20)
        
        # Add some bottom padding to ensure last element is visible
        bottom_spacer = ctk.CTkLabel(self.sidebar_frame, text="", height=20)
        bottom_spacer.pack(pady=5)
        
        # Main content area
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=(20, 20), pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)
        
        # Welcome message
        self.welcome_label = ctk.CTkLabel(
            self.main_frame,
            text="PixelProbe",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.welcome_label.grid(row=0, column=0, padx=20, pady=20)
        
        # Toolbar info frame
        self.toolbar_info_frame = ctk.CTkFrame(self.main_frame, height=40)
        self.toolbar_info_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.toolbar_info_frame.grid_columnconfigure(1, weight=1)
        
        # Zoom instructions
        self.zoom_instructions_label = ctk.CTkLabel(
            self.toolbar_info_frame,
            text="💡 Right-click and drag to pan | Mouse wheel to zoom | Double-click to reset view",
            font=ctk.CTkFont(size=11)
        )
        self.zoom_instructions_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Zoom info label
        self.zoom_info_label = ctk.CTkLabel(
            self.toolbar_info_frame,
            text="Ready for pixel-level selection",
            font=ctk.CTkFont(size=11)
        )
        self.zoom_info_label.grid(row=0, column=1, padx=10, pady=5, sticky="e")
        
        # Content area for displaying images/plots
        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
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
        
        # Enable built-in matplotlib navigation
        self.setup_manual_navigation()
        
        # Status bar
        self.status_label = ctk.CTkLabel(
            self.root,
            text="Ready",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 10))
        
        # Set up zoom tracking
        self.setup_zoom_tracking()
        
        self.logger.debug("Main interface widgets created with scrollable sidebar")

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
        
        # FIXED: Add proper close handling
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.logger.debug(f"Window configured: {width}x{height}")

    def update_status(self, message: str):
        """Update status with a persistent message that stays longer"""
        if self.is_closing:
            return
        
        self.status_label.configure(text=message)
        self.root.update_idletasks()
        
        # Clear the message after 8 seconds - with cleanup tracking
        def clear_status():
            if not self.is_closing:
                try:
                    self.status_label.configure(text="Ready")
                except:
                    pass
        
        callback_id = self.root.after(8000, clear_status)
        self.scheduled_callbacks.append(callback_id)

    def on_closing(self):
        """Handle application closing with proper cleanup"""
        self.logger.info("Application closing...")
        
        # Prevent new callbacks
        self.is_closing = True
        
        try:
            # Cancel all scheduled callbacks
            for callback_id in self.scheduled_callbacks:
                try:
                    self.root.after_cancel(callback_id)
                except:
                    pass
            
            # Cleanup ROI selector
            if self.roi_selector:
                self.roi_selector.deactivate_selection()
            
            # Close matplotlib figures
            plt.close('all')
            
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
        
        # Close the application
        self.root.quit()
        self.root.destroy()

    def run(self):
        """Start the application main loop"""
        self.logger.info("Starting PixelProbe main loop")
        try:
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
        finally:
            self.logger.info("PixelProbe application closed")

    def snap_to_pixel_grid(self, coord):
        """Snap coordinate to nearest pixel center"""
        return int(round(coord))
    
    def get_pixel_info_at_cursor(self, event):
        """Get pixel information at cursor position"""
        if event.inaxes == self.subplot and self.current_image is not None:
            x = int(round(event.xdata)) if event.xdata is not None else None
            y = int(round(event.ydata)) if event.ydata is not None else None
            
            if x is not None and y is not None:
                if 0 <= y < self.current_image.shape[0] and 0 <= x < self.current_image.shape[1]:
                    pixel_value = self.current_image[y, x]
                    return f"Pixel ({x}, {y}): {pixel_value}"
        
        return "Outside image bounds"

    def update_roi_status(self, message):
        """Update status with ROI-specific messaging"""
        pixel_perfect_message = f"[PIXEL-PERFECT] {message}"
        self.update_status(pixel_perfect_message)

    def get_roi_statistics(self):
        """Get statistics for all current ROIs with debug info"""
        print(f"DEBUG: ROI selector exists: {self.roi_selector is not None}")
        print(f"DEBUG: Current image exists: {self.current_image is not None}")
        
        if self.roi_selector:
            print(f"DEBUG: Number of ROIs: {len(self.roi_selector.rois)}")
            for i, roi in enumerate(self.roi_selector.rois):
                print(f"DEBUG: ROI {i}: {roi.label}, type: {roi.roi_type}")
        
        if self.roi_selector and self.current_image is not None:
            roi_stats = self.roi_selector.get_roi_statistics(self.current_image)
            print(f"DEBUG: ROI stats returned: {roi_stats}")
            return roi_stats
        
        print("DEBUG: Returning empty dict")
        return {}
        
    def create_histogram_plot(self, parent_frame):
        """Create histogram plot in the statistics window"""
        try:
            # Generate histogram data
            hist_data = self.analyzer.generate_histogram_data(self.current_image)
            
            if not hist_data:
                error_label = tk.Label(parent_frame, text="No histogram data available", 
                                    font=("Arial", 12), fg="red", bg='#2b2b2b')
                error_label.pack(pady=50)
                return
            
            # Create matplotlib figure
            fig = Figure(figsize=(10, 6), dpi=80, facecolor='#2b2b2b')
            
            if hist_data.get('type') == 'grayscale':
                # Grayscale histogram
                ax = fig.add_subplot(111, facecolor='#1e1e1e')
                
                # Use actual data range
                data = hist_data['data']
                data_min, data_max = float(np.min(data)), float(np.max(data))
                
                ax.hist(data, bins=256, range=(data_min, data_max), 
                    color='lightblue', alpha=0.7, edgecolor='white', linewidth=0.5)
                ax.set_title('Grayscale Histogram', fontsize=14, fontweight='bold', color='white')
                ax.set_xlabel('Pixel Intensity', color='white')
                ax.set_ylabel('Frequency', color='white')
                ax.grid(True, alpha=0.3, color='white')
                ax.tick_params(colors='white')
                
            else:
                # Color histogram
                ax = fig.add_subplot(111, facecolor='#1e1e1e')
                colors = ['red', 'green', 'blue']
                
                for color in colors:
                    if color in hist_data.get('histograms', {}):
                        hist_info = hist_data['histograms'][color]
                        bin_centers = (hist_info['bins'][:-1] + hist_info['bins'][1:]) / 2
                        ax.plot(bin_centers, hist_info['hist'], 
                            color=color, alpha=0.8, linewidth=2, label=f'{color.capitalize()} Channel')
                
                ax.set_title('RGB Histogram', fontsize=14, fontweight='bold', color='white')
                ax.set_xlabel('Pixel Intensity', color='white')
                ax.set_ylabel('Frequency', color='white')
                ax.legend()
                ax.grid(True, alpha=0.3, color='white')
                ax.tick_params(colors='white')
            
            fig.tight_layout()
            
            # Add to GUI
            canvas = FigureCanvasTkAgg(fig, parent_frame)
            canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
            canvas.draw()
            
        except Exception as e:
            self.logger.error(f"Failed to create histogram plot: {e}")
            error_label = tk.Label(parent_frame, text=f"Histogram error: {str(e)}", 
                                font=("Arial", 12), fg="red", bg='#2b2b2b')
            error_label.pack(pady=50)

    def set_rectangle_roi(self):
        """Set ROI selection to rectangle mode"""
        if self.roi_selector and self.roi_mode_active:
            self.roi_selector.set_roi_type(ROIType.RECTANGLE)
            self._update_roi_button_colors("rectangle")

    def set_circle_roi(self):
        """Set ROI selection to circle mode"""
        if self.roi_selector and self.roi_mode_active:
            self.roi_selector.set_roi_type(ROIType.CIRCLE)
            self._update_roi_button_colors("circle")

    def set_point_roi(self):
        """Set ROI selection to point mode"""
        if self.roi_selector and self.roi_mode_active:
            self.roi_selector.set_roi_type(ROIType.POINT)
            self._update_roi_button_colors("point")

    def _update_roi_button_colors(self, active_type):
        """Update ROI button colors to show active selection"""
        default_color = ["#1f538d", "#14375e"]
        
        self.roi_rect_btn.configure(fg_color=default_color)
        self.roi_circle_btn.configure(fg_color=default_color)
        self.roi_point_btn.configure(fg_color=default_color)
        
        active_color = ["#ff6b35", "#e85a31"]
        if active_type == "rectangle":
            self.roi_rect_btn.configure(fg_color=active_color)
        elif active_type == "circle":
            self.roi_circle_btn.configure(fg_color=active_color)
        elif active_type == "point":
            self.roi_point_btn.configure(fg_color=active_color)

    def clear_rois(self):
        """Clear all ROIs without disrupting ROI mode"""
        if not self.roi_selector:
            return
        
        # Clear ROIs from selector
        self.roi_selector.clear_rois()
        
        # Just redraw the canvas without calling display_image
        if self.current_image is not None:
            self.canvas.draw()
        
        self.update_status("All ROIs cleared - selection mode preserved")

    def _deactivate_roi_mode(self):
        """Deactivate ROI selection mode"""
        if self.roi_selector:
            self.roi_selector.deactivate_selection()
        
        self.roi_mode_active = False
        
        self.roi_mode_btn.configure(text="Enable ROI Mode", fg_color="gray")
        self.roi_rect_btn.configure(state="disabled")
        self.roi_circle_btn.configure(state="disabled")
        self.roi_point_btn.configure(state="disabled")
        self.roi_clear_btn.configure(state="disabled")
        
        self.update_status("ROI mode deactivated")
    
    def update_roi_average(self, roi_checkboxes, roi_stats, average_text):
        """Update the average results when ROI selection changes"""
        
        # Get selected ROIs
        selected_rois = [roi_name for roi_name, checkbox_var in roi_checkboxes.items() if checkbox_var.get()]
        
        if not selected_rois:
            # No ROIs selected
            no_selection_message = """
    📈 AVERAGE ROI RESULTS
    {'='*50}

    No ROIs selected.

    Please select at least one ROI from the 
    left panel to see averaged statistics.
            """
            average_text.config(state='normal')
            average_text.delete('1.0', tk.END)
            average_text.insert('1.0', no_selection_message)
            average_text.config(state='disabled')
            return
        
        # Calculate averages for selected ROIs
        valid_values = []
        valid_point_values = []
        valid_region_data = []
        
        for roi_name in selected_rois:
            roi_data = roi_stats[roi_name]
            
            if 'error' in roi_data:
                continue  # Skip ROIs with errors
                
            if 'pixel_value' in roi_data:
                # Point ROI
                valid_point_values.append(roi_data['pixel_value'])
                valid_values.append(roi_data['pixel_value'])
            else:
                # Region ROI - use mean value
                if 'mean' in roi_data:
                    valid_values.append(roi_data['mean'])
                    valid_region_data.append({
                        'mean': roi_data['mean'],
                        'std': roi_data['std'],
                        'pixel_count': roi_data['pixel_count']
                    })
        
        if not valid_values:
            # No valid data
            error_message = """
    📈 AVERAGE ROI RESULTS
    {'='*50}

    ❌ No valid data found in selected ROIs.

    All selected ROIs contain errors or 
    invalid data.
            """
            average_text.config(state='normal')
            average_text.delete('1.0', tk.END)
            average_text.insert('1.0', error_message)
            average_text.config(state='disabled')
            return
        
        # Calculate statistics
        mean_value = np.mean(valid_values)
        std_value = np.std(valid_values)
        min_value = np.min(valid_values)
        max_value = np.max(valid_values)
        
        # Create results text
        results_text = f"""
    📈 AVERAGE ROI RESULTS
    {'='*50}

    📊 SELECTION SUMMARY:
        Total ROIs Selected:     {len(selected_rois)}
        Valid Data Points:       {len(valid_values)}
        Point ROIs:             {len(valid_point_values)}
        Region ROIs:            {len(valid_region_data)}

    🎯 AVERAGED STATISTICS:
        Mean Value:             {mean_value:.3f}
        Standard Deviation:     {std_value:.3f}
        Minimum:                {min_value:.3f}
        Maximum:                {max_value:.3f}
        Range:                  {max_value - min_value:.3f}
        
    📋 SELECTED ROI DETAILS:
    """
        
        for roi_name in selected_rois:
            roi_data = roi_stats[roi_name]
            if 'error' in roi_data:
                results_text += f"    ❌ {roi_name}: {roi_data['error']}\n"
            elif 'pixel_value' in roi_data:
                results_text += f"    📍 {roi_name}: {roi_data['pixel_value']:.3f}\n"
            else:
                results_text += f"    📊 {roi_name}: {roi_data['mean']:.3f} ± {roi_data['std']:.3f}\n"
        
        if len(valid_region_data) > 0:
            # Additional region-specific statistics
            total_pixels = sum(r['pixel_count'] for r in valid_region_data)
            weighted_mean = sum(r['mean'] * r['pixel_count'] for r in valid_region_data) / total_pixels
            
            results_text += f"""
    🔍 REGION-SPECIFIC ANALYSIS:
        Total Pixels:           {total_pixels:,}
        Weighted Mean:          {weighted_mean:.3f}
        """
        
        # Update the text area
        average_text.config(state='normal')
        average_text.delete('1.0', tk.END)
        average_text.insert('1.0', results_text)
        average_text.config(state='disabled')

    def select_all_rois(self, roi_checkboxes, roi_stats, average_text):
        """Select all ROI checkboxes"""
        for checkbox_var in roi_checkboxes.values():
            checkbox_var.set(True)
        self.update_roi_average(roi_checkboxes, roi_stats, average_text)

    def clear_all_rois(self, roi_checkboxes, roi_stats, average_text):
        """Clear all ROI checkboxes"""
        for checkbox_var in roi_checkboxes.values():
            checkbox_var.set(False)
        self.update_roi_average(roi_checkboxes, roi_stats, average_text)

    def setup_manual_navigation(self):
        """Set up manual navigation using matplotlib's built-in features"""
        
        # Enable matplotlib's built-in pan and zoom
        def on_key_press(event):
            """Handle keyboard shortcuts for navigation"""

            # PRIORITY: Let ROI selector handle Ctrl key when in Point mode
            if (self.roi_mode_active and 
                self.roi_selector and 
                self.roi_selector.current_roi_type == ROIType.POINT and
                event.key == 'ctrl'):
                # Don't process this event - let ROI selector handle it
                return

            if event.key == 'r':  # Reset view
                self.subplot.set_xlim(auto=True)
                self.subplot.set_ylim(auto=True)
                self.canvas.draw()
            elif event.key == 'h':  # Home/fit view
                if self.current_image is not None:
                    self.subplot.set_xlim(0, self.current_image.shape[1])
                    self.subplot.set_ylim(self.current_image.shape[0], 0)
                    self.canvas.draw()
        
        def on_scroll(event):
            """Handle mouse wheel zooming"""
            if event.inaxes != self.subplot:
                return
            
            if self.current_image is None:
                return
                
            # Get current axis limits
            xlim = self.subplot.get_xlim()
            ylim = self.subplot.get_ylim()
            
            # Calculate zoom center (mouse position)
            xdata, ydata = event.xdata, event.ydata
            if xdata is None or ydata is None:
                return
            
            # Zoom factor
            zoom_factor = 1.2 if event.button == 'up' else 1/1.2
            
            # Calculate new limits
            x_range = (xlim[1] - xlim[0]) / zoom_factor
            y_range = (ylim[1] - ylim[0]) / zoom_factor
            
            # Center zoom on mouse position
            new_xlim = [xdata - x_range/2, xdata + x_range/2]
            new_ylim = [ydata - y_range/2, ydata + y_range/2]
            
            # Apply limits
            self.subplot.set_xlim(new_xlim)
            self.subplot.set_ylim(new_ylim)
            self.canvas.draw()
        
        def on_button_press(event):
            """Start panning"""
            if event.button == 3:  # Right mouse button
                self.pan_start = (event.xdata, event.ydata)
                self.canvas.get_tk_widget().configure(cursor="fleur")
        
        def on_button_release(event):
            """Stop panning"""
            if event.button == 3:  # Right mouse button
                self.pan_start = None
                self.canvas.get_tk_widget().configure(cursor="")
        
        def on_motion(event):
            """Handle panning motion"""
            if hasattr(self, 'pan_start') and self.pan_start and event.inaxes == self.subplot:
                if self.current_image is None:
                    return
                    
                dx = self.pan_start[0] - event.xdata
                dy = self.pan_start[1] - event.ydata
                
                xlim = self.subplot.get_xlim()
                ylim = self.subplot.get_ylim()
                
                self.subplot.set_xlim([xlim[0] + dx, xlim[1] + dx])
                self.subplot.set_ylim([ylim[0] + dy, ylim[1] + dy])
                self.canvas.draw_idle()
        
        def on_double_click(event):
            """Reset zoom on double click"""
            if event.dblclick and event.inaxes == self.subplot:
                if self.current_image is not None:
                    self.subplot.set_xlim(0, self.current_image.shape[1])
                    self.subplot.set_ylim(self.current_image.shape[0], 0)
                    self.canvas.draw()
        
        # Connect events
        self.figure.canvas.mpl_connect('key_press_event', on_key_press)
        self.figure.canvas.mpl_connect('scroll_event', on_scroll)
        self.figure.canvas.mpl_connect('button_press_event', on_button_press)
        self.figure.canvas.mpl_connect('button_release_event', on_button_release)
        self.figure.canvas.mpl_connect('motion_notify_event', on_motion)
        self.figure.canvas.mpl_connect('button_press_event', on_double_click)
        
        # Make the canvas focusable for keyboard events
        self.canvas.get_tk_widget().focus_set()

    def setup_zoom_tracking(self):
        """Set up zoom level tracking and pixel-level precision"""
        def on_xlims_change(axes):
            """Track zoom changes and update info"""
            try:
                xlim = axes.get_xlim()
                ylim = axes.get_ylim()
                
                if self.current_image is not None:
                    # Calculate zoom level
                    img_width = self.current_image.shape[1]
                    img_height = self.current_image.shape[0]
                    
                    view_width = abs(xlim[1] - xlim[0])
                    view_height = abs(ylim[1] - ylim[0])
                    
                    zoom_x = img_width / view_width if view_width > 0 else 1
                    zoom_y = img_height / view_height if view_height > 0 else 1
                    zoom_level = min(zoom_x, zoom_y)
                    
                    # Update zoom info
                    if hasattr(self, 'zoom_info_label'):
                        if zoom_level > 10:  # When each pixel is > 10 screen pixels
                            self.zoom_info_label.configure(
                                text=f"🔍 Zoom: {zoom_level:.1f}x | PIXEL-LEVEL - Perfect for precise selection!"
                            )
                        elif zoom_level > 2:
                            self.zoom_info_label.configure(
                                text=f"🔍 Zoom: {zoom_level:.1f}x | Good resolution for ROI selection"
                            )
                        else:
                            self.zoom_info_label.configure(
                                text=f"🔍 Zoom: {zoom_level:.1f}x | Zoom in more for pixel precision"
                            )
            except Exception as e:
                self.logger.debug(f"Zoom tracking error: {e}")
        
        # Connect zoom tracking
        self.subplot.callbacks.connect('xlim_changed', on_xlims_change)
        self.subplot.callbacks.connect('ylim_changed', on_xlims_change)

    # NEW: ROI-related methods
    def toggle_roi_mode(self):
        """Toggle ROI selection mode"""
        if self.roi_mode_active:
            # Deactivate
            self._deactivate_roi_mode()
        else:
            # Activate
            self._activate_roi_mode()

    def _activate_roi_mode(self):
        """Activate ROI selection mode with proper initialization"""
        if self.current_image is None:
            self.update_status("Please load an image first")
            messagebox.showinfo("No Image", "Please load an image before enabling ROI mode")
            return
        
        try:
            # Create ROI selector if it doesn't exist or needs reinitialization
            if not self.roi_selector:
                self.roi_selector = ROISelector(
                    self.figure, 
                    self.subplot, 
                    status_callback=self.update_status
                )
                self.logger.info("ROI selector created")
            
            # Check if ROI selector's subplot reference is still valid
            elif self.roi_selector.subplot != self.subplot:
                self.logger.info("ROI selector subplot reference outdated, reinitializing...")
                # Store existing ROIs
                existing_rois = self.roi_selector.rois.copy() if self.roi_selector.rois else []
                current_roi_type = self.roi_selector.current_roi_type
                
                # Deactivate current selection
                if self.roi_selector.selection_active:
                    self.roi_selector.deactivate_selection()
                
                # Reinitialize ROI selector
                self.roi_selector = ROISelector(
                    self.figure, 
                    self.subplot, 
                    status_callback=self.update_status
                )
                
                # Restore ROIs and type
                if existing_rois:
                    self.roi_selector.rois = existing_rois
                    # Redraw existing ROIs
                    for roi in existing_rois:
                        try:
                            self.roi_selector._visualize_roi(roi)
                        except Exception as e:
                            self.logger.warning(f"Failed to restore ROI {roi.label}: {e}")
                if current_roi_type:
                    self.roi_selector.set_roi_type(current_roi_type)
            
            # Enable ROI mode
            self.roi_mode_active = True
            
            # Activate selection
            self.roi_selector.activate_selection()
            
            # Update UI
            self.roi_mode_btn.configure(text="Disable ROI Mode", fg_color=["#ff6b35", "#e85a31"])
            self.roi_rect_btn.configure(state="normal")
            self.roi_point_btn.configure(state="normal")
            self.roi_clear_btn.configure(state="normal")
            
            # Set default to rectangle
            self.set_rectangle_roi()
            
            self.update_status("ROI mode activated - Rectangle selection ready (pixel-perfect)")
            self.logger.info("ROI mode activated successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to activate ROI mode: {e}")
            self.update_status(f"ROI activation failed: {str(e)}")
            messagebox.showerror("ROI Error", f"Failed to activate ROI mode:\n{str(e)}")

    def _deactivate_roi_mode(self):
        """Deactivate ROI selection mode with proper cleanup"""
        try:
            self.roi_mode_active = False
            
            if self.roi_selector:
                # Deactivate selection with proper cleanup
                self.roi_selector.deactivate_selection()
            
            # Update UI - Note: looking at the code, it seems like there's no circle button in the current version
            self.roi_mode_btn.configure(text="Enable ROI Mode", fg_color="gray")
            self.roi_rect_btn.configure(state="disabled")
            self.roi_point_btn.configure(state="disabled")
            self.roi_clear_btn.configure(state="disabled")
            
            # Reset button colors to default
            self._update_roi_button_colors("none")
            
            self.update_status("ROI mode deactivated")
            self.logger.info("ROI mode deactivated")
            
        except Exception as e:
            self.logger.error(f"Error deactivating ROI mode: {e}")
            self.update_status(f"ROI deactivation error: {str(e)}")

    def set_rectangle_roi(self):
        """Set ROI selection to rectangle mode"""
        if self.roi_selector and self.roi_mode_active:
            self.roi_selector.set_roi_type(ROIType.RECTANGLE)
            self._update_roi_button_colors("rectangle")

    def set_point_roi(self):
        """Set ROI selection to point mode"""
        if self.roi_selector and self.roi_mode_active:
            self.roi_selector.set_roi_type(ROIType.POINT)
            self._update_roi_button_colors("point")

    def _update_roi_button_colors(self, active_type):
        """Update ROI button colors to show active selection"""
        default_color = ["#1f538d", "#14375e"]
        
        # Reset all buttons to default
        self.roi_rect_btn.configure(fg_color=default_color)
        self.roi_point_btn.configure(fg_color=default_color)
        
        # Set active color if not deactivating
        if active_type != "none":
            active_color = ["#ff6b35", "#e85a31"]
            if active_type == "rectangle":
                self.roi_rect_btn.configure(fg_color=active_color)
            elif active_type == "point":
                self.roi_point_btn.configure(fg_color=active_color)


    def clear_rois(self):
        """Clear all ROIs"""
        if self.roi_selector:
            self.roi_selector.clear_rois()
            if self.current_image is not None:
                current_title = self.subplot.get_title()
                self.display_image(self.current_image, current_title)
            self.update_status("All ROIs cleared and display refreshed")

    def get_roi_statistics(self):
        """Get statistics for all current ROIs with debug info"""
        print(f"DEBUG: ROI selector exists: {self.roi_selector is not None}")
        print(f"DEBUG: Current image exists: {self.current_image is not None}")
        
        if self.roi_selector:
            print(f"DEBUG: Number of ROIs: {len(self.roi_selector.rois)}")
            for i, roi in enumerate(self.roi_selector.rois):
                print(f"DEBUG: ROI {i}: {roi.label}, type: {roi.roi_type}")
        
        if self.roi_selector and self.current_image is not None:
            roi_stats = self.roi_selector.get_roi_statistics(self.current_image)
            print(f"DEBUG: ROI stats returned: {roi_stats}")
            return roi_stats
        
        print("DEBUG: Returning empty dict")
        return {}

    def _redraw_roi_visual(self, roi):
        """Redraw a single ROI visual element"""
        try:
            if roi.roi_type == ROIType.RECTANGLE:
                # Get selected area coordinates
                x = int(round(roi.coordinates['x']))
                y = int(round(roi.coordinates['y']))
                w = int(round(roi.coordinates['width']))
                h = int(round(roi.coordinates['height']))
                
                # Draw rectangle using pixel-centered coordinates
                rect = patches.Rectangle(
                    (x - 0.5, y - 0.5), w, h,
                    fill=False,
                    edgecolor=roi.color,
                    linewidth=2.0,
                    alpha=0.8
                )
                self.subplot.add_patch(rect)
                
                # Add light fill to show selected area
                fill_rect = patches.Rectangle(
                    (x - 0.5, y - 0.5), w, h,
                    fill=True,
                    facecolor=roi.color,
                    alpha=0.1,
                    edgecolor='none'
                )
                self.subplot.add_patch(fill_rect)
            
            elif roi.roi_type == ROIType.POINT:
                # Enhanced point visualization
                self.subplot.plot(
                    roi.coordinates['x'],
                    roi.coordinates['y'],
                    marker='+',
                    color=roi.color,
                    markersize=12,
                    markeredgewidth=3,
                    alpha=0.9
                )
                # Add pixel coordinates as text annotation
                self.subplot.annotate(
                    f"({int(roi.coordinates['x'])}, {int(roi.coordinates['y'])})",
                    (roi.coordinates['x'], roi.coordinates['y']),
                    xytext=(10, 10), textcoords='offset points',
                    fontsize=9, color=roi.color,
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7)
                )
            
            elif roi.roi_type == ROIType.MULTI_POINT:
                # Visualize multiple points
                for i, point in enumerate(roi.coordinates['points']):
                    self.subplot.plot(
                        point['x'], point['y'],
                        marker='o',
                        color=roi.color,
                        markersize=10,
                        markeredgewidth=2,
                        markerfacecolor='none',
                        alpha=0.9
                    )
                    # Add point number
                    self.subplot.annotate(
                        f"{i+1}",
                        (point['x'], point['y']),
                        xytext=(5, 5), textcoords='offset points',
                        fontsize=8, color=roi.color,
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7)
                    )
            
        except Exception as e:
            self.logger.warning(f"Failed to redraw ROI visual: {e}")

    def display_image(self, image_data: np.ndarray, title: str = "Image"):
        """Enhanced display with ROI preservation and colorbar customization"""
        if image_data is None:
            self.logger.error("Cannot display None image data")
            return
        
        try:
            # Import required for consistent colorbar positioning
            from mpl_toolkits.axes_grid1 import make_axes_locatable
            
            # Store current title
            self.current_title = title
            
            # CRITICAL FIX: Store current ROI state (preserve mode even without existing ROIs)
            existing_rois = []
            roi_mode_was_active = False
            current_roi_type = None
            selection_was_active = False

            if self.roi_selector:
                # Always preserve ROI mode state, regardless of existing ROIs
                roi_mode_was_active = self.roi_mode_active
                current_roi_type = self.roi_selector.current_roi_type
                selection_was_active = self.roi_selector.selection_active
                
                # Only copy ROIs if they exist
                if self.roi_selector.rois:
                    existing_rois = self.roi_selector.rois.copy()
            
            # FIXED: Completely clear and recreate the figure to avoid sizing issues
            self.figure.clear()
            
            # FIXED: Create subplot with consistent positioning - always reserve space for potential colorbar
            self.subplot = self.figure.add_subplot(111)
            
            # CRITICAL FIX: Reinitialize ROI selector with new subplot
            if self.roi_selector:
                # Deactivate ROI selection to clean up old event handlers
                if self.roi_selector.selection_active:
                    self.roi_selector.deactivate_selection()
                
                # Create new ROI selector with new subplot
                from pixelprobe.gui.roi_selector import ROISelector
                self.roi_selector = ROISelector(
                    self.figure, 
                    self.subplot, 
                    status_callback=self.update_status
                )
                
                # CRITICAL FIX: Restore ROI mode state
                if roi_mode_was_active:
                    self.roi_mode_active = True
                    if current_roi_type:
                        self.roi_selector.set_roi_type(current_roi_type)
                        # Update button colors to reflect current mode
                        if current_roi_type.value == 'rectangle':
                            self._update_roi_button_colors("rectangle")
                        elif current_roi_type.value == 'point':
                            self._update_roi_button_colors("point")
                    
                    # CRITICAL FIX: Reactivate ROI selection if it was active
                    if selection_was_active:
                        self.roi_selector.activate_selection()
            
            # Get current interpolation method
            interpolation = getattr(self, 'current_display_interpolation', 'nearest')
            
            # Use ORIGINAL array values for display and colorbar calculations
            # Always use self.current_array if available, otherwise use image_data
            original_array = getattr(self, 'current_array', None)
            if original_array is not None:
                display_data = original_array
            else:
                display_data = image_data
            
            # Determine colormap and display mode
            is_grayscale = len(display_data.shape) == 2 or (len(display_data.shape) == 3 and display_data.shape[2] == 1)
            is_rgb = len(display_data.shape) == 3 and display_data.shape[2] == 3
            
            # For grayscale images, prepare data for colormap display
            if is_grayscale:
                if len(display_data.shape) == 3 and display_data.shape[2] == 1:
                    plot_data = display_data[:, :, 0]
                else:
                    plot_data = display_data
                    
                # Determine value range for colorbar
                if self.colorbar_range_mode == 'manual' and self.colorbar_vmin is not None and self.colorbar_vmax is not None:
                    vmin, vmax = self.colorbar_vmin, self.colorbar_vmax
                else:
                    vmin, vmax = plot_data.min(), plot_data.max()
                
                # Display with selected colormap and colorbar
                im = self.subplot.imshow(
                    plot_data, 
                    cmap=self.current_colormap, 
                    aspect='equal',
                    interpolation=interpolation,
                    vmin=vmin, vmax=vmax
                )
                
                # Add colorbar if enabled - ENHANCED with customization
                if self.show_colorbar:
                    divider = make_axes_locatable(self.subplot)
                    cax = divider.append_axes("right", size="5%", pad=0.1)
                    cbar = self.figure.colorbar(im, cax=cax)
                    
                    # Apply tick font size customization
                    cbar.ax.tick_params(labelsize=self.colorbar_tick_fontsize)
                    
                    # Apply colorbar label if specified
                    if self.colorbar_label.strip():
                        cbar.set_label(
                            self.colorbar_label, 
                            fontsize=self.colorbar_label_fontsize,
                            rotation=270,
                            labelpad=20
                        )
                    
                    self.current_colorbar = cbar
                else:
                    self.current_colorbar = None
            
            # For RGB images
            elif is_rgb:
                im = self.subplot.imshow(display_data, aspect='equal', interpolation=interpolation)
                self.current_colorbar = None  # No colorbar for RGB
            
            # Set title and labels
            self.subplot.set_title(title, fontsize=14, fontweight='bold', pad=20)
            self.subplot.set_xlabel('X (pixels)', fontsize=12)
            self.subplot.set_ylabel('Y (pixels)', fontsize=12)
            
            # Set axis limits to show complete image with proper orientation
            self.subplot.set_xlim(-0.5, display_data.shape[1] - 0.5)
            self.subplot.set_ylim(display_data.shape[0] - 0.5, -0.5)
            
            # FIXED: Use constrained layout instead of tight_layout for better colorbar handling
            self.figure.set_constrained_layout(True)
            
            # CRITICAL FIX: Restore ROIs AFTER ROI selector is properly reinitialized
            if existing_rois and self.roi_selector:
                self.roi_selector.rois = existing_rois
                for roi in existing_rois:
                    try:
                        self.roi_selector._visualize_roi(roi)
                    except Exception as e:
                        self.logger.warning(f"Failed to restore ROI {roi.label}: {e}")
            
            # Refresh canvas
            self.canvas.draw()
            self.current_image = image_data
            
            # Update display controls for the new image
            self.update_display_controls_for_image()
            
            # Log display information - ENHANCED
            colorbar_info = f"with colorbar (label: '{self.colorbar_label}', tick_size: {self.colorbar_tick_fontsize}, label_size: {self.colorbar_label_fontsize})" if (self.show_colorbar and is_grayscale) else "without colorbar"
            roi_info = f", {len(existing_rois)} ROIs restored" if existing_rois else ""
            self.logger.info(f"Image displayed {colorbar_info} using {self.current_colormap} colormap, {interpolation} interpolation: {display_data.shape}, {display_data.dtype}{roi_info}")
            
        except Exception as e:
            self.logger.error(f"Failed to display image: {e}")
            self.update_status(f"Display failed: {str(e)}")

    # Enhanced statistics display for point ROIs  
    def format_point_roi_stats(self, roi_name, roi_data, basic_stats):
        """Format point ROI statistics with enhanced detail"""
        if 'error' in roi_data:
            return f"""
        ❌ {roi_name.upper()}:
            Status: {roi_data['error']}
            Coordinates: {roi_data.get('coordinates', 'Unknown')}
        """
        
        x_coord = roi_data.get('x_coord', 'N/A')
        y_coord = roi_data.get('y_coord', 'N/A') 
        pixel_value = roi_data.get('pixel_value', 0)
        
        # Calculate percentile within image
        percentile = self._calculate_percentile(pixel_value, basic_stats)
        
        return f"""
        📍 {roi_name.upper()}:
            Type: Single Pixel Selection
            Pixel Coordinates: ({x_coord}, {y_coord})
            Pixel Value: {pixel_value:.3f}
            Image Percentile: {percentile:.1f}%
            
            🎯 Analysis:
            Value Classification: {'High' if percentile > 75 else 'Medium' if percentile > 25 else 'Low'}
            Relative Position: {'Bright region' if percentile > 75 else 'Dark region' if percentile < 25 else 'Mid-tone region'}
        """

    def load_data_action(self):
        """Handle load data button click"""
        self.logger.info("Load data action triggered")
        self.update_status("Selecting data directory...")
        
        # Get directory from user
        directory = self.file_dialogs.select_directory("Select Array Data Directory")
        if not directory:
            self.update_status("Data loading cancelled")
            return
        
        # CRITICAL FIX: Force clear array handler cache before setting new directory
        self.array_handler.clear_cache()
        self.logger.info("Cleared array handler cache before loading new directory")
        
        # Set directory in array handler (this will also clear cache)
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
        """Complete data loading with proper camera roll reset"""
        try:
            self.update_status(f"Loading {len(selected_items)} items...")
            
            # CRITICAL FIX: Force complete reset of everything
            self.current_array = None
            self.current_image = None
            
            # CRITICAL FIX: Completely destroy camera roll before any operation
            if hasattr(self, 'camera_roll') and self.camera_roll:
                # Stop any ongoing thumbnail generation
                self.camera_roll.thumbnail_loading_active = False
                
                # Unbind ALL keyboard shortcuts first
                try:
                    self.root.unbind('<Left>')
                    self.root.unbind('<Right>')  
                    self.root.unbind('<Home>')
                    self.root.unbind('<End>')
                    self.root.unbind('<Escape>')
                except:
                    pass
                
                # Hide and destroy the UI
                self.camera_roll._hide_camera_roll()
                
                # Completely reset camera roll object
                self.camera_roll = None
            
            if operation == "single":
                # Single item - no camera roll
                item_num = selected_items[0]
                array_data = self.array_handler.load_item(item_num)
                
                if array_data is not None:
                    self.current_array = array_data
                    self.current_image = self._array_to_display_image(array_data)
                    # FORCE immediate display
                    self.display_image(self.current_image, f"Array Item {item_num}")
                    self.update_status(f"Loaded item {item_num} - Shape: {array_data.shape}")
                    self.logger.info(f"Single item loaded and displayed: {item_num}")
                else:
                    self.update_status(f"Failed to load item {item_num}")
            
            elif operation == "multiple":
                # Multiple items - create fresh camera roll
                arrays = self.array_handler.load_multiple_items(selected_items)
                
                if arrays:
                    self.logger.info(f"Loading {len(arrays)} arrays into fresh camera roll")
                    
                    # Force create completely new camera roll
                    from pixelprobe.gui.camera_roll import CameraRollInterface
                    self.camera_roll = CameraRollInterface(self)
                    
                    # Load data (this will show camera roll and display first frame)
                    self.camera_roll.load_multiple_frames(arrays)
                    self.update_status(f"Loaded {len(arrays)} frames - Navigate with ← → keys or thumbnails")
                    self.logger.info(f"Camera roll loaded with {len(arrays)} frames")
                else:
                    self.update_status("Failed to load any items")
            
            elif operation == "average":
                # Average operation - no camera roll needed
                averaged_array = self.array_handler.average_items(selected_items)
                
                if averaged_array is not None:
                    self.current_array = averaged_array
                    self.current_image = self._array_to_display_image(averaged_array)
                    # FORCE immediate display
                    self.display_image(self.current_image, f"Averaged Items {selected_items}")
                    self.update_status(f"Averaged {len(selected_items)} items - Shape: {averaged_array.shape}")
                    self.logger.info(f"Averaged data loaded and displayed")
                else:
                    self.update_status("Failed to average items")
                    
        except Exception as e:
            self.logger.error(f"Error loading arrays: {e}")
            self.update_status(f"Error loading arrays: {str(e)}")

    def _array_to_display_image(self, array_data):
        """Convert array data to displayable image format"""
        # Normalize array data for display
        if array_data.dtype == np.uint8:
            return array_data
        else:
            # Normalize to 0-255 range
            normalized = ((array_data - array_data.min()) / 
                         (array_data.max() - array_data.min()) * 255)
            return normalized.astype(np.uint8)

    def load_image_action(self):
        """Handle load image button click with complete reset"""
        self.logger.info("Load image action triggered")
        self.update_status("Selecting image file...")
        
        # Get image file from user
        image_path = self.file_dialogs.select_image_file()
        if not image_path:
            self.update_status("Image loading cancelled")
            return
        
        try:
            # CRITICAL FIX: Complete reset before loading
            self.current_array = None
            self.current_image = None
            self.current_items = []
            self.current_operation = None
            
            # CRITICAL FIX: Completely destroy camera roll
            if hasattr(self, 'camera_roll') and self.camera_roll:
                # Stop any ongoing operations
                self.camera_roll.thumbnail_loading_active = False
                
                # Unbind keyboard shortcuts
                try:
                    self.root.unbind('<Left>')
                    self.root.unbind('<Right>')
                    self.root.unbind('<Home>')
                    self.root.unbind('<End>')
                    self.root.unbind('<Escape>')
                except:
                    pass
                
                # Hide and destroy
                self.camera_roll._hide_camera_roll()
                self.camera_roll = None
                self.logger.info("Camera roll completely destroyed for image loading")
            
            # Clear the current display
            try:
                self.figure.clear()
                self.subplot = self.figure.add_subplot(111)
                self.subplot.set_title("Loading new image...")
                self.subplot.axis('off')
                self.canvas.draw()
            except:
                pass
            
            # Load image
            image_data = self.image_loader.load_image(image_path)
            if image_data is not None:
                self.current_image = image_data
                self.current_array = image_data  # For processing operations
                # FORCE immediate display
                self.display_image(image_data, f"Image: {image_path.name}")
                self.update_status(f"Loaded image: {image_path.name} - Shape: {image_data.shape}")
                self.logger.info(f"New image loaded and displayed: {image_path.name}")
            else:
                self.update_status("Failed to load image")
        except Exception as e:
            self.logger.error(f"Error loading image: {e}")
            self.update_status(f"Error loading image: {str(e)}")

    def denoise_action(self):
        """Handle denoise button click - show options dialog"""
        self.logger.info("Denoise action triggered")
        
        if self.current_image is None:
            self.update_status("No image loaded - please load an image or array data first")
            return
        
        # Show denoising options dialog
        self.show_denoise_options()
    
    def show_denoise_options(self):
        """Show denoising method selection dialog with vertical layout and scrollbar"""
        
        # Create options window with better size for vertical layout
        options_window = tk.Toplevel(self.root)
        options_window.title("PixelProbe - Denoising Method Selection")
        options_window.geometry("1200x1300")
        options_window.transient(self.root)
        options_window.grab_set()
        
        # Configure window background
        options_window.configure(bg='#2b2b2b')
        
        # Create main container frame
        container_frame = tk.Frame(options_window, bg='#2b2b2b')
        container_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Create canvas and scrollbar for scrolling
        canvas = tk.Canvas(container_frame, bg='#2b2b2b', highlightthickness=0)
        scrollbar = tk.Scrollbar(container_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#2b2b2b')
        
        # Configure scrolling
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Now use scrollable_frame for content
        main_frame = scrollable_frame
        
        # Title with larger font
        title_label = tk.Label(
            main_frame, 
            text="Select Denoising Method", 
            font=("Arial", 28, "bold"),
            fg='#ffffff',
            bg='#2b2b2b'
        )
        title_label.pack(pady=(20, 30))
        
        # Subtitle
        subtitle_label = tk.Label(
            main_frame,
            text="Choose the denoising algorithm that best fits your image type and noise characteristics",
            font=("Arial", 16),
            fg='#cccccc',
            bg='#2b2b2b',
            wraplength=1000
        )
        subtitle_label.pack(pady=(0, 30))
        
        method_var = tk.StringVar(value="adaptive")
        methods = [
            ("Adaptive (Recommended)", "adaptive", "Automatically selects the best method based on image characteristics", "#4CAF50"),
            ("Gaussian Filter (Simple)", "gaus", "Basic blur filter - fast and simple for general noise reduction", "#2196F3"),
            ("Median Filter (Simple)", "med", "Excellent for removing salt-and-pepper noise", "#2196F3"),
            ("Mean Filter (Simple)", "mean", "Simple averaging filter for uniform noise", "#2196F3"),
            ("Non-Local Means (Advanced)", "nlm", "Superior for texture preservation and complex patterns", "#FF9800"),
            ("Total Variation (Advanced)", "tv", "Best for smooth images with sharp edges", "#FF9800"),
            ("Bilateral Filter (Advanced)", "bilateral", "Edge-preserving smoothing with noise reduction", "#FF9800")
        ]
        
        def update_selection_styling():
            """Update visual styling based on selection"""
            for widget_frame in method_frames:
                if widget_frame.method_value == method_var.get():
                    widget_frame.configure(bg='#4a5568', relief='solid', borderwidth=3)
                    for child in widget_frame.winfo_children():
                        if isinstance(child, tk.Radiobutton):
                            child.configure(bg='#4a5568')
                        elif isinstance(child, tk.Label):
                            child.configure(bg='#4a5568')
                else:
                    widget_frame.configure(bg='#3c3c3c', relief='flat', borderwidth=1)
                    for child in widget_frame.winfo_children():
                        if isinstance(child, tk.Radiobutton):
                            child.configure(bg='#3c3c3c')
                        elif isinstance(child, tk.Label):
                            child.configure(bg='#3c3c3c')
        
        # Method selection frame
        method_frames = []
        
        for name, value, description, color in methods:
            # Create frame for each method
            method_frame = tk.Frame(main_frame, bg='#3c3c3c', padx=20, pady=15, relief='flat', borderwidth=1)
            method_frame.pack(fill='x', pady=8, padx=20)
            method_frame.method_value = value  # Store the value for styling
            method_frames.append(method_frame)
            
            # Radio button with larger font
            radio = tk.Radiobutton(
                method_frame, 
                text=name,
                variable=method_var, 
                value=value,
                font=("Arial", 18, "bold"),
                fg='#ffffff',
                bg='#3c3c3c',
                activebackground='#4a5568',
                activeforeground='#ffffff',
                selectcolor='#2196F3',
                command=update_selection_styling,
                anchor='w'
            )
            radio.pack(anchor='w', fill='x')
            
            # Description label
            desc_label = tk.Label(
                method_frame, 
                text=description,
                font=("Arial", 14),
                fg='#cccccc',
                bg='#3c3c3c',
                wraplength=1000,
                justify='left'
            )
            desc_label.pack(anchor='w', padx=(30, 0), pady=(5, 0))
        
        def apply_denoising():
            """Apply selected denoising method and close window"""
            selected_method = method_var.get()
            options_window.destroy()
            self.apply_selected_denoising(selected_method)
        
        # Buttons with modern styling
        button_frame = tk.Frame(main_frame, bg='#2b2b2b')
        button_frame.pack(pady=30, fill='x')
        
        # Apply button with CustomTkinter styling
        apply_btn = ctk.CTkButton(
            button_frame,
            text="Apply Denoising",
            command=apply_denoising,
            font=ctk.CTkFont(size=18, weight="bold"),
            height=50,
            width=200,
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        apply_btn.pack(side='left', padx=20, expand=True)
        
        # Cancel button with CustomTkinter styling  
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel", 
            command=options_window.destroy,
            font=ctk.CTkFont(size=18, weight="bold"),
            height=50,
            width=200,
            fg_color="#f44336",
            hover_color="#da190b"
        )
        cancel_btn.pack(side='right', padx=20, expand=True)
        
        # Enable mouse wheel scrolling
        def on_mousewheel(event):
            # Check if canvas still exists before trying to scroll
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except tk.TclError:
                # Canvas has been destroyed, unbind the event
                pass
        
        # Bind mouse wheel to canvas specifically, not to all widgets
        canvas.bind("<MouseWheel>", on_mousewheel)
        
        # Cleanup function to properly unbind events when window closes
        def on_window_close():
            try:
                canvas.unbind("<MouseWheel>")
            except:
                pass
            options_window.destroy()
        
        # Override the window close event
        options_window.protocol("WM_DELETE_WINDOW", on_window_close)
        
        # Center the window
        options_window.update_idletasks()
        x = (options_window.winfo_screenwidth() // 2) - (1200 // 2)
        y = (options_window.winfo_screenheight() // 3) - (1300 // 4)
        options_window.geometry(f"1200x1300+{x}+{y}")
        
        # Bind variable change to update styling
        method_var.trace('w', lambda *args: update_selection_styling())
        
        # Initialize styling
        update_selection_styling()

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

    def segment_action(self):
        """Handle segment button click"""
        self.logger.info("Segment action triggered")
        self.update_status("Segmentation not yet implemented")

    def interpolation_action(self):
        """Handle interpolation button click - show simple method selector"""
        self.logger.info("Interpolation action triggered")
        
        if self.current_image is None:
            self.update_status("No image loaded - please load an image or array data first")
            messagebox.showwarning("No Image", "Please load an image or array data first.")
            return
        
        # Show simple interpolation method selector
        self.show_interpolation_selector()

    def on_colormap_change(self, colormap: str):
        """Handle colormap dropdown change"""
        self.logger.info(f"Colormap changed to: {colormap}")
        
        if self.current_image is None:
            return
        
        try:
            # Store the new colormap
            self.current_colormap = colormap
            
            # Update the display
            self.display_image(self.current_image, self.current_title)
            
            # Update status
            self.update_status(f"Applied {colormap} colormap")
            
        except Exception as e:
            self.logger.error(f"Failed to apply colormap: {e}")
            self.update_status(f"Colormap failed: {str(e)}")

    def on_colorbar_toggle(self):
        """Handle colorbar checkbox toggle"""
        self.show_colorbar = self.colorbar_checkbox.get()
        self.logger.info(f"Colorbar toggled: {self.show_colorbar}")
        
        if self.current_image is None:
            return
        
        # Only works with grayscale images
        if len(self.current_image.shape) == 3 and self.current_image.shape[2] == 3:
            self.update_status("Colorbar only applies to grayscale images")
            # Reset the checkbox to previous state
            if self.show_colorbar:
                self.colorbar_checkbox.deselect()
            else:
                self.colorbar_checkbox.select()
            self.show_colorbar = not self.show_colorbar
            return
        
        try:
            # Update the display
            self.display_image(self.current_image, self.current_title)
            
            # Update status
            status_text = "Showing" if self.show_colorbar else "Hiding"
            self.update_status(f"{status_text} colorbar")
            
        except Exception as e:
            self.logger.error(f"Failed to toggle colorbar: {e}")
            self.update_status(f"Colorbar toggle failed: {str(e)}")

    def on_range_mode_change(self, mode: str):
        """Handle range mode dropdown change"""
        self.logger.info(f"Range mode changed to: {mode}")
        
        self.colorbar_range_mode = mode
        
        if mode == 'auto':
            # Disable manual range inputs
            self.min_value_entry.configure(state="disabled")
            self.max_value_entry.configure(state="disabled")
            # Clear manual range values
            self.min_value_entry.delete(0, 'end')
            self.max_value_entry.delete(0, 'end')
            self.colorbar_vmin = None
            self.colorbar_vmax = None
        else:
            # Enable manual range inputs
            self.min_value_entry.configure(state="normal")
            self.max_value_entry.configure(state="normal")
            
            # Set default values if available
            if self.current_image is not None:
                if hasattr(self, 'current_array') and self.current_array is not None:
                    data_min = float(self.current_array.min())
                    data_max = float(self.current_array.max())
                else:
                    data_min = float(self.current_image.min())
                    data_max = float(self.current_image.max())
                
                self.min_value_entry.delete(0, 'end')
                self.max_value_entry.delete(0, 'end')
                self.min_value_entry.insert(0, f"{data_min:.3f}")
                self.max_value_entry.insert(0, f"{data_max:.3f}")
        
        # Update display if image is loaded
        if self.current_image is not None:
            try:
                self.display_image(self.current_image, self.current_title)
                self.update_status(f"Range mode set to {mode}")
            except Exception as e:
                self.logger.error(f"Failed to apply range mode: {e}")
                self.update_status(f"Range mode change failed: {str(e)}")


    def on_manual_range_change(self, event=None):
        """Handle manual range input changes"""
        if self.colorbar_range_mode != 'manual' or self.current_image is None:
            return
        
        try:
            min_text = self.min_value_entry.get().strip()
            max_text = self.max_value_entry.get().strip()
            
            # Only update if both values are provided and valid
            if min_text and max_text:
                try:
                    min_val = float(min_text)
                    max_val = float(max_text)
                    
                    if min_val >= max_val:
                        # Don't update if invalid range
                        return
                    
                    self.colorbar_vmin = min_val
                    self.colorbar_vmax = max_val
                    
                    # Update display with new range
                    self.display_image(self.current_image, self.current_title)
                    
                    self.logger.info(f"Manual range updated: [{min_val:.3f}, {max_val:.3f}]")
                    self.update_status(f"Range updated to [{min_val:.3f}, {max_val:.3f}]")
                    
                except ValueError:
                    # Invalid numeric input, ignore for now
                    pass
                    
        except Exception as e:
            self.logger.error(f"Failed to apply manual range: {e}")

    def export_frame_interval(self):
        """Export multiple frames in an interval"""
        if not self.current_items or len(self.current_items) <= 1:
            messagebox.showwarning("Insufficient Data", 
                                "Please load multiple frames first.\nFrame interval export requires at least 2 frames.")
            return
        
        try:
            # Create interval selection dialog
            result = self._show_interval_selection_dialog()
            if not result:
                return
            
            start_frame, end_frame, output_dir = result
            
            # Validate interval
            available_frames = [item for item in self.current_items if start_frame <= item <= end_frame]
            if not available_frames:
                messagebox.showwarning("Invalid Interval", 
                                    f"No frames found in interval {start_frame}-{end_frame}")
                return
            
            # Export frames
            self._export_frame_range(available_frames, output_dir)
            
        except Exception as e:
            error_msg = f"Error exporting frame interval: {str(e)}"
            messagebox.showerror("Export Error", error_msg)
            self.logger.error(f"Frame interval export error: {e}")

    def _export_frame_range(self, frame_numbers, output_dir):
        """Export a range of frames to the specified directory"""
        from pathlib import Path
        import os
        
        output_path = Path(output_dir)
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)
        
        total_frames = len(frame_numbers)
        exported_count = 0
        errors = []
        
        # Show progress dialog
        progress_dialog = self._create_progress_dialog(f"Exporting {total_frames} frames...")
        
        try:
            for i, frame_num in enumerate(frame_numbers):
                try:
                    # Load and display the frame
                    if hasattr(self.array_handler, 'load_item'):
                        array = self.array_handler.load_item(frame_num)
                        if array is not None:
                            # Display the frame (this updates self.current_image and the plot)
                            self.display_image(array, f"Frame {frame_num}")
                            
                            # Generate filename
                            filename = output_path / f"frame_{frame_num:04d}.{self.export_format}"
                            
                            # Export the frame
                            self.figure.savefig(
                                filename,
                                format=self.export_format,
                                dpi=self.export_dpi,
                                bbox_inches=self.export_bbox_inches,
                                facecolor='white',
                                edgecolor='none'
                            )
                            
                            exported_count += 1
                            
                        else:
                            errors.append(f"Could not load frame {frame_num}")
                    
                    # Update progress
                    progress = int((i + 1) / total_frames * 100)
                    self._update_progress_dialog(progress_dialog, progress, f"Exported frame {frame_num}")
                    
                except Exception as e:
                    errors.append(f"Frame {frame_num}: {str(e)}")
            
            # Close progress dialog
            if progress_dialog and progress_dialog.winfo_exists():
                progress_dialog.destroy()
            
            # Show results
            if exported_count > 0:
                success_msg = f"Successfully exported {exported_count} frames to:\n{output_dir}"
                if errors:
                    success_msg += f"\n\n{len(errors)} frames failed to export"
                messagebox.showinfo("Export Complete", success_msg)
                self.update_status(f"Exported {exported_count} frames")
            else:
                messagebox.showerror("Export Failed", "No frames were exported successfully")
                
        except Exception as e:
            if progress_dialog and progress_dialog.winfo_exists():
                progress_dialog.destroy()
            raise e

    def _create_progress_dialog(self, title):
        """Create a progress dialog"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Export Progress")
        dialog.geometry("300x120")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 150
        y = (dialog.winfo_screenheight() // 2) - 60
        dialog.geometry(f"300x120+{x}+{y}")
        
        # Progress label
        dialog.progress_label = ctk.CTkLabel(dialog, text=title)
        dialog.progress_label.pack(pady=10)
        
        # Progress bar
        dialog.progress_bar = ctk.CTkProgressBar(dialog, width=250)
        dialog.progress_bar.pack(pady=10)
        dialog.progress_bar.set(0)
        
        # Status label
        dialog.status_label = ctk.CTkLabel(dialog, text="Starting export...")
        dialog.status_label.pack(pady=5)
        
        dialog.update()
        return dialog

    def _update_progress_dialog(self, dialog, progress, status):
        """Update progress dialog"""
        if dialog and dialog.winfo_exists():
            dialog.progress_bar.set(progress / 100)
            dialog.status_label.configure(text=status)
            dialog.update()
            self.root.update_idletasks()

    def _show_interval_selection_dialog(self):
        """Show dialog for selecting frame interval and output directory"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Export Frame Interval")
        dialog.geometry("450x550")  # INCREASED from 400x300 to 450x420
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 225  # Adjusted for new width
        y = (dialog.winfo_screenheight() // 2) - 275  # Adjusted for new height
        dialog.geometry(f"450x550+{x}+{y}")
        
        result = {'value': None}
        
        # Main frame with more padding
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(main_frame, 
                                text="Select Frame Interval to Export",
                                font=ctk.CTkFont(size=18, weight="bold"))  # Slightly larger font
        title_label.pack(pady=(10, 25))  # More spacing
        
        # Available frames info with better spacing
        min_frame = min(self.current_items)
        max_frame = max(self.current_items)
        info_label = ctk.CTkLabel(main_frame,
                                text=f"Available frames: {min_frame} to {max_frame}\nTotal: {len(self.current_items)} frames",
                                font=ctk.CTkFont(size=13))  # Slightly larger font
        info_label.pack(pady=(0, 25))  # More spacing
        
        # Frame selection section with better layout
        selection_frame = ctk.CTkFrame(main_frame)
        selection_frame.pack(fill="x", pady=(0, 20))
        
        # Start frame with more spacing
        start_frame = ctk.CTkFrame(selection_frame)
        start_frame.pack(fill="x", padx=15, pady=8)
        
        ctk.CTkLabel(start_frame, text="Start Frame:", width=120, font=ctk.CTkFont(size=13)).pack(side="left", padx=5)
        start_entry = ctk.CTkEntry(start_frame, width=120, height=30, font=ctk.CTkFont(size=12))  # Taller entry
        start_entry.insert(0, str(min_frame))
        start_entry.pack(side="left", padx=10)
        
        # End frame with more spacing
        end_frame = ctk.CTkFrame(selection_frame)
        end_frame.pack(fill="x", padx=15, pady=8)
        
        ctk.CTkLabel(end_frame, text="End Frame:", width=120, font=ctk.CTkFont(size=13)).pack(side="left", padx=5)
        end_entry = ctk.CTkEntry(end_frame, width=120, height=30, font=ctk.CTkFont(size=12))  # Taller entry
        end_entry.insert(0, str(max_frame))
        end_entry.pack(side="left", padx=10)
        
        # Output directory section with better spacing
        dir_frame = ctk.CTkFrame(main_frame)
        dir_frame.pack(fill="x", pady=(0, 25))
        
        ctk.CTkLabel(dir_frame, text="Output Directory:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=15, pady=(10, 5))
        
        dir_select_frame = ctk.CTkFrame(dir_frame)
        dir_select_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        dir_entry = ctk.CTkEntry(dir_select_frame, placeholder_text="Select output directory...", height=30, font=ctk.CTkFont(size=11))
        dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        def select_directory():
            from tkinter import filedialog
            directory = filedialog.askdirectory(title="Select Output Directory")
            if directory:
                dir_entry.delete(0, 'end')
                dir_entry.insert(0, directory)
        
        dir_btn = ctk.CTkButton(dir_select_frame, text="Browse", command=select_directory, width=90, height=30)
        dir_btn.pack(side="right")
        
        # Buttons with better spacing and larger size
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(pady=(10, 15))
        
        def on_export():
            try:
                start = int(start_entry.get())
                end = int(end_entry.get())
                output_dir = dir_entry.get().strip()
                
                if start > end:
                    messagebox.showerror("Invalid Range", "Start frame must be less than or equal to end frame")
                    return
                    
                if not output_dir:
                    messagebox.showerror("No Directory", "Please select an output directory")
                    return
                
                result['value'] = (start, end, output_dir)
                dialog.destroy()
                
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid frame numbers")
        
        export_btn = ctk.CTkButton(btn_frame, text="Export", command=on_export, width=120, height=35, 
                                font=ctk.CTkFont(size=13, weight="bold"))
        export_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=dialog.destroy, width=120, height=35,
                                font=ctk.CTkFont(size=13))
        cancel_btn.pack(side="left", padx=10)
        
        dialog.wait_window()
        return result['value']

    def export_current_frame(self):
        """Export the currently displayed frame with colorbar"""
        if self.current_image is None:
            messagebox.showwarning("No Image", "Please load an image first")
            return
        
        try:
            from tkinter import filedialog
            
            # Get filename from user
            filename = filedialog.asksaveasfilename(
                title="Export Current Frame",
                defaultextension=f".{self.export_format}",
                filetypes=[
                    (f"{self.export_format.upper()}", f"*.{self.export_format}"),
                    ("All files", "*.*")
                ]
            )
            
            if filename:
                # Save the current figure
                self.figure.savefig(
                    filename,
                    format=self.export_format,
                    dpi=self.export_dpi,
                    bbox_inches=self.export_bbox_inches,
                    facecolor='white',
                    edgecolor='none'
                )
                
                messagebox.showinfo("Export Success", f"Frame exported successfully to:\n{filename}")
                self.update_status(f"Exported current frame to {filename}")
                self.logger.info(f"Exported current frame to {filename} ({self.export_format}, {self.export_dpi} DPI)")
                
        except Exception as e:
            error_msg = f"Error exporting frame: {str(e)}"
            messagebox.showerror("Export Error", error_msg)
            self.update_status("Export failed")
            self.logger.error(f"Export error: {e}")

    def on_colorbar_label_change(self, event=None):
        """Handle colorbar label change"""
        if self.colorbar_label_entry:
            new_label = self.colorbar_label_entry.get().strip()
            if new_label != self.colorbar_label:
                self.colorbar_label = new_label
                self.logger.info(f"Colorbar label changed to: '{self.colorbar_label}'")
                
                # Update display if image is loaded
                if self.current_image is not None:
                    self.display_image(self.current_image, self.current_title)
                    self.update_status(f"Updated colorbar label")

    def on_colorbar_font_change(self, event=None):
        """Handle colorbar font size changes"""
        try:
            # Get tick font size
            if self.colorbar_tick_font_entry:
                tick_size = int(self.colorbar_tick_font_entry.get())
                if tick_size > 0:
                    self.colorbar_tick_fontsize = tick_size
            
            # Get label font size  
            if self.colorbar_label_font_entry:
                label_size = int(self.colorbar_label_font_entry.get())
                if label_size > 0:
                    self.colorbar_label_fontsize = label_size
            
            self.logger.info(f"Colorbar font sizes changed - tick: {self.colorbar_tick_fontsize}, label: {self.colorbar_label_fontsize}")
            
            # Update display if image is loaded
            if self.current_image is not None:
                self.display_image(self.current_image, self.current_title)
                self.update_status("Updated colorbar font sizes")
                
        except ValueError:
            # Invalid input, restore previous values
            if self.colorbar_tick_font_entry:
                self.colorbar_tick_font_entry.delete(0, 'end')
                self.colorbar_tick_font_entry.insert(0, str(self.colorbar_tick_fontsize))
            if self.colorbar_label_font_entry:
                self.colorbar_label_font_entry.delete(0, 'end')
                self.colorbar_label_font_entry.insert(0, str(self.colorbar_label_fontsize))
            self.update_status("Invalid font size - please enter a positive number")
        except Exception as e:
            self.logger.error(f"Error updating colorbar font sizes: {e}")

    def on_export_format_change(self, format_name: str):
        """Handle export format change"""
        self.export_format = format_name
        self.logger.info(f"Export format changed to: {self.export_format}")

    def on_export_dpi_change(self, dpi_value: str):
        """Handle export DPI change"""
        try:
            self.export_dpi = int(dpi_value)
            self.logger.info(f"Export DPI changed to: {self.export_dpi}")
        except ValueError:
            self.logger.error(f"Invalid DPI value: {dpi_value}")

    def update_display_controls_for_image(self):
        """Update display controls when a new image is loaded - enhanced for colorbar customization"""
        if self.current_image is None:
            return
        
        try:
            # Update colormap dropdown to current selection
            if self.colormap_dropdown:
                self.colormap_dropdown.set(self.current_colormap)
            
            # Update colorbar checkbox
            if self.colorbar_checkbox:
                if self.show_colorbar:
                    self.colorbar_checkbox.select()
                else:
                    self.colorbar_checkbox.deselect()
            
            # Update colorbar customization entries
            if self.colorbar_label_entry:
                # Clear and set current label
                current_label = self.colorbar_label_entry.get()
                if current_label != self.colorbar_label:
                    self.colorbar_label_entry.delete(0, 'end')
                    if self.colorbar_label:
                        self.colorbar_label_entry.insert(0, self.colorbar_label)
            
            # Update font size entries
            if self.colorbar_tick_font_entry:
                current_tick_font = self.colorbar_tick_font_entry.get()
                if current_tick_font != str(self.colorbar_tick_fontsize):
                    self.colorbar_tick_font_entry.delete(0, 'end')
                    self.colorbar_tick_font_entry.insert(0, str(self.colorbar_tick_fontsize))
            
            if self.colorbar_label_font_entry:
                current_label_font = self.colorbar_label_font_entry.get()
                if current_label_font != str(self.colorbar_label_fontsize):
                    self.colorbar_label_font_entry.delete(0, 'end')
                    self.colorbar_label_font_entry.insert(0, str(self.colorbar_label_fontsize))
            
            # Update range mode dropdown
            if self.range_mode_dropdown:
                self.range_mode_dropdown.set(self.colorbar_range_mode)
            
            # If in manual mode, update the range entries with data bounds
            if self.colorbar_range_mode == 'manual' and self.min_value_entry and self.max_value_entry:
                if hasattr(self, 'current_array') and self.current_array is not None:
                    data_min = float(self.current_array.min())
                    data_max = float(self.current_array.max())
                else:
                    data_min = float(self.current_image.min())
                    data_max = float(self.current_image.max())
                
                # Only update if entries are empty
                if not self.min_value_entry.get().strip():
                    self.min_value_entry.insert(0, f"{data_min:.3f}")
                if not self.max_value_entry.get().strip():
                    self.max_value_entry.insert(0, f"{data_max:.3f}")
            
            # Update export controls state
            if hasattr(self, 'export_current_btn') and self.export_current_btn:
                self.export_current_btn.configure(state="normal")
            
            # Enable/disable controls based on image type
            is_rgb = len(self.current_image.shape) == 3 and self.current_image.shape[2] == 3
            
            if is_rgb:
                # For RGB images, disable colorbar-related controls
                if self.colorbar_checkbox:
                    self.colorbar_checkbox.configure(state="disabled")
                if self.range_mode_dropdown:
                    self.range_mode_dropdown.configure(state="disabled")
                if self.min_value_entry:
                    self.min_value_entry.configure(state="disabled")
                if self.max_value_entry:
                    self.max_value_entry.configure(state="disabled")
                # Disable colorbar customization for RGB images
                if self.colorbar_label_entry:
                    self.colorbar_label_entry.configure(state="disabled")
                if self.colorbar_tick_font_entry:
                    self.colorbar_tick_font_entry.configure(state="disabled")
                if self.colorbar_label_font_entry:
                    self.colorbar_label_font_entry.configure(state="disabled")
            else:
                # For grayscale images, enable all controls
                if self.colorbar_checkbox:
                    self.colorbar_checkbox.configure(state="normal")
                if self.range_mode_dropdown:
                    self.range_mode_dropdown.configure(state="normal")
                    
                # Enable colorbar customization for grayscale images
                if self.colorbar_label_entry:
                    self.colorbar_label_entry.configure(state="normal")
                if self.colorbar_tick_font_entry:
                    self.colorbar_tick_font_entry.configure(state="normal")
                if self.colorbar_label_font_entry:
                    self.colorbar_label_font_entry.configure(state="normal")
                    
                # Range entries are controlled by range mode
                if self.colorbar_range_mode == 'manual':
                    if self.min_value_entry:
                        self.min_value_entry.configure(state="normal")
                    if self.max_value_entry:
                        self.max_value_entry.configure(state="normal")
                else:
                    if self.min_value_entry:
                        self.min_value_entry.configure(state="disabled")
                    if self.max_value_entry:
                        self.max_value_entry.configure(state="disabled")
                        
        except Exception as e:
            self.logger.error(f"Error updating display controls: {e}")

    def show_interpolation_selector(self):
        """Show simple interpolation method selection dialog - TALLER VERSION"""
        # Create dialog window - INCREASED HEIGHT
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Display Interpolation")
        dialog.grab_set()  # Make dialog modal
        dialog.geometry("450x700")  # INCREASED from 400x500 to 450x700
        dialog.resizable(False, False)
        
        # Main frame
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="Select Display Interpolation",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(10, 15))
        
        # Description
        desc_label = ctk.CTkLabel(
            main_frame,
            text="Choose how to display the image\n(does not modify pixel data)",
            font=ctk.CTkFont(size=12),
            text_color="gray70"
        )
        desc_label.pack(pady=(0, 15))
        
        # Current method display
        current_label = ctk.CTkLabel(
            main_frame,
            text=f"Current: {self.current_display_interpolation}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#4CAF50"
        )
        current_label.pack(pady=(0, 15))
        
        # Method selection variable
        method_var = tk.StringVar(value=self.current_display_interpolation)
        
        # Get available methods
        methods = self.interpolator.get_interpolation_methods()
        
        # Create scrollable frame for methods - INCREASED HEIGHT
        methods_frame = ctk.CTkScrollableFrame(main_frame, height=400)  # INCREASED from 250 to 400
        methods_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Method descriptions
        descriptions = {
            'none': "Raw pixels - no smoothing",
            'nearest': "Sharp, pixelated look", 
            'bilinear': "Smooth linear interpolation",
            'bicubic': "Very smooth cubic interpolation",
            'spline16': "High quality spline",
            'spline36': "Very high quality spline", 
            'hanning': "Windowed smoothing",
            'hamming': "Windowed smoothing",
            'hermite': "Smooth hermite curves",
            'kaiser': "Kaiser windowed",
            'quadric': "Quadratic smoothing",
            'catrom': "Catmull-Rom curves",
            'gaussian': "Gaussian blur effect",
            'bessel': "Bessel smoothing",
            'mitchell': "Mitchell smoothing",
            'sinc': "High quality sinc",
            'lanczos': "Premium quality",
            'antialiased': "Anti-aliasing",
            'auto': "Automatic selection"
        }
        
        # Create radio buttons with descriptions
        for method in methods:
            # Method container - INCREASED PADDING
            method_container = ctk.CTkFrame(methods_frame)
            method_container.pack(fill="x", padx=5, pady=4)  # INCREASED pady from 2 to 4
            
            # Radio button with method name
            radio = ctk.CTkRadioButton(
                method_container,
                text=method.capitalize(),
                variable=method_var,
                value=method,
                font=ctk.CTkFont(size=12, weight="bold")  # INCREASED font size
            )
            radio.pack(anchor="w", padx=10, pady=(8, 4))  # INCREASED padding
            
            # Description
            desc_text = descriptions.get(method, "Standard interpolation method")
            desc_label = ctk.CTkLabel(
                method_container,
                text=desc_text,
                font=ctk.CTkFont(size=10),  # INCREASED font size
                text_color="gray60"
            )
            desc_label.pack(anchor="w", padx=25, pady=(0, 8))  # INCREASED padding
        
        # Buttons frame - INCREASED HEIGHT
        buttons_frame = ctk.CTkFrame(main_frame, height=60)  # INCREASED from default
        buttons_frame.pack(fill="x", padx=10, pady=(20, 10))  # INCREASED top padding
        buttons_frame.pack_propagate(False)  # Maintain fixed height
        
        # Apply button
        apply_btn = ctk.CTkButton(
            buttons_frame,
            text="Apply",
            command=lambda: self.apply_simple_interpolation(method_var.get(), dialog),
            fg_color="#4CAF50",
            hover_color="#45a049",
            font=ctk.CTkFont(size=14, weight="bold"),  # INCREASED font size
            height=40  # INCREASED button height
        )
        apply_btn.pack(side="left", padx=(10, 5), pady=10, fill="x", expand=True)
        
        # Cancel button
        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Cancel",
            command=dialog.destroy,
            fg_color="#757575",
            hover_color="#616161",
            font=ctk.CTkFont(size=14, weight="bold"),  # INCREASED font size
            height=40  # INCREASED button height
        )
        cancel_btn.pack(side="right", padx=(5, 10), pady=10, fill="x", expand=True)
        
        # Center the dialog - UPDATED FOR NEW SIZE
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)  # UPDATED for new width
        y = (dialog.winfo_screenheight() // 2) - (700 // 2)  # UPDATED for new height
        dialog.geometry(f"450x700+{x}+{y}")

    def apply_simple_interpolation(self, method: str, dialog):
        """Apply the selected interpolation method for display only"""
        
        try:
            # Validate the method
            if not self.interpolator.is_valid_method(method):
                method = 'nearest'  # Fallback
                self.logger.warning(f"Invalid interpolation method, using 'nearest'")
            
            # Store the new interpolation method
            self.current_display_interpolation = method
            
            # Update the title to show interpolation method
            base_title = getattr(self, 'current_title', 'Image')
            # Remove any existing interpolation info from title
            if '(Display:' in base_title:
                base_title = base_title.split('(Display:')[0].strip()
            
            new_title = f"{base_title} (Display: {method})"
            
            # Use your existing display_image method - it already handles interpolation!
            self.display_image(self.current_image, new_title)
            
            # Update status
            self.update_status(f"Applied {method} display interpolation")
            
            # Close dialog
            dialog.destroy()
            
            self.logger.info(f"Applied display interpolation: {method}")
            
        except Exception as e:
            self.logger.error(f"Failed to apply interpolation: {e}")
            self.update_status(f"Interpolation failed: {str(e)}")
            messagebox.showerror("Error", f"Failed to apply interpolation:\n{str(e)}")

        
    def plot_action(self):
        """Handle plot button click - Enhanced with ROI vs Frame plotting"""
        self.logger.info("Plot action triggered")
        
        # Validate prerequisites
        if not self.current_items or len(self.current_items) < 2:
            self.update_status("Need at least 2 frames loaded for plotting")
            messagebox.showinfo(
                "Insufficient Data",
                "ROI vs Frame plotting requires multiple frames.\n\n"
                f"Currently loaded: {len(self.current_items) if self.current_items else 0} frames\n"
                "Required: At least 2 frames\n\n"
                "Please load multiple frames using 'Load Data' → 'Multiple Items' mode."
            )
            return
        
        if not self.roi_selector or not self.roi_selector.rois:
            self.update_status("No ROIs available for plotting")
            messagebox.showinfo(
                "No ROIs Selected",
                "ROI vs Frame plotting requires at least one Region of Interest.\n\n"
                "Steps to create ROIs:\n"
                "1. Click 'Enable ROI Mode'\n"
                "2. Select 'Rectangle' or 'Point' ROI type\n"
                "3. Draw ROI on your image\n\n"
                "Then try plotting again."
            )
            return
        
        # All prerequisites met - show plotting dialog
        self.update_status(f"Opening ROI plotting dialog - {len(self.current_items)} frames, {len(self.roi_selector.rois)} ROIs")
        
        try:
            # Import and create plotting dialog
            from pixelprobe.gui.dialogs.plotting_dialog import create_plotting_dialog
            
            create_plotting_dialog(
                parent=self.root,
                array_handler=self.array_handler,
                roi_selector=self.roi_selector,
                current_items=self.current_items
            )
            
            self.logger.info("ROI plotting dialog opened successfully")
            
        except Exception as e:
            self.logger.error(f"Error opening plotting dialog: {e}")
            self.update_status(f"Error opening plotting dialog: {str(e)}")
            messagebox.showerror("Plotting Error", f"Could not open plotting dialog:\n{str(e)}")

    # Also add this helper method to provide better user feedback
    def get_plotting_status_info(self) -> str:
        """Get current status for plotting functionality"""
        frames_loaded = len(self.current_items) if self.current_items else 0
        rois_available = len(self.roi_selector.rois) if self.roi_selector else 0
        
        status_parts = []
        status_parts.append(f"Frames: {frames_loaded}")
        status_parts.append(f"ROIs: {rois_available}")
        
        if frames_loaded < 2:
            status_parts.append("⚠️ Need ≥2 frames")
        if rois_available == 0:
            status_parts.append("⚠️ Need ≥1 ROI")
        if frames_loaded >= 2 and rois_available > 0:
            status_parts.append("✅ Ready to plot")
            
        return " | ".join(status_parts)

    def stats_action(self):
        """Handle statistics button click"""
        self.logger.info("Statistics action triggered")
        
        if self.current_image is None:
            self.update_status("No image loaded - please load an image or array data first")
            return
        
        self.update_status("Calculating image statistics...")
        
        try:
            # Calculate basic statistics
            basic_stats = self.analyzer.basic_statistics(self.current_image)
            quality_metrics = self.analyzer.image_quality_metrics(self.current_image)
            
            # Get ROI statistics if available
            roi_stats = self.get_roi_statistics()
            
            # Show statistics in a new window
            self.show_statistics_window(basic_stats, quality_metrics, roi_stats)
            
            self.update_status("Statistics calculated successfully")
            self.logger.info("Statistics window displayed")
            
        except Exception as e:
            self.logger.error(f"Statistics calculation failed: {e}")
            self.update_status("Statistics calculation failed")

    def show_statistics_window(self, basic_stats, quality_metrics, roi_stats=None):
        """Display statistics in a professional window with ROI selection functionality"""
        
        # Create statistics window with larger size
        stats_window = tk.Toplevel(self.root)
        stats_window.title("PixelProbe - Image Statistics and Analysis")
        stats_window.geometry("1400x1100")
        stats_window.transient(self.root)
        stats_window.configure(bg='#2b2b2b')
        
        # Center the window
        stats_window.update_idletasks()
        x = (stats_window.winfo_screenwidth() // 3) - (1400 // 4)
        y = (stats_window.winfo_screenheight() // 3) - (1100 // 4)
        stats_window.geometry(f"1400x1100+{x}+{y}")
        
        # Configure ttk style for better appearance
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Custom.TNotebook', background='#2b2b2b')
        style.configure('Custom.TNotebook.Tab', background='#404040', foreground='white', padding=[20, 10])
        
        # Main notebook for tabs
        notebook = ttk.Notebook(stats_window, style='Custom.TNotebook')
        notebook.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Basic Statistics Tab
        basic_frame = tk.Frame(notebook, bg='#2b2b2b')
        notebook.add(basic_frame, text="📊 Basic Stats")
        
        basic_text = tk.Text(
            basic_frame,
            font=("Consolas", 16),
            wrap='word',
            bg='#1e1e1e',
            fg='#e0e0e0',
            insertbackground='#ffffff',
            selectbackground='#4a5568',
            selectforeground='#ffffff',
            relief='flat',
            padx=20,
            pady=20
        )
        basic_scrollbar = tk.Scrollbar(basic_frame, orient="vertical", command=basic_text.yview)
        basic_text.configure(yscrollcommand=basic_scrollbar.set)
        
        basic_scrollbar.pack(side="right", fill="y")
        basic_text.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        
        # Format basic statistics text
        basic_text_content = f"""
    📊 BASIC IMAGE STATISTICS
    {'='*70}

    🔢 PIXEL VALUE DISTRIBUTION:
        Mean (Average):          {basic_stats.get('mean', 0):.3f}
        Median (50th Percentile): {basic_stats.get('median', 0):.3f}
        Mode (Most Frequent):    {basic_stats.get('mode', 0):.3f}
        
    📏 SPREAD & VARIABILITY:
        Standard Deviation:      {basic_stats.get('std', 0):.3f}
        Variance:               {basic_stats.get('variance', 0):.3f}
        Range (Max - Min):      {basic_stats.get('range', 0):.3f}
        
    ⚡ EXTREME VALUES:
        Minimum Pixel Value:     {basic_stats.get('min', 0):.3f}
        Maximum Pixel Value:     {basic_stats.get('max', 0):.3f}
        
    📐 IMAGE DIMENSIONS:
        Width (pixels):          {basic_stats.get('width', 0):,}
        Height (pixels):         {basic_stats.get('height', 0):,}
        Total Pixels:           {basic_stats.get('total_pixels', 0):,}
        
    🎨 IMAGE TYPE:
        Data Type:              {basic_stats.get('dtype', 'Unknown')}
        Color Channels:         {basic_stats.get('channels', 'Unknown')}
        Bit Depth:              {basic_stats.get('bit_depth', 'Unknown')} bits
    """
        
        basic_text.insert('1.0', basic_text_content)
        basic_text.config(state='disabled')
        
        # Quality Metrics Tab
        quality_frame = tk.Frame(notebook, bg='#2b2b2b')
        notebook.add(quality_frame, text="🔍 Quality")
        
        quality_text = tk.Text(
            quality_frame,
            font=("Consolas", 16),
            wrap='word',
            bg='#1e1e1e',
            fg='#e0e0e0',
            insertbackground='#ffffff',
            selectbackground='#4a5568',
            selectforeground='#ffffff',
            relief='flat',
            padx=20,
            pady=20
        )
        quality_text.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        
        # Format quality metrics text
        quality_text_content = f"""
    🔍 QUALITY ASSESSMENT REPORT
    {'='*70}

    📊 IMAGE QUALITY METRICS:
        Signal-to-Noise Ratio:   {quality_metrics.get('snr', 0):.2f} dB
        Peak Signal-to-Noise:    {quality_metrics.get('psnr', 0):.2f} dB
        Structural Similarity:   {quality_metrics.get('ssim', 0):.4f}
        
    🎯 QUALITY INDICATORS:
        Sharpness Score:         {quality_metrics.get('sharpness', 0):.4f}
        Contrast Level:          {quality_metrics.get('contrast', 0):.4f}
        Brightness Balance:      {quality_metrics.get('brightness', 0):.3f}
        
    ✅ ASSESSMENT SUMMARY:
        Overall Quality:         {'🟢 Excellent' if quality_metrics.get('overall_score', 0) > 0.8 else '🟡 Good' if quality_metrics.get('overall_score', 0) > 0.6 else '🔴 Needs Improvement'}
        Recommended Action:      {'✨ Image is optimal' if quality_metrics.get('overall_score', 0) > 0.8 else '🔧 Consider denoising' if quality_metrics.get('overall_score', 0) > 0.6 else '⚠️  Significant processing needed'}
    """
        
        quality_text.insert('1.0', quality_text_content)
        quality_text.config(state='disabled')
        
        # ROI Statistics Tab with Selection (if ROI data available)
        if roi_stats:
            roi_frame = tk.Frame(notebook, bg='#2b2b2b')
            notebook.add(roi_frame, text="🎯 ROI Analysis")
            
            # Create main container with two sections
            main_container = tk.Frame(roi_frame, bg='#2b2b2b')
            main_container.pack(fill='both', expand=True, padx=20, pady=20)
            
            # Left side: Individual ROI selection and stats
            left_frame = tk.Frame(main_container, bg='#1e1e1e', relief='ridge', bd=2)
            left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
            
            # ROI selection header
            roi_header = tk.Label(
                left_frame,
                text="🎯 Select ROIs for Averaging",
                font=("Arial", 18, "bold"),
                bg='#1e1e1e',
                fg='#4CAF50'
            )
            roi_header.pack(pady=10)
            
            # Scrollable frame for ROI checkboxes
            roi_canvas = tk.Canvas(left_frame, bg='#1e1e1e', highlightthickness=0)
            roi_scrollbar = tk.Scrollbar(left_frame, orient="vertical", command=roi_canvas.yview)
            roi_scrollable_frame = tk.Frame(roi_canvas, bg='#1e1e1e')
            
            roi_scrollable_frame.bind(
                "<Configure>",
                lambda e: roi_canvas.configure(scrollregion=roi_canvas.bbox("all"))
            )
            
            roi_canvas.create_window((0, 0), window=roi_scrollable_frame, anchor="nw")
            roi_canvas.configure(yscrollcommand=roi_scrollbar.set)
            
            roi_canvas.pack(side="left", fill="both", expand=True, padx=10)
            roi_scrollbar.pack(side="right", fill="y")
            
            # Dictionary to store checkbox variables
            roi_checkboxes = {}
            
            # Create checkboxes for each ROI
            for i, (roi_name, roi_data) in enumerate(roi_stats.items()):
                # ROI container frame
                roi_container = tk.Frame(roi_scrollable_frame, bg='#2b2b2b', relief='raised', bd=1)
                roi_container.pack(fill='x', padx=5, pady=5)
                
                # Checkbox variable
                checkbox_var = tk.BooleanVar()
                roi_checkboxes[roi_name] = checkbox_var
                
                # Checkbox
                checkbox = tk.Checkbutton(
                    roi_container,
                    text=roi_name,
                    variable=checkbox_var,
                    font=("Arial", 14, "bold"),
                    bg='#2b2b2b',
                    fg='#ffffff',
                    selectcolor='#404040',
                    activebackground='#2b2b2b',
                    activeforeground='#4CAF50',
                    command=lambda: self.update_roi_average(roi_checkboxes, roi_stats, average_text)
                )
                checkbox.pack(anchor='w', padx=10, pady=5)
                
                # ROI details
                if 'error' in roi_data:
                    details_text = f"❌ Error: {roi_data['error']}"
                    detail_color = '#f44336'
                elif 'pixel_value' in roi_data:
                    # Point ROI
                    details_text = f"📍 Point: ({roi_data.get('x_coord', 'N/A')}, {roi_data.get('y_coord', 'N/A')}) | Value: {roi_data.get('pixel_value', 0):.3f}"
                    detail_color = '#4CAF50'
                else:
                    # Region ROI  
                    details_text = f"📊 Region: {roi_data.get('pixel_count', 0)} pixels | Mean: {roi_data.get('mean', 0):.3f} | Std: {roi_data.get('std', 0):.3f}"
                    detail_color = '#2196F3'
                
                details_label = tk.Label(
                    roi_container,
                    text=details_text,
                    font=("Consolas", 11),
                    bg='#2b2b2b',
                    fg=detail_color
                )
                details_label.pack(anchor='w', padx=30, pady=(0, 5))
            
            # Right side: Average results
            right_frame = tk.Frame(main_container, bg='#1e1e1e', relief='ridge', bd=2)
            right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))
            
            # Average results header
            avg_header = tk.Label(
                right_frame,
                text="📈 Average of Selected ROIs",
                font=("Arial", 18, "bold"),
                bg='#1e1e1e',
                fg='#FF9800'
            )
            avg_header.pack(pady=10)
            
            # Average results text area
            average_text = tk.Text(
                right_frame,
                font=("Consolas", 14),
                wrap='word',
                bg='#2b2b2b',
                fg='#e0e0e0',
                insertbackground='#ffffff',
                selectbackground='#4a5568',
                selectforeground='#ffffff',
                relief='flat',
                padx=15,
                pady=15,
                height=20
            )
            average_text.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Initial message
            initial_message = """
    📈 AVERAGE ROI RESULTS
    {'='*50}

    Select ROIs from the left panel to see
    averaged statistics here.

    Instructions:
    ✅ Check ROIs you want to include
    📊 Results update automatically  
    🎯 Mix points and regions as needed
            """
            average_text.insert('1.0', initial_message)
            average_text.config(state='disabled')
            
            # Control buttons frame
            control_frame = tk.Frame(right_frame, bg='#1e1e1e')
            control_frame.pack(fill='x', padx=10, pady=10)
            
            # Select All button
            select_all_btn = tk.Button(
                control_frame,
                text="Select All ROIs",
                command=lambda: self.select_all_rois(roi_checkboxes, roi_stats, average_text),
                font=("Arial", 12, "bold"),
                bg='#4CAF50',
                fg='white',
                activebackground='#45a049',
                padx=20,
                pady=5
            )
            select_all_btn.pack(side='left', padx=5)
            
            # Clear All button
            clear_all_btn = tk.Button(
                control_frame,
                text="Clear All ROIs", 
                command=lambda: self.clear_all_rois(roi_checkboxes, roi_stats, average_text),
                font=("Arial", 12, "bold"),
                bg='#f44336',
                fg='white',
                activebackground='#da190b',
                padx=20,
                pady=5
            )
            clear_all_btn.pack(side='left', padx=5)
        
        # Histogram Tab
        histogram_frame = tk.Frame(notebook, bg='#2b2b2b')
        notebook.add(histogram_frame, text="📈 Histogram")
        
        # Add histogram plot with better styling
        self.create_histogram_plot(histogram_frame)
        
        # Close button with better styling
        button_frame = tk.Frame(stats_window, bg='#2b2b2b')
        button_frame.pack(pady=20)
        
        close_btn = tk.Button(
            button_frame, 
            text="Close Analysis", 
            command=stats_window.destroy,
            font=("Arial", 16, "bold"), 
            bg='#2196F3', 
            fg='white',
            activebackground='#1976D2',
            activeforeground='white',
            padx=40, 
            pady=15,
            relief='flat',
            cursor='hand2'
        )
        close_btn.pack()

    def toggle_theme(self):
        """Toggle between light and dark themes"""
        current_mode = ctk.get_appearance_mode()
        new_mode = "Light" if current_mode == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        self.update_status(f"Theme changed to {new_mode}")
        self.logger.info(f"Theme toggled to {new_mode}")
    
    def update_status(self, message: str):
        """Update status with a persistent message that stays longer"""
        self.status_label.configure(text=message)
        self.root.update_idletasks()
        
        # Clear the message after 8 seconds
        self.root.after(8000, lambda: self.update_status("Ready"))
        
    def _get_current_timestamp(self):
        """Get current timestamp for ROI analysis"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _calculate_percentile(self, value, basic_stats):
        """Calculate what percentile a value represents in the image"""
        # Simple approximation based on min/max
        img_min = basic_stats.get('min', 0)
        img_max = basic_stats.get('max', 255)
        if img_max > img_min:
            return ((value - img_min) / (img_max - img_min)) * 100
        return 50.0
    
    def run(self):
        """Start the application main loop"""
        self.logger.info("Starting PixelProbe main loop")
        self.root.mainloop()
        self.logger.info("PixelProbe application closed")