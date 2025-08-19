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
    POLYGON = "polygon"


@dataclass
class ROI:
    """Data class for storing ROI information"""
    roi_type: ROIType
    coordinates: Dict[str, float]  # Flexible coordinate storage
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
        
        elif self.roi_type == ROIType.POINT:
            x, y = self.coordinates['x'], self.coordinates['y']
            return int(x), int(y), int(x + 1), int(y + 1)
        
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
        
        return mask
    
    def get_pixel_coordinates(self) -> List[Tuple[int, int]]:
        """Get list of (x, y) pixel coordinates within this ROI"""
        if self.roi_type == ROIType.POINT:
            return [(int(self.coordinates['x']), int(self.coordinates['y']))]
        
        # For other types, we'll implement this when needed
        x_min, y_min, x_max, y_max = self.get_bounds()
        pixels = []
        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                pixels.append((x, y))
        return pixels


class ROISelector:
    """Main ROI selection class for handling interactive region selection"""
    
    def __init__(self, figure, subplot, status_callback=None):
        """
        Initialize ROI selector
        
        Args:
            figure: Matplotlib figure
            subplot: Matplotlib subplot/axes
            status_callback: Function to call for status updates
        """
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
        self.current_roi_patch = None
        
        # Event handlers storage
        self.event_handlers = {}
        
        # Colors for different ROI types
        self.roi_colors = {
            ROIType.RECTANGLE: "red",
            ROIType.CIRCLE: "blue", 
            ROIType.POINT: "green",
            ROIType.POLYGON: "orange"
        }
        
        self.logger.info("ROI Selector initialized")
    
    def set_roi_type(self, roi_type: ROIType):
        """Set the current ROI selection type"""
        self.current_roi_type = roi_type
        self._update_status(f"ROI selection mode: {roi_type.value}")
        self.logger.info(f"ROI type set to {roi_type.value}")
    
    def activate_selection(self):
        """Activate ROI selection mode"""
        if self.selection_active:
            return
        
        self.selection_active = True
        self._setup_event_handlers()
        self._update_status(f"ROI selection active - Click and drag to select {self.current_roi_type.value}")
        self.logger.info("ROI selection activated")
    
    def deactivate_selection(self):
        """Deactivate ROI selection mode"""
        if not self.selection_active:
            return
        
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
        """Setup rectangle selection using matplotlib RectangleSelector"""
        self.current_selector = RectangleSelector(
            self.subplot,
            self._on_rectangle_select,
            useblit=True,
            button=[1],  # Only left mouse button
            minspanx=5,
            minspany=5,
            spancoords='pixels',
            interactive=True
        )
    
    def _setup_circle_selector(self):
        """Setup circle selection using mouse events"""
        self.event_handlers['button_press'] = self.figure.canvas.mpl_connect(
            'button_press_event', self._on_circle_start
        )
        self.event_handlers['motion_notify'] = self.figure.canvas.mpl_connect(
            'motion_notify_event', self._on_circle_motion
        )
        self.event_handlers['button_release'] = self.figure.canvas.mpl_connect(
            'button_release_event', self._on_circle_end
        )
        self.circle_start = None
        self.circle_preview = None
    
    def _setup_point_selector(self):
        """Setup point selection using click events"""
        self.event_handlers['button_press'] = self.figure.canvas.mpl_connect(
            'button_press_event', self._on_point_click
        )
    
    def _cleanup_event_handlers(self):
        """Clean up all event handlers"""
        if self.current_selector:
            self.current_selector.set_active(False)
            self.current_selector = None
        
        for event_id in self.event_handlers.values():
            self.figure.canvas.mpl_disconnect(event_id)
        self.event_handlers.clear()
        
        # Clean up any preview elements
        if hasattr(self, 'circle_preview') and self.circle_preview:
            self.circle_preview.remove()
            self.circle_preview = None
    
    def _on_rectangle_select(self, eclick, erelease):
        """Handle rectangle selection completion"""
        x_min, x_max = sorted([eclick.xdata, erelease.xdata])
        y_min, y_max = sorted([eclick.ydata, erelease.ydata])
        
        width = x_max - x_min
        height = y_max - y_min
        
        roi = ROI(
            roi_type=ROIType.RECTANGLE,
            coordinates={
                'x': x_min,
                'y': y_min,
                'width': width,
                'height': height
            },
            label=f"Rectangle_{self.roi_counter}",
            color=self.roi_colors[ROIType.RECTANGLE]
        )
        
        self._add_roi(roi)
        self._log_roi_coordinates(roi)
    
    def _on_circle_start(self, event):
        """Handle circle selection start"""
        if event.inaxes != self.subplot or event.button != 1:
            return
        self.circle_start = (event.xdata, event.ydata)
    
    def _on_circle_motion(self, event):
        """Handle circle selection motion (preview)"""
        if not self.circle_start or event.inaxes != self.subplot:
            return
        
        # Remove previous preview
        if self.circle_preview:
            self.circle_preview.remove()
        
        # Calculate radius
        cx, cy = self.circle_start
        radius = np.sqrt((event.xdata - cx)**2 + (event.ydata - cy)**2)
        
        # Create preview circle
        self.circle_preview = patches.Circle(
            (cx, cy), radius, 
            fill=False, 
            edgecolor=self.roi_colors[ROIType.CIRCLE],
            linestyle='--',
            alpha=0.7
        )
        self.subplot.add_patch(self.circle_preview)
        self.figure.canvas.draw_idle()
    
    def _on_circle_end(self, event):
        """Handle circle selection end"""
        if not self.circle_start or event.inaxes != self.subplot or event.button != 1:
            return
        
        cx, cy = self.circle_start
        radius = np.sqrt((event.xdata - cx)**2 + (event.ydata - cy)**2)
        
        roi = ROI(
            roi_type=ROIType.CIRCLE,
            coordinates={
                'cx': cx,
                'cy': cy,
                'radius': radius
            },
            label=f"Circle_{self.roi_counter}",
            color=self.roi_colors[ROIType.CIRCLE]
        )
        
        self._add_roi(roi)
        self._log_roi_coordinates(roi)
        
        # Clean up
        self.circle_start = None
        if self.circle_preview:
            self.circle_preview.remove()
            self.circle_preview = None
    
    def _on_point_click(self, event):
        """Handle point selection"""
        if event.inaxes != self.subplot or event.button != 1:
            return
        
        roi = ROI(
            roi_type=ROIType.POINT,
            coordinates={
                'x': event.xdata,
                'y': event.ydata
            },
            label=f"Point_{self.roi_counter}",
            color=self.roi_colors[ROIType.POINT]
        )
        
        self._add_roi(roi)
        self._log_roi_coordinates(roi)
    
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
                linewidth=roi.linewidth
            )
            self.subplot.add_patch(rect)
        
        elif roi.roi_type == ROIType.CIRCLE:
            circle = patches.Circle(
                (roi.coordinates['cx'], roi.coordinates['cy']),
                roi.coordinates['radius'],
                fill=False,
                edgecolor=roi.color,
                linewidth=roi.linewidth
            )
            self.subplot.add_patch(circle)
        
        elif roi.roi_type == ROIType.POINT:
            self.subplot.plot(
                roi.coordinates['x'],
                roi.coordinates['y'],
                marker='o',
                color=roi.color,
                markersize=8,
                markeredgewidth=2,
                markerfacecolor='none'
            )
        
        self.figure.canvas.draw_idle()
    
    def _log_roi_coordinates(self, roi: ROI):
        """Log ROI coordinates to status"""
        if roi.roi_type == ROIType.RECTANGLE:
            coords = f"({roi.coordinates['x']:.1f}, {roi.coordinates['y']:.1f}) " \
                    f"size: {roi.coordinates['width']:.1f}×{roi.coordinates['height']:.1f}"
        elif roi.roi_type == ROIType.CIRCLE:
            coords = f"center: ({roi.coordinates['cx']:.1f}, {roi.coordinates['cy']:.1f}) " \
                    f"radius: {roi.coordinates['radius']:.1f}"
        elif roi.roi_type == ROIType.POINT:
            coords = f"({roi.coordinates['x']:.1f}, {roi.coordinates['y']:.1f})"
        
        self._update_status(f"{roi.label}: {coords}")
    
    def clear_rois(self):
        """Clear all ROIs"""
        self.rois.clear()
        self.roi_counter = 0
        
        # Clear visual elements - recreate the plot
        self.subplot.clear()
        self._update_status("All ROIs cleared")
        self.logger.info("All ROIs cleared")
    
    def get_roi_statistics(self, image_data: np.ndarray) -> Dict[str, Dict[str, float]]:
        """Calculate statistics for all ROIs on given image data"""
        stats = {}
        
        for roi in self.rois:
            if roi.roi_type == ROIType.POINT:
                x, y = int(roi.coordinates['x']), int(roi.coordinates['y'])
                if 0 <= y < image_data.shape[0] and 0 <= x < image_data.shape[1]:
                    pixel_value = image_data[y, x]
                    stats[roi.label] = {
                        'pixel_value': float(pixel_value),
                        'coordinates': f"({x}, {y})"
                    }
            else:
                # For regions, calculate statistics
                mask = roi.get_mask(image_data.shape[:2])
                if np.any(mask):
                    roi_data = image_data[mask]
                    stats[roi.label] = {
                        'mean': float(np.mean(roi_data)),
                        'std': float(np.std(roi_data)),
                        'min': float(np.min(roi_data)),
                        'max': float(np.max(roi_data)),
                        'pixel_count': int(np.sum(mask))
                    }
        
        return stats
    
    def _update_status(self, message: str):
        """Update status through callback"""
        if self.status_callback:
            self.status_callback(message)
    
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