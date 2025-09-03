"""
Fixed PixelProbe Plotting Dialog - Clean implementation with working controls
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.ticker as ticker
import numpy as np
from typing import Dict, List, Optional, Any
import json
from pathlib import Path
import logging
from datetime import datetime
import matplotlib.ticker as ticker
import math
import re

# Import ROIType for enum handling
try:
    from pixelprobe.gui.roi_selector import ROIType
except ImportError:
    ROIType = None


class ROIFramePlottingDialog:
    """Fixed plotting dialog with working controls"""
    
    def __init__(self, parent, array_handler, roi_selector, current_items):
        self.parent = parent
        self.array_handler = array_handler
        self.roi_selector = roi_selector
        self.current_items = current_items
        self.logger = logging.getLogger(__name__)
        
        # Dialog window
        self.dialog = None
        
        # Data for plotting
        self.plot_data = {}
        
        # Plotting figure and canvas
        self.figure = None
        self.canvas = None
        self.subplot = None
        
        # Individual trace customization
        self.trace_custom = {}
        self.trace_controls = {}
        
        # UI control variables
        self.roi_checkboxes = {}
        self.manual_axis_controls = []
        
    def show(self):
        """Show the dialog"""
        self._create_dialog()
        self._create_widgets()
        self._calculate_initial_data()
        
    def _create_dialog(self):
        """Create the main dialog window"""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("PixelProbe - ROI vs Frame Analysis")
        self.dialog.geometry("1400x900")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center window
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (700)
        y = (self.dialog.winfo_screenheight() // 2) - (450)
        self.dialog.geometry(f"1400x900+{x}+{y}")
        
        # Configure grid weights
        self.dialog.grid_columnconfigure(1, weight=1)
        self.dialog.grid_rowconfigure(0, weight=1)
        
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_dialog_close)
        
    def _create_widgets(self):
        """Create all dialog widgets"""
        self._create_control_panel()
        self._create_plot_area()
        
    def _create_control_panel(self):
        """Create control panel"""
        self.control_scroll = ctk.CTkScrollableFrame(
            self.dialog, 
            width=350,
            label_text="Plot Controls"
        )
        self.control_scroll.grid(row=0, column=0, sticky="nsew", padx=(15, 8), pady=15)
        
        # Create sections
        self._create_roi_selection_section()
        self._create_plot_settings_section()
        self._create_individual_traces_section()
        self._create_mathematical_operations_section()
        self._create_export_section()

    def _create_plot_area(self):
        """Create plot area with FIXED sizing"""
        plot_frame = ctk.CTkFrame(self.dialog)
        plot_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 15), pady=15)
        plot_frame.grid_columnconfigure(0, weight=1)
        plot_frame.grid_rowconfigure(0, weight=1)
        
        # Create matplotlib figure with FIXED parameters
        self.figure = Figure(figsize=(12, 8), dpi=100, facecolor='white', tight_layout=True)
        self.subplot = self.figure.add_subplot(111)
        
        # Canvas
        self.canvas = FigureCanvasTkAgg(self.figure, plot_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        
        # Initial empty plot
        self._show_empty_plot()
        
    def _show_empty_plot(self):
        """Show empty plot with instructions"""
        self.subplot.clear()
        self.subplot.text(0.5, 0.5, 'Click "Plot Data" to create plot\n\nFeatures:\n• Individual trace customization\n• Axis step size control\n• Legend positioning\n• Export options', 
                         ha='center', va='center', fontsize=12, 
                         bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.7))
        self.subplot.set_title("PixelProbe ROI Analysis")
        self.canvas.draw()

    def _create_roi_selection_section(self):
        """Create ROI selection"""
        roi_frame = ctk.CTkFrame(self.control_scroll)
        roi_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(roi_frame, text="ROI Selection", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        # Buttons
        buttons_frame = ctk.CTkFrame(roi_frame)
        buttons_frame.pack(fill="x", padx=8, pady=3)
        
        ctk.CTkButton(buttons_frame, text="Select All", command=self._select_all_rois, 
                     width=80, height=28).pack(side="left", padx=3)
        ctk.CTkButton(buttons_frame, text="Clear All", command=self._clear_all_rois,
                     width=80, height=28).pack(side="left", padx=3)
        
        # Plot mode
        mode_frame = ctk.CTkFrame(roi_frame)
        mode_frame.pack(fill="x", padx=8, pady=3)
        ctk.CTkLabel(mode_frame, text="Mode:").pack(side="left", padx=(5, 5))
        self.plot_mode_var = tk.StringVar(value="separate")
        ctk.CTkComboBox(mode_frame, values=["separate", "average", "both"],
                       variable=self.plot_mode_var, width=100).pack(side="left", padx=3)
        
        # ROI checkboxes
        if self.roi_selector and self.roi_selector.rois:
            roi_scroll = ctk.CTkScrollableFrame(roi_frame, height=100)
            roi_scroll.pack(fill="x", padx=8, pady=5)
            
            for roi in self.roi_selector.rois:
                checkbox_var = tk.BooleanVar(value=True)
                checkbox = ctk.CTkCheckBox(roi_scroll, text=roi.label, variable=checkbox_var)
                checkbox.pack(anchor="w", padx=5, pady=2)
                self.roi_checkboxes[roi.label] = checkbox_var
        
        # Action button
        ctk.CTkButton(roi_frame, text="PLOT DATA", command=self._plot_data,
                     font=ctk.CTkFont(size=12, weight="bold"), height=40,
                     fg_color="green").pack(pady=10)
        
    def _create_plot_settings_section(self):
        """Create enhanced plot settings with proper validation for font size entries"""
        settings_frame = ctk.CTkFrame(self.control_scroll)
        settings_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(settings_frame, text="Plot Settings", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        # Helper function to validate numeric entries
        def validate_numeric_entry(var, default_value):
            """Validate and fix numeric entry values"""
            try:
                value = var.get()
                if value == "" or value is None:
                    var.set(default_value)
                    return default_value
                return float(value)
            except (ValueError, tk.TclError):
                var.set(default_value)
                return default_value
        
        # Create validation command
        def create_validation_callback(var, default_val):
            def callback(*args):
                validate_numeric_entry(var, default_val)
            return callback
        
        # Basic labels with font size controls
        labels_data = [
            ("Title:", "title_var", "ROI Average vs Frame Number", "title_font_size_var", 16),
            ("X-Label:", "xlabel_var", "Frame Number", "axis_label_font_size_var", 12),
            ("Y-Label:", "ylabel_var", "Average Pixel Value", None, None)  # Y-label shares axis_label_font_size_var
        ]
        
        for i, (label_text, var_name, default, size_var_name, default_size) in enumerate(labels_data):
            row = ctk.CTkFrame(settings_frame)
            row.pack(fill="x", padx=8, pady=2)
            ctk.CTkLabel(row, text=label_text, width=60).pack(side="left", padx=(5, 5))
            
            # Text entry
            var = tk.StringVar(value=default)
            entry = ctk.CTkEntry(row, textvariable=var, height=28)
            entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
            setattr(self, var_name, var)
            
            # Font size control (create only once for each unique size variable)
            if size_var_name and not hasattr(self, size_var_name):
                ctk.CTkLabel(row, text="Size:", width=35).pack(side="left")
                size_var = tk.StringVar(value=str(default_size))  # Use StringVar instead of DoubleVar
                
                # Add validation callback
                validation_callback = create_validation_callback(size_var, default_size)
                size_var.trace_add('write', validation_callback)
                
                size_entry = ctk.CTkEntry(row, textvariable=size_var, width=50, height=28)
                size_entry.pack(side="left", padx=(0, 5))
                setattr(self, size_var_name, size_var)
        
        # Axis values font size (separate from axis labels)
        axis_values_row = ctk.CTkFrame(settings_frame)
        axis_values_row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(axis_values_row, text="Axis Values Size:", width=120).pack(side="left", padx=(5, 5))
        
        self.axis_values_font_size_var = tk.StringVar(value="10")  # Use StringVar
        axis_values_validation = create_validation_callback(self.axis_values_font_size_var, 10)
        self.axis_values_font_size_var.trace_add('write', axis_values_validation)
        
        axis_values_entry = ctk.CTkEntry(axis_values_row, textvariable=self.axis_values_font_size_var, width=50, height=28)
        axis_values_entry.pack(side="left", padx=(0, 5))
        
        # Grid settings
        grid_frame = ctk.CTkFrame(settings_frame)
        grid_frame.pack(fill="x", padx=8, pady=3)
        
        self.grid_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(grid_frame, text="Grid", variable=self.grid_var).pack(side="left", padx=5)
        
        ctk.CTkLabel(grid_frame, text="Alpha:", width=40).pack(side="left")
        self.grid_alpha_var = tk.DoubleVar(value=0.3)
        ctk.CTkSlider(grid_frame, from_=0.1, to=1.0, variable=self.grid_alpha_var, width=80).pack(side="left", padx=2)
        
        ctk.CTkLabel(grid_frame, text="Width:", width=40).pack(side="left")
        self.grid_width_var = tk.DoubleVar(value=0.8)
        ctk.CTkSlider(grid_frame, from_=0.5, to=2.0, variable=self.grid_width_var, width=80).pack(side="left", padx=2)
        
        # Axis controls
        axis_frame = ctk.CTkFrame(settings_frame)
        axis_frame.pack(fill="x", padx=8, pady=3)
        
        self.auto_axis_var = tk.BooleanVar(value=True)
        auto_check = ctk.CTkCheckBox(axis_frame, text="Auto Axis", variable=self.auto_axis_var,
                                    command=self._toggle_axis_controls)
        auto_check.pack(side="left", padx=5)
        
        # Manual axis controls frame
        self.manual_axis_frame = ctk.CTkFrame(settings_frame)
        self.manual_axis_frame.pack(fill="x", padx=8, pady=3)
        
        # X-axis controls
        x_frame = ctk.CTkFrame(self.manual_axis_frame)
        x_frame.pack(fill="x", pady=1)
        ctk.CTkLabel(x_frame, text="X:", width=20).pack(side="left", padx=2)
        
        ctk.CTkLabel(x_frame, text="Min:", width=30).pack(side="left")
        self.x_min_var = tk.DoubleVar(value=0)
        ctk.CTkEntry(x_frame, textvariable=self.x_min_var, width=50).pack(side="left", padx=1)
        
        ctk.CTkLabel(x_frame, text="Max:", width=30).pack(side="left")
        self.x_max_var = tk.DoubleVar(value=10)
        ctk.CTkEntry(x_frame, textvariable=self.x_max_var, width=50).pack(side="left", padx=1)
        
        ctk.CTkLabel(x_frame, text="Step:", width=30).pack(side="left")
        self.x_step_var = tk.DoubleVar(value=1.0)
        ctk.CTkEntry(x_frame, textvariable=self.x_step_var, width=50).pack(side="left", padx=1)
        
        # Y-axis controls
        y_frame = ctk.CTkFrame(self.manual_axis_frame)
        y_frame.pack(fill="x", pady=1)
        ctk.CTkLabel(y_frame, text="Y:", width=20).pack(side="left", padx=2)
        
        ctk.CTkLabel(y_frame, text="Min:", width=30).pack(side="left")
        self.y_min_var = tk.DoubleVar(value=0)
        ctk.CTkEntry(y_frame, textvariable=self.y_min_var, width=50).pack(side="left", padx=1)
        
        ctk.CTkLabel(y_frame, text="Max:", width=30).pack(side="left")
        self.y_max_var = tk.DoubleVar(value=200)
        ctk.CTkEntry(y_frame, textvariable=self.y_max_var, width=50).pack(side="left", padx=1)
        
        ctk.CTkLabel(y_frame, text="Step:", width=30).pack(side="left")
        self.y_step_var = tk.DoubleVar(value=10.0)
        ctk.CTkEntry(y_frame, textvariable=self.y_step_var, width=50).pack(side="left", padx=1)
        
        # Legend settings with size control
        legend_frame = ctk.CTkFrame(settings_frame)
        legend_frame.pack(fill="x", padx=8, pady=3)
        
        ctk.CTkLabel(legend_frame, text="Legend:", width=60).pack(side="left", padx=5)
        self.legend_location_var = tk.StringVar(value="upper right")
        ctk.CTkComboBox(legend_frame, values=['upper right', 'upper left', 'lower right', 'lower left', 
                                            'upper center', 'lower center', 'center'],
                    variable=self.legend_location_var, width=120).pack(side="left", padx=5)
        
        # Legend font size with validation
        ctk.CTkLabel(legend_frame, text="Size:", width=35).pack(side="left")
        self.legend_font_size_var = tk.StringVar(value="10")  # Use StringVar
        legend_validation = create_validation_callback(self.legend_font_size_var, 10)
        self.legend_font_size_var.trace_add('write', legend_validation)
        
        legend_size_entry = ctk.CTkEntry(legend_frame, textvariable=self.legend_font_size_var, width=50, height=28)
        legend_size_entry.pack(side="left", padx=(0, 5))
        
        self._toggle_axis_controls()  # Initialize state

    def _create_individual_traces_section(self):
        """Create individual trace customization including average trace options"""
        if not self.roi_selector or not self.roi_selector.rois:
            return
            
        traces_frame = ctk.CTkFrame(self.control_scroll)
        traces_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(traces_frame, text="Individual Traces", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        traces_scroll = ctk.CTkScrollableFrame(traces_frame, height=250)  # Increased height
        traces_scroll.pack(fill="x", padx=8, pady=5)
        
        # Initialize trace settings
        default_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        default_markers = ['o', 's', '^', 'v', 'D', '*']
        marker_options = ['o', 's', '^', 'v', 'D', '*', '+', 'x', 'none']  # Added 'none' option
        
        # Create trace settings for individual ROIs
        for i, roi in enumerate(self.roi_selector.rois):
            roi_name = roi.label
            
            # Initialize defaults
            self.trace_custom[roi_name] = {
                'color': default_colors[i % len(default_colors)],
                'label': roi_name,
                'visible': True,
                'linewidth': 2.0,
                'linestyle': '-',
                'marker': default_markers[i % len(default_markers)],
                'markersize': 6
            }
            
            # Create UI for each trace
            trace_frame = ctk.CTkFrame(traces_scroll)
            trace_frame.pack(fill="x", padx=2, pady=2)
            
            # Header with ROI name
            header_frame = ctk.CTkFrame(trace_frame)
            header_frame.pack(fill="x", padx=3, pady=1)
            ctk.CTkLabel(header_frame, text=f"📊 {roi_name}", font=ctk.CTkFont(weight="bold")).pack(side="left")
            
            # Visibility and color row
            name_row = ctk.CTkFrame(trace_frame)
            name_row.pack(fill="x", padx=3, pady=1)
            
            visible_var = tk.BooleanVar(value=True)
            ctk.CTkCheckBox(name_row, text="Show", variable=visible_var, width=50).pack(side="left")
            
            color_btn = ctk.CTkButton(name_row, text="Color", width=60, height=25,
                                    fg_color=self.trace_custom[roi_name]['color'],
                                    command=lambda rn=roi_name: self._choose_color(rn))
            color_btn.pack(side="left", padx=5)
            
            label_var = tk.StringVar(value=roi_name)
            ctk.CTkEntry(name_row, textvariable=label_var, width=100, height=25).pack(side="left", padx=5)
            
            # Properties row
            props_row = ctk.CTkFrame(trace_frame)
            props_row.pack(fill="x", padx=3, pady=1)
            
            # Line width
            ctk.CTkLabel(props_row, text="Width:", width=40).pack(side="left")
            linewidth_var = tk.DoubleVar(value=2.0)
            ctk.CTkSlider(props_row, from_=0.5, to=5.0, variable=linewidth_var, width=60).pack(side="left", padx=2)
            
            # Marker size
            ctk.CTkLabel(props_row, text="Size:", width=35).pack(side="left")
            markersize_var = tk.DoubleVar(value=6.0)
            ctk.CTkSlider(props_row, from_=2, to=12, variable=markersize_var, width=60).pack(side="left", padx=2)
            
            # Line style and marker
            style_row = ctk.CTkFrame(trace_frame)
            style_row.pack(fill="x", padx=3, pady=1)
            
            ctk.CTkLabel(style_row, text="Style:", width=40).pack(side="left")
            linestyle_var = tk.StringVar(value='-')
            ctk.CTkComboBox(style_row, values=['-', '--', '-.', ':'], 
                        variable=linestyle_var, width=60).pack(side="left", padx=2)
            
            ctk.CTkLabel(style_row, text="Marker:", width=50).pack(side="left")
            marker_var = tk.StringVar(value=default_markers[i % len(default_markers)])
            ctk.CTkComboBox(style_row, values=marker_options,  # Now includes 'none'
                        variable=marker_var, width=60).pack(side="left", padx=2)
            
            # Store controls
            self.trace_controls[roi_name] = {
                'visible_var': visible_var,
                'color_btn': color_btn,
                'label_var': label_var,
                'linewidth_var': linewidth_var,
                'linestyle_var': linestyle_var,
                'marker_var': marker_var,
                'markersize_var': markersize_var
            }
        
        # Separator
        separator = ctk.CTkFrame(traces_scroll, height=2)
        separator.pack(fill="x", padx=2, pady=10)
        
        # Average Trace Settings Section
        avg_trace_frame = ctk.CTkFrame(traces_scroll)
        avg_trace_frame.pack(fill="x", padx=2, pady=2)
        
        # Average trace header
        avg_header_frame = ctk.CTkFrame(avg_trace_frame)
        avg_header_frame.pack(fill="x", padx=3, pady=1)
        ctk.CTkLabel(avg_header_frame, text="📈 Average Trace", 
                    font=ctk.CTkFont(weight="bold", size=12)).pack(side="left")
        
        # Initialize average trace settings
        if not hasattr(self, 'avg_trace_settings'):
            self.avg_trace_settings = {
                'color': '#FF0000',  # Red for average
                'label': 'Average',
                'visible': True,
                'linewidth': 3.0,
                'linestyle': '-',
                'marker': 'o',
                'markersize': 8
            }
        
        # Average trace visibility and color
        avg_name_row = ctk.CTkFrame(avg_trace_frame)
        avg_name_row.pack(fill="x", padx=3, pady=1)
        
        avg_visible_var = tk.BooleanVar(value=self.avg_trace_settings['visible'])
        ctk.CTkCheckBox(avg_name_row, text="Show", variable=avg_visible_var, width=50).pack(side="left")
        
        avg_color_btn = ctk.CTkButton(avg_name_row, text="Color", width=60, height=25,
                                    fg_color=self.avg_trace_settings['color'],
                                    command=self._choose_avg_color)
        avg_color_btn.pack(side="left", padx=5)
        
        avg_label_var = tk.StringVar(value=self.avg_trace_settings['label'])
        ctk.CTkEntry(avg_name_row, textvariable=avg_label_var, width=100, height=25).pack(side="left", padx=5)
        
        # Average trace properties
        avg_props_row = ctk.CTkFrame(avg_trace_frame)
        avg_props_row.pack(fill="x", padx=3, pady=1)
        
        # Line width
        ctk.CTkLabel(avg_props_row, text="Width:", width=40).pack(side="left")
        avg_linewidth_var = tk.DoubleVar(value=self.avg_trace_settings['linewidth'])
        ctk.CTkSlider(avg_props_row, from_=0.5, to=5.0, variable=avg_linewidth_var, width=60).pack(side="left", padx=2)
        
        # Marker size
        ctk.CTkLabel(avg_props_row, text="Size:", width=35).pack(side="left")
        avg_markersize_var = tk.DoubleVar(value=self.avg_trace_settings['markersize'])
        ctk.CTkSlider(avg_props_row, from_=2, to=12, variable=avg_markersize_var, width=60).pack(side="left", padx=2)
        
        # Average trace style and marker
        avg_style_row = ctk.CTkFrame(avg_trace_frame)
        avg_style_row.pack(fill="x", padx=3, pady=1)
        
        ctk.CTkLabel(avg_style_row, text="Style:", width=40).pack(side="left")
        avg_linestyle_var = tk.StringVar(value=self.avg_trace_settings['linestyle'])
        ctk.CTkComboBox(avg_style_row, values=['-', '--', '-.', ':'], 
                    variable=avg_linestyle_var, width=60).pack(side="left", padx=2)
        
        ctk.CTkLabel(avg_style_row, text="Marker:", width=50).pack(side="left")
        avg_marker_var = tk.StringVar(value=self.avg_trace_settings['marker'])
        ctk.CTkComboBox(avg_style_row, values=marker_options,  # Includes 'none'
                    variable=avg_marker_var, width=60).pack(side="left", padx=2)
        
        # Store average trace controls
        self.avg_trace_controls = {
            'visible_var': avg_visible_var,
            'color_btn': avg_color_btn,
            'label_var': avg_label_var,
            'linewidth_var': avg_linewidth_var,
            'linestyle_var': avg_linestyle_var,
            'marker_var': avg_marker_var,
            'markersize_var': avg_markersize_var
        }

    def _create_export_section(self):
        """Create export controls with metadata options"""
        export_frame = ctk.CTkFrame(self.control_scroll)
        export_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(export_frame, text="Export", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        format_row = ctk.CTkFrame(export_frame)
        format_row.pack(fill="x", padx=8, pady=3)
        
        ctk.CTkLabel(format_row, text="Format:", width=60).pack(side="left", padx=5)
        self.export_format_var = tk.StringVar(value="png")
        ctk.CTkComboBox(format_row, values=['png', 'pdf', 'svg', 'jpg'],
                       variable=self.export_format_var, width=80).pack(side="left", padx=5)
        
        dpi_row = ctk.CTkFrame(export_frame)
        dpi_row.pack(fill="x", padx=8, pady=3)
        
        ctk.CTkLabel(dpi_row, text="DPI:", width=60).pack(side="left", padx=5)
        self.export_dpi_var = tk.StringVar(value="300")
        ctk.CTkComboBox(dpi_row, values=['150', '300', '600', '1200'],
                       variable=self.export_dpi_var, width=80).pack(side="left", padx=5)
        
        # Metadata options
        metadata_frame = ctk.CTkFrame(export_frame)
        metadata_frame.pack(fill="x", padx=8, pady=3)
        
        ctk.CTkLabel(metadata_frame, text="Include:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=5)
        
        self.include_roi_coords_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(metadata_frame, text="ROI coordinates", 
                       variable=self.include_roi_coords_var, font=ctk.CTkFont(size=9)).pack(anchor="w", padx=15)
        
        self.include_frame_info_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(metadata_frame, text="Frame information", 
                       variable=self.include_frame_info_var, font=ctk.CTkFont(size=9)).pack(anchor="w", padx=15)
        
        self.include_plot_settings_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(metadata_frame, text="Plot settings", 
                       variable=self.include_plot_settings_var, font=ctk.CTkFont(size=9)).pack(anchor="w", padx=15)
        
        self.include_trace_settings_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(metadata_frame, text="Trace customization", 
                       variable=self.include_trace_settings_var, font=ctk.CTkFont(size=9)).pack(anchor="w", padx=15)
        
        # Export buttons
        button_frame = ctk.CTkFrame(export_frame)
        button_frame.pack(fill="x", padx=8, pady=5)
        
        ctk.CTkButton(button_frame, text="Export Plot", command=self._export_plot,
                     width=200, height=35).pack(pady=2)
        ctk.CTkButton(button_frame, text="Export Data (CSV)", command=self._export_data_csv,
                     width=200, height=35).pack(pady=2)
        ctk.CTkButton(button_frame, text="Export JSON", command=self._export_data_json,
                     width=200, height=35).pack(pady=2)

    # Control handlers
    def _select_all_rois(self):
        for var in self.roi_checkboxes.values():
            var.set(True)
        
    def _clear_all_rois(self):
        for var in self.roi_checkboxes.values():
            var.set(False)
    
    def _toggle_axis_controls(self):
        """Toggle manual axis controls"""
        if self.auto_axis_var.get():
            for widget in self.manual_axis_frame.winfo_children():
                for child in widget.winfo_children():
                    if hasattr(child, 'configure'):
                        try:
                            child.configure(state="disabled")
                        except:
                            pass
        else:
            for widget in self.manual_axis_frame.winfo_children():
                for child in widget.winfo_children():
                    if hasattr(child, 'configure'):
                        try:
                            child.configure(state="normal")
                        except:
                            pass
    
    def _choose_color(self, roi_name):
        """Choose color for trace"""
        current_color = self.trace_custom[roi_name]['color']
        color = colorchooser.askcolor(color=current_color, title=f"Color for {roi_name}")
        if color[1]:
            self.trace_custom[roi_name]['color'] = color[1]
            self.trace_controls[roi_name]['color_btn'].configure(fg_color=color[1])

    def _calculate_initial_data(self):
        """Calculate plot data for all ROIs"""
        if not self.roi_selector or not self.roi_selector.rois or not self.current_items:
            return
        
        self.plot_data = {}
        
        for roi in self.roi_selector.rois:
            roi_name = roi.label
            frame_numbers = []
            averages = []
            
            for frame_num in self.current_items:
                try:
                    array_data = self.array_handler.load_item(frame_num)
                    if array_data is None:
                        continue
                    
                    # Handle ROI coordinate dictionary format
                    roi_type_str = str(roi.roi_type).lower()
                    if 'rectangle' in roi_type_str or (ROIType and roi.roi_type == ROIType.RECTANGLE):
                        x = int(round(roi.coordinates['x']))
                        y = int(round(roi.coordinates['y']))
                        width = int(round(roi.coordinates['width']))
                        height = int(round(roi.coordinates['height']))
                        
                        x1, y1 = x, y
                        x2, y2 = x + width, y + height
                        
                        # Bounds check
                        x1 = max(0, min(x1, array_data.shape[1]-1))
                        x2 = max(x1+1, min(x2, array_data.shape[1]))
                        y1 = max(0, min(y1, array_data.shape[0]-1))
                        y2 = max(y1+1, min(y2, array_data.shape[0]))
                        
                        roi_data = array_data[y1:y2, x1:x2]
                        
                    elif 'point' in roi_type_str or (ROIType and roi.roi_type == ROIType.POINT):
                        x = int(round(roi.coordinates['x']))
                        y = int(round(roi.coordinates['y']))
                        
                        x = max(0, min(x, array_data.shape[1]-1))
                        y = max(0, min(y, array_data.shape[0]-1))
                        
                        roi_data = array_data[y, x]
                    else:
                        continue
                    
                    # Calculate average
                    if hasattr(roi_data, 'size') and roi_data.size > 0:
                        avg_value = float(np.mean(roi_data))
                        frame_numbers.append(frame_num)
                        averages.append(avg_value)
                        
                except Exception as e:
                    print(f"Error processing frame {frame_num} for ROI {roi_name}: {e}")
                    continue
            
            if frame_numbers and averages:
                self.plot_data[roi_name] = {
                    'frame_numbers': frame_numbers,
                    'averages': averages
                }

    def _create_mathematical_operations_section(self):
        """Create enhanced mathematical operations section with better layout"""
        # Only show if there are ROIs available
        if not hasattr(self, 'roi_selector') or not self.roi_selector.rois:
            return
        
        # Main operations frame with enhanced styling
        operations_frame = ctk.CTkFrame(self.control_scroll)
        operations_frame.pack(fill="x", padx=5, pady=8)
        
        # Title with better visibility
        title_frame = ctk.CTkFrame(operations_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(title_frame, text="🔢 Mathematical Operations", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        # Status indicator
        ops_count = len(getattr(self, 'mathematical_operations', {}))
        status_text = f"({ops_count} operations)" if ops_count > 0 else "(none yet)"
        ctk.CTkLabel(title_frame, text=status_text, 
                    font=ctk.CTkFont(size=11), text_color="gray").pack(side="right")
        
        # Scrollable operations container with FIXED height
        operations_scroll = ctk.CTkScrollableFrame(operations_frame, height=400)
        operations_scroll.pack(fill="x", padx=8, pady=5)
        
        # Initialize operations storage
        if not hasattr(self, 'mathematical_operations'):
            self.mathematical_operations = {}
            self.operation_controls = {}
            self.operation_counter = 0
        
        # CREATE NEW OPERATION SECTION
        create_frame = ctk.CTkFrame(operations_scroll)
        create_frame.pack(fill="x", padx=3, pady=5)
        
        # Section header
        header_frame = ctk.CTkFrame(create_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=5, pady=(8, 5))
        
        ctk.CTkLabel(header_frame, text="➕ Create New Operation:",
                    font=ctk.CTkFont(weight="bold", size=13)).pack(side="left")
        
        # Help button prominently placed
        help_btn = ctk.CTkButton(header_frame, text="Syntax Help", width=90, height=25,
                                fg_color="blue", hover_color="darkblue",
                                command=self._show_expression_help)
        help_btn.pack(side="right", padx=5)
        
        # Input form with better layout
        input_container = ctk.CTkFrame(create_frame)
        input_container.pack(fill="x", padx=5, pady=5)
        
        # Name input row
        name_row = ctk.CTkFrame(input_container)
        name_row.pack(fill="x", padx=5, pady=3)
        
        ctk.CTkLabel(name_row, text="Name:", width=80, 
                    font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.new_operation_name = ctk.CTkEntry(
            name_row, width=220, 
            placeholder_text="e.g., ROI1_plus_ROI2",
            font=ctk.CTkFont(size=11)
        )
        self.new_operation_name.pack(side="left", padx=5, fill="x", expand=True)
        
        # Expression input row
        expr_row = ctk.CTkFrame(input_container)
        expr_row.pack(fill="x", padx=5, pady=3)
        
        ctk.CTkLabel(expr_row, text="Expression:", width=80,
                    font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.new_operation_expr = ctk.CTkEntry(
            expr_row, width=220,
            placeholder_text="e.g., A + B, (A + B) / 2, A * 2",
            font=ctk.CTkFont(size=11)
        )
        self.new_operation_expr.pack(side="left", padx=5, fill="x", expand=True)
        
        # Variables section with compact grid layout
        var_section = ctk.CTkFrame(input_container)
        var_section.pack(fill="x", padx=5, pady=3)
        
        ctk.CTkLabel(var_section, text="Variables:", width=80,
                    font=ctk.CTkFont(weight="bold")).pack(side="left", anchor="n")
        
        # Variable assignment frame
        self.var_assignment_frame = ctk.CTkFrame(var_section)
        self.var_assignment_frame.pack(side="left", fill="x", expand=True, padx=5)
        
        self._create_variable_assignments()
        
        # Create operation button - more prominent
        create_btn_frame = ctk.CTkFrame(input_container)
        create_btn_frame.pack(fill="x", padx=5, pady=8)
        
        create_btn = ctk.CTkButton(
            create_btn_frame, 
            text="➕ Create Operation", 
            width=300, height=40, 
            fg_color="green", hover_color="darkgreen",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._create_mathematical_operation
        )
        create_btn.pack(pady=5)
        
        # Separator line
        separator = ctk.CTkFrame(operations_scroll, height=3, fg_color="gray")
        separator.pack(fill="x", padx=10, pady=10)
        
        # EXISTING OPERATIONS SECTION
        existing_frame = ctk.CTkFrame(operations_scroll)
        existing_frame.pack(fill="x", padx=3, pady=5)
        
        # Section header for existing operations
        existing_header = ctk.CTkFrame(existing_frame, fg_color="transparent")
        existing_header.pack(fill="x", padx=5, pady=(8, 5))
        
        ctk.CTkLabel(existing_header, text="📋 Existing Operations:",
                    font=ctk.CTkFont(weight="bold", size=13)).pack(side="left")
        
        # Count display
        count_text = f"{len(self.mathematical_operations)} operations" if hasattr(self, 'mathematical_operations') else "0 operations"
        ctk.CTkLabel(existing_header, text=count_text,
                    font=ctk.CTkFont(size=11), text_color="gray").pack(side="right")
        
        # Operations list with GUARANTEED space for buttons
        self.operations_list_frame = ctk.CTkScrollableFrame(existing_frame, height=250)
        self.operations_list_frame.pack(fill="x", padx=5, pady=5)
        
        # Refresh the operations list
        self._refresh_operations_list()
        
        # Add usage instructions at bottom
        instructions_frame = ctk.CTkFrame(operations_scroll)
        instructions_frame.pack(fill="x", padx=3, pady=5)
        
        ctk.CTkLabel(instructions_frame, text="💡 Usage Tips:",
                    font=ctk.CTkFont(weight="bold", size=12)).pack(anchor="w", padx=5, pady=(5, 2))
        
        tips_text = """• Use variables A, B, C, D to reference ROI traces
    • Supported operations: +, -, *, /, **, abs(), sqrt(), log()
    • Example: (A + B) / 2 calculates average of two ROIs
    • Use "Show" checkbox to toggle visibility in plot
    • Mathematical operations appear as colored traces"""
        
        ctk.CTkLabel(instructions_frame, text=tips_text,
                    font=ctk.CTkFont(size=10), 
                    justify="left").pack(anchor="w", padx=15, pady=(0, 8))

    def _create_variable_assignments(self):
        """Create variable assignment dropdowns - COMPACT LAYOUT"""
        for widget in self.var_assignment_frame.winfo_children():
            widget.destroy()
        
        available_traces = list(self.trace_custom.keys()) if hasattr(self, 'trace_custom') else []
        if not available_traces:
            ctk.CTkLabel(self.var_assignment_frame, text="No traces available").pack()
            return
        
        self.variable_dropdowns = {}
        variables = ['A', 'B', 'C', 'D']
        
        # Create 2x2 grid for variables
        for i, var in enumerate(variables):
            row = i // 2
            col = i % 2
            
            if col == 0:
                var_row = ctk.CTkFrame(self.var_assignment_frame)
                var_row.pack(fill="x", pady=1)
            
            var_container = ctk.CTkFrame(var_row)
            var_container.pack(side="left", padx=2, fill="x", expand=True)
            
            ctk.CTkLabel(var_container, text=f"{var}=", width=20).pack(side="left")
            
            dropdown = ctk.CTkComboBox(var_container, values=["None"] + available_traces, width=90)
            dropdown.set("None")
            dropdown.pack(side="left", padx=2)
            
            self.variable_dropdowns[var] = dropdown

    def _create_variable_assignments(self):
        """Create variable assignment dropdowns"""
        for widget in self.var_assignment_frame.winfo_children():
            widget.destroy()
        
        available_traces = list(self.trace_custom.keys()) if hasattr(self, 'trace_custom') else []
        if not available_traces:
            ctk.CTkLabel(self.var_assignment_frame, text="No traces available").pack()
            return
        
        self.variable_dropdowns = {}
        variables = ['A', 'B', 'C', 'D']
        
        for i, var in enumerate(variables):
            var_row = ctk.CTkFrame(self.var_assignment_frame)
            var_row.pack(fill="x", pady=1)
            
            ctk.CTkLabel(var_row, text=f"{var} =", width=30).pack(side="left")
            
            dropdown = ctk.CTkComboBox(var_row, values=["None"] + available_traces, width=120)
            dropdown.set("None")
            dropdown.pack(side="left", padx=5)
            
            self.variable_dropdowns[var] = dropdown

    def _show_expression_help(self):
        """Show help dialog for expression syntax"""
        help_text = """Mathematical Expression Help:

    OPERATORS:
    + : Addition (A + B, A + 5)
    - : Subtraction (A - B, A - 2) 
    * : Multiplication (A * B, A * 0.5)
    / : Division (A / B, A / 2)
    ** : Power (A ** 2, A ** 0.5)

    FUNCTIONS:
    abs(A) : Absolute value
    sqrt(A) : Square root  
    log(A) : Natural logarithm
    log10(A) : Base-10 logarithm
    sin(A), cos(A), tan(A) : Trigonometric functions
    exp(A) : Exponential function

    EXAMPLES:
    - A + B : Add two traces
    - A * 2 : Multiply trace by constant
    - (A + B) / 2 : Average of two traces
    - A - B : Difference between traces
    - sqrt(A**2 + B**2) : Euclidean combination
    - abs(A - B) : Absolute difference

    VARIABLES:
    Assign traces to variables A, B, C, D using dropdowns below.
    Constants can be used directly in expressions.
    """
        
        messagebox.showinfo("Expression Syntax Help", help_text)

    def _create_mathematical_operation(self):
        """Create a new mathematical operation"""
        try:
            name = self.new_operation_name.get().strip()
            expression = self.new_operation_expr.get().strip()
            
            if not name or not expression:
                messagebox.showwarning("Input Required", "Please enter both name and expression")
                return
            
            if name in self.mathematical_operations or name in self.trace_custom:
                messagebox.showwarning("Name Exists", "Operation name already exists. Please choose a different name.")
                return
            
            variables = {}
            for var, dropdown in self.variable_dropdowns.items():
                selected = dropdown.get()
                if selected != "None":
                    variables[var] = selected
            
            if not variables:
                messagebox.showwarning("Variables Required", "Please assign at least one variable to a trace")
                return
            
            expr_variables = set(re.findall(r'\b[A-D]\b', expression))
            assigned_variables = set(variables.keys())
            
            undefined_vars = expr_variables - assigned_variables
            if undefined_vars:
                messagebox.showwarning("Undefined Variables", 
                                    f"Expression uses undefined variables: {', '.join(undefined_vars)}\n"
                                    f"Please assign traces to these variables.")
                return
            
            result_data = self._calculate_mathematical_operation(expression, variables)
            if result_data is None:
                return
            
            self.mathematical_operations[name] = {
                'expression': expression,
                'variables': variables.copy(),
                'data': result_data,
                'visible': True
            }
            
            default_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
            color_idx = len(self.trace_custom) % len(default_colors)
            
            self.trace_custom[name] = {
                'color': default_colors[color_idx],
                'label': name,
                'visible': True,
                'linewidth': 2.0,
                'linestyle': '-',
                'marker': 's',
                'markersize': 6
            }
            
            self.plot_data[name] = result_data
            
            self.new_operation_name.delete(0, 'end')
            self.new_operation_expr.delete(0, 'end')
            for dropdown in self.variable_dropdowns.values():
                dropdown.set("None")
            
            self._refresh_operations_list()
            self._create_individual_traces_section()
            
            messagebox.showinfo("Success", f"Mathematical operation '{name}' created successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create operation: {str(e)}")

    def _calculate_mathematical_operation(self, expression, variables):
        """Calculate mathematical operation on traces"""
        try:
            import numpy as np
            import math
            
            trace_data = {}
            all_frames = set()
            
            for var, trace_name in variables.items():
                if trace_name in self.plot_data:
                    data = self.plot_data[trace_name]
                    trace_data[var] = {
                        'frames': data['frame_numbers'],
                        'values': data['averages']
                    }
                    all_frames.update(data['frame_numbers'])
            
            if not trace_data:
                messagebox.showerror("Error", "No valid trace data found for variables")
                return None
            
            common_frames = set(trace_data[list(trace_data.keys())[0]]['frames'])
            for var_data in trace_data.values():
                common_frames &= set(var_data['frames'])
            
            if not common_frames:
                messagebox.showerror("Error", "No common frames found between selected traces")
                return None
            
            common_frames = sorted(common_frames)
            result_frames = []
            result_values = []
            
            for frame in common_frames:
                try:
                    frame_values = {}
                    for var, data in trace_data.items():
                        if frame in data['frames']:
                            idx = data['frames'].index(frame)
                            frame_values[var] = data['values'][idx]
                    
                    if len(frame_values) != len(variables):
                        continue
                    
                    safe_dict = {
                        '__builtins__': {},
                        'abs': abs,
                        'sqrt': math.sqrt,
                        'log': math.log,
                        'log10': math.log10,
                        'sin': math.sin,
                        'cos': math.cos,
                        'tan': math.tan,
                        'exp': math.exp,
                        'pi': math.pi,
                        'e': math.e,
                        **frame_values
                    }
                    
                    result = eval(expression, safe_dict)
                    
                    if math.isnan(result) or math.isinf(result):
                        continue
                    
                    result_frames.append(frame)
                    result_values.append(float(result))
                    
                except Exception as e:
                    continue
            
            if not result_frames:
                messagebox.showerror("Error", "No valid results calculated. Check your expression and data.")
                return None
            
            return {
                'frame_numbers': result_frames,
                'averages': result_values
            }
            
        except Exception as e:
            messagebox.showerror("Error", f"Calculation failed: {str(e)}")
            return None

    def _refresh_operations_list(self):
        """Refresh the list of existing operations with FIXED button visibility"""
        for widget in self.operations_list_frame.winfo_children():
            widget.destroy()
        
        if not hasattr(self, 'mathematical_operations') or not self.mathematical_operations:
            ctk.CTkLabel(self.operations_list_frame, text="No operations created yet").pack(pady=5)
            return
        
        for name, operation in self.mathematical_operations.items():
            # Main operation container with fixed height
            op_frame = ctk.CTkFrame(self.operations_list_frame, height=80)
            op_frame.pack(fill="x", padx=2, pady=3)
            op_frame.pack_propagate(False)  # Maintain fixed height
            
            # Left side - Operation information
            info_frame = ctk.CTkFrame(op_frame)
            info_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
            
            # Operation name
            ctk.CTkLabel(info_frame, text=name, font=ctk.CTkFont(weight="bold", size=12)).pack(anchor="w", padx=5, pady=(2, 0))
            
            # Expression info
            ctk.CTkLabel(info_frame, text=f"Expression: {operation['expression']}", 
                        font=ctk.CTkFont(size=10)).pack(anchor="w", padx=5, pady=(0, 1))
            
            # Variables info
            var_info = ", ".join([f"{var}={trace}" for var, trace in operation['variables'].items()])
            ctk.CTkLabel(info_frame, text=f"Variables: {var_info}", 
                        font=ctk.CTkFont(size=9), text_color="gray").pack(anchor="w", padx=5, pady=(0, 2))
            
            # Right side - Control buttons with fixed width
            btn_frame = ctk.CTkFrame(op_frame, width=140)
            btn_frame.pack(side="right", fill="y", padx=5, pady=5)
            btn_frame.pack_propagate(False)  # Maintain fixed width
            
            # Show/Hide checkbox - LARGER and more visible
            visibility_var = tk.BooleanVar(value=operation.get('visible', True))
            visibility_cb = ctk.CTkCheckBox(
                btn_frame, 
                text="Show", 
                variable=visibility_var,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda n=name, v=visibility_var: self._toggle_operation_visibility(n, v),
                width=120,
                height=25
            )
            visibility_cb.pack(padx=5, pady=(5, 2), anchor="center")
            
            # Delete button - LARGER and more visible
            delete_btn = ctk.CTkButton(
                btn_frame, 
                text="Delete", 
                width=120,
                height=30,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="red",
                hover_color="darkred",
                command=lambda n=name: self._delete_operation(n)
            )
            delete_btn.pack(padx=5, pady=(2, 5), anchor="center")


    def _toggle_operation_visibility(self, operation_name, visibility_var):
        """Toggle visibility of a mathematical operation"""
        if operation_name in self.mathematical_operations:
            self.mathematical_operations[operation_name]['visible'] = visibility_var.get()
            if operation_name in self.trace_custom:
                self.trace_custom[operation_name]['visible'] = visibility_var.get()

    def _delete_operation(self, operation_name):
        """Delete a mathematical operation"""
        result = messagebox.askyesno("Delete Operation", 
                                    f"Are you sure you want to delete operation '{operation_name}'?")
        if result:
            if operation_name in self.mathematical_operations:
                del self.mathematical_operations[operation_name]
            if operation_name in self.trace_custom:
                del self.trace_custom[operation_name]
            if operation_name in self.plot_data:
                del self.plot_data[operation_name]
            if operation_name in self.trace_controls:
                del self.trace_controls[operation_name]
            
            self._refresh_operations_list()
            self._create_individual_traces_section()

    def _refresh_variable_assignments_if_exists(self):
        """Refresh variable assignments if the mathematical operations section exists"""
        if hasattr(self, 'variable_dropdowns') and hasattr(self, 'var_assignment_frame'):
            try:
                self._create_variable_assignments()
            except:
                pass

    def _plot_data(self):
        """Create the plot with current data - FIXED with proper average plotting and WORKING GRID SETTINGS"""
        try:
            # Get selected ROIs
            selected_rois = [roi_name for roi_name, var in self.roi_checkboxes.items() if var.get()]
            
            # ADD mathematical operations that are visible
            if hasattr(self, 'mathematical_operations'):
                for op_name, op_data in self.mathematical_operations.items():
                    if op_data.get('visible', True) and op_name in self.plot_data:
                        if op_name not in selected_rois:
                            selected_rois.append(op_name)
            
            if not selected_rois:
                messagebox.showwarning("No Selection", "Please select at least one ROI to plot")
                return
            
            plot_mode = self.plot_mode_var.get()
            
            # Update trace settings
            self._update_trace_settings()
            
            # COMPLETELY CLEAR AND RECREATE THE PLOT
            self.subplot.clear()
            
            plotted_count = 0
            
            # Plot individual ROIs (for separate and both modes)
            if plot_mode in ["separate", "both"]:
                for roi_name in selected_rois:
                    if roi_name not in self.plot_data:
                        continue
                    if not self.trace_custom[roi_name]['visible']:
                        continue
                        
                    data = self.plot_data[roi_name]
                    if not data['frame_numbers'] or not data['averages']:
                        continue
                    
                    settings = self.trace_custom[roi_name]
                    
                    self.subplot.plot(
                        data['frame_numbers'], data['averages'],
                        color=settings['color'],
                        label=settings['label'],
                        linewidth=settings['linewidth'],
                        linestyle=settings['linestyle'],
                        marker=settings['marker'] if settings['marker'] != 'none' else '',
                        markersize=settings['markersize'],
                        alpha=0.8
                    )
                    plotted_count += 1
            
            # Plot average of all selected ROIs (for average and both modes)
            if plot_mode in ["average", "both"]:
                # Calculate average across all selected ROIs
                avg_frame_numbers = []
                avg_values = []
                
                # Get all unique frame numbers from selected ROIs
                all_frames = set()
                for roi_name in selected_rois:
                    if roi_name in self.plot_data and self.plot_data[roi_name]['frame_numbers']:
                        all_frames.update(self.plot_data[roi_name]['frame_numbers'])
                
                all_frames = sorted(all_frames)
                
                # For each frame, calculate the average value across all selected ROIs
                for frame_num in all_frames:
                    frame_values = []
                    for roi_name in selected_rois:
                        if roi_name in self.plot_data:
                            data = self.plot_data[roi_name]
                            if frame_num in data['frame_numbers']:
                                idx = data['frame_numbers'].index(frame_num)
                                frame_values.append(data['averages'][idx])
                    
                    if frame_values:  # Only add if we have at least one value for this frame
                        avg_frame_numbers.append(frame_num)
                        avg_values.append(np.mean(frame_values))
                
                # Plot the average trace if we have data
                if avg_frame_numbers and avg_values:
                    # Use average trace settings if they exist
                    avg_settings = getattr(self, 'avg_trace_settings', {
                        'color': '#FF0000',  # Red for average
                        'linewidth': 3.0,
                        'linestyle': '-',
                        'marker': 'o',
                        'markersize': 8,
                        'visible': True
                    })
                    
                    if avg_settings.get('visible', True):
                        self.subplot.plot(
                            avg_frame_numbers, avg_values,
                            color=avg_settings['color'],
                            label=f'Average of {len(selected_rois)} ROIs',
                            linewidth=avg_settings['linewidth'],
                            linestyle=avg_settings['linestyle'],
                            marker=avg_settings['marker'] if avg_settings['marker'] != 'none' else '',
                            markersize=avg_settings['markersize'],
                            alpha=0.9
                        )
                        plotted_count += 1
            
            # Handle case where no data was plotted
            if plotted_count == 0:
                self.subplot.text(0.5, 0.5, 'No data to plot\nCheck ROI selection and visibility',
                                ha='center', va='center', fontsize=12)
                self.canvas.draw()
                return
            
            # Helper function to safely get numeric values from StringVar or DoubleVar
            def safe_get_numeric(var, default):
                try:
                    if hasattr(var, 'get'):
                        value = var.get()
                        if isinstance(value, str):
                            return float(value) if value.strip() != "" else default
                        return float(value)
                    return default
                except (ValueError, tk.TclError, AttributeError):
                    return default
            
            # Apply settings with safe numeric conversion
            title_font_size = safe_get_numeric(getattr(self, 'title_font_size_var', None), 16)
            axis_label_font_size = safe_get_numeric(getattr(self, 'axis_label_font_size_var', None), 12)
            axis_values_font_size = safe_get_numeric(getattr(self, 'axis_values_font_size_var', None), 10)
            legend_font_size = safe_get_numeric(getattr(self, 'legend_font_size_var', None), 10)
            
            # Set title and labels
            title_text = getattr(self, 'title_var', tk.StringVar(value="ROI vs Frame")).get() or "ROI vs Frame"
            xlabel_text = getattr(self, 'xlabel_var', tk.StringVar(value="Frame Number")).get() or "Frame Number"
            ylabel_text = getattr(self, 'ylabel_var', tk.StringVar(value="Average Value")).get() or "Average Value"
            
            self.subplot.set_title(title_text, fontsize=title_font_size, pad=20)
            self.subplot.set_xlabel(xlabel_text, fontsize=axis_label_font_size)
            self.subplot.set_ylabel(ylabel_text, fontsize=axis_label_font_size)
            
            # Apply axis settings
            if not getattr(self, 'auto_axis_var', tk.BooleanVar(value=True)).get():
                try:
                    xmin = safe_get_numeric(getattr(self, 'xmin_var', None), None)
                    xmax = safe_get_numeric(getattr(self, 'xmax_var', None), None)
                    ymin = safe_get_numeric(getattr(self, 'ymin_var', None), None)
                    ymax = safe_get_numeric(getattr(self, 'ymax_var', None), None)
                    
                    if xmin is not None and xmax is not None:
                        self.subplot.set_xlim(xmin, xmax)
                    if ymin is not None and ymax is not None:
                        self.subplot.set_ylim(ymin, ymax)
                except:
                    pass
            
            # NO CUSTOM TICK LOCATORS - Let matplotlib handle it automatically
            
            # Format axis values
            self.subplot.tick_params(axis='both', which='major', labelsize=axis_values_font_size)
            
            # Add legend
            if getattr(self, 'show_legend_var', tk.BooleanVar(value=True)).get():
                legend_location = getattr(self, 'legend_location_var', tk.StringVar(value='best')).get()
                self.subplot.legend(loc=legend_location, fontsize=legend_font_size)
            
            # FIXED GRID SETTINGS - Now uses the correct variables and slider values
            try:
                # Use the CORRECT variable names from the UI
                show_grid = getattr(self, 'grid_var', tk.BooleanVar(value=True))
                grid_alpha = getattr(self, 'grid_alpha_var', tk.DoubleVar(value=0.3))
                grid_width = getattr(self, 'grid_width_var', tk.DoubleVar(value=0.8))
                
                if show_grid.get():
                    # Apply grid with the USER-CONTROLLED alpha and linewidth settings
                    self.subplot.grid(
                        True, 
                        alpha=grid_alpha.get(),  # Use slider value
                        linewidth=grid_width.get()  # Use slider value
                    )
                else:
                    # Turn off grid completely
                    self.subplot.grid(False)
                    self.subplot.grid(False, which='minor')
            except Exception as e:
                print(f"Grid setting error: {e}")
                # Fallback - no grid
                self.subplot.grid(False)
            
            # Draw the plot
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            messagebox.showerror("Plot Error", f"Failed to create plot: {str(e)}")
            print(f"Plot error details: {e}")

    def _export_plot(self):
        """Export the plot"""
        if not self.plot_data:
            messagebox.showwarning("No Data", "Please create a plot first")
            return
            
        file_format = self.export_format_var.get()
        dpi = int(self.export_dpi_var.get())
        
        filename = filedialog.asksaveasfilename(
            title="Export Plot",
            defaultextension=f".{file_format}",
            filetypes=[(f"{file_format.upper()}", f"*.{file_format}")]
        )
        
        if filename:
            try:
                self.figure.savefig(filename, format=file_format, dpi=dpi, bbox_inches='tight')
                messagebox.showinfo("Export Success", f"Plot exported to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Error exporting plot:\n{str(e)}")

    def _export_data_csv(self):
        """Export data to CSV with comprehensive metadata"""
        if not self.plot_data:
            messagebox.showwarning("No Data", "No plot data available for export")
            return
            
        filename = filedialog.asksaveasfilename(
            title="Export Data to CSV", 
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                import csv
                
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Header with metadata
                    writer.writerow(['# PixelProbe ROI vs Frame Data Export'])
                    writer.writerow(['# Export timestamp:', datetime.now().isoformat()])
                    
                    # Plot settings metadata
                    if self.include_plot_settings_var.get():
                        writer.writerow(['# Plot Configuration:'])
                        writer.writerow(['# Title:', self.title_var.get()])
                        writer.writerow(['# X-Label:', self.xlabel_var.get()])
                        writer.writerow(['# Y-Label:', self.ylabel_var.get()])
                        writer.writerow(['# Grid enabled:', self.grid_var.get()])
                        writer.writerow(['# Legend location:', self.legend_location_var.get()])
                    
                    # Frame information
                    if self.include_frame_info_var.get():
                        writer.writerow(['# Frame Information:'])
                        writer.writerow(['# Total frames:', len(self.current_items)])
                        writer.writerow(['# Frame range:', f"{min(self.current_items)}-{max(self.current_items)}"])
                    
                    # ROI coordinates and pixel/area info
                    if self.include_roi_coords_var.get():
                        writer.writerow(['# ROI Information:'])
                        for roi in self.roi_selector.rois:
                            if roi.label in self.plot_data:
                                coords = roi.coordinates
                                roi_type = str(roi.roi_type).lower()
                                
                                if 'rectangle' in roi_type:
                                    x, y = int(coords['x']), int(coords['y'])
                                    w, h = int(coords['width']), int(coords['height'])
                                    area_pixels = w * h
                                    writer.writerow([f'# {roi.label} (Rectangle):'])
                                    writer.writerow(['#   Coordinates:', f"x={x}, y={y}, width={w}, height={h}"])
                                    writer.writerow(['#   Area:', f"{area_pixels} pixels"])
                                    writer.writerow(['#   Pixel count:', f"{w}×{h} = {area_pixels}"])
                                    writer.writerow(['#   Bounds:', f"({x},{y}) to ({x+w},{y+h})"])
                                    
                                elif 'point' in roi_type:
                                    x, y = int(coords['x']), int(coords['y'])
                                    writer.writerow([f'# {roi.label} (Point):'])
                                    writer.writerow(['#   Coordinates:', f"x={x}, y={y}"])
                                    writer.writerow(['#   Area:', "1 pixel"])
                                    writer.writerow(['#   Pixel count:', "1"])
                    
                    # Trace customization
                    if self.include_trace_settings_var.get():
                        writer.writerow(['# Trace Settings:'])
                        for roi_name, settings in self.trace_custom.items():
                            writer.writerow([f'# {roi_name}:', 
                                           f"Color: {settings.get('color', 'N/A')}", 
                                           f"LineWidth: {settings.get('linewidth', 'N/A')}", 
                                           f"Marker: {settings.get('marker', 'N/A')}"])
                    
                    writer.writerow([])  # Empty row
                    
                    # Data section
                    selected_rois = [roi_name for roi_name, var in self.roi_checkboxes.items() if var.get()]
                    
                    # Get all unique frame numbers
                    all_frames = set()
                    for roi_name in selected_rois:
                        if roi_name in self.plot_data:
                            all_frames.update(self.plot_data[roi_name]['frame_numbers'])
                    all_frames = sorted(all_frames)
                    
                    # Create header row
                    header = ['Frame_Number']
                    for roi_name in selected_rois:
                        if roi_name in self.plot_data:
                            header.append(f"{roi_name}_Average")
                    writer.writerow(header)
                    
                    # Write data rows
                    for frame_num in all_frames:
                        row = [frame_num]
                        for roi_name in selected_rois:
                            if roi_name in self.plot_data:
                                data = self.plot_data[roi_name]
                                try:
                                    frame_idx = data['frame_numbers'].index(frame_num)
                                    row.append(f"{data['averages'][frame_idx]:.6f}")
                                except ValueError:
                                    row.append('')  # Empty cell if no data for this frame
                            else:
                                row.append('')
                        writer.writerow(row)
                
                messagebox.showinfo("Export Success", f"Data with metadata exported to:\n{filename}")
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Could not export data:\n{str(e)}")

    def _export_data_json(self):
        """Export data to JSON with complete metadata"""
        if not self.plot_data:
            messagebox.showwarning("No Data", "No plot data available for export")
            return
            
        filename = filedialog.asksaveasfilename(
            title="Export Data to JSON", 
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                export_data = {
                    'export_info': {
                        'timestamp': datetime.now().isoformat(),
                        'pixelprobe_version': '1.0',
                        'export_type': 'roi_vs_frame_analysis'
                    },
                    'plot_data': self.plot_data
                }
                
                # Add optional metadata sections
                if self.include_plot_settings_var.get():
                    export_data['plot_settings'] = {
                        'title': self.title_var.get(),
                        'xlabel': self.xlabel_var.get(),
                        'ylabel': self.ylabel_var.get(),
                        'grid_enabled': self.grid_var.get(),
                        'legend_location': self.legend_location_var.get(),
                        'auto_axis': self.auto_axis_var.get()
                    }
                
                if self.include_frame_info_var.get():
                    export_data['frame_info'] = {
                        'total_frames': len(self.current_items),
                        'frame_numbers': self.current_items,
                        'frame_range': [min(self.current_items), max(self.current_items)]
                    }
                
                if self.include_roi_coords_var.get():
                    export_data['roi_information'] = {}
                    for roi in self.roi_selector.rois:
                        if roi.label in self.plot_data:
                            coords = roi.coordinates
                            roi_type = str(roi.roi_type).lower()
                            
                            roi_info = {
                                'type': roi_type,
                                'coordinates': coords
                            }
                            
                            if 'rectangle' in roi_type:
                                x, y = int(coords['x']), int(coords['y'])
                                w, h = int(coords['width']), int(coords['height'])
                                area_pixels = w * h
                                roi_info.update({
                                    'area_pixels': area_pixels,
                                    'pixel_count': f"{w}×{h}",
                                    'bounds': f"({x},{y}) to ({x+w},{y+h})",
                                    'dimensions': f"{w}×{h}"
                                })
                            elif 'point' in roi_type:
                                x, y = int(coords['x']), int(coords['y'])
                                roi_info.update({
                                    'area_pixels': 1,
                                    'pixel_count': "1",
                                    'location': f"({x},{y})"
                                })
                            
                            export_data['roi_information'][roi.label] = roi_info
                
                if self.include_trace_settings_var.get():
                    export_data['trace_customization'] = self.trace_custom
                
                with open(filename, 'w', encoding='utf-8') as jsonfile:
                    json.dump(export_data, jsonfile, indent=2, default=str)
                
                messagebox.showinfo("Export Success", f"JSON data with metadata exported to:\n{filename}")
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Could not export JSON:\n{str(e)}")

    def _on_dialog_close(self):
        """Handle dialog close"""
        if hasattr(self, 'canvas'):
            try:
                self.canvas.get_tk_widget().destroy()
            except:
                pass
        self.dialog.destroy()
    def _choose_color(self, roi_name):
        """Choose color for individual ROI trace"""
        current_color = self.trace_custom[roi_name]['color']
        color = colorchooser.askcolor(color=current_color, title=f"Color for {roi_name}")
        if color[1]:
            self.trace_custom[roi_name]['color'] = color[1]
            self.trace_controls[roi_name]['color_btn'].configure(fg_color=color[1])

    def _create_individual_traces_section(self):
        """Create individual trace customization including BOTH ROI traces AND mathematical operation traces"""
        # Clear existing traces section first
        for widget in self.control_scroll.winfo_children():
            if hasattr(widget, '_section_type') and widget._section_type == 'traces':
                widget.destroy()
        
        traces_frame = ctk.CTkFrame(self.control_scroll)
        traces_frame.pack(fill="x", padx=5, pady=5)
        traces_frame._section_type = 'traces'  # Mark for cleanup
        
        ctk.CTkLabel(traces_frame, text="🎨 Trace Customization", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        traces_scroll = ctk.CTkScrollableFrame(traces_frame, height=350)  # Increased height
        traces_scroll.pack(fill="x", padx=8, pady=5)
        
        # Initialize marker options
        marker_options = ['o', 's', '^', 'v', 'D', '*', '+', 'x', 'none']
        linestyle_options = ['-', '--', '-.', ':']
        
        # Count all available traces
        all_trace_names = []
        
        # Add regular ROI traces
        if self.roi_selector and self.roi_selector.rois:
            all_trace_names.extend([roi.label for roi in self.roi_selector.rois])
        
        # Add mathematical operation traces
        if hasattr(self, 'mathematical_operations'):
            all_trace_names.extend(list(self.mathematical_operations.keys()))
        
        if not all_trace_names:
            ctk.CTkLabel(traces_scroll, text="No traces available for customization").pack(pady=10)
            return
        
        # SECTION 1: REGULAR ROI TRACES
        if self.roi_selector and self.roi_selector.rois:
            roi_section = ctk.CTkFrame(traces_scroll)
            roi_section.pack(fill="x", padx=3, pady=5)
            
            ctk.CTkLabel(roi_section, text="📍 ROI Traces", 
                        font=ctk.CTkFont(weight="bold", size=13)).pack(pady=(8, 5))
            
            default_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
            default_markers = ['o', 's', '^', 'v', 'D', '*']
            
            for i, roi in enumerate(self.roi_selector.rois):
                roi_name = roi.label
                
                # Initialize defaults if not exists
                if roi_name not in self.trace_custom:
                    self.trace_custom[roi_name] = {
                        'color': default_colors[i % len(default_colors)],
                        'label': roi_name,
                        'visible': True,
                        'linewidth': 2.0,
                        'linestyle': '-',
                        'marker': default_markers[i % len(default_markers)],
                        'markersize': 6
                    }
                
                self._create_trace_control_row(roi_section, roi_name, "📍", marker_options, linestyle_options)
        
        # SECTION 2: MATHEMATICAL OPERATION TRACES
        if hasattr(self, 'mathematical_operations') and self.mathematical_operations:
            math_section = ctk.CTkFrame(traces_scroll)
            math_section.pack(fill="x", padx=3, pady=5)
            
            ctk.CTkLabel(math_section, text="🔢 Mathematical Operation Traces", 
                        font=ctk.CTkFont(weight="bold", size=13)).pack(pady=(8, 5))
            
            for op_name in self.mathematical_operations.keys():
                if op_name in self.trace_custom:  # Should already exist from creation
                    self._create_trace_control_row(math_section, op_name, "🔢", marker_options, linestyle_options)
        
        # SECTION 3: AVERAGE TRACE (if applicable)
        avg_section = ctk.CTkFrame(traces_scroll)
        avg_section.pack(fill="x", padx=3, pady=5)
        
        ctk.CTkLabel(avg_section, text="📈 Average Trace", 
                    font=ctk.CTkFont(weight="bold", size=13)).pack(pady=(8, 5))
        
        # Initialize average trace settings
        if not hasattr(self, 'avg_trace_settings'):
            self.avg_trace_settings = {
                'color': '#FF0000',  # Red for average
                'label': 'Average',
                'visible': True,
                'linewidth': 3.0,
                'linestyle': '-',
                'marker': 'o',
                'markersize': 8
            }
        
        self._create_average_trace_controls(avg_section, marker_options, linestyle_options)

    def _create_trace_control_row(self, parent_frame, trace_name, icon, marker_options, linestyle_options):
        """Create a complete trace control row for ANY trace (ROI or Mathematical Operation)"""
        trace_frame = ctk.CTkFrame(parent_frame)
        trace_frame.pack(fill="x", padx=5, pady=3)
        
        # ROW 1: Name, visibility, color, and TRACE NAME EDITOR
        name_row = ctk.CTkFrame(trace_frame)
        name_row.pack(fill="x", padx=3, pady=2)
        
        # Trace identifier with icon
        ctk.CTkLabel(name_row, text=f"{icon} {trace_name}", 
                    font=ctk.CTkFont(weight="bold", size=11), width=100).pack(side="left")
        
        # Visibility checkbox
        visible_var = tk.BooleanVar(value=self.trace_custom[trace_name]['visible'])
        ctk.CTkCheckBox(name_row, text="Show", variable=visible_var, width=50).pack(side="left", padx=2)
        
        # Color button
        color_btn = ctk.CTkButton(
            name_row, text="Color", width=60, height=25,
            fg_color=self.trace_custom[trace_name]['color'],
            command=lambda tn=trace_name: self._choose_color(tn)
        )
        color_btn.pack(side="left", padx=3)
        
        # ROW 2: TRACE NAME EDITOR (NEW!)
        label_row = ctk.CTkFrame(trace_frame)
        label_row.pack(fill="x", padx=3, pady=2)
        
        ctk.CTkLabel(label_row, text="Trace Name:", width=80, 
                    font=ctk.CTkFont(size=10)).pack(side="left", padx=2)
        
        # Label entry field - This is what was missing!
        label_var = tk.StringVar(value=self.trace_custom[trace_name]['label'])
        label_entry = ctk.CTkEntry(label_row, textvariable=label_var, width=150, height=25)
        label_entry.pack(side="left", padx=3, fill="x", expand=True)
        
        # ROW 3: Line properties
        props_row = ctk.CTkFrame(trace_frame)
        props_row.pack(fill="x", padx=3, pady=2)
        
        # Line width
        ctk.CTkLabel(props_row, text="Width:", width=45).pack(side="left")
        linewidth_var = tk.DoubleVar(value=self.trace_custom[trace_name]['linewidth'])
        ctk.CTkSlider(props_row, from_=0.5, to=5.0, variable=linewidth_var, width=70).pack(side="left", padx=2)
        
        # Marker size  
        ctk.CTkLabel(props_row, text="Size:", width=35).pack(side="left")
        markersize_var = tk.DoubleVar(value=self.trace_custom[trace_name]['markersize'])
        ctk.CTkSlider(props_row, from_=2, to=12, variable=markersize_var, width=70).pack(side="left", padx=2)
        
        # ROW 4: Style and marker
        style_row = ctk.CTkFrame(trace_frame)
        style_row.pack(fill="x", padx=3, pady=2)
        
        # Line style
        ctk.CTkLabel(style_row, text="Style:", width=45).pack(side="left")
        linestyle_var = tk.StringVar(value=self.trace_custom[trace_name]['linestyle'])
        ctk.CTkComboBox(style_row, values=linestyle_options, 
                        variable=linestyle_var, width=60).pack(side="left", padx=2)
        
        # Marker
        ctk.CTkLabel(style_row, text="Marker:", width=50).pack(side="left")
        marker_var = tk.StringVar(value=self.trace_custom[trace_name]['marker'])
        ctk.CTkComboBox(style_row, values=marker_options,
                        variable=marker_var, width=60).pack(side="left", padx=2)
        
        # Store controls for this trace (including the label_var!)
        self.trace_controls[trace_name] = {
            'visible_var': visible_var,
            'color_btn': color_btn,
            'label_var': label_var,  # This ensures the label changes are captured
            'linewidth_var': linewidth_var,
            'linestyle_var': linestyle_var,
            'marker_var': marker_var,
            'markersize_var': markersize_var
        }

    def _create_average_trace_controls(self, parent_frame, marker_options, linestyle_options):
        """Create average trace controls with trace name editing"""
        avg_trace_frame = ctk.CTkFrame(parent_frame)
        avg_trace_frame.pack(fill="x", padx=5, pady=3)
        
        # ROW 1: Identity, visibility, and color
        avg_name_row = ctk.CTkFrame(avg_trace_frame)
        avg_name_row.pack(fill="x", padx=3, pady=2)
        
        ctk.CTkLabel(avg_name_row, text="📈 Average Trace", 
                    font=ctk.CTkFont(weight="bold", size=11), width=100).pack(side="left")
        
        avg_visible_var = tk.BooleanVar(value=self.avg_trace_settings['visible'])
        ctk.CTkCheckBox(avg_name_row, text="Show", variable=avg_visible_var, width=50).pack(side="left", padx=2)
        
        avg_color_btn = ctk.CTkButton(avg_name_row, text="Color", width=60, height=25,
                                    fg_color=self.avg_trace_settings['color'],
                                    command=self._choose_avg_color)
        avg_color_btn.pack(side="left", padx=3)
        
        # ROW 2: TRACE NAME EDITOR FOR AVERAGE (NEW!)
        avg_label_row = ctk.CTkFrame(avg_trace_frame)
        avg_label_row.pack(fill="x", padx=3, pady=2)
        
        ctk.CTkLabel(avg_label_row, text="Trace Name:", width=80,
                    font=ctk.CTkFont(size=10)).pack(side="left", padx=2)
        
        # Average trace label entry field
        avg_label_var = tk.StringVar(value=self.avg_trace_settings['label'])
        avg_label_entry = ctk.CTkEntry(avg_label_row, textvariable=avg_label_var, width=150, height=25)
        avg_label_entry.pack(side="left", padx=3, fill="x", expand=True)
        
        # ROW 3: Line properties
        avg_props_row = ctk.CTkFrame(avg_trace_frame)
        avg_props_row.pack(fill="x", padx=3, pady=2)
        
        # Line width
        ctk.CTkLabel(avg_props_row, text="Width:", width=45).pack(side="left")
        avg_linewidth_var = tk.DoubleVar(value=self.avg_trace_settings['linewidth'])
        ctk.CTkSlider(avg_props_row, from_=0.5, to=5.0, variable=avg_linewidth_var, width=70).pack(side="left", padx=2)
        
        # Marker size
        ctk.CTkLabel(avg_props_row, text="Size:", width=35).pack(side="left")
        avg_markersize_var = tk.DoubleVar(value=self.avg_trace_settings['markersize'])
        ctk.CTkSlider(avg_props_row, from_=2, to=12, variable=avg_markersize_var, width=70).pack(side="left", padx=2)
        
        # ROW 4: Style and marker
        avg_style_row = ctk.CTkFrame(avg_trace_frame)
        avg_style_row.pack(fill="x", padx=3, pady=2)
        
        ctk.CTkLabel(avg_style_row, text="Style:", width=45).pack(side="left")
        avg_linestyle_var = tk.StringVar(value=self.avg_trace_settings['linestyle'])
        ctk.CTkComboBox(avg_style_row, values=linestyle_options,
                        variable=avg_linestyle_var, width=60).pack(side="left", padx=2)
        
        ctk.CTkLabel(avg_style_row, text="Marker:", width=50).pack(side="left")
        avg_marker_var = tk.StringVar(value=self.avg_trace_settings['marker'])
        ctk.CTkComboBox(avg_style_row, values=marker_options,
                        variable=avg_marker_var, width=60).pack(side="left", padx=2)
        
        # Store average trace controls (including label_var!)
        self.avg_trace_controls = {
            'visible_var': avg_visible_var,
            'color_btn': avg_color_btn,
            'label_var': avg_label_var,  # This ensures average trace name changes are captured
            'linewidth_var': avg_linewidth_var,
            'linestyle_var': avg_linestyle_var,
            'marker_var': avg_marker_var,
            'markersize_var': avg_markersize_var
        }

    def _choose_avg_color(self):
        """Choose color for average trace"""
        current_color = self.avg_trace_settings['color']
        color = colorchooser.askcolor(color=current_color, title="Color for Average Trace")
        if color[1]:
            self.avg_trace_settings['color'] = color[1]
            self.avg_trace_controls['color_btn'].configure(fg_color=color[1])


    def _update_trace_settings(self):
        """Update trace settings from UI - Enhanced for average traces"""
        # Update individual ROI trace settings
        for roi_name, controls in self.trace_controls.items():
            if roi_name in self.trace_custom:
                try:
                    self.trace_custom[roi_name]['visible'] = controls['visible_var'].get()
                    self.trace_custom[roi_name]['label'] = controls['label_var'].get()
                    self.trace_custom[roi_name]['linewidth'] = controls['linewidth_var'].get()
                    self.trace_custom[roi_name]['linestyle'] = controls['linestyle_var'].get()
                    self.trace_custom[roi_name]['marker'] = controls['marker_var'].get()
                    self.trace_custom[roi_name]['markersize'] = controls['markersize_var'].get()
                except Exception as e:
                    print(f"Error updating settings for {roi_name}: {e}")
        
        # Update average trace settings if they exist
        if hasattr(self, 'avg_trace_controls') and hasattr(self, 'avg_trace_settings'):
            try:
                self.avg_trace_settings['visible'] = self.avg_trace_controls['visible_var'].get()
                self.avg_trace_settings['label'] = self.avg_trace_controls['label_var'].get()
                self.avg_trace_settings['linewidth'] = self.avg_trace_controls['linewidth_var'].get()
                self.avg_trace_settings['linestyle'] = self.avg_trace_controls['linestyle_var'].get()
                self.avg_trace_settings['marker'] = self.avg_trace_controls['marker_var'].get()
                self.avg_trace_settings['markersize'] = self.avg_trace_controls['markersize_var'].get()
            except Exception as e:
                print(f"Error updating average trace settings: {e}")

    def _toggle_axis_controls(self):
        """Toggle manual axis controls based on auto axis setting"""
        if self.auto_axis_var.get():
            # Disable manual controls
            for widget in self.manual_axis_frame.winfo_children():
                for child in widget.winfo_children():
                    if hasattr(child, 'configure'):
                        try:
                            child.configure(state="disabled")
                        except:
                            pass
        else:
            # Enable manual controls
            for widget in self.manual_axis_frame.winfo_children():
                for child in widget.winfo_children():
                    if hasattr(child, 'configure'):
                        try:
                            child.configure(state="normal")
                        except:
                            pass


def create_plotting_dialog(parent, array_handler, roi_selector, current_items):
    """Factory function to create plotting dialog"""
    dialog = ROIFramePlottingDialog(parent, array_handler, roi_selector, current_items)
    dialog.show()
    return dialog