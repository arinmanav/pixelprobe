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
        """Create main plot settings"""
        settings_frame = ctk.CTkFrame(self.control_scroll)
        settings_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(settings_frame, text="Plot Settings", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        # Basic labels
        for label_text, var_name, default in [
            ("Title:", "title_var", "ROI Average vs Frame Number"),
            ("X-Label:", "xlabel_var", "Frame Number"),
            ("Y-Label:", "ylabel_var", "Average Pixel Value")
        ]:
            row = ctk.CTkFrame(settings_frame)
            row.pack(fill="x", padx=8, pady=2)
            ctk.CTkLabel(row, text=label_text, width=60).pack(side="left", padx=(5, 5))
            var = tk.StringVar(value=default)
            entry = ctk.CTkEntry(row, textvariable=var, height=28)
            entry.pack(side="right", fill="x", expand=True, padx=(5, 5))
            setattr(self, var_name, var)
        
        # Grid settings
        grid_frame = ctk.CTkFrame(settings_frame)
        grid_frame.pack(fill="x", padx=8, pady=3)
        
        self.grid_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(grid_frame, text="Show Grid", variable=self.grid_var).pack(anchor="w", padx=5, pady=2)
        
        # Grid controls
        grid_row1 = ctk.CTkFrame(grid_frame)
        grid_row1.pack(fill="x", padx=5, pady=1)
        ctk.CTkLabel(grid_row1, text="Width:", width=50).pack(side="left", padx=2)
        self.grid_width_var = tk.DoubleVar(value=0.8)
        ctk.CTkSlider(grid_row1, from_=0.1, to=3.0, variable=self.grid_width_var, width=80).pack(side="left", padx=2)
        self.grid_width_label = ctk.CTkLabel(grid_row1, text="0.8", width=30)
        self.grid_width_label.pack(side="left", padx=2)
        
        grid_row2 = ctk.CTkFrame(grid_frame)
        grid_row2.pack(fill="x", padx=5, pady=1)
        ctk.CTkLabel(grid_row2, text="Alpha:", width=50).pack(side="left", padx=2)
        self.grid_alpha_var = tk.DoubleVar(value=0.7)
        ctk.CTkSlider(grid_row2, from_=0.1, to=1.0, variable=self.grid_alpha_var, width=80).pack(side="left", padx=2)
        self.grid_alpha_label = ctk.CTkLabel(grid_row2, text="0.7", width=30)
        self.grid_alpha_label.pack(side="left", padx=2)
        
        # Axis settings
        axis_frame = ctk.CTkFrame(settings_frame)
        axis_frame.pack(fill="x", padx=8, pady=3)
        
        self.auto_axis_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(axis_frame, text="Auto Scaling", variable=self.auto_axis_var,
                       command=self._toggle_axis_controls).pack(anchor="w", padx=5, pady=2)
        
        # Manual axis controls
        self.manual_axis_frame = ctk.CTkFrame(axis_frame)
        self.manual_axis_frame.pack(fill="x", padx=5, pady=2)
        
        # X-axis
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
        
        # Y-axis
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
        
        # Legend settings
        legend_frame = ctk.CTkFrame(settings_frame)
        legend_frame.pack(fill="x", padx=8, pady=3)
        
        ctk.CTkLabel(legend_frame, text="Legend:", width=60).pack(side="left", padx=5)
        self.legend_location_var = tk.StringVar(value="upper right")
        ctk.CTkComboBox(legend_frame, values=['upper right', 'upper left', 'lower right', 'lower left', 
                                            'upper center', 'lower center', 'center'],
                       variable=self.legend_location_var, width=120).pack(side="right", padx=5)
        
        self._toggle_axis_controls()  # Initialize state

    def _create_individual_traces_section(self):
        """Create individual trace customization"""
        if not self.roi_selector or not self.roi_selector.rois:
            return
            
        traces_frame = ctk.CTkFrame(self.control_scroll)
        traces_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(traces_frame, text="Individual Traces", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        traces_scroll = ctk.CTkScrollableFrame(traces_frame, height=200)
        traces_scroll.pack(fill="x", padx=8, pady=5)
        
        # Initialize trace settings
        default_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        default_markers = ['o', 's', '^', 'v', 'D', '*']
        
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
            
            # Name and visibility
            name_row = ctk.CTkFrame(trace_frame)
            name_row.pack(fill="x", padx=3, pady=1)
            
            visible_var = tk.BooleanVar(value=True)
            ctk.CTkCheckBox(name_row, text="", variable=visible_var, width=20).pack(side="left")
            
            color_btn = ctk.CTkButton(name_row, text="", width=25, height=20,
                                    fg_color=self.trace_custom[roi_name]['color'],
                                    command=lambda rn=roi_name: self._choose_color(rn))
            color_btn.pack(side="left", padx=2)
            
            label_var = tk.StringVar(value=roi_name)
            ctk.CTkEntry(name_row, textvariable=label_var, width=80, height=20).pack(side="left", padx=2)
            
            # Properties
            props_row = ctk.CTkFrame(trace_frame)
            props_row.pack(fill="x", padx=3, pady=1)
            
            ctk.CTkLabel(props_row, text="W:", width=20).pack(side="left")
            linewidth_var = tk.DoubleVar(value=2.0)
            ctk.CTkSlider(props_row, from_=0.5, to=5.0, variable=linewidth_var, width=40).pack(side="left")
            
            ctk.CTkLabel(props_row, text="S:", width=20).pack(side="left")
            markersize_var = tk.DoubleVar(value=6.0)
            ctk.CTkSlider(props_row, from_=2, to=12, variable=markersize_var, width=40).pack(side="left")
            
            linestyle_var = tk.StringVar(value='-')
            ctk.CTkComboBox(props_row, values=['-', '--', '-.', ':'], 
                           variable=linestyle_var, width=50).pack(side="left", padx=2)
            
            marker_var = tk.StringVar(value=default_markers[i % len(default_markers)])
            ctk.CTkComboBox(props_row, values=['o', 's', '^', 'v', 'D', '*', '+'], 
                           variable=marker_var, width=40).pack(side="left")
            
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

    def _update_trace_settings(self):
        """Update trace settings from UI"""
        for roi_name, controls in self.trace_controls.items():
            if roi_name in self.trace_custom:
                try:
                    self.trace_custom[roi_name]['visible'] = controls['visible_var'].get()
                    self.trace_custom[roi_name]['label'] = controls['label_var'].get()
                    self.trace_custom[roi_name]['linewidth'] = controls['linewidth_var'].get()
                    self.trace_custom[roi_name]['linestyle'] = controls['linestyle_var'].get()
                    self.trace_custom[roi_name]['marker'] = controls['marker_var'].get()
                    self.trace_custom[roi_name]['markersize'] = controls['markersize_var'].get()
                except:
                    pass

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

    def _plot_data(self):
        """Create the plot with current data"""
        try:
            # Get selected ROIs
            selected_rois = [roi_name for roi_name, var in self.roi_checkboxes.items() if var.get()]
            if not selected_rois:
                messagebox.showwarning("No Selection", "Please select at least one ROI to plot")
                return
            
            plot_mode = self.plot_mode_var.get()
            
            # Update trace settings
            self._update_trace_settings()
            
            # COMPLETELY CLEAR AND RECREATE THE PLOT
            self.subplot.clear()
            
            plotted_count = 0
            
            # Plot individual ROIs
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
                        marker=settings['marker'],
                        markersize=settings['markersize'],
                        alpha=0.8
                    )
                    plotted_count += 1
            
            if plotted_count == 0:
                self.subplot.text(0.5, 0.5, 'No data to plot\nCheck ROI selection and visibility',
                                ha='center', va='center', fontsize=12)
                self.canvas.draw()
                return
            
            # Apply settings
            self.subplot.set_title(self.title_var.get(), fontsize=14, fontweight='bold')
            self.subplot.set_xlabel(self.xlabel_var.get(), fontsize=12)
            self.subplot.set_ylabel(self.ylabel_var.get(), fontsize=12)
            
            # Grid
            if self.grid_var.get():
                self.subplot.grid(True, alpha=self.grid_alpha_var.get(), 
                                linewidth=self.grid_width_var.get())
            
            # Axis settings
            if not self.auto_axis_var.get():
                self.subplot.set_xlim(self.x_min_var.get(), self.x_max_var.get())
                self.subplot.set_ylim(self.y_min_var.get(), self.y_max_var.get())
                
                # Apply step sizes
                try:
                    if self.x_step_var.get() > 0:
                        self.subplot.xaxis.set_major_locator(ticker.MultipleLocator(self.x_step_var.get()))
                    if self.y_step_var.get() > 0:
                        self.subplot.yaxis.set_major_locator(ticker.MultipleLocator(self.y_step_var.get()))
                except:
                    pass
            
            # Legend
            if plotted_count > 0:
                self.subplot.legend(loc=self.legend_location_var.get(), fontsize=10)
            
            # Update canvas
            self.figure.tight_layout()
            self.canvas.draw()
            
            print(f"Plot created successfully with {plotted_count} traces")
            
        except Exception as e:
            print(f"Error creating plot: {e}")
            messagebox.showerror("Plot Error", f"Error creating plot:\n{str(e)}")

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


def create_plotting_dialog(parent, array_handler, roi_selector, current_items):
    """Factory function to create plotting dialog"""
    dialog = ROIFramePlottingDialog(parent, array_handler, roi_selector, current_items)
    dialog.show()
    return dialog