"""
Advanced ROI vs Frame plotting dialog for PixelProbe - Complete Implementation
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import json
from pathlib import Path
import logging
from datetime import datetime


class ROIFramePlottingDialog:
    """Advanced plotting dialog with full customization support"""
    
    # ============================================================================
    # INITIALIZATION AND SETUP
    # ============================================================================
    
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
        self.selected_rois = {}
        
        # Plotting figure and canvas
        self.figure = None
        self.canvas = None
        self.subplot = None
        
        # Plot customization settings
        self.plot_settings = self._get_default_plot_settings()
        
        # Export settings
        self.export_settings = self._get_default_export_settings()
        
        # Manual axis controls (for enable/disable)
        self.manual_axis_controls = []
        
        # Trace customization - Initialize properly
        self.trace_custom = {}
        self.trace_controls = {}
        
        # UI control variables - Initialize to None, will be created in UI setup
        self.avg_visible_var = None
        self.avg_label_var = None
        self.avg_color_btn = None
        
    def show(self):
        """Show the plotting dialog"""
        if not self._validate_prerequisites():
            return
            
        self._create_dialog()
        self._create_widgets()
        self._populate_roi_list()
        self._calculate_initial_data()
        
    def _validate_prerequisites(self) -> bool:
        """Validate that we have the required data for plotting"""
        if not self.current_items or len(self.current_items) < 2:
            messagebox.showerror(
                "Insufficient Data", 
                "Please load at least 2 frames to create ROI vs Frame plots.\n\n"
                "Current frames loaded: " + str(len(self.current_items) if self.current_items else 0)
            )
            return False
            
        if not self.roi_selector or not self.roi_selector.rois:
            messagebox.showerror(
                "No ROIs Selected",
                "Please select at least one Region of Interest (ROI) before plotting.\n\n"
                "1. Enable ROI Mode\n"
                "2. Select Rectangle or Point ROI\n"
                "3. Draw ROI on the image"
            )
            return False
            
        return True
    
    def _get_default_plot_settings(self) -> Dict[str, Any]:
        """Default plot settings"""
        return {
            'title': 'ROI Average vs Frame Number', 'xlabel': 'Frame Number', 'ylabel': 'Average Pixel Value',
            'linewidth': 2.0, 'linestyle': '-', 'marker': 'o', 'markersize': 6,
            'grid': True, 'facecolor': 'white', 'font_family': 'Arial',
            'title_fontsize': 16, 'label_fontsize': 12, 'tick_fontsize': 10,
            'auto_axis': True, 'x_interval': 0, 'y_interval': 0,
            'x_min': 0, 'x_max': 100, 'y_min': 0, 'y_max': 100
        }
        
    def _get_default_export_settings(self) -> Dict[str, Any]:
        """Default export settings"""
        return {'format': 'png', 'dpi': 300}
    
    # ============================================================================
    # DIALOG CREATION AND UI SETUP
    # ============================================================================
    
    def _create_dialog(self):
        """Create the main dialog window"""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("PixelProbe - ROI vs Frame Analysis & Plotting")
        
        self.dialog.geometry("1400x900")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center window
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (1400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (900 // 2)
        self.dialog.geometry(f"1400x900+{x}+{y}")
        
        # Configure grid weights for responsive design
        self.dialog.grid_columnconfigure(1, weight=1)
        self.dialog.grid_rowconfigure(0, weight=1)
        
        self.dialog.minsize(1200, 750)
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_dialog_close)
        
    def _create_widgets(self):
        """Create all dialog widgets"""
        self._create_control_panel()
        self._create_plot_area()
        
    def _create_control_panel(self):
        """Create control panel with proper scrolling"""
        self.main_control_scroll = ctk.CTkScrollableFrame(
            self.dialog, 
            width=360,
            label_text="Analysis Controls"
        )
        self.main_control_scroll.grid(row=0, column=0, sticky="nsew", padx=(15, 8), pady=15)
        
        # Title
        title_label = ctk.CTkLabel(
            self.main_control_scroll,
            text="ROI vs Frame Plotting",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(10, 15))
        
        # Create control sections in logical order
        self._create_roi_selection_section()
        self._create_quick_actions_section()
        self._create_plot_customization_section()
        self._create_export_section()
        
    def _create_plot_area(self):
        """Create plot area"""
        plot_frame = ctk.CTkFrame(self.dialog)
        plot_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 15), pady=15)
        plot_frame.grid_columnconfigure(0, weight=1)
        plot_frame.grid_rowconfigure(1, weight=1)
        
        # Plot title
        plot_title = ctk.CTkLabel(plot_frame, text="ROI Average vs Frame Number",
                                 font=ctk.CTkFont(size=16, weight="bold"))
        plot_title.grid(row=0, column=0, pady=(15, 10), sticky="ew")
        
        # Matplotlib figure
        self.figure = Figure(figsize=(9, 7), dpi=100)
        self.subplot = self.figure.add_subplot(111)
        
        # Canvas
        self.canvas = FigureCanvasTkAgg(self.figure, plot_frame)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        
        # Initial plot
        self._show_empty_plot()
    
    # ============================================================================
    # CONTROL PANEL SECTIONS
    # ============================================================================
    
    def _create_roi_selection_section(self):
        """Create ROI selection with better organization"""
        roi_frame = ctk.CTkFrame(self.main_control_scroll)
        roi_frame.pack(fill="x", padx=10, pady=(0, 8))
        
        ctk.CTkLabel(roi_frame, text="ROI Selection", 
                    font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(8, 5))
        
        # Bulk selection buttons with info
        buttons_frame = ctk.CTkFrame(roi_frame)
        buttons_frame.pack(fill="x", padx=8, pady=3)
        
        ctk.CTkButton(buttons_frame, text="All", command=self._select_all_rois, 
                     width=80, height=28, font=ctk.CTkFont(size=10)).pack(side="left", padx=(5, 2))
        ctk.CTkButton(buttons_frame, text="Clear", command=self._clear_all_rois,
                     width=80, height=28, font=ctk.CTkFont(size=10)).pack(side="left", padx=(2, 5))
        
        # ROI count info
        roi_count = len(self.roi_selector.rois) if self.roi_selector else 0
        ctk.CTkLabel(buttons_frame, text=f"{roi_count} ROIs available", 
                    font=ctk.CTkFont(size=9), text_color="gray60").pack(side="right", padx=5)
        
        # ROI list
        self.roi_scroll_frame = ctk.CTkScrollableFrame(roi_frame, height=80)
        self.roi_scroll_frame.pack(fill="both", expand=True, padx=8, pady=(3, 8))
        
        self.roi_checkboxes = {}
        
    def _create_quick_actions_section(self):
        """Create quick action buttons with plotting mode selection"""
        action_frame = ctk.CTkFrame(self.main_control_scroll)
        action_frame.pack(fill="x", padx=10, pady=(0, 8))
        
        ctk.CTkLabel(action_frame, text="Quick Actions", 
                    font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(8, 5))
        
        # Plotting mode selection
        mode_frame = ctk.CTkFrame(action_frame)
        mode_frame.pack(fill="x", padx=8, pady=(0, 5))
        
        ctk.CTkLabel(mode_frame, text="Plot Mode:", 
                    font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=5, pady=2)
        
        self.plot_mode_var = tk.StringVar(value="separate")
        
        # Radio buttons for plot mode
        modes_container = ctk.CTkFrame(mode_frame)
        modes_container.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkRadioButton(modes_container, text="Individual ROIs", 
                          variable=self.plot_mode_var, value="separate",
                          font=ctk.CTkFont(size=10)).pack(anchor="w", padx=5, pady=1)
        ctk.CTkRadioButton(modes_container, text="Average Only", 
                          variable=self.plot_mode_var, value="average",
                          font=ctk.CTkFont(size=10)).pack(anchor="w", padx=5, pady=1)
        ctk.CTkRadioButton(modes_container, text="Both Individual + Average", 
                          variable=self.plot_mode_var, value="both",
                          font=ctk.CTkFont(size=10)).pack(anchor="w", padx=5, pady=1)
        
        # Action buttons
        actions_grid = ctk.CTkFrame(action_frame)
        actions_grid.pack(fill="x", padx=8, pady=(5, 8))
        
        ctk.CTkButton(actions_grid, text="Quick Plot", command=self._quick_plot,
                     font=ctk.CTkFont(size=11, weight="bold"), height=35,
                     width=200).pack(fill="x", pady=2)
        ctk.CTkButton(actions_grid, text="Calculate Data", command=self._calculate_plot_data,
                     height=32, font=ctk.CTkFont(size=10),
                     width=200).pack(fill="x", pady=2)
        
    def _create_plot_customization_section(self):
        """Create plot customization controls"""
        custom_frame = ctk.CTkFrame(self.main_control_scroll)
        custom_frame.pack(fill="x", padx=10, pady=(0, 8))
        
        ctk.CTkLabel(custom_frame, text="Plot Customization", 
                    font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(8, 5))
        
        # Create subsections
        self._create_basic_labels_section(custom_frame)
        self._create_trace_customization_section(custom_frame)
        self._create_line_marker_section(custom_frame)
        self._create_font_section(custom_frame)
        self._create_axis_section(custom_frame)
        self._create_appearance_section(custom_frame)
        
    def _create_export_section(self):
        """Create export section with properly sized buttons and organized layout"""
        export_frame = ctk.CTkFrame(self.main_control_scroll)
        export_frame.pack(fill="x", padx=10, pady=(8, 20))
        
        ctk.CTkLabel(export_frame, text="Export & Save", 
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="#2E7D32").pack(pady=(10, 8))
        
        # File Format
        format_frame = ctk.CTkFrame(export_frame)
        format_frame.pack(fill="x", padx=8, pady=4)
        
        ctk.CTkLabel(format_frame, text="File Format:", 
                    font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=5, pady=3)
        
        self.export_format_var = tk.StringVar(value=self.export_settings['format'])
        format_combo = ctk.CTkComboBox(
            format_frame, 
            values=['png', 'pdf', 'svg', 'jpg', 'eps', 'tiff', 'ps'],
            variable=self.export_format_var,
            width=250,
            height=32,
            font=ctk.CTkFont(size=11)
        )
        format_combo.pack(padx=5, pady=3, fill="x")
        
        # DPI/Quality Settings
        dpi_frame = ctk.CTkFrame(export_frame)
        dpi_frame.pack(fill="x", padx=8, pady=4)
        
        ctk.CTkLabel(dpi_frame, text="Quality (DPI):", 
                    font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=5, pady=3)
        
        self.export_dpi_var = tk.IntVar(value=self.export_settings['dpi'])
        dpi_combo = ctk.CTkComboBox(
            dpi_frame,
            values=['72', '150', '300', '600', '1200', '2400'],
            variable=self.export_dpi_var,
            width=250,
            height=32,
            font=ctk.CTkFont(size=11)
        )
        dpi_combo.pack(padx=5, pady=3, fill="x")
        
        # Quality help
        help_text = ctk.CTkLabel(
            dpi_frame,
            text="72: Web • 150: Screen • 300: Print • 600+: High Quality",
            font=ctk.CTkFont(size=9),
            text_color="gray60"
        )
        help_text.pack(anchor="w", padx=5, pady=(0, 5))
        
        # Metadata options in two columns
        metadata_frame = ctk.CTkFrame(export_frame)
        metadata_frame.pack(fill="x", padx=8, pady=4)
        
        ctk.CTkLabel(metadata_frame, text="Export Options:", 
                    font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=5, pady=3)
        
        checkbox_container = ctk.CTkFrame(metadata_frame)
        checkbox_container.pack(fill="x", padx=5, pady=3)
        
        left_col = ctk.CTkFrame(checkbox_container)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 2))
        
        right_col = ctk.CTkFrame(checkbox_container)
        right_col.pack(side="right", fill="both", expand=True, padx=(2, 0))
        
        # Checkbox options
        self.include_metadata_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(left_col, text="Include metadata", 
                       variable=self.include_metadata_var, font=ctk.CTkFont(size=9)).pack(anchor="w", padx=3, pady=1)
        
        self.include_timestamp_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(left_col, text="Include timestamp", 
                       variable=self.include_timestamp_var, font=ctk.CTkFont(size=9)).pack(anchor="w", padx=3, pady=1)
        
        self.include_roi_info_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(left_col, text="ROI coordinates", 
                       variable=self.include_roi_info_var, font=ctk.CTkFont(size=9)).pack(anchor="w", padx=3, pady=1)
        
        self.include_plot_settings_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(right_col, text="Plot settings", 
                       variable=self.include_plot_settings_var, font=ctk.CTkFont(size=9)).pack(anchor="w", padx=3, pady=1)
        
        self.transparent_bg_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(right_col, text="Transparent BG", 
                       variable=self.transparent_bg_var, font=ctk.CTkFont(size=9)).pack(anchor="w", padx=3, pady=1)
        
        self.tight_layout_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(right_col, text="Tight layout", 
                       variable=self.tight_layout_var, font=ctk.CTkFont(size=9)).pack(anchor="w", padx=3, pady=1)
        
        # Export buttons
        export_buttons = ctk.CTkFrame(export_frame)
        export_buttons.pack(fill="x", padx=8, pady=(8, 12))
        
        ctk.CTkButton(export_buttons, text="Export Plot", command=self._export_plot,
                     width=170, height=40, font=ctk.CTkFont(size=11, weight="bold"),
                     fg_color="#4CAF50", hover_color="#45a049").pack(side="left", padx=(5, 3))
        
        ctk.CTkButton(export_buttons, text="Export Data", command=self._export_data,
                     width=170, height=40, font=ctk.CTkFont(size=11, weight="bold"),
                     fg_color="#2196F3", hover_color="#1976D2").pack(side="right", padx=(3, 5))
    
    # ============================================================================
    # DETAILED CUSTOMIZATION SECTIONS
    # ============================================================================
    
    def _create_basic_labels_section(self, parent):
        """Create basic labels section"""
        basic_frame = ctk.CTkFrame(parent)
        basic_frame.pack(fill="x", padx=8, pady=3)
        
        ctk.CTkLabel(basic_frame, text="Labels", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(5, 3))
        
        for label, var_name, default in [
            ("Title:", "title_entry", self.plot_settings['title']),
            ("X-axis:", "xlabel_entry", self.plot_settings['xlabel']),
            ("Y-axis:", "ylabel_entry", self.plot_settings['ylabel'])
        ]:
            row = ctk.CTkFrame(basic_frame)
            row.pack(fill="x", padx=5, pady=2)
            ctk.CTkLabel(row, text=label, width=50, font=ctk.CTkFont(size=11)).pack(side="left", padx=(5, 5))
            entry = ctk.CTkEntry(row, font=ctk.CTkFont(size=10), height=28)
            entry.pack(side="right", fill="x", expand=True, padx=(5, 5))
            entry.insert(0, default)
            setattr(self, var_name, entry)
    
    def _create_trace_customization_section(self, parent):
        """Create trace customization section for individual ROI colors and labels"""
        if not hasattr(self, 'roi_selector') or not self.roi_selector or not self.roi_selector.rois:
            return
            
        trace_frame = ctk.CTkFrame(parent)
        trace_frame.pack(fill="x", padx=8, pady=3)
        
        ctk.CTkLabel(trace_frame, text="Individual Traces", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(5, 3))
        
        # Scrollable frame for trace customization
        traces_scroll = ctk.CTkScrollableFrame(trace_frame, height=120)
        traces_scroll.pack(fill="x", padx=5, pady=3)
        
        # Define default colors at the method level
        default_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                         '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        # Initialize trace customization data if not exists
        if not hasattr(self, 'trace_custom') or not self.trace_custom:
            self.trace_custom = {}
            
        # Create customization controls for each ROI
        if not hasattr(self, 'trace_controls'):
            self.trace_controls = {}
        
        for i, roi in enumerate(self.roi_selector.rois):
            roi_name = roi.label
            
            # Initialize defaults
            if roi_name not in self.trace_custom:
                self.trace_custom[roi_name] = {
                    'color': default_colors[i % len(default_colors)],
                    'label': roi_name,
                    'visible': True
                }
            
            # ROI customization row
            roi_row = ctk.CTkFrame(traces_scroll)
            roi_row.pack(fill="x", padx=2, pady=2)
            
            # Visibility checkbox
            visible_var = tk.BooleanVar(value=self.trace_custom[roi_name]['visible'])
            visible_check = ctk.CTkCheckBox(roi_row, text="", variable=visible_var, width=20)
            visible_check.pack(side="left", padx=(3, 5), pady=3)
            
            # Color button
            color_btn = ctk.CTkButton(
                roi_row, text="", width=25, height=25,
                fg_color=self.trace_custom[roi_name]['color'],
                hover_color=self.trace_custom[roi_name]['color'],
                command=lambda r=roi_name: self._choose_trace_color(r)
            )
            color_btn.pack(side="left", padx=(0, 5), pady=3)
            
            # Label entry
            label_var = tk.StringVar(value=self.trace_custom[roi_name]['label'])
            label_entry = ctk.CTkEntry(roi_row, textvariable=label_var, 
                                     font=ctk.CTkFont(size=9), height=25)
            label_entry.pack(side="left", fill="x", expand=True, padx=(0, 5), pady=3)
            
            # ROI type indicator - handle the case where roi_type might not have .name attribute
            try:
                if hasattr(roi.roi_type, 'name'):
                    roi_type_text = f"({roi.roi_type.name})"
                elif hasattr(roi.roi_type, 'value'):
                    roi_type_text = f"({roi.roi_type.value})"
                else:
                    roi_type_text = f"({str(roi.roi_type)})"
            except:
                roi_type_text = "(ROI)"
                
            roi_type_label = ctk.CTkLabel(roi_row, text=roi_type_text, 
                                        font=ctk.CTkFont(size=8), text_color="gray60", width=50)
            roi_type_label.pack(side="right", padx=(0, 3), pady=3)
            
            # Store controls
            self.trace_controls[roi_name] = {
                'visible_var': visible_var,
                'color_btn': color_btn,
                'label_var': label_var
            }
        
        # Average line customization
        avg_row = ctk.CTkFrame(traces_scroll)
        avg_row.pack(fill="x", padx=2, pady=2)
        
        # Initialize average settings
        if 'AVERAGE' not in self.trace_custom:
            self.trace_custom['AVERAGE'] = {
                'color': '#FF1744',
                'label': 'Average',
                'visible': True
            }
        
        ctk.CTkLabel(avg_row, text="Average Line:", font=ctk.CTkFont(size=10, weight="bold")).pack(side="left", padx=(5, 5), pady=3)
        
        # Average controls
        self.avg_visible_var = tk.BooleanVar(value=self.trace_custom['AVERAGE']['visible'])
        avg_check = ctk.CTkCheckBox(avg_row, text="", variable=self.avg_visible_var, width=20)
        avg_check.pack(side="left", padx=(0, 5), pady=3)
        
        self.avg_color_btn = ctk.CTkButton(
            avg_row, text="", width=25, height=25,
            fg_color=self.trace_custom['AVERAGE']['color'],
            hover_color=self.trace_custom['AVERAGE']['color'],
            command=lambda: self._choose_trace_color('AVERAGE')
        )
        self.avg_color_btn.pack(side="left", padx=(0, 5), pady=3)
        
        self.avg_label_var = tk.StringVar(value=self.trace_custom['AVERAGE']['label'])
        avg_entry = ctk.CTkEntry(avg_row, textvariable=self.avg_label_var, 
                               font=ctk.CTkFont(size=9), height=25)
        avg_entry.pack(side="left", fill="x", expand=True, padx=(0, 5), pady=3)
    
    def _create_line_marker_section(self, parent):
        """Create line & marker settings"""
        line_frame = ctk.CTkFrame(parent)
        line_frame.pack(fill="x", padx=8, pady=3)
        
        ctk.CTkLabel(line_frame, text="Line & Markers", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(5, 3))
        
        # Sliders
        self._create_readable_slider(line_frame, "Line Width:", "linewidth_var", 0.1, 15.0, 
                                    self.plot_settings['linewidth'], format_func=lambda x: f"{x:.1f}")
        
        self._create_readable_slider(line_frame, "Marker Size:", "markersize_var", 1, 50,
                                    self.plot_settings['markersize'], format_func=lambda x: f"{int(x)}")
        
        # Style dropdowns
        style_row = ctk.CTkFrame(line_frame)
        style_row.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(style_row, text="Line Style:", width=70, font=ctk.CTkFont(size=10)).pack(side="left", padx=(5, 5))
        self.linestyle_var = tk.StringVar(value=self.plot_settings['linestyle'])
        ctk.CTkComboBox(style_row, values=['-', '--', '-.', ':', 'None'], 
                       variable=self.linestyle_var, width=80, height=28, font=ctk.CTkFont(size=10)).pack(side="left", padx=3)
        
        ctk.CTkLabel(style_row, text="Marker:", font=ctk.CTkFont(size=10)).pack(side="left", padx=(10, 5))
        self.marker_var = tk.StringVar(value=self.plot_settings['marker'])
        ctk.CTkComboBox(style_row, values=['o', 's', '^', 'v', 'D', '*', '+', 'x', 'None'],
                       variable=self.marker_var, width=80, height=28, font=ctk.CTkFont(size=10)).pack(side="right", padx=(5, 5))
    
    def _create_font_section(self, parent):
        """Create font settings"""
        font_frame = ctk.CTkFrame(parent)
        font_frame.pack(fill="x", padx=8, pady=3)
        
        ctk.CTkLabel(font_frame, text="Font Settings", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(5, 3))
        
        # Font family
        family_row = ctk.CTkFrame(font_frame)
        family_row.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(family_row, text="Family:", width=50, font=ctk.CTkFont(size=10)).pack(side="left", padx=(5, 5))
        self.fontfamily_var = tk.StringVar(value=self.plot_settings['font_family'])
        ctk.CTkComboBox(family_row, values=['Arial', 'Times New Roman', 'Courier New', 'Helvetica', 'Verdana'],
                       variable=self.fontfamily_var, height=28, font=ctk.CTkFont(size=10)).pack(side="right", fill="x", expand=True, padx=(5, 5))
        
        # Font sizes
        self._create_readable_slider(font_frame, "Title Size:", "title_fontsize_var", 6, 48,
                                    self.plot_settings['title_fontsize'], format_func=int)
        
        self._create_readable_slider(font_frame, "Label Size:", "label_fontsize_var", 4, 36,
                                    self.plot_settings['label_fontsize'], format_func=int)
        
        self._create_readable_slider(font_frame, "Tick Size:", "tick_fontsize_var", 4, 32,
                                    self.plot_settings.get('tick_fontsize', 10), format_func=int)
    
    def _create_axis_section(self, parent):
        """Create axis settings"""
        axis_frame = ctk.CTkFrame(parent)
        axis_frame.pack(fill="x", padx=8, pady=3)
        
        ctk.CTkLabel(axis_frame, text="Axis Control", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(5, 3))
        
        # Toggle options
        mode_row = ctk.CTkFrame(axis_frame)
        mode_row.pack(fill="x", padx=5, pady=2)
        
        self.auto_axis_var = tk.BooleanVar(value=self.plot_settings['auto_axis'])
        ctk.CTkCheckBox(mode_row, text="Auto Axis", variable=self.auto_axis_var, 
                       command=self._on_axis_mode_change, font=ctk.CTkFont(size=10)).pack(side="left", padx=(5, 10))
        
        self.grid_var = tk.BooleanVar(value=self.plot_settings['grid'])
        ctk.CTkCheckBox(mode_row, text="Show Grid", variable=self.grid_var, font=ctk.CTkFont(size=10)).pack(side="right", padx=(10, 5))
        
        # Manual axis controls
        manual_frame = ctk.CTkFrame(axis_frame)
        manual_frame.pack(fill="x", padx=5, pady=3)
        
        # X axis
        x_frame = ctk.CTkFrame(manual_frame)
        x_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(x_frame, text="X Range:", width=60, font=ctk.CTkFont(size=10)).pack(side="left", padx=(5, 5))
        
        self.x_min_var = tk.DoubleVar(value=self.plot_settings['x_min'])
        x_min_entry = ctk.CTkEntry(x_frame, textvariable=self.x_min_var, width=60, height=26, font=ctk.CTkFont(size=9))
        x_min_entry.pack(side="left", padx=2)
        self.manual_axis_controls.append(x_min_entry)
        
        ctk.CTkLabel(x_frame, text="to", font=ctk.CTkFont(size=9)).pack(side="left", padx=3)
        self.x_max_var = tk.DoubleVar(value=self.plot_settings['x_max'])
        x_max_entry = ctk.CTkEntry(x_frame, textvariable=self.x_max_var, width=60, height=26, font=ctk.CTkFont(size=9))
        x_max_entry.pack(side="left", padx=2)
        self.manual_axis_controls.append(x_max_entry)
        
        ctk.CTkLabel(x_frame, text="Step:", font=ctk.CTkFont(size=9)).pack(side="left", padx=(8, 2))
        self.x_interval_var = tk.DoubleVar(value=self.plot_settings['x_interval'])
        x_int_entry = ctk.CTkEntry(x_frame, textvariable=self.x_interval_var, width=50, height=26, font=ctk.CTkFont(size=9))
        x_int_entry.pack(side="left", padx=2)
        self.manual_axis_controls.append(x_int_entry)
        
        # Y axis
        y_frame = ctk.CTkFrame(manual_frame)
        y_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(y_frame, text="Y Range:", width=60, font=ctk.CTkFont(size=10)).pack(side="left", padx=(5, 5))
        
        self.y_min_var = tk.DoubleVar(value=self.plot_settings['y_min'])
        y_min_entry = ctk.CTkEntry(y_frame, textvariable=self.y_min_var, width=60, height=26, font=ctk.CTkFont(size=9))
        y_min_entry.pack(side="left", padx=2)
        self.manual_axis_controls.append(y_min_entry)
        
        ctk.CTkLabel(y_frame, text="to", font=ctk.CTkFont(size=9)).pack(side="left", padx=3)
        self.y_max_var = tk.DoubleVar(value=self.plot_settings['y_max'])
        y_max_entry = ctk.CTkEntry(y_frame, textvariable=self.y_max_var, width=60, height=26, font=ctk.CTkFont(size=9))
        y_max_entry.pack(side="left", padx=2)
        self.manual_axis_controls.append(y_max_entry)
        
        ctk.CTkLabel(y_frame, text="Step:", font=ctk.CTkFont(size=9)).pack(side="left", padx=(8, 2))
        self.y_interval_var = tk.DoubleVar(value=self.plot_settings['y_interval'])
        y_int_entry = ctk.CTkEntry(y_frame, textvariable=self.y_interval_var, width=50, height=26, font=ctk.CTkFont(size=9))
        y_int_entry.pack(side="left", padx=2)
        self.manual_axis_controls.append(y_int_entry)
        
        # Initial state
        self._on_axis_mode_change()
    
    def _create_appearance_section(self, parent):
        """Create appearance settings"""
        appear_frame = ctk.CTkFrame(parent)
        appear_frame.pack(fill="x", padx=8, pady=3)
        
        ctk.CTkLabel(appear_frame, text="Appearance", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(5, 3))
        
        # Background color
        bg_row = ctk.CTkFrame(appear_frame)
        bg_row.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(bg_row, text="Background:", width=80, font=ctk.CTkFont(size=10)).pack(side="left", padx=(5, 5))
        
        self.bgcolor_var = tk.StringVar(value=self.plot_settings['facecolor'])
        ctk.CTkComboBox(bg_row, values=['white', 'lightgray', '#f0f0f0', 'black'],
                       variable=self.bgcolor_var, width=100, height=28, font=ctk.CTkFont(size=10)).pack(side="left", padx=3)
        ctk.CTkButton(bg_row, text="Custom Color", command=self._choose_background_color,
                     width=90, height=26, font=ctk.CTkFont(size=9)).pack(side="right", padx=(5, 5))
    
    def _create_readable_slider(self, parent, label, var_name, min_val, max_val, default_val, format_func=float):
        """Create a readable slider with proper fonts"""
        row = ctk.CTkFrame(parent)
        row.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(row, text=label, width=70, font=ctk.CTkFont(size=10)).pack(side="left", padx=(5, 5))
        
        var = tk.DoubleVar(value=default_val) if isinstance(default_val, float) else tk.IntVar(value=default_val)
        setattr(self, var_name, var)
        
        # Value label
        value_label = ctk.CTkLabel(row, text=str(format_func(default_val)), width=35, font=ctk.CTkFont(size=10))
        value_label.pack(side="right", padx=(5, 5))
        
        # Slider
        slider = ctk.CTkSlider(row, from_=min_val, to=max_val, variable=var, height=20,
                              command=lambda val: value_label.configure(text=str(format_func(float(val)))))
        slider.pack(side="right", fill="x", expand=True, padx=(5, 3))
    
    # ============================================================================
    # TRACE CUSTOMIZATION METHODS
    # ============================================================================
    
    def _choose_trace_color(self, roi_name):
        """Choose color for individual trace"""
        current_color = self.trace_custom.get(roi_name, {}).get('color', '#1f77b4')
        color = colorchooser.askcolor(color=current_color, title=f"Color for {roi_name}")
        if color[1]:  # If user selected a color
            if roi_name not in self.trace_custom:
                self.trace_custom[roi_name] = {}
            self.trace_custom[roi_name]['color'] = color[1]
            
            # Update button color
            if roi_name == 'AVERAGE':
                self.avg_color_btn.configure(fg_color=color[1], hover_color=color[1])
            elif roi_name in self.trace_controls:
                self.trace_controls[roi_name]['color_btn'].configure(
                    fg_color=color[1], hover_color=color[1]
                )

    def _update_trace_customization(self):
        """Update trace customization from UI controls"""
        try:
            # Ensure trace_custom exists
            if not hasattr(self, 'trace_custom'):
                self.trace_custom = {}
                
            # Update from trace controls if they exist
            if hasattr(self, 'trace_controls') and self.trace_controls:
                for roi_name, controls in self.trace_controls.items():
                    if roi_name not in self.trace_custom:
                        self.trace_custom[roi_name] = {}
                        
                    try:
                        self.trace_custom[roi_name]['visible'] = controls['visible_var'].get()
                        self.trace_custom[roi_name]['label'] = controls['label_var'].get()
                    except Exception as e:
                        self.logger.warning(f"Could not update trace customization for {roi_name}: {e}")
                        continue
            
            # Update average settings if they exist
            try:
                if hasattr(self, 'avg_visible_var') and self.avg_visible_var:
                    if 'AVERAGE' not in self.trace_custom:
                        self.trace_custom['AVERAGE'] = {}
                    self.trace_custom['AVERAGE']['visible'] = self.avg_visible_var.get()
            except Exception as e:
                self.logger.warning(f"Could not update average visibility: {e}")
                
            try:
                if hasattr(self, 'avg_label_var') and self.avg_label_var:
                    if 'AVERAGE' not in self.trace_custom:
                        self.trace_custom['AVERAGE'] = {}
                    self.trace_custom['AVERAGE']['label'] = self.avg_label_var.get()
            except Exception as e:
                self.logger.warning(f"Could not update average label: {e}")
                
        except Exception as e:
            self.logger.error(f"Error in _update_trace_customization: {e}")
            # Initialize with defaults if everything fails
            self.trace_custom = {}
    
    # ============================================================================
    # DATA CALCULATION AND PROCESSING
    # ============================================================================
    
    def _calculate_initial_data(self):
        """Calculate data for all ROIs"""
        self.plot_data = {}
        for roi in self.roi_selector.rois:
            roi_data = self._calculate_roi_data(roi)
            if roi_data is not None:
                self.plot_data[roi.label] = roi_data
                
    def _calculate_roi_data(self, roi) -> Optional[Dict]:
        """Calculate average values for a single ROI across all frames with detailed logging"""
        try:
            frame_numbers = []
            roi_averages = []
            
            self.logger.info(f"Calculating data for ROI '{roi.label}' ({roi.roi_type.name}) across {len(self.current_items)} frames")
            
            for i, frame_num in enumerate(self.current_items):
                try:
                    array_data = self.array_handler.load_item(frame_num)
                    if array_data is None:
                        self.logger.warning(f"Could not load frame {frame_num}")
                        continue
                    
                    roi_avg = self._get_roi_average(roi, array_data)
                    if roi_avg is not None:
                        frame_numbers.append(frame_num)
                        roi_averages.append(roi_avg)
                        self.logger.debug(f"Frame {frame_num}: ROI {roi.label} = {roi_avg}")
                    else:
                        self.logger.warning(f"Could not calculate average for ROI {roi.label} in frame {frame_num}")
                        
                except Exception as e:
                    self.logger.error(f"Error processing frame {frame_num} for ROI {roi.label}: {e}")
                    continue
                    
            if len(frame_numbers) == 0:
                self.logger.warning(f"No valid data points found for ROI '{roi.label}'")
                return None
            
            self.logger.info(f"Successfully calculated {len(frame_numbers)} data points for ROI '{roi.label}' (values: {min(roi_averages):.2f} - {max(roi_averages):.2f})")
                
            return {
                'frame_numbers': frame_numbers,
                'averages': roi_averages,
                'roi_type': roi.roi_type.name,
                'roi_coordinates': roi.coordinates,
                'data_points': len(frame_numbers),
                'value_range': [float(min(roi_averages)), float(max(roi_averages))]
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating ROI data for {roi.label}: {e}")
            return None
    
    def _get_roi_average(self, roi, array_data) -> Optional[float]:
        """Get average value for ROI in given array - handles both points and rectangles"""
        try:
            if roi.roi_type.name == 'POINT':
                # Single pixel value
                x = int(round(roi.coordinates['x']))
                y = int(round(roi.coordinates['y']))
                
                # Bounds check
                if (0 <= x < array_data.shape[1] and 0 <= y < array_data.shape[0]):
                    pixel_value = array_data[y, x]
                    # Handle different data types
                    if len(array_data.shape) == 3:  # Color image
                        # For color images, use average of RGB channels
                        if array_data.shape[2] == 3:
                            pixel_value = float(np.mean(pixel_value))
                        elif array_data.shape[2] == 1:
                            pixel_value = float(pixel_value[0])
                        else:
                            pixel_value = float(pixel_value[0])  # Use first channel
                    else:
                        # Grayscale - single value
                        pixel_value = float(pixel_value)
                    
                    self.logger.debug(f"Point ROI {roi.label} at ({x},{y}): value = {pixel_value}")
                    return pixel_value
                else:
                    self.logger.warning(f"Point ROI {roi.label} at ({x},{y}) is out of bounds for image shape {array_data.shape}")
                    return None
                    
            elif roi.roi_type.name == 'RECTANGLE':
                # Rectangle region average
                x, y = int(roi.coordinates['x']), int(roi.coordinates['y'])
                width, height = int(roi.coordinates['width']), int(roi.coordinates['height'])
                
                # Bounds check and clipping
                x_end = min(x + width, array_data.shape[1])
                y_end = min(y + height, array_data.shape[0])
                x = max(0, x)
                y = max(0, y)
                
                if x < x_end and y < y_end:
                    region = array_data[y:y_end, x:x_end]
                    if len(region.shape) == 3:  # Color image
                        # Average across all pixels and channels
                        region_avg = float(np.mean(region))
                    else:
                        # Grayscale - average across all pixels
                        region_avg = float(np.mean(region))
                    
                    self.logger.debug(f"Rectangle ROI {roi.label} at ({x},{y}) size ({width}x{height}): avg = {region_avg}")
                    return region_avg
                else:
                    self.logger.warning(f"Rectangle ROI {roi.label} has no valid pixels")
                    return None
                    
            elif roi.roi_type.name == 'MULTI_POINT':
                # Multiple points - average their values
                values = []
                for point in roi.coordinates['points']:
                    x = int(round(point['x']))
                    y = int(round(point['y']))
                    if (0 <= x < array_data.shape[1] and 0 <= y < array_data.shape[0]):
                        pixel_value = array_data[y, x]
                        if len(array_data.shape) == 3:  # Color
                            if array_data.shape[2] == 3:
                                values.append(float(np.mean(pixel_value)))
                            else:
                                values.append(float(pixel_value[0]))
                        else:
                            values.append(float(pixel_value))
                
                if values:
                    multi_point_avg = float(np.mean(values))
                    self.logger.debug(f"Multi-point ROI {roi.label}: {len(values)} points, avg = {multi_point_avg}")
                    return multi_point_avg
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Error calculating ROI average for {roi.label}: {e}")
            return None
    
    def _calculate_roi_average(self, selected_rois) -> Optional[Dict]:
        """Calculate average across multiple ROIs for each frame"""
        try:
            # Get all frame numbers that appear in any ROI
            all_frames = set()
            for roi_name in selected_rois:
                if roi_name in self.plot_data:
                    all_frames.update(self.plot_data[roi_name]['frame_numbers'])
            
            if not all_frames:
                return None
            
            sorted_frames = sorted(all_frames)
            frame_averages = []
            
            for frame in sorted_frames:
                frame_values = []
                for roi_name in selected_rois:
                    if roi_name in self.plot_data:
                        data = self.plot_data[roi_name]
                        if frame in data['frame_numbers']:
                            idx = data['frame_numbers'].index(frame)
                            frame_values.append(data['averages'][idx])
                
                if frame_values:
                    frame_averages.append(np.mean(frame_values))
                else:
                    # Skip frames where no ROIs have data
                    sorted_frames.remove(frame)
            
            if not frame_averages:
                return None
            
            return {
                'frame_numbers': sorted_frames,
                'averages': frame_averages,
                'roi_type': 'AVERAGE',
                'roi_coordinates': f'Average of {len(selected_rois)} ROIs',
                'data_points': len(frame_averages),
                'value_range': [float(min(frame_averages)), float(max(frame_averages))]
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating ROI average: {e}")
            return None
    
    # ============================================================================
    # PLOTTING AND VISUALIZATION
    # ============================================================================
    
    def _create_plot(self):
        """Create the plot with proper mode support and trace customization"""
        try:
            selected_rois = [roi_name for roi_name, var in self.roi_checkboxes.items() if var.get()]
            
            if not selected_rois:
                messagebox.showwarning("No Selection", "Please select at least one ROI to plot")
                return
            
            plot_mode = self.plot_mode_var.get()
            self.logger.info(f"Creating plot for {len(selected_rois)} ROIs in '{plot_mode}' mode: {selected_rois}")
            
            # Update trace customization from UI
            self._update_trace_customization()
                
            self.subplot.clear()
            plt.style.use('default')
            self.subplot.set_facecolor(self.plot_settings['facecolor'])
            
            plotted_count = 0
            
            # Plot individual ROIs (for "separate" and "both" modes)
            if plot_mode in ["separate", "both"]:
                for roi_name in selected_rois:
                    if roi_name not in self.plot_data:
                        self.logger.warning(f"No plot data available for ROI '{roi_name}'")
                        continue
                    
                    # Check if this trace should be visible
                    if roi_name in self.trace_custom and not self.trace_custom[roi_name]['visible']:
                        continue
                        
                    data = self.plot_data[roi_name]
                    
                    # Verify data
                    if not data['frame_numbers'] or not data['averages']:
                        self.logger.warning(f"Empty data for ROI '{roi_name}'")
                        continue
                        
                    if len(data['frame_numbers']) != len(data['averages']):
                        self.logger.error(f"Data length mismatch for ROI '{roi_name}': {len(data['frame_numbers'])} frames vs {len(data['averages'])} values")
                        continue
                    
                    self.logger.info(f"Plotting individual ROI '{roi_name}': {len(data['frame_numbers'])} points, values {min(data['averages']):.2f}-{max(data['averages']):.2f}")
                    
                    # Use custom color and label if available
                    if roi_name in self.trace_custom:
                        color = self.trace_custom[roi_name]['color']
                        label = self.trace_custom[roi_name]['label']
                    else:
                        # Fallback colors
                        default_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
                        color = default_colors[plotted_count % len(default_colors)]
                        label = roi_name
                    
                    marker = self.plot_settings['marker'] if self.plot_settings['marker'] != 'None' else None
                    linestyle = self.plot_settings['linestyle'] if self.plot_settings['linestyle'] != 'None' else None
                    
                    # Plot individual ROI
                    self.subplot.plot(
                        data['frame_numbers'], data['averages'],
                        color=color, 
                        label=label,
                        linewidth=self.plot_settings['linewidth'],
                        linestyle=linestyle, marker=marker,
                        markersize=self.plot_settings['markersize'], alpha=0.8
                    )
                    
                    plotted_count += 1
            
            # Calculate and plot average (for "average" and "both" modes)
            if plot_mode in ["average", "both"]:
                # Check if average should be visible
                show_average = True
                if hasattr(self, 'avg_visible_var'):
                    show_average = self.avg_visible_var.get()
                    
                if show_average:
                    if len(selected_rois) > 1:
                        avg_data = self._calculate_roi_average(selected_rois)
                        if avg_data:
                            self.logger.info(f"Plotting average of {len(selected_rois)} ROIs: {len(avg_data['frame_numbers'])} points, values {min(avg_data['averages']):.2f}-{max(avg_data['averages']):.2f}")
                            
                            marker = self.plot_settings['marker'] if self.plot_settings['marker'] != 'None' else None
                            linestyle = self.plot_settings['linestyle'] if self.plot_settings['linestyle'] != 'None' else None
                            
                            # Use custom average settings
                            avg_color = self.trace_custom['AVERAGE']['color'] if 'AVERAGE' in self.trace_custom else '#FF1744'
                            avg_label = self.trace_custom['AVERAGE']['label'] if 'AVERAGE' in self.trace_custom else f"Average of {len(selected_rois)} ROIs"
                            avg_linewidth = self.plot_settings['linewidth'] * 1.5 if plot_mode == "both" else self.plot_settings['linewidth']
                            
                            self.subplot.plot(
                                avg_data['frame_numbers'], avg_data['averages'],
                                color=avg_color, 
                                label=avg_label,
                                linewidth=avg_linewidth,
                                linestyle=linestyle, marker=marker,
                                markersize=self.plot_settings['markersize'] * 1.2 if plot_mode == "both" else self.plot_settings['markersize'], 
                                alpha=0.9
                            )
                            
                            plotted_count += 1
                    elif len(selected_rois) == 1:
                        # Single ROI in average mode - plot it with average styling
                        roi_name = selected_rois[0]
                        if roi_name in self.plot_data:
                            data = self.plot_data[roi_name]
                            marker = self.plot_settings['marker'] if self.plot_settings['marker'] != 'None' else None
                            linestyle = self.plot_settings['linestyle'] if self.plot_settings['linestyle'] != 'None' else None
                            
                            # Use average color and custom label
                            avg_color = self.trace_custom['AVERAGE']['color'] if 'AVERAGE' in self.trace_custom else '#FF1744'
                            avg_label = self.trace_custom['AVERAGE']['label'] if 'AVERAGE' in self.trace_custom else roi_name
                            
                            self.subplot.plot(
                                data['frame_numbers'], data['averages'],
                                color=avg_color, 
                                label=avg_label,
                                linewidth=self.plot_settings['linewidth'],
                                linestyle=linestyle, marker=marker,
                                markersize=self.plot_settings['markersize'], alpha=0.8
                            )
                            plotted_count += 1
            
            if plotted_count == 0:
                self.logger.error("No valid data to plot!")
                messagebox.showerror("No Data", "No valid data found for the selected ROIs.\n\nPlease check that:\n1. ROIs are within image boundaries\n2. Array data is loading correctly\n3. ROI coordinates are valid\n4. At least one trace is set to visible")
                return
            
            self.logger.info(f"Successfully plotted {plotted_count} data series in '{plot_mode}' mode")
            
            # Apply formatting
            self.subplot.set_title(
                self.plot_settings['title'],
                fontsize=self.plot_settings['title_fontsize'],
                fontfamily=self.plot_settings['font_family'],
                fontweight='bold'
            )
            
            self.subplot.set_xlabel(
                self.plot_settings['xlabel'],
                fontsize=self.plot_settings['label_fontsize'],
                fontfamily=self.plot_settings['font_family']
            )
            
            self.subplot.set_ylabel(
                self.plot_settings['ylabel'],
                fontsize=self.plot_settings['label_fontsize'],
                fontfamily=self.plot_settings['font_family']
            )
            
            self.subplot.tick_params(axis='both', which='major', labelsize=self.plot_settings['tick_fontsize'])
            
            # Axis settings
            if not self.plot_settings['auto_axis']:
                self.subplot.set_xlim(self.plot_settings['x_min'], self.plot_settings['x_max'])
                self.subplot.set_ylim(self.plot_settings['y_min'], self.plot_settings['y_max'])
            
            if self.plot_settings['x_interval'] > 0:
                x_min, x_max = self.subplot.get_xlim()
                x_ticks = np.arange(
                    np.ceil(x_min / self.plot_settings['x_interval']) * self.plot_settings['x_interval'],
                    x_max + self.plot_settings['x_interval'], self.plot_settings['x_interval']
                )
                self.subplot.set_xticks(x_ticks)
                
            if self.plot_settings['y_interval'] > 0:
                y_min, y_max = self.subplot.get_ylim()
                y_ticks = np.arange(
                    np.floor(y_min / self.plot_settings['y_interval']) * self.plot_settings['y_interval'],
                    y_max + self.plot_settings['y_interval'], self.plot_settings['y_interval']
                )
                self.subplot.set_yticks(y_ticks)
            
            if self.plot_settings['grid']:
                self.subplot.grid(True, alpha=0.3)
            
            # Show legend if there are multiple traces or user wants it
            if plotted_count > 1:
                legend = self.subplot.legend(
                    fontsize=max(8, self.plot_settings['label_fontsize'] - 2), 
                    framealpha=0.9,
                    loc='best'
                )
                # Make average line stand out in legend if present
                if plot_mode in ["average", "both"]:
                    for text in legend.get_texts():
                        if hasattr(self, 'avg_label_var') and self.avg_label_var.get() in text.get_text():
                            text.set_weight('bold')
            elif plotted_count == 1:
                # Show legend even for single trace to show custom label
                self.subplot.legend(
                    fontsize=max(8, self.plot_settings['label_fontsize'] - 2), 
                    framealpha=0.9,
                    loc='best'
                )
                
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            self.logger.error(f"Error creating plot: {e}")
            messagebox.showerror("Plot Error", f"Error creating plot: {str(e)}")
    
    def _show_empty_plot(self):
        """Show empty plot with instructions"""
        self.subplot.clear()
        self.subplot.text(
            0.5, 0.5, 
            "[ROI vs Frame Analysis]\n\n"
            "1. Select ROIs from controls\n"
            "2. Click 'Quick Plot' to start\n"
            "3. Customize and export\n\n"
            "Ready to plot!",
            horizontalalignment='center',
            verticalalignment='center',
            fontsize=14,
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7)
        )
        self.subplot.set_xlim(0, 1)
        self.subplot.set_ylim(0, 1)
        self.subplot.axis('off')
        self.canvas.draw()
    
    # ============================================================================
    # USER INTERACTION AND UTILITY METHODS
    # ============================================================================
    
    def _populate_roi_list(self):
        """Populate compact but readable ROI list"""
        for widget in self.roi_scroll_frame.winfo_children():
            widget.destroy()
            
        self.roi_checkboxes = {}
        
        for roi in self.roi_selector.rois:
            row = ctk.CTkFrame(self.roi_scroll_frame)
            row.pack(fill="x", padx=2, pady=1)
            
            # Checkbox
            checkbox_var = tk.BooleanVar()
            checkbox = ctk.CTkCheckBox(row, text="", variable=checkbox_var, width=18)
            checkbox.pack(side="left", padx=(3, 5), pady=2)
            
            # ROI info - readable but compact
            if roi.roi_type.name == 'POINT':
                info = f"{roi.label} - Point ({int(roi.coordinates['x'])}, {int(roi.coordinates['y'])})"
            elif roi.roi_type.name == 'RECTANGLE':
                w, h = int(roi.coordinates['width']), int(roi.coordinates['height'])
                info = f"{roi.label} - Rect ({w} × {h} px)"
            else:
                info = f"{roi.label} - {roi.roi_type.name}"
                
            ctk.CTkLabel(row, text=info, font=ctk.CTkFont(size=9)).pack(side="left", padx=(0, 5), pady=2)
            self.roi_checkboxes[roi.label] = checkbox_var
    
    def _select_all_rois(self):
        """Select all ROI checkboxes"""
        for checkbox_var in self.roi_checkboxes.values():
            checkbox_var.set(True)
        
    def _clear_all_rois(self):
        """Clear all ROI checkboxes"""
        for checkbox_var in self.roi_checkboxes.values():
            checkbox_var.set(False)
    
    def _quick_plot(self):
        """Create a quick plot with debugging"""
        if not any(var.get() for var in self.roi_checkboxes.values()):
            self._select_all_rois()
            
        # Force recalculate data before plotting
        self.logger.info("Quick plot: Recalculating data before plotting")
        self._calculate_initial_data()
        
        # Update settings and create plot
        self._update_plot_from_settings()
        self._create_plot()
        
    def _calculate_plot_data(self):
        """Recalculate plot data"""
        self._calculate_initial_data()
        messagebox.showinfo("Data Calculated", "Plot data recalculated for all ROIs")
    
    def _on_axis_mode_change(self):
        """Handle axis mode change"""
        is_auto = self.auto_axis_var.get()
        
        # Enable/disable manual controls
        for control in self.manual_axis_controls:
            if is_auto:
                control.configure(state="disabled")
            else:
                control.configure(state="normal")
    
    def _choose_background_color(self):
        """Choose background color"""
        color = colorchooser.askcolor(color=self.plot_settings['facecolor'], title="Background Color")
        if color[1]:
            self.bgcolor_var.set(color[1])
            self.plot_settings['facecolor'] = color[1]
            
    def _update_plot_from_settings(self):
        """Update plot settings from UI controls"""
        self.plot_settings.update({
            'title': self.title_entry.get(),
            'xlabel': self.xlabel_entry.get(),
            'ylabel': self.ylabel_entry.get(),
            'linewidth': self.linewidth_var.get(),
            'linestyle': self.linestyle_var.get(),
            'marker': self.marker_var.get(),
            'markersize': self.markersize_var.get(),
            'grid': self.grid_var.get(),
            'font_family': self.fontfamily_var.get(),
            'title_fontsize': self.title_fontsize_var.get(),
            'label_fontsize': self.label_fontsize_var.get(),
            'tick_fontsize': self.tick_fontsize_var.get(),
            'facecolor': self.bgcolor_var.get(),
            'auto_axis': self.auto_axis_var.get(),
            'x_interval': self.x_interval_var.get(),
            'y_interval': self.y_interval_var.get(),
            'x_min': self.x_min_var.get(),
            'x_max': self.x_max_var.get(),
            'y_min': self.y_min_var.get(),
            'y_max': self.y_max_var.get()
        })
    
    # ============================================================================
    # EXPORT FUNCTIONALITY
    # ============================================================================
    
    def _export_plot(self):
        """Export plot with metadata options"""
        if not self.plot_data:
            messagebox.showwarning("No Data", "Please create a plot before exporting")
            return
            
        file_format = self.export_format_var.get()
        dpi = self.export_dpi_var.get()
        
        filename = filedialog.asksaveasfilename(
            title="Export Plot", 
            defaultextension=f".{file_format}",
            filetypes=[(f"{file_format.upper()} files", f"*.{file_format}"), ("All files", "*.*")]
        )
        
        if not filename:
            return
            
        try:
            # Prepare export options
            export_kwargs = {
                'dpi': dpi,
                'bbox_inches': 'tight' if self.tight_layout_var.get() else None,
                'transparent': self.transparent_bg_var.get(),
                'format': file_format
            }
            
            # Save the plot
            self.figure.savefig(filename, **export_kwargs)
            
            # Generate metadata if requested
            if self.include_metadata_var.get():
                metadata = self._generate_export_metadata()
                metadata_file = Path(filename).with_suffix('.json')
                
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2, default=str)
                    
                messagebox.showinfo(
                    "Export Complete", 
                    f"Plot exported successfully!\n\nFiles created:\n• {filename}\n• {metadata_file.name}"
                )
            else:
                messagebox.showinfo("Export Complete", f"Plot exported successfully to {filename}")
                
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            messagebox.showerror("Export Error", f"Failed to export plot: {str(e)}")
    
    def _export_data(self):
        """Export plotting data to CSV"""
        if not self.plot_data:
            messagebox.showwarning("No Data", "Please calculate plot data before exporting")
            return
            
        filename = filedialog.asksaveasfilename(
            title="Export Data", 
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filename:
            return
            
        try:
            if filename.endswith('.csv'):
                self._export_data_csv(filename)
            elif filename.endswith('.json'):
                self._export_data_json(filename)
            else:
                # Default to CSV
                self._export_data_csv(filename)
                
            messagebox.showinfo("Export Complete", f"Data exported successfully to {filename}")
            
        except Exception as e:
            self.logger.error(f"Data export failed: {e}")
            messagebox.showerror("Export Error", f"Failed to export data: {str(e)}")
    
    def _export_data_csv(self, filename):
        """Export data to CSV format"""
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            header = ['Frame_Number']
            for roi_name in self.plot_data.keys():
                header.append(f'{roi_name}_Average')
            writer.writerow(header)
            
            # Get all frame numbers
            all_frames = set()
            for data in self.plot_data.values():
                all_frames.update(data['frame_numbers'])
            
            # Write data rows
            for frame in sorted(all_frames):
                row = [frame]
                for roi_name in self.plot_data.keys():
                    data = self.plot_data[roi_name]
                    if frame in data['frame_numbers']:
                        idx = data['frame_numbers'].index(frame)
                        row.append(data['averages'][idx])
                    else:
                        row.append('')  # Empty cell if no data for this frame
                writer.writerow(row)
    
    def _export_data_json(self, filename):
        """Export data to JSON format"""
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'plot_settings': self.plot_settings,
            'roi_data': self.plot_data,
            'trace_customization': self.trace_custom if hasattr(self, 'trace_custom') else {}
        }
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, indent=2, default=str)
    
    def _generate_export_metadata(self):
        """Generate metadata for export"""
        selected_rois = [roi_name for roi_name, var in self.roi_checkboxes.items() if var.get()]
        
        metadata = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'pixelprobe_version': '1.0',  # You can update this
                'export_type': 'roi_vs_frame_plot'
            },
            'plot_data_summary': {
                'total_rois': len(selected_rois),
                'selected_rois': selected_rois,
                'total_frames': len(self.current_items),
                'frame_range': [min(self.current_items), max(self.current_items)] if self.current_items else [0, 0]
            }
        }
        
        # ROI information
        if self.include_roi_info_var.get():
            metadata['roi_coordinates'] = {}
            for roi_name in selected_rois:
                if roi_name in self.plot_data:
                    metadata['roi_coordinates'][roi_name] = self.plot_data[roi_name]['roi_coordinates']
        
        # Timestamp
        if self.include_timestamp_var.get():
            metadata['processing_timestamp'] = datetime.now().isoformat()
        
        # Plot settings
        if self.include_plot_settings_var.get():
            metadata['plot_configuration'] = {
                'title': self.plot_settings['title'],
                'xlabel': self.plot_settings['xlabel'], 
                'ylabel': self.plot_settings['ylabel'],
                'grid_enabled': self.plot_settings['grid'],
                'font_family': self.plot_settings['font_family'],
                'plot_mode': self.plot_mode_var.get() if hasattr(self, 'plot_mode_var') else 'unknown'
            }
        
        # Trace customization
        if hasattr(self, 'trace_custom'):
            metadata['trace_customization'] = self.trace_custom
        
        return metadata
    
    # ============================================================================
    # DIALOG MANAGEMENT
    # ============================================================================
    
    def _on_dialog_close(self):
        """Handle dialog close"""
        if hasattr(self, 'canvas'):
            try:
                self.canvas.get_tk_widget().destroy()
            except:
                pass
        self.dialog.destroy()


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_plotting_dialog(parent, array_handler, roi_selector, current_items):
    """Factory function to create plotting dialog"""
    dialog = ROIFramePlottingDialog(parent, array_handler, roi_selector, current_items)
    dialog.show()
    return dialog