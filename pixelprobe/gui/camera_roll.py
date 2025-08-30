"""
Improved Camera Roll Interface for PixelProbe
Optimized for handling large numbers of frames (1000+) efficiently
"""
import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed


class CameraRollInterface:
    """Optimized camera roll-style interface for navigating multiple frames"""
    
    def __init__(self, main_app):
        self.main_app = main_app
        self.logger = logging.getLogger(__name__)
        self.loaded_arrays: Dict[int, np.ndarray] = {}
        self.current_frame_index = 0
        self.frame_keys = []  # Ordered list of frame numbers
        self.thumbnail_size = (80, 60)  # Width, height for thumbnails
        self.thumbnails = {}  # Cache for thumbnail images
        self.thumbnail_buttons = {}  # References to thumbnail buttons
        
        # Performance optimization settings
        self.max_visible_thumbnails = 200  # Max thumbnails to show at once
        self.thumbnail_batch_size = 50    # Process thumbnails in batches
        self.current_thumbnail_start = 0   # Start index for visible thumbnails
        self.thumbnail_loading_active = False
        
        # Camera roll UI elements (will be created when needed)
        self.camera_roll_frame = None
        self.thumbnail_frame = None
        self.nav_frame = None
        self.frame_info_label = None
        self.is_visible = False
        self.progress_label = None
    
    def load_multiple_frames(self, arrays_dict: Dict[int, np.ndarray]):
        """Load multiple frames into the camera roll - optimized version"""
        self.logger.info(f"Loading {len(arrays_dict)} frames into camera roll")
        
        self.loaded_arrays = arrays_dict.copy()
        self.frame_keys = sorted(arrays_dict.keys())
        self.current_frame_index = 0
        
        # Show camera roll interface first
        self._show_camera_roll()
        
        # Display first frame immediately
        if self.frame_keys:
            self._display_frame(self.frame_keys[0])
        
        # Generate thumbnails in background with progress
        self._generate_thumbnails_async()
    
    def _generate_thumbnails_async(self):
        """Generate thumbnails asynchronously with progress updates"""
        if self.thumbnail_loading_active:
            return
            
        self.thumbnail_loading_active = True
        
        # Clear existing thumbnails
        self.thumbnails.clear()
        self.thumbnail_buttons.clear()
        
        # Show progress
        if self.progress_label:
            self.progress_label.configure(text="Loading thumbnails...")
        
        # Start background thread for thumbnail generation
        def generate_thumbnails():
            try:
                self.logger.info(f"Starting thumbnail generation for {len(self.frame_keys)} frames")
                
                # Process thumbnails in batches to avoid memory issues
                batch_size = self.thumbnail_batch_size
                total_frames = len(self.frame_keys)
                
                for batch_start in range(0, total_frames, batch_size):
                    batch_end = min(batch_start + batch_size, total_frames)
                    batch_frames = self.frame_keys[batch_start:batch_end]
                    
                    # Generate thumbnails for this batch
                    batch_thumbnails = {}
                    for frame_num in batch_frames:
                        try:
                            array = self.loaded_arrays[frame_num]
                            thumbnail = self._create_single_thumbnail(array)
                            if thumbnail:
                                batch_thumbnails[frame_num] = thumbnail
                        except Exception as e:
                            self.logger.warning(f"Failed to create thumbnail for frame {frame_num}: {e}")
                    
                    # Update UI in main thread
                    self.main_app.root.after(0, self._update_thumbnails_batch, batch_thumbnails, batch_end, total_frames)
                    
                    # Small delay to prevent UI freezing
                    if batch_end < total_frames:
                        import time
                        time.sleep(0.01)
                
                # Finalize UI
                self.main_app.root.after(0, self._finalize_thumbnail_loading)
                
            except Exception as e:
                self.logger.error(f"Error generating thumbnails: {e}")
                self.main_app.root.after(0, self._finalize_thumbnail_loading)
        
        # Start in background thread
        thumbnail_thread = threading.Thread(target=generate_thumbnails, daemon=True)
        thumbnail_thread.start()
    
    def _create_single_thumbnail(self, array: np.ndarray) -> Optional[ImageTk.PhotoImage]:
        """Create a single thumbnail from array data"""
        try:
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
            return ImageTk.PhotoImage(thumbnail)
            
        except Exception as e:
            self.logger.warning(f"Failed to create thumbnail: {e}")
            return None
    
    def _update_thumbnails_batch(self, batch_thumbnails: Dict[int, ImageTk.PhotoImage], completed: int, total: int):
        """Update UI with a batch of thumbnails (called from main thread)"""
        try:
            # Add batch to thumbnails cache
            self.thumbnails.update(batch_thumbnails)
            
            # Update progress
            if self.progress_label:
                progress_pct = int((completed / total) * 100)
                self.progress_label.configure(text=f"Loading thumbnails... {progress_pct}% ({completed}/{total})")
            
            # Update thumbnail display if this is the first batch or we're in the visible range
            if completed <= self.max_visible_thumbnails or len(self.thumbnails) <= self.max_visible_thumbnails:
                self._update_thumbnail_display()
                
        except Exception as e:
            self.logger.error(f"Error updating thumbnail batch: {e}")
    
    def _finalize_thumbnail_loading(self):
        """Finalize thumbnail loading (called from main thread)"""
        self.thumbnail_loading_active = False
        
        if self.progress_label:
            self.progress_label.configure(text=f"Loaded {len(self.frame_keys)} frames")
        
        # Make sure all visible thumbnails are displayed
        self._update_thumbnail_display()
        
        self.logger.info(f"Finished loading {len(self.thumbnails)} thumbnails")
    
    def _show_camera_roll(self):
        """Show the camera roll interface"""
        if self.is_visible:
            return
            
        # Create camera roll frame at bottom of main content
        self.camera_roll_frame = ctk.CTkFrame(self.main_app.main_frame, height=180)  # Increased height
        self.camera_roll_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(10, 0))
        self.camera_roll_frame.grid_columnconfigure(1, weight=1)
        
        # Top row: Navigation controls and progress
        self.nav_frame = ctk.CTkFrame(self.camera_roll_frame)
        self.nav_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 0))
        self.nav_frame.grid_columnconfigure(2, weight=1)  # Make center area expandable
        
        # Navigation buttons (left side)
        nav_left_frame = ctk.CTkFrame(self.nav_frame)
        nav_left_frame.grid(row=0, column=0, sticky="w")
        
        # Previous button
        self.prev_btn = ctk.CTkButton(
            nav_left_frame,
            text="◀ Prev",
            command=self._prev_frame,
            width=70,
            height=30
        )
        self.prev_btn.pack(side='left', padx=2)
        
        # Next button
        self.next_btn = ctk.CTkButton(
            nav_left_frame,
            text="Next ▶",
            command=self._next_frame,
            width=70,
            height=30
        )
        self.next_btn.pack(side='left', padx=2)
        
        # Jump buttons
        self.jump_start_btn = ctk.CTkButton(
            nav_left_frame,
            text="⏮ Start",
            command=self._jump_to_start,
            width=60,
            height=30
        )
        self.jump_start_btn.pack(side='left', padx=2)
        
        self.jump_end_btn = ctk.CTkButton(
            nav_left_frame,
            text="End ⏭",
            command=self._jump_to_end,
            width=60,
            height=30
        )
        self.jump_end_btn.pack(side='left', padx=2)
        
        # Center: Frame info and progress
        info_frame = ctk.CTkFrame(self.nav_frame)
        info_frame.grid(row=0, column=2, sticky="ew", padx=20)
        
        self.frame_info_label = ctk.CTkLabel(
            info_frame,
            text=f"Frame {self.frame_keys[0] if self.frame_keys else 0} (1 of {len(self.frame_keys)})",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.frame_info_label.pack(pady=5)
        
        self.progress_label = ctk.CTkLabel(
            info_frame,
            text="Preparing thumbnails...",
            font=ctk.CTkFont(size=10)
        )
        self.progress_label.pack()
        
        # Right side: Close and navigation controls
        nav_right_frame = ctk.CTkFrame(self.nav_frame)
        nav_right_frame.grid(row=0, column=3, sticky="e")
        
        # Thumbnail navigation (for large numbers)
        if len(self.frame_keys) > self.max_visible_thumbnails:
            self.thumb_nav_label = ctk.CTkLabel(
                nav_right_frame,
                text=f"Showing 1-{min(self.max_visible_thumbnails, len(self.frame_keys))} of {len(self.frame_keys)}",
                font=ctk.CTkFont(size=10)
            )
            self.thumb_nav_label.pack(side='left', padx=5)
            
            self.prev_thumbs_btn = ctk.CTkButton(
                nav_right_frame,
                text="◀",
                command=self._prev_thumbnails,
                width=30,
                height=30
            )
            self.prev_thumbs_btn.pack(side='left', padx=1)
            
            self.next_thumbs_btn = ctk.CTkButton(
                nav_right_frame,
                text="▶",
                command=self._next_thumbnails,
                width=30,
                height=30
            )
            self.next_thumbs_btn.pack(side='left', padx=1)
        
        # Close camera roll button
        self.close_btn = ctk.CTkButton(
            nav_right_frame,
            text="✕",
            command=self._hide_camera_roll,
            width=30,
            height=30,
            fg_color="red",
            hover_color="darkred"
        )
        self.close_btn.pack(side='right', padx=(10, 0))
        
        # Bottom row: Thumbnail strip frame with scrollable area
        self.thumbnail_container = ctk.CTkFrame(self.camera_roll_frame)
        self.thumbnail_container.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.thumbnail_container.grid_columnconfigure(0, weight=1)
        
        # Create scrollable thumbnail frame
        self.thumbnail_canvas = tk.Canvas(
            self.thumbnail_container,
            height=110,  # Increased height
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
        
        self.is_visible = True
        
        # Bind keyboard shortcuts
        self.main_app.root.bind('<Left>', lambda e: self._prev_frame())
        self.main_app.root.bind('<Right>', lambda e: self._next_frame())
        self.main_app.root.bind('<Home>', lambda e: self._jump_to_start())
        self.main_app.root.bind('<End>', lambda e: self._jump_to_end())
        self.main_app.root.bind('<Escape>', lambda e: self._hide_camera_roll())
    
    def _update_thumbnail_display(self):
        """Update the thumbnail display with current visible range"""
        try:
            # Clear existing thumbnail buttons
            for widget in self.thumbnail_frame.winfo_children():
                widget.destroy()
            self.thumbnail_buttons.clear()
            
            # Determine visible range
            start_idx = self.current_thumbnail_start
            end_idx = min(start_idx + self.max_visible_thumbnails, len(self.frame_keys))
            visible_frames = self.frame_keys[start_idx:end_idx]
            
            # Create thumbnail buttons for visible frames
            for i, frame_num in enumerate(visible_frames):
                if frame_num in self.thumbnails:
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
            
            # Update thumbnail selection
            self._update_thumbnail_selection()
            
            # Update thumbnail navigation label
            if hasattr(self, 'thumb_nav_label') and self.thumb_nav_label:
                self.thumb_nav_label.configure(
                    text=f"Showing {start_idx + 1}-{end_idx} of {len(self.frame_keys)}"
                )
                
        except Exception as e:
            self.logger.error(f"Error updating thumbnail display: {e}")
    
    def _prev_thumbnails(self):
        """Show previous batch of thumbnails"""
        if self.current_thumbnail_start > 0:
            self.current_thumbnail_start = max(0, self.current_thumbnail_start - self.max_visible_thumbnails)
            self._update_thumbnail_display()
    
    def _next_thumbnails(self):
        """Show next batch of thumbnails"""
        if self.current_thumbnail_start + self.max_visible_thumbnails < len(self.frame_keys):
            self.current_thumbnail_start += self.max_visible_thumbnails
            self._update_thumbnail_display()
    
    def _jump_to_start(self):
        """Jump to first frame"""
        if self.frame_keys:
            self.current_frame_index = 0
            self._display_frame(self.frame_keys[0])
            self._update_thumbnail_selection()
            self._scroll_to_current_frame()
    
    def _jump_to_end(self):
        """Jump to last frame"""
        if self.frame_keys:
            self.current_frame_index = len(self.frame_keys) - 1
            self._display_frame(self.frame_keys[-1])
            self._update_thumbnail_selection()
            self._scroll_to_current_frame()
    
    def _scroll_to_current_frame(self):
        """Ensure current frame is in visible thumbnail range"""
        current_frame = self.frame_keys[self.current_frame_index]
        current_global_index = self.current_frame_index
        
        # Check if current frame is outside visible range
        visible_start = self.current_thumbnail_start
        visible_end = self.current_thumbnail_start + self.max_visible_thumbnails
        
        if current_global_index < visible_start or current_global_index >= visible_end:
            # Adjust visible range to include current frame
            self.current_thumbnail_start = max(0, current_global_index - self.max_visible_thumbnails // 2)
            self._update_thumbnail_display()
    
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
            self._scroll_to_current_frame()
    
    def _next_frame(self):
        """Navigate to next frame"""
        if self.current_frame_index < len(self.frame_keys) - 1:
            self.current_frame_index += 1
            current_frame = self.frame_keys[self.current_frame_index]
            self._display_frame(current_frame)
            self._update_thumbnail_selection()
            self._scroll_to_current_frame()
    
    def _select_frame(self, frame_num: int):
        """Select specific frame by number"""
        if frame_num in self.frame_keys:
            self.current_frame_index = self.frame_keys.index(frame_num)
            self._display_frame(frame_num)
            self._update_thumbnail_selection()
    
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
        self.main_app.root.unbind('<Home>')
        self.main_app.root.unbind('<End>')
        self.main_app.root.unbind('<Escape>')
        
        self.is_visible = False
        self.thumbnail_loading_active = False
        
        # Clear references
        self.thumbnail_buttons.clear()
        self.thumbnails.clear()
        
        self.main_app.update_status("Camera roll hidden")
    
    def is_active(self) -> bool:
        """Check if camera roll is currently active"""
        return self.is_visible and len(self.loaded_arrays) > 1