"""
ROI (Region of Interest) selector for PixelProbe
Handles interactive region selection on images with multiple selection types
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
    CIRCLE = "circle"
    POINT = "point"
    MULTI_POINT = "multi_point"
    POLYGON = "polygon"


@dataclass
class ROI:
    """Data class for storing ROI information"""
    roi_type: ROIType
    coordinates: Dict[str, Any]  # Changed to Any to handle lists
    label: str
    color: str = "red"
    linewidth: float = 2.0
    
    def get_bounds(self) -> Tuple[int, int, int, int]:
        """Get bounding box as (x_min, y_min, x_max, y_max)"""
        if self.roi_type == ROIType.RECTANGLE:
            x, y, w, h = self.coordinates['x'], self.coordinates['y'], \
                        self.coordinates['width'], self.coordinates['height']
            return int(x), int(y), int(x + w), int(y + h)
        
        elif self.roi_type == ROIType.CIRCLE:
            cx, cy, r = self.coordinates['cx'], self.coordinates['cy'], self.coordinates['radius']
            return int(cx - r), int(cy - r), int(cx + r), int(cy + r)
        
        elif self.roi_type in [ROIType.POINT, ROIType.MULTI_POINT]:
            if self.roi_type == ROIType.POINT:
                x, y = self.coordinates['x'], self.coordinates['y']
                return int(x), int(y), int(x + 1), int(y + 1)
            else:  # MULTI_POINT
                xs = [p['x'] for p in self.coordinates['points']]
                ys = [p['y'] for p in self.coordinates['points']]
                return int(min(xs)), int(min(ys)), int(max(xs)) + 1, int(max(ys)) + 1
        
        else:  # POLYGON
            xs = self.coordinates['x_points']
            ys = self.coordinates['y_points']
            return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
    
    def get_mask(self, image_shape: Tuple[int, int]) -> np.ndarray:
        """Generate boolean mask for this ROI"""
        mask = np.zeros(image_shape, dtype=bool)
        
        if self.roi_type == ROIType.RECTANGLE:
            x_min, y_min, x_max, y_max = self.get_bounds()
            mask[max(0, y_min):min(image_shape[0], y_max), 
                 max(0, x_min):min(image_shape[1], x_max)] = True
        
        elif self.roi_type == ROIType.CIRCLE:
            cx, cy, r = self.coordinates['cx'], self.coordinates['cy'], self.coordinates['radius']
            y, x = np.ogrid[:image_shape[0], :image_shape[1]]
            mask = (x - cx)**2 + (y - cy)**2 <= r**2
        
        elif self.roi_type == ROIType.POINT:
            x, y = int(self.coordinates['x']), int(self.coordinates['y'])
            if 0 <= y < image_shape[0] and 0 <= x < image_shape[1]:
                mask[y, x] = True
        
        elif self.roi_type == ROIType.MULTI_POINT:
            for point in self.coordinates['points']:
                x, y = int(point['x']), int(point['y'])
                if 0 <= y < image_shape[0] and 0 <= x < image_shape[1]:
                    mask[y, x] = True
        
        return mask
    
    def get_pixel_coordinates(self) -> List[Tuple[int, int]]:
        """Get list of (x, y) pixel coordinates within this ROI"""
        if self.roi_type == ROIType.POINT:
            return [(int(self.coordinates['x']), int(self.coordinates['y']))]
        elif self.roi_type == ROIType.MULTI_POINT:
            return [(int(p['x']), int(p['y'])) for p in self.coordinates['points']]
        else:
            # For regions, return all pixels in bounds
            x_min, y_min, x_max, y_max = self.get_bounds()
            pixels = []
            for y in range(y_min, y_max):
                for x in range(x_min, x_max):
                    pixels.append((x, y))
            return pixels


class ROISelector:
    """Main ROI selection class for handling interactive region selection"""
    
    def __init__(self, figure, subplot, status_callback=None):
        """Initialize ROI selector with all required attributes"""
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
        
        # Circle selection state
        self.circle_start = None
        self.circle_preview = None
        
        # Multi-point selection state
        self.multi_point_mode = False
        self.current_multi_point_roi = None
        self.multi_point_previews = []
        
        # Colors for different ROI types
        self.roi_colors = {
            ROIType.RECTANGLE: "red",
            ROIType.CIRCLE: "blue", 
            ROIType.POINT: "green",
            ROIType.MULTI_POINT: "orange",
            ROIType.POLYGON: "purple"
        }
        
        self.logger.info("ROI Selector initialized")
    
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
            self._update_status(f"ROI selection active - Click to select points. Hold Ctrl for multi-point selection")
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
        elif self.current_roi_type == ROIType.CIRCLE:
            self._setup_circle_selector()
        elif self.current_roi_type == ROIType.POINT:
            self._setup_point_selector()
    
    def _setup_rectangle_selector(self):
        """Setup rectangle selection with interactive preview"""
        self.current_selector = RectangleSelector(
            self.subplot,
            self._on_rectangle_select,
            useblit=True,  # Keep interactive preview
            button=[1],  # Only left mouse button
            minspanx=1,
            minspany=1,
            spancoords='data',
            interactive=True,  # Enable interactive preview
            drag_from_anywhere=True
        )
    
    def _setup_circle_selector(self):
        """Setup circle selection using mouse events with proper circular mask"""
        self.event_handlers['button_press'] = self.figure.canvas.mpl_connect(
            'button_press_event', self._on_circle_start
        )
        self.event_handlers['motion_notify'] = self.figure.canvas.mpl_connect(
            'motion_notify_event', self._on_circle_motion
        )
        self.event_handlers['button_release'] = self.figure.canvas.mpl_connect(
            'button_release_event', self._on_circle_end
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
        
        # Clean up preview elements
        if hasattr(self, 'circle_preview') and self.circle_preview:
            try:
                self.circle_preview.remove()
            except:
                pass
            self.circle_preview = None
        
        # Clean up multi-point previews
        for preview in getattr(self, 'multi_point_previews', []):
            try:
                preview.remove()
            except:
                pass
        self.multi_point_previews = []
        
        # Reset selection states
        self.circle_start = None
        self.multi_point_mode = False
        self.current_multi_point_roi = None
    
    def _on_rectangle_select(self, eclick, erelease):
        """Handle rectangle selection completion with proper coordinates"""
        if eclick is None or erelease is None:
            return
        
        if eclick.xdata is None or eclick.ydata is None or \
           erelease.xdata is None or erelease.ydata is None:
            return
        
        # Get proper coordinates
        x_min, x_max = sorted([eclick.xdata, erelease.xdata])
        y_min, y_max = sorted([eclick.ydata, erelease.ydata])
        
        # Use float coordinates for better accuracy
        width = abs(x_max - x_min)
        height = abs(y_max - y_min)
        
        roi = ROI(
            roi_type=ROIType.RECTANGLE,
            coordinates={
                'x': x_min,
                'y': y_min,
                'width': width,
                'height': height
            },
            label=f"Rectangle_{self.roi_counter + 1}",
            color=self.roi_colors[ROIType.RECTANGLE]
        )
        
        self._add_roi(roi)
        self._log_roi_coordinates(roi)
    
    def _on_circle_start(self, event):
        """Handle circle selection start"""
        if event.inaxes != self.subplot or event.button != 1:
            return
        if event.xdata is None or event.ydata is None:
            return
        self.circle_start = (event.xdata, event.ydata)
    
    def _on_circle_motion(self, event):
        """Handle circle selection motion with proper circular preview"""
        if not self.circle_start or event.inaxes != self.subplot:
            return
        
        if event.xdata is None or event.ydata is None:
            return
        
        # Remove previous preview
        if hasattr(self, 'circle_preview') and self.circle_preview:
            try:
                self.circle_preview.remove()
            except:
                pass
        
        # Calculate radius
        cx, cy = self.circle_start
        radius = np.sqrt((event.xdata - cx)**2 + (event.ydata - cy)**2)
        
        # Create circular preview
        self.circle_preview = patches.Circle(
            (cx, cy), radius, 
            fill=False, 
            edgecolor=self.roi_colors[ROIType.CIRCLE],
            linestyle='--',
            alpha=0.7,
            linewidth=2
        )
        self.subplot.add_patch(self.circle_preview)
        self.figure.canvas.draw_idle()
    
    def _on_circle_end(self, event):
        """Handle circle selection end with proper circular ROI"""
        if not self.circle_start or event.inaxes != self.subplot or event.button != 1:
            return
        
        if event.xdata is None or event.ydata is None:
            return
        
        cx, cy = self.circle_start
        radius = np.sqrt((event.xdata - cx)**2 + (event.ydata - cy)**2)
        
        # Ensure minimum radius
        radius = max(1, radius)
        
        roi = ROI(
            roi_type=ROIType.CIRCLE,
            coordinates={
                'cx': cx,
                'cy': cy,
                'radius': radius
            },
            label=f"Circle_{self.roi_counter + 1}",
            color=self.roi_colors[ROIType.CIRCLE]
        )
        
        self._add_roi(roi)
        self._log_roi_coordinates(roi)
        
        # Clean up
        self.circle_start = None
        if hasattr(self, 'circle_preview') and self.circle_preview:
            try:
                self.circle_preview.remove()
            except:
                pass
            self.circle_preview = None
    
    def _on_key_press(self, event):
        """Handle key press for multi-point selection"""
        if event.key == 'ctrl':
            if not self.multi_point_mode:
                self.multi_point_mode = True
                self._update_status("Multi-point mode: Click points, press Ctrl again or Esc to finish")
    
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
                coordinates={
                    'x': x_pixel,
                    'y': y_pixel
                },
                label=f"Point_{self.roi_counter + 1}",
                color=self.roi_colors[ROIType.POINT]
            )
            
            self._add_roi(roi)
            self._log_roi_coordinates(roi)
            self._update_status(f"Selected pixel at ({x_pixel}, {y_pixel})")
    
    def _add_point_to_multi_selection(self, x, y):
        """Add point to current multi-point selection"""
        if self.current_multi_point_roi is None:
            # Start new multi-point ROI
            self.current_multi_point_roi = {
                'points': [],
                'label': f"MultiPoint_{self.roi_counter + 1}",
                'color': self.roi_colors[ROIType.MULTI_POINT]
            }
        
        # Add point
        self.current_multi_point_roi['points'].append({'x': x, 'y': y})
        
        # Add visual preview
        preview = self.subplot.plot(
            x, y,
            marker='o',
            color=self.current_multi_point_roi['color'],
            markersize=8,
            markeredgewidth=2,
            markerfacecolor='none',
            alpha=0.7
        )[0]
        self.multi_point_previews.append(preview)
        
        # Add point label
        label_preview = self.subplot.annotate(
            f"{len(self.current_multi_point_roi['points'])}",
            (x, y),
            xytext=(5, 5), textcoords='offset points',
            fontsize=8, color=self.current_multi_point_roi['color'],
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7)
        )
        self.multi_point_previews.append(label_preview)
        
        self.figure.canvas.draw_idle()
        self._update_status(f"Multi-point: {len(self.current_multi_point_roi['points'])} points selected")
    
    def _finish_multi_point_selection(self):
        """Finish multi-point selection and create ROI"""
        if self.current_multi_point_roi and len(self.current_multi_point_roi['points']) > 0:
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
        """Add visual representation of ROI to the plot"""
        if roi.roi_type == ROIType.RECTANGLE:
            rect = patches.Rectangle(
                (roi.coordinates['x'], roi.coordinates['y']),
                roi.coordinates['width'],
                roi.coordinates['height'],
                fill=False,
                edgecolor=roi.color,
                linewidth=roi.linewidth,
                alpha=0.8
            )
            self.subplot.add_patch(rect)
        
        elif roi.roi_type == ROIType.CIRCLE:
            circle = patches.Circle(
                (roi.coordinates['cx'], roi.coordinates['cy']),
                roi.coordinates['radius'],
                fill=False,
                edgecolor=roi.color,
                linewidth=roi.linewidth,
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
                markerfacecolor='none',
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
        
        self.figure.canvas.draw_idle()
    
    def _log_roi_coordinates(self, roi: ROI):
        """Enhanced coordinate logging with pixel precision"""
        if roi.roi_type == ROIType.RECTANGLE:
            coords = f"({roi.coordinates['x']:.1f}, {roi.coordinates['y']:.1f}) " \
                    f"size: {roi.coordinates['width']:.1f}×{roi.coordinates['height']:.1f} pixels"
        elif roi.roi_type == ROIType.CIRCLE:
            coords = f"center: ({roi.coordinates['cx']:.1f}, {roi.coordinates['cy']:.1f}) " \
                    f"radius: {roi.coordinates['radius']:.1f} pixels"
        elif roi.roi_type == ROIType.POINT:
            coords = f"pixel: ({roi.coordinates['x']:.0f}, {roi.coordinates['y']:.0f})"
        elif roi.roi_type == ROIType.MULTI_POINT:
            point_count = len(roi.coordinates['points'])
            coords = f"{point_count} points: " + ", ".join([
                f"({p['x']:.0f},{p['y']:.0f})" for p in roi.coordinates['points'][:3]
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
        """Simple working statistics calculation"""
        stats = {}
        
        for roi in self.rois:
            try:
                if roi.roi_type == ROIType.POINT:
                    x, y = int(roi.coordinates['x']), int(roi.coordinates['y'])
                    
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
                    # For rectangles and circles
                    mask = roi.get_mask(image_data.shape[:2])
                    if np.any(mask):
                        roi_data = image_data[mask]
                        
                        # Handle color images
                        if len(roi_data.shape) > 1 and roi_data.shape[1] > 1:
                            # Color image - convert to grayscale
                            if roi_data.shape[1] == 3:  # RGB
                                roi_data = 0.299 * roi_data[:, 0] + 0.587 * roi_data[:, 1] + 0.114 * roi_data[:, 2]
                            else:
                                roi_data = np.mean(roi_data, axis=1)
                        
                        stats[roi.label] = {
                            'mean': float(np.mean(roi_data)),
                            'std': float(np.std(roi_data)),
                            'min': float(np.min(roi_data)),
                            'max': float(np.max(roi_data)),
                            'pixel_count': int(np.sum(mask)),
                            'roi_type': roi.roi_type.value
                        }
                    else:
                        stats[roi.label] = {
                            'error': 'No pixels in mask',
                            'roi_type': roi.roi_type.value
                        }
            
            except Exception as e:
                self.logger.error(f"Error calculating statistics for {roi.label}: {e}")
                stats[roi.label] = {
                    'error': f'Calculation failed: {str(e)}',
                    'roi_type': getattr(roi, 'roi_type', ROIType.POINT).value
                }
        
        return stats
    
    def _update_status(self, message: str):
        """Update status through callback"""
        if self.status_callback:
            self.status_callback(message)
        else:
            # Fallback: just log the message if no callback
            self.logger.info(f"ROI Status: {message}")
    
    def export_rois(self) -> List[Dict[str, Any]]:
        """Export ROI data for saving/analysis"""
        return [
            {
                'label': roi.label,
                'type': roi.roi_type.value,
                'coordinates': roi.coordinates,
                'color': roi.color
            }
            for roi in self.rois
        ]