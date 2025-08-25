import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class CameraRollInterface:
    """Camera roll-style interface for navigating multiple frames"""
    
    def __init__(self, main_app):
        self.main_app = main_app
        self.loaded_arrays: Dict[int, np.ndarray] = {}
        self.current_frame_index = 0
        self.frame_keys = []  # Ordered list of frame numbers
        self.thumbnail_size = (80, 60)  # Width, height for thumbnails
        self.thumbnails = {}  # Cache for thumbnail images
        self.thumbnail_buttons = {}  # References to thumbnail buttons
        
        # Camera roll UI elements (will be created when needed)
        self.camera_roll_frame = None
        self.thumbnail_frame = None
        self.nav_frame = None
        self.frame_info_label = None
        self.is_visible = False
    
    def load_multiple_frames(self, arrays_dict: Dict[int, np.ndarray]):
        """Load multiple frames into the camera roll"""
        self.loaded_arrays = arrays_dict.copy()
        self.frame_keys = sorted(arrays_dict.keys())
        self.current_frame_index = 0
        
        # Generate thumbnails
        self._generate_thumbnails()
        
        # Show camera roll interface
        self._show_camera_roll()
        
        # Display first frame
        if self.frame_keys:
            self._display_frame(self.frame_keys[0])
    
    def _generate_thumbnails(self):
        """Generate thumbnail images for all frames"""
        self.thumbnails.clear()
        
        for frame_num in self.frame_keys:
            array = self.loaded_arrays[frame_num]
            
            # Convert array to displayable format
            display_array = self.main_app._array_to_display_image(array)
            
            # Create PIL Image
            if len(display_array.shape) == 2:
                # Grayscale
                pil_image = Image.fromarray(display_array, mode='L')
            else:
                # Color
                pil_image = Image.fromarray(display_array)
            
            # Resize to thumbnail size
            thumbnail = pil_image.resize(self.thumbnail_size, Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage for tkinter
            photo = ImageTk.PhotoImage(thumbnail)
            self.thumbnails[frame_num] = photo
    
    def _show_camera_roll(self):
        """Show the camera roll interface"""
        if self.is_visible:
            return
            
        # Create camera roll frame at bottom of main content
        self.camera_roll_frame = ctk.CTkFrame(self.main_app.main_frame, height=150)
        self.camera_roll_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(10, 0))
        self.camera_roll_frame.grid_columnconfigure(1, weight=1)
        
        # Navigation controls
        self.nav_frame = ctk.CTkFrame(self.camera_roll_frame)
        self.nav_frame.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        # Previous button
        self.prev_btn = ctk.CTkButton(
            self.nav_frame,
            text="◀ Prev",
            command=self._prev_frame,
            width=70,
            height=30
        )
        self.prev_btn.pack(side='left', padx=2)
        
        # Frame info
        self.frame_info_label = ctk.CTkLabel(
            self.nav_frame,
            text=f"Frame 1 of {len(self.frame_keys)}",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.frame_info_label.pack(side='left', padx=10)
        
        # Next button
        self.next_btn = ctk.CTkButton(
            self.nav_frame,
            text="Next ▶",
            command=self._next_frame,
            width=70,
            height=30
        )
        self.next_btn.pack(side='left', padx=2)
        
        # Close camera roll button
        self.close_btn = ctk.CTkButton(
            self.nav_frame,
            text="✕",
            command=self._hide_camera_roll,
            width=30,
            height=30,
            fg_color="red",
            hover_color="darkred"
        )
        self.close_btn.pack(side='right', padx=(20, 0))
        
        # Thumbnail strip frame with scrollable area
        self.thumbnail_container = ctk.CTkFrame(self.camera_roll_frame)
        self.thumbnail_container.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        self.thumbnail_container.grid_columnconfigure(0, weight=1)
        
        # Create scrollable thumbnail frame
        self.thumbnail_canvas = tk.Canvas(
            self.thumbnail_container,
            height=100,
            bg="#212121",
            highlightthickness=0
        )
        self.thumbnail_scrollbar = ctk.CTkScrollbar(
            self.thumbnail_container,
            orientation="horizontal",
            command=self.thumbnail_canvas.xview
        )
        self.thumbnail_canvas.configure(xscrollcommand=self.thumbnail_scrollbar.set)
        
        self.thumbnail_frame = tk.Frame(self.thumbnail_canvas, bg="#212121")
        self.thumbnail_canvas.create_window((0, 0), window=self.thumbnail_frame, anchor="nw")
        
        self.thumbnail_canvas.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        self.thumbnail_scrollbar.pack(side="bottom", fill="x", padx=5)
        
        # Create thumbnail buttons
        self._create_thumbnail_buttons()
        
        self.is_visible = True
        
        # Bind keyboard shortcuts
        self.main_app.root.bind('<Left>', lambda e: self._prev_frame())
        self.main_app.root.bind('<Right>', lambda e: self._next_frame())
        self.main_app.root.bind('<Escape>', lambda e: self._hide_camera_roll())
    
    def _create_thumbnail_buttons(self):
        """Create clickable thumbnail buttons"""
        self.thumbnail_buttons.clear()
        
        for i, frame_num in enumerate(self.frame_keys):
            # Create frame for each thumbnail
            thumb_frame = tk.Frame(self.thumbnail_frame, bg="#212121")
            thumb_frame.pack(side='left', padx=2, pady=2)
            
            # Thumbnail button
            thumb_btn = tk.Button(
                thumb_frame,
                image=self.thumbnails[frame_num],
                command=lambda fn=frame_num: self._select_frame(fn),
                relief='raised',
                borderwidth=2,
                bg="#404040",
                activebackground="#606060"
            )
            thumb_btn.pack()
            
            # Frame number label
            label = tk.Label(
                thumb_frame,
                text=f"Frame {frame_num}",
                font=("Arial", 8),
                fg="white",
                bg="#212121"
            )
            label.pack()
            
            self.thumbnail_buttons[frame_num] = thumb_btn
        
        # Update scroll region
        self.thumbnail_frame.update_idletasks()
        self.thumbnail_canvas.configure(scrollregion=self.thumbnail_canvas.bbox("all"))
        
        # Highlight first thumbnail
        self._update_thumbnail_selection()
    
    def _update_thumbnail_selection(self):
        """Update visual selection of current thumbnail"""
        current_frame = self.frame_keys[self.current_frame_index]
        
        # Reset all thumbnails to normal
        for frame_num, btn in self.thumbnail_buttons.items():
            if frame_num == current_frame:
                btn.configure(relief='solid', borderwidth=3, bg="#4CAF50")
            else:
                btn.configure(relief='raised', borderwidth=2, bg="#404040")
    
    def _prev_frame(self):
        """Navigate to previous frame"""
        if self.current_frame_index > 0:
            self.current_frame_index -= 1
            current_frame = self.frame_keys[self.current_frame_index]
            self._display_frame(current_frame)
            self._update_thumbnail_selection()
            self._scroll_to_current_thumbnail()
    
    def _next_frame(self):
        """Navigate to next frame"""
        if self.current_frame_index < len(self.frame_keys) - 1:
            self.current_frame_index += 1
            current_frame = self.frame_keys[self.current_frame_index]
            self._display_frame(current_frame)
            self._update_thumbnail_selection()
            self._scroll_to_current_thumbnail()
    
    def _select_frame(self, frame_num: int):
        """Select specific frame by number"""
        if frame_num in self.frame_keys:
            self.current_frame_index = self.frame_keys.index(frame_num)
            self._display_frame(frame_num)
            self._update_thumbnail_selection()
    
    def _scroll_to_current_thumbnail(self):
        """Scroll thumbnail strip to show current frame"""
        if not self.thumbnail_buttons:
            return
            
        current_frame = self.frame_keys[self.current_frame_index]
        current_btn = self.thumbnail_buttons[current_frame]
        
        # Get button position
        btn_x = current_btn.winfo_x()
        canvas_width = self.thumbnail_canvas.winfo_width()
        scroll_width = self.thumbnail_frame.winfo_width()
        
        # Calculate scroll position to center the button
        if scroll_width > canvas_width:
            center_x = btn_x + (self.thumbnail_size[0] / 2)
            scroll_pos = (center_x - canvas_width / 2) / scroll_width
            scroll_pos = max(0, min(1, scroll_pos))
            self.thumbnail_canvas.xview_moveto(scroll_pos)
    
    def _display_frame(self, frame_num: int):
        """Display the selected frame in main view"""
        if frame_num not in self.loaded_arrays:
            return
        
        array = self.loaded_arrays[frame_num]
        display_image = self.main_app._array_to_display_image(array)
        
        # Update main app's current data
        self.main_app.current_array = array
        self.main_app.current_image = display_image
        
        # Display in main view
        self.main_app.display_image(display_image, f"Frame {frame_num}")
        
        # Update frame info
        if self.frame_info_label:
            self.frame_info_label.configure(
                text=f"Frame {frame_num} ({self.current_frame_index + 1} of {len(self.frame_keys)})"
            )
        
        # Update status
        self.main_app.update_status(
            f"Displaying frame {frame_num} - Shape: {array.shape} - "
            f"Frame {self.current_frame_index + 1} of {len(self.frame_keys)}"
        )
    
    def _hide_camera_roll(self):
        """Hide the camera roll interface"""
        if not self.is_visible:
            return
            
        if self.camera_roll_frame:
            self.camera_roll_frame.destroy()
            self.camera_roll_frame = None
        
        # Unbind keyboard shortcuts
        self.main_app.root.unbind('<Left>')
        self.main_app.root.unbind('<Right>')
        self.main_app.root.unbind('<Escape>')
        
        self.is_visible = False
        
        # Clear references
        self.thumbnail_buttons.clear()
        self.thumbnails.clear()
        
        self.main_app.update_status("Camera roll hidden")
    
    def is_active(self) -> bool:
        """Check if camera roll is currently active"""
        return self.is_visible and len(self.loaded_arrays) > 1
