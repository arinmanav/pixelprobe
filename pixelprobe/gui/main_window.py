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
        self.create_widgets()

        # Initialize processing
        self.denoiser = AdvancedDenoiseProcessor()

        self.interpolator = InterpolationProcessor()  # NEW PROCESSOR
        
        # Current interpolation settings - SIMPLIFIED
        self.current_display_interpolation = 'nearest'  # Single setting for all interpolation
        self.current_title = "Image"  # Track current image title


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


    def create_widgets(self):
        """Create and arrange the main interface widgets with CustomTkinter compatibility"""
        # Create sidebar frame
        self.sidebar_frame = ctk.CTkFrame(self.root, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(17, weight=1)  # Updated for additional button
        
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

        self.interpolation_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Interpolation",
            command=self.interpolation_action
        )
        self.interpolation_btn.grid(row=6, column=0, padx=20, pady=5)
        
        # NEW: Add Undo button right after interpolation
        self.undo_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Undo Interpolation",
            command=self.undo_interpolation,
            state="disabled",  # Initially disabled
            fg_color="#FF9800",  # Orange color for undo
            hover_color="#F57C00",
            width=120
        )
        self.undo_btn.grid(row=7, column=0, padx=20, pady=2)
        
        # ROI Section - UPDATED ROW NUMBERS (+1 from original)
        self.roi_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="ROI Selection",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.roi_label.grid(row=8, column=0, padx=20, pady=(20, 10))  # Was row=7, now row=8
        
        # ROI mode toggle
        self.roi_mode_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Enable ROI Mode",
            command=self.toggle_roi_mode,
            fg_color="gray"
        )
        self.roi_mode_btn.grid(row=9, column=0, padx=20, pady=5)  # Was row=8, now row=9
        
        # ROI selection buttons
        self.roi_rect_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Rectangle",
            command=self.set_rectangle_roi,
            state="disabled",
            width=120
        )
        self.roi_rect_btn.grid(row=10, column=0, padx=20, pady=2)  # Was row=9, now row=10
        
        self.roi_point_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Point",
            command=self.set_point_roi,
            state="disabled",
            width=120
        )
        self.roi_point_btn.grid(row=11, column=0, padx=20, pady=2)  # Was row=10, now row=11
        
        # ROI management buttons
        self.roi_clear_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Clear ROIs",
            command=self.clear_rois,
            state="disabled",
            width=120,
            fg_color="red",
            hover_color="darkred"
        )
        self.roi_clear_btn.grid(row=12, column=0, padx=20, pady=5)  # Was row=11, now row=12
        
        # Analysis section
        self.analysis_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Analysis",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.analysis_label.grid(row=13, column=0, padx=20, pady=(20, 10))  # Was row=12, now row=13
        
        self.plot_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Plot Data",
            command=self.plot_action
        )
        self.plot_btn.grid(row=14, column=0, padx=20, pady=5)  # Was row=13, now row=14
        
        self.stats_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Statistics", 
            command=self.stats_action
        )
        self.stats_btn.grid(row=15, column=0, padx=20, pady=5)  # Was row=14, now row=15
        
        # Theme toggle
        self.theme_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Toggle Theme",
            command=self.toggle_theme
        )
        self.theme_btn.grid(row=17, column=0, padx=20, pady=10)  # Was row=16, now row=17
        
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
        
        # FIXED: Simple toolbar info frame (no matplotlib toolbar for now)
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
        
        # FIXED: Enable built-in matplotlib navigation without toolbar widget
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
        
        self.logger.debug("Main interface widgets created with manual navigation")

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
        """Clear all ROIs"""
        if self.roi_selector:
            self.roi_selector.clear_rois()
            if self.current_image is not None:
                current_title = self.subplot.get_title()
                self.display_image(self.current_image, current_title)
            self.update_status("All ROIs cleared and display refreshed")

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
        """Activate ROI selection mode"""
        if self.current_image is None:
            self.update_status("Please load an image first")
            return
        
        self.roi_mode_active = True
        
        # Initialize ROI selector if not exists
        if self.roi_selector is None:
            self.roi_selector = ROISelector(self.figure, self.subplot, self.update_status)
        
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

    def _deactivate_roi_mode(self):
        """Deactivate ROI selection mode"""
        if self.roi_selector:
            self.roi_selector.deactivate_selection()
        
        self.roi_mode_active = False
        
        self.roi_mode_btn.configure(text="Enable ROI Mode", fg_color="gray")
        self.roi_rect_btn.configure(state="disabled")
        self.roi_point_btn.configure(state="disabled")
        self.roi_clear_btn.configure(state="disabled")
        
        self.update_status("ROI mode deactivated")

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
        """Update ROI button colors to show active selection - Circle removed"""
        default_color = ["#1f538d", "#14375e"]
        
        self.roi_rect_btn.configure(fg_color=default_color)
        self.roi_point_btn.configure(fg_color=default_color)
        
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
                rect = patches.Rectangle(
                    (roi.coordinates['x'], roi.coordinates['y']),
                    roi.coordinates['width'],
                    roi.coordinates['height'],
                    fill=False,
                    edgecolor=roi.color,
                    linewidth=2.0,
                    alpha=0.8
                )
                self.subplot.add_patch(rect)
            
            elif roi.roi_type == ROIType.CIRCLE:
                circle = patches.Circle(
                    (roi.coordinates['cx'], roi.coordinates['cy']),
                    roi.coordinates['radius'],
                    fill=False,
                    edgecolor=roi.color,
                    linewidth=2.0,
                    alpha=0.8
                )
                self.subplot.add_patch(circle)
            
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

    def display_image(self, image: np.ndarray, title: str = "Image"):
            """Display image in the matplotlib subplot with ROI preservation - RESTORED + INTERPOLATION"""
            try:
                # Store current ROIs if they exist
                existing_rois = []
                if self.roi_selector and self.roi_selector.rois:
                    existing_rois = self.roi_selector.rois.copy()
                
                # Clear the subplot and figure completely to remove old colorbars
                self.subplot.clear()
                # Also clear any existing colorbars from the figure
                if hasattr(self.figure, 'axes') and len(self.figure.axes) > 1:
                    # Remove extra axes (colorbars)
                    for ax in self.figure.axes[1:]:
                        ax.remove()
                
                # Display image WITHOUT colorbar - WITH INTERPOLATION
                if len(image.shape) == 2:
                    # Grayscale
                    im = self.subplot.imshow(image, cmap='gray', aspect='equal', 
                                        interpolation=self.current_display_interpolation)
                else:
                    # Color
                    im = self.subplot.imshow(image, aspect='equal', 
                                        interpolation=self.current_display_interpolation)
                
                self.subplot.set_title(title)
                self.subplot.axis('on')  # Show axes for pixel coordinates
                
                # Set up pixel-perfect display
                self.subplot.set_xlim(-0.5, image.shape[1] - 0.5)
                self.subplot.set_ylim(image.shape[0] - 0.5, -0.5)
                
                # Restore ROIs if they existed
                if existing_rois and self.roi_selector:
                    self.roi_selector.rois = existing_rois
                    for roi in existing_rois:
                        self.roi_selector._visualize_roi(roi)
                
                # NO COLORBAR - removed this line: plt.colorbar(im, ax=self.subplot, shrink=0.8)
                
                self.canvas.draw()
                self.current_image = image
                
                self.logger.info(f"Image displayed: {image.shape}, {image.dtype}")
                
            except Exception as e:
                self.logger.error(f"Failed to display image: {e}")
                self.update_status(f"Display error: {str(e)}")

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
        """Enhanced version with camera roll for multiple items"""
        try:
            self.update_status(f"Loading {len(selected_items)} items...")
            
            if operation == "single":
                # Single item (hide camera roll)
                if hasattr(self, 'camera_roll') and self.camera_roll:
                    self.camera_roll._hide_camera_roll()
                    
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
                # Multiple items - show camera roll
                arrays = self.array_handler.load_multiple_items(selected_items)
                
                if arrays:
                    # Create camera roll if needed
                    if not hasattr(self, 'camera_roll') or not self.camera_roll:
                        from pixelprobe.gui.camera_roll import CameraRollInterface
                        self.camera_roll = CameraRollInterface(self)
                    
                    # Load into camera roll
                    self.camera_roll.load_multiple_frames(arrays)
                    self.update_status(f"Loaded {len(arrays)} frames - Navigate with ← → keys or thumbnails")
                else:
                    self.update_status("Failed to load any items")
            
            elif operation == "average":
                # Average (hide camera roll)
                if hasattr(self, 'camera_roll') and self.camera_roll:
                    self.camera_roll._hide_camera_roll()
                    
                averaged_array = self.array_handler.average_items(selected_items)
                
                if averaged_array is not None:
                    self.current_array = averaged_array
                    self.current_image = self._array_to_display_image(averaged_array)
                    self.display_image(self.current_image, f"Averaged Items {selected_items}")
                    self.update_status(f"Averaged {len(selected_items)} items - Shape: {averaged_array.shape}")
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
        """Handle load image button click"""
        self.logger.info("Load image action triggered")
        self.update_status("Selecting image file...")
        
        # Get image file from user
        image_path = self.file_dialogs.select_image_file()
        if not image_path:
            self.update_status("Image loading cancelled")
            return
        
        try:
            # Load image
            image_data = self.image_loader.load_image(image_path)
            if image_data is not None:
                self.current_image = image_data
                self.current_array = image_data  # For processing operations
                self.display_image(image_data, f"Image: {image_path.name}")
                self.update_status(f"Loaded image: {image_path.name} - Shape: {image_data.shape}")
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
        """Handle interpolation button click - show options dialog"""
        self.logger.info("Interpolation action triggered")
        
        if self.current_image is None:
            self.update_status("No image loaded - please load an image or array data first")
            return
        
        # Show interpolation options dialog
        self.show_interpolation_options()

    def show_interpolation_options(self):
        """Show interpolation method selection dialog with properly sized sections"""
        # Create dialog window
        options_window = ctk.CTkToplevel(self.root)
        options_window.title("Interpolation Methods")
        options_window.grab_set()  # Make dialog modal
        
        # Configure window - TALLER to fit everything
        options_window.geometry("550x950")
        options_window.resizable(True, True)  # Allow resizing
        
        # Main frame
        main_frame = ctk.CTkFrame(options_window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="Select Interpolation Method",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(10, 20))
        
        # Description
        desc_label = ctk.CTkLabel(
            main_frame,
            text="Choose from all available matplotlib interpolation methods:",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        desc_label.pack(pady=(0, 15))
        
        # Method selection
        method_var = tk.StringVar(value=self.current_display_interpolation)
        methods = self.interpolator.get_interpolation_methods()
        
        # Create scrollable frame for methods - SMALLER HEIGHT
        scrollable_frame = ctk.CTkScrollableFrame(main_frame, width=500, height=350)  # Reduced from 550 to 350
        scrollable_frame.pack(pady=10, padx=20, fill="x")  # Changed from fill="both", expand=True
        
        # Method descriptions for user understanding
        method_descriptions = {
            'none': "No interpolation - raw pixels",
            'nearest': "Nearest neighbor - sharp, pixelated", 
            'bilinear': "Linear interpolation - smooth",
            'bicubic': "Cubic interpolation - very smooth",
            'spline16': "16-element spline interpolation",
            'spline36': "36-element spline interpolation", 
            'hanning': "Hanning windowed interpolation",
            'hamming': "Hamming windowed interpolation",
            'hermite': "Hermite interpolation",
            'kaiser': "Kaiser windowed interpolation",
            'quadric': "Quadratic interpolation",
            'catrom': "Catmull-Rom interpolation",
            'gaussian': "Gaussian interpolation",
            'bessel': "Bessel interpolation",
            'mitchell': "Mitchell interpolation",
            'sinc': "Sinc interpolation - high quality",
            'lanczos': "Lanczos interpolation - very high quality",
            'antialiased': "Antialiased interpolation",
            'auto': "Automatic selection by matplotlib"
        }
        
        # Create radio buttons for each method - COMPACT LAYOUT
        for method in methods:
            method_frame = ctk.CTkFrame(scrollable_frame)
            method_frame.pack(fill="x", padx=5, pady=2)  # Reduced padding
            
            # Radio button
            radio = ctk.CTkRadioButton(
                method_frame,
                text=f"{method}",
                variable=method_var,
                value=method,
                font=ctk.CTkFont(size=12, weight="bold")  # Smaller font
            )
            radio.pack(anchor="w", padx=10, pady=4)  # Reduced padding
            
            # Description - more compact
            desc = method_descriptions.get(method, "Matplotlib interpolation method")
            desc_label = ctk.CTkLabel(
                method_frame,
                text=desc,
                font=ctk.CTkFont(size=10),  # Smaller description font
                text_color="gray"
            )
            desc_label.pack(anchor="w", padx=25, pady=(0, 4))  # Reduced padding
        
        # Options frame - FIXED HEIGHT
        options_frame = ctk.CTkFrame(main_frame, height=180)  # Fixed height
        options_frame.pack(fill="x", padx=20, pady=15)
        options_frame.pack_propagate(False)  # Prevent frame from shrinking
        
        # Add title for options section
        options_title = ctk.CTkLabel(
            options_frame,
            text="Application Options",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        options_title.pack(pady=(10, 8))
        
        # ROI only option
        roi_only_var = tk.BooleanVar(value=False)
        roi_check = ctk.CTkCheckBox(
            options_frame,
            text="Apply to ROI only (if ROI selected)",
            variable=roi_only_var
        )
        roi_check.pack(pady=3)
        
        # Apply to all loaded frames option
        all_frames_var = tk.BooleanVar(value=False)
        all_frames_check = ctk.CTkCheckBox(
            options_frame,
            text=f"Apply to all loaded frames ({len(self.current_items) if self.current_items else 0} frames)",
            variable=all_frames_var
        )
        all_frames_check.pack(pady=3)
        
        # Disable if no multiple frames loaded
        if not self.current_items or len(self.current_items) <= 1:
            all_frames_check.configure(state="disabled")
        
        # NEW: Modify pixel data option
        modify_data_var = tk.BooleanVar(value=False)
        modify_data_check = ctk.CTkCheckBox(
            options_frame,
            text="Modify pixel data (vs display only)",
            variable=modify_data_var
        )
        modify_data_check.pack(pady=3)
        
        # Add explanation for the new option - more compact
        explanation_label = ctk.CTkLabel(
            options_frame,
            text="• Checked: Permanently change pixel values\n• Unchecked: Only change visual display",
            font=ctk.CTkFont(size=10),
            text_color="gray",
            justify="left"
        )
        explanation_label.pack(pady=(2, 8))
        
        # Button frame - FIXED HEIGHT
        button_frame = ctk.CTkFrame(main_frame, height=80)  # Fixed height for buttons
        button_frame.pack(fill="x", padx=20, pady=15)
        button_frame.pack_propagate(False)  # Prevent frame from shrinking
        
        # Apply button - UPDATED to pass modify_data option
        apply_btn = ctk.CTkButton(
            button_frame,
            text="Apply Interpolation",
            command=lambda: self.apply_interpolation_method(
                method_var.get(), 
                roi_only_var.get(), 
                all_frames_var.get(), 
                modify_data_var.get(),  # NEW PARAMETER
                options_window
            ),
            fg_color="#4CAF50",
            hover_color="#45a049",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        apply_btn.pack(side="left", padx=10, pady=15, expand=True, fill="x")
        
        # Cancel button
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=options_window.destroy,
            fg_color="#f44336",
            hover_color="#da190b",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        cancel_btn.pack(side="right", padx=10, pady=15, expand=True, fill="x")
        
        # Center the window - UPDATED FOR TALLER SIZE
        options_window.update_idletasks()
        x = (options_window.winfo_screenwidth() // 2) - (550 // 2)
        y = (options_window.winfo_screenheight() // 2) - (950 // 2)
        options_window.geometry(f"550x950+{x}+{y}")

    def apply_interpolation_method(self, method: str, roi_only: bool, all_frames: bool, modify_data: bool, dialog_window):
        """Apply the selected interpolation method with full ROI, all-frames, and data modification support"""
        
        # Validate inputs
        if not self._validate_interpolation_inputs(roi_only, modify_data):
            return
            
        validated_method = self.interpolator.apply_interpolation_method(method)
        
        # Log the operation parameters
        self.logger.info(f"Interpolation: {validated_method}, ROI only: {roi_only}, All frames: {all_frames}, Modify data: {modify_data}")
        
        try:
            if modify_data:
                # Option A: Modify actual pixel data
                self._apply_data_interpolation(validated_method, roi_only, all_frames)
            else:
                # Option B: Display-only interpolation
                self._apply_display_interpolation(validated_method, roi_only, all_frames)
                
            dialog_window.destroy()
            
        except Exception as e:
            self.logger.error(f"Interpolation failed: {e}")
            self.update_status(f"Interpolation failed: {str(e)}")
            messagebox.showerror("Interpolation Error", f"Failed to apply interpolation:\n{str(e)}")

    def _validate_interpolation_inputs(self, roi_only: bool, modify_data: bool) -> bool:
        """Validate interpolation inputs and show error messages if needed"""
        
        # Check if image is loaded
        if self.current_image is None:
            messagebox.showerror("No Image", "No image loaded. Please load an image or array data first.")
            return False
            
        # Check ROI requirement
        if roi_only and (not self.roi_selector or not self.roi_selector.rois):
            messagebox.showerror(
                "No ROI Selected", 
                "ROI-only interpolation requires at least one Region of Interest.\n\n"
                "Steps to create ROI:\n"
                "1. Click 'Enable ROI Mode'\n"
                "2. Select ROI type (Rectangle/Point)\n"
                "3. Draw ROI on your image\n\n"
                "Then try interpolation again."
            )
            return False
            
        # Warn about data modification
        if modify_data:
            result = messagebox.askyesno(
                "Modify Pixel Data", 
                "This will permanently change the pixel values.\n\n"
                "The original data will be stored for undo.\n\n"
                "Do you want to proceed?",
                icon="warning"
            )
            if not result:
                return False
                
        return True

    def _apply_data_interpolation(self, method: str, roi_only: bool, all_frames: bool):
        """Apply interpolation to actual pixel data (Option A)"""
        
        # Store original data for undo functionality
        self._store_undo_data(all_frames)
        
        if all_frames:
            self._apply_data_interpolation_all_frames(method, roi_only)
        else:
            self._apply_data_interpolation_single_frame(method, roi_only)

    def _apply_display_interpolation(self, method: str, roi_only: bool, all_frames: bool):
        """Apply interpolation to display only (Option B)"""
        
        # Update display interpolation setting
        self.current_display_interpolation = method
        
        # Update title to show interpolation method
        current_title = getattr(self, 'current_title', 'Image')
        if ' (' in current_title and current_title.endswith(')'):
            current_title = current_title.split(' (')[0]
        
        new_title = f"{current_title} ({method})"
        self.current_title = new_title
        
        # For display-only, we just update the matplotlib imshow interpolation
        # The ROI and all-frames options don't apply to display-only mode
        if self.current_image is not None:
            self.display_image(self.current_image, new_title)
        
        status_msg = f"Applied {method} display interpolation"
        if roi_only or all_frames:
            status_msg += " (ROI and all-frames options apply only when modifying data)"
            
        self.update_status(status_msg)

    def _apply_data_interpolation_single_frame(self, method: str, roi_only: bool):
        """Apply data interpolation to current frame only"""
        
        if roi_only:
            # Apply to ROI interior pixels only (excluding boundary)
            roi_mask = self._get_roi_interior_mask(self.current_image.shape[:2])
            self.current_image = self.interpolator.interpolate_roi_pixels(
                self.current_image, roi_mask, method
            )
            status_msg = f"Applied {method} interpolation to ROI interior pixels"
        else:
            # Apply to full image
            self.current_image = self.interpolator.interpolate_pixel_data(self.current_image, method)
            status_msg = f"Applied {method} interpolation to full image"
        
        # Update current array data
        self.current_array = self.current_image
        
        # Refresh display
        title = f"Interpolated ({method})"
        self.display_image(self.current_image, title)
        self.update_status(status_msg)
        
        # Enable undo button
        self.undo_btn.configure(state="normal")

    def _apply_data_interpolation_all_frames(self, method: str, roi_only: bool):
        """Apply data interpolation to all loaded frames with progress tracking"""
        
        if not self.current_items or len(self.current_items) <= 1:
            messagebox.showwarning("Insufficient Frames", "All frames option requires multiple frames loaded.")
            return
        
        # Create progress dialog
        progress_window = self._create_progress_dialog(len(self.current_items))
        
        try:
            processed_count = 0
            
            for i, item_num in enumerate(self.current_items):
                # Update progress
                progress_msg = f"Processing frame {item_num} ({i+1}/{len(self.current_items)})"
                self._update_progress_dialog(progress_window, progress_msg, i, len(self.current_items))
                
                # Load frame data
                frame_data = self.array_handler.load_item(item_num)
                if frame_data is None:
                    continue
                
                # Apply interpolation
                if roi_only:
                    roi_mask = self._get_roi_interior_mask(frame_data.shape[:2])
                    processed_frame = self.interpolator.interpolate_roi_pixels(frame_data, roi_mask, method)
                else:
                    processed_frame = self.interpolator.interpolate_pixel_data(frame_data, method)
                
                # Update the frame in memory (if we had persistent storage, we'd save here)
                # For now, we'll update the current display if it matches
                if item_num == self.current_items[0]:  # If this is the currently displayed frame
                    self.current_image = processed_frame
                    self.current_array = processed_frame
                
                processed_count += 1
            
            # Close progress dialog
            progress_window.destroy()
            
            # Refresh display
            title = f"All Frames Interpolated ({method})"
            if self.current_image is not None:
                self.display_image(self.current_image, title)
            
            status_msg = f"Applied {method} interpolation to {processed_count}/{len(self.current_items)} frames"
            if roi_only:
                status_msg += " (ROI interior pixels only)"
            
            self.update_status(status_msg)
            
            # Enable undo button
            self.undo_btn.configure(state="normal")
            
        except Exception as e:
            progress_window.destroy()
            raise e

    def _get_roi_interior_mask(self, image_shape: Tuple[int, int]) -> np.ndarray:
        """Get combined mask for all ROIs with interior pixels only (excluding boundaries)"""
        
        if not self.roi_selector or not self.roi_selector.rois:
            return np.zeros(image_shape, dtype=bool)
        
        combined_mask = np.zeros(image_shape, dtype=bool)
        
        for roi in self.roi_selector.rois:
            roi_mask = roi.get_mask(image_shape)  # This already excludes boundaries per your ROI implementation
            combined_mask |= roi_mask
        
        return combined_mask

    def undo_interpolation(self):
        """Undo last interpolation operation"""
        
        if not hasattr(self, 'undo_data') or not self.undo_data:
            messagebox.showinfo("No Undo Available", "No interpolation operation to undo.")
            return
        
        try:
            if self.undo_data['type'] == 'all_frames':
                # For all frames, we restore the original data
                # Note: Since we don't have persistent frame storage yet, 
                # we'll restore the currently displayed frame
                if 'current_image_backup' in self.undo_data:
                    self.current_image = self.undo_data['current_image_backup']
                    self.current_array = self.undo_data['current_array_backup']
                    self.display_image(self.current_image, "Restored from Undo")
                
                self.update_status(f"Undid interpolation for all frames")
                
            else:
                # Restore single frame
                self.current_image = self.undo_data['current_image']
                if self.undo_data['current_array'] is not None:
                    self.current_array = self.undo_data['current_array']
                
                self.display_image(self.current_image, "Restored from Undo")
                self.update_status("Undid last interpolation operation")
            
            # Clear undo data after use and disable undo button
            self.undo_data = {}
            self.undo_btn.configure(state="disabled")
            
        except Exception as e:
            self.logger.error(f"Undo failed: {e}")
            messagebox.showerror("Undo Error", f"Failed to undo interpolation:\n{str(e)}")

    def _store_undo_data(self, all_frames: bool):
        """Store original data for undo functionality"""
        
        if not hasattr(self, 'undo_data'):
            self.undo_data = {}
        
        if all_frames and self.current_items:
            # For all frames, store the current display state
            self.undo_data['type'] = 'all_frames'
            self.undo_data['current_image_backup'] = self.current_image.copy()
            self.undo_data['current_array_backup'] = self.current_array.copy() if self.current_array is not None else None
        else:
            # Store current frame data
            self.undo_data['type'] = 'single_frame'
            self.undo_data['current_image'] = self.current_image.copy()
            self.undo_data['current_array'] = self.current_array.copy() if self.current_array is not None else None
        
        self.logger.info(f"Stored undo data: {self.undo_data['type']}")

    def _create_progress_dialog(self, total_frames: int):
        """Create progress dialog for multi-frame operations"""
        
        progress_window = ctk.CTkToplevel(self.root)
        progress_window.title("Processing Frames")
        progress_window.geometry("450x180")
        progress_window.grab_set()
        progress_window.resizable(False, False)
        
        # Center the window
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (450 // 2)
        y = (progress_window.winfo_screenheight() // 2) - (180 // 2)
        progress_window.geometry(f"450x180+{x}+{y}")
        
        # Progress frame
        progress_frame = ctk.CTkFrame(progress_window)
        progress_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            progress_frame,
            text="Interpolating Frames",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(10, 5))
        
        # Progress label
        progress_label = ctk.CTkLabel(
            progress_frame,
            text="Initializing...",
            font=ctk.CTkFont(size=12)
        )
        progress_label.pack(pady=(5, 5))
        
        # Progress bar
        progress_bar = ctk.CTkProgressBar(progress_frame, width=350, height=20)
        progress_bar.pack(pady=(10, 15))
        progress_bar.set(0)
        
        # Progress percentage label
        percentage_label = ctk.CTkLabel(
            progress_frame,
            text="0%",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        percentage_label.pack()
        
        # Store references for updates
        progress_window.progress_label = progress_label
        progress_window.progress_bar = progress_bar
        progress_window.percentage_label = percentage_label
        
        return progress_window

    def _update_progress_dialog(self, progress_window, message: str, current: int, total: int):
        """Update progress dialog with current status"""
        
        try:
            progress_window.progress_label.configure(text=message)
            progress_value = current / total
            progress_window.progress_bar.set(progress_value)
            percentage = int(progress_value * 100)
            progress_window.percentage_label.configure(text=f"{percentage}%")
            progress_window.update()
        except:
            # Progress window might have been closed
            pass

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