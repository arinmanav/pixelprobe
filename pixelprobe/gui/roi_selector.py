"""
ROI (Region of Interest) selector for PixelProbe
Handles interactive region selection on images with pixel-perfect precision
Rectangle selection includes all pixels within the drawn area
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.widgets import RectangleSelector
from typing import Dict, List, Tuple, Optional, Any
import logging
from dataclasses import dataclass
from enum import Enum


class ROIType(Enum):
    """Types of ROI selections available"""
    RECTANGLE = "rectangle"
    POINT = "point"
    MULTI_POINT = "multi_point"
    POLYGON = "polygon"  # For future use


@dataclass
class ROI:
    """Data class for storing ROI information with pixel-perfect selection"""
    roi_type: ROIType
    coordinates: Dict[str, Any]
    label: str
    color: str = "red"
    linewidth: float = 2.0
    
    def get_bounds(self) -> Tuple[int, int, int, int]:
        """Get bounding box as (x_min, y_min, x_max, y_max) - includes all selected pixels"""
        if self.roi_type == ROIType.RECTANGLE:
            # Return the actual selected bounds (all pixels within drawn rectangle)
            x = int(round(self.coordinates['x']))
            y = int(round(self.coordinates['y']))
            w = int(round(self.coordinates['width']))
            h = int(round(self.coordinates['height']))
            return x, y, x + w, y + h
        
        elif self.roi_type in [ROIType.POINT, ROIType.MULTI_POINT]:
            if self.roi_type == ROIType.POINT:
                x, y = int(round(self.coordinates['x'])), int(round(self.coordinates['y']))
                return x, y, x + 1, y + 1
            else:
                # Multi-point bounding box
                points = self.coordinates['points']
                xs = [int(round(p['x'])) for p in points]
                ys = [int(round(p['y'])) for p in points]
                return min(xs), min(ys), max(xs) + 1, max(ys) + 1
        
        return 0, 0, 1, 1
    
    def get_mask(self, image_shape: Tuple[int, int]) -> np.ndarray:
        """Generate boolean mask for this ROI - selects all pixels within drawn area"""
        mask = np.zeros(image_shape, dtype=bool)
        
        if self.roi_type == ROIType.RECTANGLE:
            # Use the full selected area (all pixels within the drawn rectangle)
            x = int(round(self.coordinates['x']))
            y = int(round(self.coordinates['y']))
            w = int(round(self.coordinates['width']))
            h = int(round(self.coordinates['height']))
            
            # Ensure we stay within image bounds
            x_start = max(0, min(x, image_shape[1] - 1))
            y_start = max(0, min(y, image_shape[0] - 1))
            x_end = max(x_start + 1, min(x + w, image_shape[1]))
            y_end = max(y_start + 1, min(y + h, image_shape[0]))
            
            # Select all pixels within the drawn rectangle
            if x_end > x_start and y_end > y_start:
                mask[y_start:y_end, x_start:x_end] = True
        
        elif self.roi_type == ROIType.POINT:
            x = int(round(self.coordinates['x']))
            y = int(round(self.coordinates['y']))
            if 0 <= y < image_shape[0] and 0 <= x < image_shape[1]:
                mask[y, x] = True
        
        elif self.roi_type == ROIType.MULTI_POINT:
            for point in self.coordinates['points']:
                x = int(round(point['x']))
                y = int(round(point['y']))
                if 0 <= y < image_shape[0] and 0 <= x < image_shape[1]:
                    mask[y, x] = True
        
        return mask
    
    def get_pixel_coordinates(self) -> List[Tuple[int, int]]:
        """Get list of (x, y) pixel coordinates within this ROI - all selected pixels"""
        if self.roi_type == ROIType.POINT:
            return [(int(round(self.coordinates['x'])), int(round(self.coordinates['y'])))]
        elif self.roi_type == ROIType.MULTI_POINT:
            return [(int(round(p['x'])), int(round(p['y']))) for p in self.coordinates['points']]
        elif self.roi_type == ROIType.RECTANGLE:
            # Return all pixels within the drawn rectangle
            x_min, y_min, x_max, y_max = self.get_bounds()
            pixels = []
            for y in range(y_min, y_max):
                for x in range(x_min, x_max):
                    pixels.append((x, y))
            return pixels
        else:
            return []


class ROISelector:
    """Main ROI selection class for handling interactive region selection"""
    
    def __init__(self, figure, subplot, status_callback=None):
        """Initialize ROI selector with pixel-perfect selection"""
        self.logger = logging.getLogger(__name__)
        self.figure = figure
        self.subplot = subplot
        self.status_callback = status_callback
        
        # ROI storage
        self.rois: List[ROI] = []
        self.current_roi_type = ROIType.RECTANGLE
        self.roi_counter = 0
        
        # Selection state
        self.selection_active = False
        self.current_selector = None
        
        # Event handlers storage for proper cleanup
        self.event_handlers = {}
        
        # Multi-point selection state
        self.multi_point_mode = False
        self.current_multi_point_roi = None
        self.multi_point_previews = []
        
        # Colors for different ROI types
        self.roi_colors = {
            ROIType.RECTANGLE: "red",
            ROIType.POINT: "green",
            ROIType.MULTI_POINT: "orange",
            ROIType.POLYGON: "purple"
        }
        
        self.logger.info("ROI Selector initialized with pixel-perfect selection")
    
    def _update_status(self, message: str):
        """Update status through callback if available"""
        if self.status_callback:
            self.status_callback(message)
    
    def set_roi_type(self, roi_type: ROIType):
        """Set the current ROI selection type with proper reinitialization"""
        # Finish any ongoing multi-point selection
        if self.multi_point_mode and self.current_multi_point_roi:
            self._finish_multi_point_selection()
        
        self.current_roi_type = roi_type
        
        # If selection is active, reinitialize event handlers
        if self.selection_active:
            self._cleanup_event_handlers()
            self._setup_event_handlers()
        
        self._update_status(f"ROI selection mode: {roi_type.value}")
        self.logger.info(f"ROI type set to {roi_type.value}")
    
    def activate_selection(self):
        """Activate ROI selection mode with proper cleanup"""
        if self.selection_active:
            return
        
        # Clean up any existing handlers first
        self._cleanup_event_handlers()
        
        self.selection_active = True
        self._setup_event_handlers()
        
        if self.current_roi_type == ROIType.POINT:
            self._update_status(f"ROI selection active - Click to select pixels")
        else:
            self._update_status(f"ROI selection active - {self.current_roi_type.value} mode")
        self.logger.info("ROI selection activated")
    
    def deactivate_selection(self):
        """Deactivate ROI selection mode with complete cleanup"""
        if not self.selection_active:
            return
        
        # Finish any ongoing multi-point selection
        if self.multi_point_mode and self.current_multi_point_roi:
            self._finish_multi_point_selection()
        
        self.selection_active = False
        self._cleanup_event_handlers()
        self._update_status("ROI selection deactivated")
        self.logger.info("ROI selection deactivated")
    
    def _setup_event_handlers(self):
        """Setup matplotlib event handlers for ROI selection"""
        if self.current_roi_type == ROIType.RECTANGLE:
            self._setup_rectangle_selector()
        elif self.current_roi_type == ROIType.POINT:
            self._setup_point_selector()
    
    def _setup_rectangle_selector(self):
        """Setup rectangle selection with minimum 2x2 pixel requirement"""
        self.current_selector = RectangleSelector(
            self.subplot,
            self._on_rectangle_select,
            useblit=True,
            button=[1],  # Only left mouse button
            minspanx=2,  # Minimum 2 pixels width (for 2x2 minimum)
            minspany=2,  # Minimum 2 pixels height (for 2x2 minimum)
            spancoords='data',
            interactive=True,
            drag_from_anywhere=True
        )
    
    def _setup_point_selector(self):
        """Setup point selection with pixel coordinate display"""
        self.event_handlers['button_press'] = self.figure.canvas.mpl_connect(
            'button_press_event', self._on_point_click
        )
        self.event_handlers['key_press'] = self.figure.canvas.mpl_connect(
            'key_press_event', self._on_key_press
        )
        self.event_handlers['key_release'] = self.figure.canvas.mpl_connect(
            'key_release_event', self._on_key_release
        )
    
    def _cleanup_event_handlers(self):
        """Clean up all event handlers completely"""
        # Deactivate matplotlib selector
        if hasattr(self, 'current_selector') and self.current_selector:
            try:
                self.current_selector.set_active(False)
            except:
                pass
            self.current_selector = None
        
        # Disconnect all event handlers
        if hasattr(self, 'event_handlers'):
            for event_id in self.event_handlers.values():
                try:
                    self.figure.canvas.mpl_disconnect(event_id)
                except:
                    pass
            self.event_handlers.clear()
        
        # Clean up multi-point previews
        for preview in getattr(self, 'multi_point_previews', []):
            try:
                preview.remove()
            except:
                pass
        self.multi_point_previews = []
        
        # Reset selection states
        self.multi_point_mode = False
        self.current_multi_point_roi = None
    
    def _on_rectangle_select(self, eclick, erelease):
        """Handle rectangle selection completion with proper pixel selection"""
        if eclick is None or erelease is None:
            return
        
        if eclick.xdata is None or eclick.ydata is None or \
           erelease.xdata is None or erelease.ydata is None:
            return
        
        # Snap to exact pixel coordinates (first and last clicked pixels)
        start_x = int(round(eclick.xdata))
        start_y = int(round(eclick.ydata))
        end_x = int(round(erelease.xdata))
        end_y = int(round(erelease.ydata))
        
        # Calculate the actual selected rectangle bounds
        # Use the full area that the user visually selected
        min_x = min(start_x, end_x)
        max_x = max(start_x, end_x)
        min_y = min(start_y, end_y)
        max_y = max(start_y, end_y)
        
        # Calculate width and height (inclusive of both endpoints)
        width = max_x - min_x + 1
        height = max_y - min_y + 1
        
        # Rectangle ROI requires minimum 2x2 pixels (single pixels use Point ROI)
        if width < 2 or height < 2:
            self._update_status("Rectangle ROI requires minimum 2×2 pixels. Use Point ROI for single pixels.")
            return
        
        # Ensure valid selection
        if width <= 0 or height <= 0:
            self._update_status("Invalid selection. Try selecting a larger area.")
            return
        
        # Store both selection coordinates and visual boundary coordinates
        roi = ROI(
            roi_type=ROIType.RECTANGLE,
            coordinates={
                # Selected area coordinates (what gets selected for analysis)
                'x': float(min_x),
                'y': float(min_y), 
                'width': float(width),
                'height': float(height),
                # Visual boundary coordinates (for display)
                'boundary_start_x': float(min_x - 0.5),  # Visual boundary
                'boundary_start_y': float(min_y - 0.5),
                'boundary_end_x': float(max_x + 0.5),
                'boundary_end_y': float(max_y + 0.5),
                # First and last clicked pixels
                'first_pixel': {'x': start_x, 'y': start_y},
                'last_pixel': {'x': end_x, 'y': end_y}
            },
            label=f"Rectangle_{self.roi_counter + 1}",
            color=self.roi_colors[ROIType.RECTANGLE]
        )
        
        self._add_roi(roi)
        self._log_roi_coordinates(roi)
    
    def _on_key_press(self, event):
        """Handle key press for multi-point selection"""
        if event.key == 'ctrl':
            if not self.multi_point_mode:
                self.multi_point_mode = True
                self._update_status("Multi-point mode: Click pixels, press Ctrl again or Esc to finish")
    
    def _on_key_release(self, event):
        """Handle key release for multi-point selection"""
        if event.key == 'ctrl' and self.multi_point_mode:
            self._finish_multi_point_selection()
        elif event.key == 'escape' and self.multi_point_mode:
            self._finish_multi_point_selection()
    
    def _on_point_click(self, event):
        """Handle point selection with exact pixel coordinates"""
        if event.inaxes != self.subplot or event.button != 1:
            return
        
        if event.xdata is None or event.ydata is None:
            return
        
        # Get exact pixel coordinates
        x_pixel = int(round(event.xdata))
        y_pixel = int(round(event.ydata))
        
        if self.multi_point_mode:
            self._add_point_to_multi_selection(x_pixel, y_pixel)
        else:
            # Single point selection
            roi = ROI(
                roi_type=ROIType.POINT,
                coordinates={'x': float(x_pixel), 'y': float(y_pixel)},
                label=f"Point_{self.roi_counter + 1}",
                color=self.roi_colors[ROIType.POINT]
            )
            
            self._add_roi(roi)
            self._log_roi_coordinates(roi)
    
    def _add_point_to_multi_selection(self, x: int, y: int):
        """Add a point to the current multi-point selection"""
        # Initialize multi-point ROI if not exists
        if self.current_multi_point_roi is None:
            self.current_multi_point_roi = {
                'points': [],
                'label': f"MultiPoint_{self.roi_counter + 1}",
                'color': self.roi_colors[ROIType.MULTI_POINT]
            }
        
        # Add the point
        point = {'x': float(x), 'y': float(y)}
        self.current_multi_point_roi['points'].append(point)
        
        # Add visual preview
        preview = self.subplot.plot(
            x, y, marker='o', color=self.current_multi_point_roi['color'],
            markersize=8, markeredgewidth=2, markerfacecolor='none',
            alpha=0.7
        )[0]
        self.multi_point_previews.append(preview)
        
        # Add point number
        text_preview = self.subplot.annotate(
            f"{len(self.current_multi_point_roi['points'])}",
            (x, y),
            xytext=(5, 5), textcoords='offset points',
            fontsize=8, color=self.current_multi_point_roi['color'],
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7)
        )
        self.multi_point_previews.append(text_preview)
        
        self.figure.canvas.draw_idle()
        
        point_count = len(self.current_multi_point_roi['points'])
        self._update_status(f"Multi-point selection: {point_count} points selected. Ctrl or Esc to finish.")
    
    def _finish_multi_point_selection(self):
        """Finish multi-point selection and create ROI"""
        if self.current_multi_point_roi and self.current_multi_point_roi['points']:
            # Create the multi-point ROI
            roi = ROI(
                roi_type=ROIType.MULTI_POINT,
                coordinates={
                    'points': self.current_multi_point_roi['points']
                },
                label=self.current_multi_point_roi['label'],
                color=self.current_multi_point_roi['color']
            )
            
            # Remove previews
            for preview in self.multi_point_previews:
                try:
                    preview.remove()
                except:
                    pass
            self.multi_point_previews = []
            
            self._add_roi(roi)
            self._log_roi_coordinates(roi)
        
        # Reset multi-point state
        self.multi_point_mode = False
        self.current_multi_point_roi = None
        self._update_status("Multi-point selection finished")
    
    def _add_roi(self, roi: ROI):
        """Add ROI to collection and visualize it"""
        self.rois.append(roi)
        self.roi_counter += 1
        self._visualize_roi(roi)
        self._update_status(f"Added {roi.label} - Total ROIs: {len(self.rois)}")
        self.logger.info(f"Added ROI: {roi.label}")

    def _visualize_roi(self, roi: ROI):
        """Add visual representation of ROI with clear selected area indication"""
        if roi.roi_type == ROIType.RECTANGLE:
            # Get selected area coordinates
            x = int(round(roi.coordinates['x']))
            y = int(round(roi.coordinates['y']))
            w = int(round(roi.coordinates['width']))
            h = int(round(roi.coordinates['height']))
            
            # Draw the selected area rectangle (pixel-centered)
            selected_rect = patches.Rectangle(
                (x - 0.5, y - 0.5), w, h,
                fill=False,
                edgecolor=roi.color,
                linewidth=2.0,
                alpha=0.8,
                linestyle='-'
            )
            self.subplot.add_patch(selected_rect)
            
            # Add a light fill to show the selected area
            fill_rect = patches.Rectangle(
                (x - 0.5, y - 0.5), w, h,
                fill=True,
                facecolor=roi.color,
                alpha=0.1,  # Light transparent fill
                edgecolor='none'
            )
            self.subplot.add_patch(fill_rect)
            
            # Mark first and last clicked pixels
            first_pixel = roi.coordinates.get('first_pixel', {'x': x, 'y': y})
            last_pixel = roi.coordinates.get('last_pixel', {'x': x + w - 1, 'y': y + h - 1})
            
            # First pixel marker (green)
            self.subplot.plot(
                first_pixel['x'], first_pixel['y'],
                marker='s', color='green', markersize=6,
                markeredgewidth=2, markerfacecolor='lightgreen',
                alpha=0.9
            )
            
            # Last pixel marker (red)  
            self.subplot.plot(
                last_pixel['x'], last_pixel['y'],
                marker='s', color='red', markersize=6,
                markeredgewidth=2, markerfacecolor='lightcoral',
                alpha=0.9
            )
            
            # START label - positioned outside the rectangle (left side)
            self.subplot.annotate(
                f"START\n({first_pixel['x']}, {first_pixel['y']})",
                (x - 0.5, y - 0.5),  # Top-left corner of selected area
                xytext=(-50, 0), textcoords='offset points',  # Far left of rectangle
                fontsize=11, color='green', weight='bold',
                ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='green', alpha=0.9)
            )
            
            # END label - positioned outside the rectangle (right side)
            self.subplot.annotate(
                f"END\n({last_pixel['x']}, {last_pixel['y']})",
                (x + w - 0.5, y + h - 0.5),  # Bottom-right corner of selected area
                xytext=(50, 0), textcoords='offset points',  # Far right of rectangle
                fontsize=11, color='red', weight='bold',
                ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='red', alpha=0.9)
            )
            
            # Size label at top-right corner
            self.subplot.annotate(
                f"{w}×{h}px",
                (x + w - 0.5, y - 0.5),  # Top-right corner of selected area
                xytext=(10, -10), textcoords='offset points',
                fontsize=11, color=roi.color, weight='bold',
                ha='left', va='top',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=roi.color, alpha=0.9)
            )
        
        elif roi.roi_type == ROIType.POINT:
            # Enhanced point visualization
            x = int(round(roi.coordinates['x']))
            y = int(round(roi.coordinates['y']))
            
            self.subplot.plot(
                x, y,
                marker='+', color=roi.color, markersize=12,
                markeredgewidth=3, markerfacecolor='none', alpha=0.9
            )
            
            # Add pixel coordinates as text annotation
            self.subplot.annotate(
                f"({x}, {y})",
                (x, y),
                xytext=(10, 10), textcoords='offset points',
                fontsize=12, color=roi.color,
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7)
            )
        
        elif roi.roi_type == ROIType.MULTI_POINT:
            # Visualize multiple points with integer coordinates
            for i, point in enumerate(roi.coordinates['points']):
                x = int(round(point['x']))
                y = int(round(point['y']))
                
                self.subplot.plot(
                    x, y, marker='o', color=roi.color, markersize=10,
                    markeredgewidth=2, markerfacecolor='none', alpha=0.9
                )
                
                # Add point number
                self.subplot.annotate(
                    f"{i+1}",
                    (x, y),
                    xytext=(5, 5), textcoords='offset points',
                    fontsize=8, color=roi.color,
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7)
                )
        
        self.figure.canvas.draw_idle()
        
    def _log_roi_coordinates(self, roi: ROI):
        """Enhanced coordinate logging with selected pixel info"""
        if roi.roi_type == ROIType.RECTANGLE:
            # Selected area coordinates  
            x = int(round(roi.coordinates['x']))
            y = int(round(roi.coordinates['y']))
            w = int(round(roi.coordinates['width']))
            h = int(round(roi.coordinates['height']))
            
            # Clicked pixels
            first_pixel = roi.coordinates.get('first_pixel', {'x': 0, 'y': 0})
            last_pixel = roi.coordinates.get('last_pixel', {'x': 0, 'y': 0})
            
            coords = f"Selected: ({x}, {y}) {w}×{h}px | Clicked: ({first_pixel['x']},{first_pixel['y']}) to ({last_pixel['x']},{last_pixel['y']})"
        
        elif roi.roi_type == ROIType.POINT:
            x = int(round(roi.coordinates['x']))
            y = int(round(roi.coordinates['y']))
            coords = f"pixel: ({x}, {y})"
        
        elif roi.roi_type == ROIType.MULTI_POINT:
            point_count = len(roi.coordinates['points'])
            coords = f"{point_count} pixels: " + ", ".join([
                f"({int(round(p['x']))},{int(round(p['y']))})" for p in roi.coordinates['points'][:3]
            ])
            if point_count > 3:
                coords += f" ... (+{point_count-3} more)"
        else:
            coords = "Unknown ROI type"
        
        self._update_status(f"{roi.label}: {coords}")
        self.logger.info(f"ROI coordinates: {roi.label} - {coords}")
    
    def clear_rois(self):
        """Clear all ROIs with proper cleanup"""
        # Finish any ongoing multi-point selection first
        if self.multi_point_mode and self.current_multi_point_roi:
            self._finish_multi_point_selection()
        
        self.rois.clear()
        self.roi_counter = 0
        
        self._update_status("All ROIs cleared")
        self.logger.info("All ROIs cleared")
        
        # Trigger canvas redraw
        self.figure.canvas.draw_idle()

    def get_roi_statistics(self, image_data: np.ndarray) -> Dict[str, Dict[str, Any]]:
        """Calculate statistics for all ROIs with proper pixel selection"""
        stats = {}
        
        for roi in self.rois:
            try:
                if roi.roi_type == ROIType.POINT:
                    x, y = int(round(roi.coordinates['x'])), int(round(roi.coordinates['y']))
                    
                    # Validate coordinates
                    if 0 <= y < image_data.shape[0] and 0 <= x < image_data.shape[1]:
                        pixel_value_raw = image_data[y, x]
                        
                        # Simple conversion for color images
                        if hasattr(pixel_value_raw, '__len__') and len(pixel_value_raw) > 1:
                            # Color image - convert to grayscale
                            if len(pixel_value_raw) == 3:  # RGB
                                pixel_value = float(0.299 * pixel_value_raw[0] + 0.587 * pixel_value_raw[1] + 0.114 * pixel_value_raw[2])
                            else:
                                pixel_value = float(np.mean(pixel_value_raw))
                        else:
                            # Grayscale image
                            pixel_value = float(pixel_value_raw)
                        
                        stats[roi.label] = {
                            'pixel_value': pixel_value,
                            'coordinates': f"({x}, {y})",
                            'x_coord': x,
                            'y_coord': y
                        }
                    else:
                        stats[roi.label] = {
                            'error': 'Coordinates out of bounds',
                            'coordinates': f"({x}, {y})"
                        }
                
                else:
                    # For rectangles and multi-points - use all selected pixels
                    mask = roi.get_mask(image_data.shape[:2])
                    
                    if np.any(mask):
                        # Extract pixel values using the mask
                        if len(image_data.shape) == 3:
                            # Color image - convert to grayscale for statistics
                            if image_data.shape[2] == 3:  # RGB
                                gray_data = 0.299 * image_data[:, :, 0] + 0.587 * image_data[:, :, 1] + 0.114 * image_data[:, :, 2]
                            else:
                                gray_data = np.mean(image_data, axis=2)
                            pixel_values = gray_data[mask]
                        else:
                            # Grayscale image
                            pixel_values = image_data[mask]
                        
                        # Calculate statistics
                        mean_val = float(np.mean(pixel_values))
                        std_val = float(np.std(pixel_values))
                        min_val = float(np.min(pixel_values))
                        max_val = float(np.max(pixel_values))
                        pixel_count = int(np.sum(mask))
                        
                        # Get bounds for coordinate info
                        x_min, y_min, x_max, y_max = roi.get_bounds()
                        
                        stats[roi.label] = {
                            'mean': mean_val,
                            'std': std_val,
                            'min': min_val,
                            'max': max_val,
                            'pixel_count': pixel_count,
                            'bounds': f"({x_min}, {y_min}) to ({x_max}, {y_max})"
                        }
                    else:
                        stats[roi.label] = {
                            'error': 'No pixels selected or all pixels out of bounds'
                        }
                        
            except Exception as e:
                self.logger.error(f"Error calculating statistics for {roi.label}: {e}")
                stats[roi.label] = {
                    'error': f'Calculation failed: {str(e)}'
                }
        
        return stats