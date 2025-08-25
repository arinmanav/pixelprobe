"""
Advanced ROI vs Frame plotting dialog for PixelProbe - Compact & Well-Arranged Layout
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
    """Advanced plotting dialog with compact, accessible layout"""
    
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
    
    def _create_dialog(self):
        """Create the main dialog window - COMPACT & ACCESSIBLE"""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("PixelProbe - ROI vs Frame Analysis & Plotting")
        
        # COMPACT: Start with reasonable size, user can resize if needed
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
        
        # REASONABLE minimum size
        self.dialog.minsize(1200, 750)
        
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_dialog_close)
        
    def _create_widgets(self):
        """Create all dialog widgets with compact layout"""
        self._create_control_panel()
        self._create_plot_area()
        
    def _create_control_panel(self):
        """Create compact, accessible control panel"""
        # COMPACT: Reasonable width that doesn't overwhelm
        self.main_control_scroll = ctk.CTkScrollableFrame(
            self.dialog, 
            width=350,  # Reduced from 480
            label_text="📊 Controls"
        )
        self.main_control_scroll.grid(row=0, column=0, sticky="nsew", padx=(15, 8), pady=15)
        
        # Compact title
        title_label = ctk.CTkLabel(
            self.main_control_scroll,
            text="ROI vs Frame Plotting",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(5, 15))
        
        # Create compact sections
        self._create_data_info_section(self.main_control_scroll)
        self._create_roi_selection_section(self.main_control_scroll)
        self._create_quick_actions_section(self.main_control_scroll)
        self._create_basic_settings_section(self.main_control_scroll)
        self._create_line_marker_compact_section(self.main_control_scroll)
        self._create_font_compact_section(self.main_control_scroll)
        self._create_axis_compact_section(self.main_control_scroll)
        self._create_style_export_section(self.main_control_scroll)
        
    def _create_data_info_section(self, parent):
        """Create compact data info section"""
        info_frame = ctk.CTkFrame(parent)
        info_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        info_title = ctk.CTkLabel(info_frame, text="📈 Dataset Info", font=ctk.CTkFont(size=13, weight="bold"))
        info_title.pack(pady=(8, 5))
        
        # Compact info display
        frames_text = f"{len(self.current_items)} frames ({min(self.current_items)}-{max(self.current_items)})"
        info_text = f"📊 {frames_text}\n🎯 {len(self.roi_selector.rois)} ROIs available"
        
        info_label = ctk.CTkLabel(info_frame, text=info_text, font=ctk.CTkFont(size=11))
        info_label.pack(pady=(0, 8))
        
    def _create_roi_selection_section(self, parent):
        """Create compact ROI selection"""
        roi_frame = ctk.CTkFrame(parent)
        roi_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        roi_title = ctk.CTkLabel(roi_frame, text="🎯 Select ROIs", font=ctk.CTkFont(size=13, weight="bold"))
        roi_title.pack(pady=(8, 5))
        
        # Compact control buttons
        controls_frame = ctk.CTkFrame(roi_frame)
        controls_frame.pack(fill="x", padx=8, pady=(0, 5))
        
        ctk.CTkButton(controls_frame, text="All", command=self._select_all_rois, width=60, height=25).pack(side="left", padx=(5, 3))
        ctk.CTkButton(controls_frame, text="Clear", command=self._clear_all_rois, width=60, height=25).pack(side="right", padx=(3, 5))
        
        # Compact ROI list
        self.roi_scroll_frame = ctk.CTkScrollableFrame(roi_frame, height=80)
        self.roi_scroll_frame.pack(fill="x", padx=8, pady=(0, 8))
        
    def _create_quick_actions_section(self, parent):
        """Create compact quick actions"""
        actions_frame = ctk.CTkFrame(parent)
        actions_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        actions_title = ctk.CTkLabel(actions_frame, text="⚡ Actions", font=ctk.CTkFont(size=13, weight="bold"))
        actions_title.pack(pady=(8, 5))
        
        buttons_frame = ctk.CTkFrame(actions_frame)
        buttons_frame.pack(fill="x", padx=8, pady=(0, 8))
        
        ctk.CTkButton(
            buttons_frame, text="🚀 Quick Plot", command=self._quick_plot,
            width=120, height=30, fg_color="#FF5722", hover_color="#E64A19",
            font=ctk.CTkFont(size=11, weight="bold")
        ).pack(side="left", padx=(5, 3))
        
        ctk.CTkButton(
            buttons_frame, text="📊 Calculate", command=self._calculate_plot_data,
            width=120, height=30, font=ctk.CTkFont(size=11)
        ).pack(side="right", padx=(3, 5))
        
    def _create_basic_settings_section(self, parent):
        """Create compact basic settings"""
        basic_frame = ctk.CTkFrame(parent)
        basic_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(basic_frame, text="📝 Basic Settings", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(8, 5))
        
        # Compact entry fields
        for label, var_name, default in [
            ("Title:", "title_entry", self.plot_settings['title']),
            ("X-axis:", "xlabel_entry", self.plot_settings['xlabel']),
            ("Y-axis:", "ylabel_entry", self.plot_settings['ylabel'])
        ]:
            row = ctk.CTkFrame(basic_frame)
            row.pack(fill="x", padx=8, pady=2)
            ctk.CTkLabel(row, text=label, width=50).pack(side="left", padx=(5, 5))
            entry = ctk.CTkEntry(row, font=ctk.CTkFont(size=10))
            entry.pack(side="right", fill="x", expand=True, padx=(5, 5))
            entry.insert(0, default)
            setattr(self, var_name, entry)
        
        # Add spacing
        ctk.CTkLabel(basic_frame, text="").pack(pady=4)
        
    def _create_line_marker_compact_section(self, parent):
        """Create compact line & marker settings"""
        line_frame = ctk.CTkFrame(parent)
        line_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(line_frame, text="📈 Line & Markers", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(8, 5))
        
        # Line width with value display
        self._create_compact_slider(line_frame, "Line Width:", "linewidth_var", 0.1, 15.0, 
                                   self.plot_settings['linewidth'], format_func=lambda x: f"{x:.1f}")
        
        # Marker size with value display  
        self._create_compact_slider(line_frame, "Marker Size:", "markersize_var", 1, 50,
                                   self.plot_settings['markersize'], format_func=lambda x: f"{int(x)}")
        
        # Style dropdowns in one row
        style_row = ctk.CTkFrame(line_frame)
        style_row.pack(fill="x", padx=8, pady=2)
        
        ctk.CTkLabel(style_row, text="Style:", width=50).pack(side="left", padx=(5, 5))
        self.linestyle_var = tk.StringVar(value=self.plot_settings['linestyle'])
        ctk.CTkComboBox(style_row, values=['-', '--', '-.', ':', 'None'], 
                       variable=self.linestyle_var, width=70).pack(side="left", padx=(0, 5))
        
        ctk.CTkLabel(style_row, text="Marker:").pack(side="left", padx=(5, 5))
        self.marker_var = tk.StringVar(value=self.plot_settings['marker'])
        ctk.CTkComboBox(style_row, values=['o', 's', '^', 'v', 'D', '*', '+', 'x', 'None'],
                       variable=self.marker_var, width=70).pack(side="right", padx=(5, 5))
        
        ctk.CTkLabel(line_frame, text="").pack(pady=2)
        
    def _create_font_compact_section(self, parent):
        """Create compact font settings"""
        font_frame = ctk.CTkFrame(parent)
        font_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(font_frame, text="🔤 Fonts", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(8, 5))
        
        # Font family
        family_row = ctk.CTkFrame(font_frame)
        family_row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(family_row, text="Family:", width=50).pack(side="left", padx=(5, 5))
        self.fontfamily_var = tk.StringVar(value=self.plot_settings['font_family'])
        ctk.CTkComboBox(family_row, values=['Arial', 'Times New Roman', 'Courier New', 'Helvetica', 'Verdana'],
                       variable=self.fontfamily_var).pack(side="right", fill="x", expand=True, padx=(5, 5))
        
        # Font sizes with compact sliders
        self._create_compact_slider(font_frame, "Title Size:", "title_fontsize_var", 6, 48,
                                   self.plot_settings['title_fontsize'], format_func=int)
        
        self._create_compact_slider(font_frame, "Labels:", "label_fontsize_var", 4, 36,
                                   self.plot_settings['label_fontsize'], format_func=int)
        
        self._create_compact_slider(font_frame, "Values:", "tick_fontsize_var", 4, 32,
                                   self.plot_settings.get('tick_fontsize', 10), format_func=int)
        
        ctk.CTkLabel(font_frame, text="").pack(pady=2)
        
    def _create_axis_compact_section(self, parent):
        """Create compact axis settings"""
        axis_frame = ctk.CTkFrame(parent)
        axis_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(axis_frame, text="📏 Axis Control", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(8, 5))
        
        # Auto/Manual toggle
        mode_row = ctk.CTkFrame(axis_frame)
        mode_row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(mode_row, text="Mode:", width=50).pack(side="left", padx=(5, 5))
        self.auto_axis_var = tk.BooleanVar(value=self.plot_settings.get('auto_axis', True))
        ctk.CTkSwitch(mode_row, variable=self.auto_axis_var, text="Auto Scale", 
                     command=self._on_axis_mode_change).pack(side="right", padx=(5, 5))
        
        # Intervals row
        interval_row = ctk.CTkFrame(axis_frame)
        interval_row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(interval_row, text="X Int:", width=40).pack(side="left", padx=(5, 2))
        self.x_interval_var = tk.IntVar(value=self.plot_settings.get('x_interval', 0))
        ctk.CTkEntry(interval_row, width=50, textvariable=self.x_interval_var).pack(side="left", padx=(0, 5))
        
        ctk.CTkLabel(interval_row, text="Y Int:").pack(side="left", padx=(10, 2))
        self.y_interval_var = tk.DoubleVar(value=self.plot_settings.get('y_interval', 0))
        ctk.CTkEntry(interval_row, width=50, textvariable=self.y_interval_var).pack(side="right", padx=(5, 5))
        
        # Ranges (compact)
        range_row = ctk.CTkFrame(axis_frame)
        range_row.pack(fill="x", padx=8, pady=2)
        
        ctk.CTkLabel(range_row, text="X:", width=15).pack(side="left", padx=(5, 2))
        self.x_min_var = tk.DoubleVar(value=self.plot_settings.get('x_min', 0))
        self.x_min_entry = ctk.CTkEntry(range_row, width=45, textvariable=self.x_min_var)
        self.x_min_entry.pack(side="left", padx=(0, 2))
        
        ctk.CTkLabel(range_row, text="-").pack(side="left", padx=1)
        self.x_max_var = tk.DoubleVar(value=self.plot_settings.get('x_max', 100))
        self.x_max_entry = ctk.CTkEntry(range_row, width=45, textvariable=self.x_max_var)
        self.x_max_entry.pack(side="left", padx=(2, 10))
        
        ctk.CTkLabel(range_row, text="Y:").pack(side="left", padx=(5, 2))
        self.y_min_var = tk.DoubleVar(value=self.plot_settings.get('y_min', 0))
        self.y_min_entry = ctk.CTkEntry(range_row, width=45, textvariable=self.y_min_var)
        self.y_min_entry.pack(side="left", padx=(0, 2))
        
        ctk.CTkLabel(range_row, text="-").pack(side="left", padx=1)
        self.y_max_var = tk.DoubleVar(value=self.plot_settings.get('y_max', 100))
        self.y_max_entry = ctk.CTkEntry(range_row, width=45, textvariable=self.y_max_var)
        self.y_max_entry.pack(side="right", padx=(2, 5))
        
        # Store manual controls
        self.manual_axis_controls = [self.x_min_entry, self.x_max_entry, self.y_min_entry, self.y_max_entry]
        self._on_axis_mode_change()
        
        ctk.CTkLabel(axis_frame, text="").pack(pady=2)
        
    def _create_style_export_section(self, parent):
        """Create combined style and export section"""
        combined_frame = ctk.CTkFrame(parent)
        combined_frame.pack(fill="x", padx=10, pady=(0, 15))
        
        # Style section
        ctk.CTkLabel(combined_frame, text="🎨 Style & Export", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(8, 5))
        
        # Grid and background row
        style_row = ctk.CTkFrame(combined_frame)
        style_row.pack(fill="x", padx=8, pady=2)
        
        ctk.CTkLabel(style_row, text="Grid:", width=40).pack(side="left", padx=(5, 5))
        self.grid_var = tk.BooleanVar(value=self.plot_settings['grid'])
        ctk.CTkSwitch(style_row, variable=self.grid_var, width=40).pack(side="left", padx=(0, 10))
        
        self.bgcolor_var = tk.StringVar(value=self.plot_settings['facecolor'])
        ctk.CTkButton(style_row, text="Background", command=self._choose_background_color, 
                     width=90, height=25).pack(side="right", padx=(5, 5))
        
        # Export options row
        export_row = ctk.CTkFrame(combined_frame)
        export_row.pack(fill="x", padx=8, pady=2)
        
        ctk.CTkLabel(export_row, text="Format:", width=50).pack(side="left", padx=(5, 5))
        self.export_format_var = tk.StringVar(value=self.export_settings['format'])
        ctk.CTkComboBox(export_row, values=['png', 'jpg', 'pdf', 'svg', 'eps', 'tiff'],
                       variable=self.export_format_var, width=80).pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(export_row, text="DPI:").pack(side="left", padx=(5, 5))
        self.export_dpi_var = tk.IntVar(value=self.export_settings['dpi'])
        ctk.CTkComboBox(export_row, values=['150', '300', '600', '1200', '2400'],
                       variable=self.export_dpi_var, width=80).pack(side="right", padx=(5, 5))
        
        # Export buttons
        export_buttons = ctk.CTkFrame(combined_frame)
        export_buttons.pack(fill="x", padx=8, pady=(5, 8))
        
        ctk.CTkButton(export_buttons, text="💾 Export Plot", command=self._export_plot,
                     width=110, height=30, fg_color="#4CAF50", hover_color="#45a049",
                     font=ctk.CTkFont(size=10, weight="bold")).pack(side="left", padx=(5, 3))
        
        ctk.CTkButton(export_buttons, text="📊 Export Data", command=self._export_data,
                     width=110, height=30, font=ctk.CTkFont(size=10)).pack(side="right", padx=(3, 5))
        
    def _create_compact_slider(self, parent, label, var_name, min_val, max_val, default_val, format_func=float):
        """Create a compact slider with value display"""
        row = ctk.CTkFrame(parent)
        row.pack(fill="x", padx=8, pady=2)
        
        ctk.CTkLabel(row, text=label, width=50).pack(side="left", padx=(5, 5))
        
        var = tk.DoubleVar(value=default_val) if isinstance(default_val, float) else tk.IntVar(value=default_val)
        setattr(self, var_name, var)
        
        # Value label
        value_label = ctk.CTkLabel(row, text=str(format_func(default_val)), width=30)
        value_label.pack(side="right", padx=(5, 5))
        
        # Slider
        slider = ctk.CTkSlider(row, from_=min_val, to=max_val, variable=var,
                              command=lambda val: value_label.configure(text=str(format_func(float(val)))))
        slider.pack(side="right", fill="x", expand=True, padx=(5, 0))
        
    def _create_plot_area(self):
        """Create optimized plot area"""
        plot_frame = ctk.CTkFrame(self.dialog)
        plot_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 15), pady=15)
        plot_frame.grid_columnconfigure(0, weight=1)
        plot_frame.grid_rowconfigure(1, weight=1)
        
        # Compact plot title
        plot_title = ctk.CTkLabel(plot_frame, text="📈 ROI Average vs Frame Number",
                                 font=ctk.CTkFont(size=16, weight="bold"))
        plot_title.grid(row=0, column=0, pady=(15, 10), sticky="ew")
        
        # Optimized matplotlib figure
        self.figure = Figure(figsize=(9, 7), dpi=100)
        self.subplot = self.figure.add_subplot(111)
        
        # Canvas
        self.canvas = FigureCanvasTkAgg(self.figure, plot_frame)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        
        # Initial plot
        self._show_empty_plot()
        
    def _populate_roi_list(self):
        """Populate compact ROI list"""
        for widget in self.roi_scroll_frame.winfo_children():
            widget.destroy()
            
        self.roi_checkboxes = {}
        
        for roi in self.roi_selector.rois:
            row = ctk.CTkFrame(self.roi_scroll_frame)
            row.pack(fill="x", padx=3, pady=1)
            
            checkbox_var = tk.BooleanVar()
            checkbox = ctk.CTkCheckBox(row, text="", variable=checkbox_var, width=20)
            checkbox.pack(side="left", padx=(5, 5), pady=3)
            
            # Compact info
            if roi.roi_type.name == 'POINT':
                info = f"{roi.label} • Point ({int(roi.coordinates['x'])},{int(roi.coordinates['y'])})"
            elif roi.roi_type.name == 'RECTANGLE':
                w, h = int(roi.coordinates['width']), int(roi.coordinates['height'])
                info = f"{roi.label} • Rect {w}×{h}px"
            else:
                info = f"{roi.label} • {roi.roi_type.name}"
                
            ctk.CTkLabel(row, text=info, font=ctk.CTkFont(size=9)).pack(side="left", padx=(0, 5), pady=3)
            self.roi_checkboxes[roi.label] = checkbox_var
            
    def _on_axis_mode_change(self):
        """Handle axis mode change"""
        is_auto = self.auto_axis_var.get()
        state = "disabled" if is_auto else "normal"
        for control in self.manual_axis_controls:
            control.configure(state=state)
    
    def _select_all_rois(self):
        """Select all ROI checkboxes"""
        for checkbox_var in self.roi_checkboxes.values():
            checkbox_var.set(True)
        
    def _clear_all_rois(self):
        """Clear all ROI checkboxes"""
        for checkbox_var in self.roi_checkboxes.values():
            checkbox_var.set(False)
        
    def _on_roi_selection_changed(self):
        """Handle ROI selection change"""
        pass
        
    def _quick_plot(self):
        """Create a quick plot"""
        if not any(var.get() for var in self.roi_checkboxes.values()):
            self._select_all_rois()
        self._update_plot_from_settings()
        self._create_plot()
        
    def _calculate_plot_data(self):
        """Recalculate plot data"""
        self._calculate_initial_data()
        messagebox.showinfo("Data Calculated", "Plot data recalculated for all ROIs")
        
    def _calculate_initial_data(self):
        """Calculate data for all ROIs"""
        self.plot_data = {}
        for roi in self.roi_selector.rois:
            roi_data = self._calculate_roi_data(roi)
            if roi_data is not None:
                self.plot_data[roi.label] = roi_data
                
    def _calculate_roi_data(self, roi) -> Optional[Dict]:
        """Calculate average values for a single ROI across all frames"""
        try:
            frame_numbers = []
            roi_averages = []
            
            for frame_num in self.current_items:
                array_data = self.array_handler.load_item(frame_num)
                if array_data is None:
                    continue
                roi_avg = self._get_roi_average(roi, array_data)
                if roi_avg is not None:
                    frame_numbers.append(frame_num)
                    roi_averages.append(roi_avg)
                    
            if len(frame_numbers) == 0:
                return None
                
            return {
                'frame_numbers': frame_numbers,
                'averages': roi_averages,
                'roi_type': roi.roi_type.name,
                'roi_coordinates': roi.coordinates
            }
        except Exception as e:
            self.logger.error(f"Error calculating ROI data for {roi.label}: {e}")
            return None
            
    def _get_roi_average(self, roi, array_data) -> Optional[float]:
        """Get average value for ROI in given array"""
        try:
            if roi.roi_type.name == 'POINT':
                x = int(round(roi.coordinates['x']))
                y = int(round(roi.coordinates['y']))
                if (0 <= x < array_data.shape[1] and 0 <= y < array_data.shape[0]):
                    return float(array_data[y, x])
            elif roi.roi_type.name == 'RECTANGLE':
                x, y = int(roi.coordinates['x']), int(roi.coordinates['y'])
                width, height = int(roi.coordinates['width']), int(roi.coordinates['height'])
                x_end = min(x + width, array_data.shape[1])
                y_end = min(y + height, array_data.shape[0])
                if x >= 0 and y >= 0 and x < x_end and y < y_end:
                    region = array_data[y:y_end, x:x_end]
                    return float(np.mean(region))
            return None
        except Exception as e:
            self.logger.error(f"Error calculating ROI average: {e}")
            return None
        
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
        
    def _create_plot(self):
        """Create the plot"""
        try:
            selected_rois = [roi_name for roi_name, var in self.roi_checkboxes.items() if var.get()]
            
            if not selected_rois:
                messagebox.showwarning("No Selection", "Please select at least one ROI to plot")
                return
                
            self.subplot.clear()
            plt.style.use('default')
            self.subplot.set_facecolor(self.plot_settings['facecolor'])
            
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                     '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
            
            for i, roi_name in enumerate(selected_rois):
                if roi_name not in self.plot_data:
                    continue
                    
                data = self.plot_data[roi_name]
                color = colors[i % len(colors)]
                
                marker = self.plot_settings['marker'] if self.plot_settings['marker'] != 'None' else None
                linestyle = self.plot_settings['linestyle'] if self.plot_settings['linestyle'] != 'None' else None
                
                self.subplot.plot(
                    data['frame_numbers'], data['averages'],
                    color=color, label=roi_name,
                    linewidth=self.plot_settings['linewidth'],
                    linestyle=linestyle, marker=marker,
                    markersize=self.plot_settings['markersize'], alpha=0.8
                )
            
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
                
            if len(selected_rois) > 1:
                self.subplot.legend(fontsize=max(8, self.plot_settings['label_fontsize'] - 2), framealpha=0.9)
                
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
            "📊 ROI vs Frame Analysis\n\n"
            "1. Select ROIs from controls\n"
            "2. Click 'Quick Plot' to start\n"
            "3. Customize and export\n\n"
            "Ready to plot!",
            horizontalalignment='center', verticalalignment='center',
            transform=self.subplot.transAxes, fontsize=12,
            bbox=dict(boxstyle='round,pad=1', facecolor='lightblue', alpha=0.8)
        )
        self.subplot.set_title("ROI Plotting Tool", fontsize=14, fontweight='bold')
        self.canvas.draw()
        
    def _choose_background_color(self):
        """Choose background color"""
        color = colorchooser.askcolor(color=self.plot_settings['facecolor'], title="Background Color")
        if color[1]:
            self.bgcolor_var.set(color[1])
            self.plot_settings['facecolor'] = color[1]
            
    def _export_plot(self):
        """Export plot"""
        if not self.plot_data:
            messagebox.showwarning("No Data", "Please create a plot before exporting")
            return
            
        file_format = self.export_format_var.get()
        dpi = self.export_dpi_var.get()
        
        filename = filedialog.asksaveasfilename(
            title="Export Plot", defaultextension=f".{file_format}",
            filetypes=[(f"{file_format.upper()} files", f"*.{file_format}"), ("All files", "*.*")]
        )
        
        if not filename:
            return
            
        try:
            self._update_plot_from_settings()
            self._create_plot()
            
            metadata = self._get_export_metadata()
            if file_format == 'png':
                self.figure.savefig(filename, dpi=dpi, bbox_inches='tight', 
                                  facecolor=self.plot_settings['facecolor'], metadata=metadata)
            else:
                self.figure.savefig(filename, dpi=dpi, bbox_inches='tight',
                                  facecolor=self.plot_settings['facecolor'])
                
            messagebox.showinfo("Export Complete", f"Plot exported to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting: {str(e)}")
            
    def _export_data(self):
        """Export data as CSV"""
        if not self.plot_data:
            messagebox.showwarning("No Data", "Please calculate plot data first")
            return
            
        selected_rois = [roi for roi, var in self.roi_checkboxes.items() if var.get()]
        if not selected_rois:
            messagebox.showwarning("No Selection", "Please select at least one ROI")
            return
            
        filename = filedialog.asksaveasfilename(
            title="Export Data", defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filename:
            return
            
        try:
            if filename.endswith('.json'):
                self._export_data_json(filename, selected_rois)
            else:
                self._export_data_csv(filename, selected_rois)
            messagebox.showinfo("Export Complete", f"Data exported to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting: {str(e)}")
    
    def _export_data_csv(self, filename: str, selected_rois: List[str]):
        """Export as CSV"""
        import csv
        with open(filename, 'w', newline='') as f:
            f.write(f"# PixelProbe ROI vs Frame Analysis Export\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Frame Range: {min(self.current_items)}-{max(self.current_items)}\n")
            f.write(f"# Selected ROIs: {', '.join(selected_rois)}\n#\n")
            
            all_frames = sorted(set().union(*[self.plot_data[roi]['frame_numbers'] for roi in selected_rois]))
            header = ['Frame_Number'] + [f'{roi}_Average' for roi in selected_rois]
            
            writer = csv.writer(f)
            writer.writerow(header)
            
            for frame in all_frames:
                row = [frame]
                for roi in selected_rois:
                    if roi in self.plot_data:
                        data = self.plot_data[roi]
                        if frame in data['frame_numbers']:
                            idx = data['frame_numbers'].index(frame)
                            row.append(data['averages'][idx])
                        else:
                            row.append('')
                    else:
                        row.append('')
                writer.writerow(row)
                
    def _export_data_json(self, filename: str, selected_rois: List[str]):
        """Export as JSON"""
        export_data = {
            'metadata': self._get_export_metadata(),
            'plot_settings': self.plot_settings.copy(),
            'roi_data': {roi: self.plot_data[roi].copy() for roi in selected_rois if roi in self.plot_data}
        }
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
            
    def _get_export_metadata(self) -> Dict[str, Any]:
        """Get export metadata"""
        selected_rois = [roi for roi, var in self.roi_checkboxes.items() if var.get()]
        return {
            'software': 'PixelProbe',
            'analysis_type': 'ROI_vs_Frame',
            'timestamp': datetime.now().isoformat(),
            'frame_count': len(self.current_items),
            'frame_range': f"{min(self.current_items)}-{max(self.current_items)}",
            'selected_rois': selected_rois,
            'roi_count': len(selected_rois),
            'plot_title': self.plot_settings['title'],
            'plot_settings': self.plot_settings.copy()
        }
        
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
        
    def _on_dialog_close(self):
        """Handle dialog close"""
        if hasattr(self, 'canvas'):
            try:
                self.canvas.get_tk_widget().destroy()
            except:
                pass
        self.dialog.destroy()


def create_plotting_dialog(parent, array_handler, roi_selector, current_items):
    """Factory function to create plotting dialog"""
    dialog = ROIFramePlottingDialog(parent, array_handler, roi_selector, current_items)
    dialog.show()
    return dialog