"""
Array selection dialog for PixelProbe - Simple fixes: narrower window, bigger font
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional, List, Tuple
import customtkinter as ctk


class ArraySelectionDialog:
    """Dialog for selecting array directory and item numbers with improved UI"""
    
    def __init__(self, parent, array_handler):
        self.parent = parent
        self.array_handler = array_handler
        self.result = None
        self.dialog = None
        
    def show(self) -> Optional[Tuple[List[int], str]]:
        """Show the array selection dialog with improved sizing"""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("PixelProbe - Array Data Selection")
        
        # Set window size - clean proportions
        self.dialog.geometry("1000x680")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Set minimum size to prevent shrinking
        self.dialog.minsize(1000, 680)
        
        # Center the window
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (1000 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (680 // 2)
        self.dialog.geometry(f"1000x680+{x}+{y}")
        
        # Configure grid weights for two columns
        self.dialog.grid_columnconfigure(0, weight=0)  # Fixed width left column
        self.dialog.grid_columnconfigure(1, weight=1)  # Expanding right column
        self.dialog.grid_rowconfigure(0, weight=1)
        
        self._create_widgets()
        self.dialog.wait_window()
        return self.result
    
    def _create_widgets(self):
        """Create dialog widgets with clean, readable design"""
        # LEFT COLUMN - Controls (fixed width)
        left_frame = ctk.CTkFrame(self.dialog, width=350)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        left_frame.grid_propagate(False)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(3, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            left_frame, 
            text="Array Data Selection", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.grid(row=0, column=0, pady=(20, 25), sticky="ew")
        
        # Directory information
        dir_info_frame = ctk.CTkFrame(left_frame)
        dir_info_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 20))
        
        dir_title = ctk.CTkLabel(
            dir_info_frame,
            text="Directory Information",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        dir_title.pack(pady=(15, 10))
        
        # Directory path
        current_dir = self.array_handler.current_directory if hasattr(self.array_handler, 'current_directory') else "No directory selected"
        dir_path_label = ctk.CTkLabel(
            dir_info_frame,
            text=f"{current_dir}",
            font=ctk.CTkFont(size=10),
            wraplength=300
        )
        dir_path_label.pack(pady=(0, 8))
        
        # Available items count
        available_items = self.array_handler.get_available_items()
        items_count_label = ctk.CTkLabel(
            dir_info_frame,
            text=f"{len(available_items)} items ({min(available_items) if available_items else 'N/A'} - {max(available_items) if available_items else 'N/A'})",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        items_count_label.pack(pady=(0, 15))
        
        # Operation mode
        mode_frame = ctk.CTkFrame(left_frame)
        mode_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 20))
        
        mode_title = ctk.CTkLabel(
            mode_frame,
            text="Operation Mode",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        mode_title.pack(pady=(15, 12))
        
        self.operation_mode = tk.StringVar(value="single")
        
        modes = [
            ("single", "Single Item"),
            ("multiple", "Multiple Items"),
            ("average", "Frame Averaging")
        ]
        
        for value, description in modes:
            radio = ctk.CTkRadioButton(
                mode_frame,
                text=description,
                variable=self.operation_mode,
                value=value,
                font=ctk.CTkFont(size=12)
            )
            radio.pack(pady=6, anchor="w", padx=20)
        
        # Spacer
        spacer = ctk.CTkFrame(left_frame, height=1, fg_color="transparent")
        spacer.grid(row=3, column=0, sticky="ew")
        
        # Action buttons
        button_container = ctk.CTkFrame(left_frame, fg_color="transparent")
        button_container.grid(row=4, column=0, sticky="ew", padx=15, pady=(0, 25))
        
        load_btn = ctk.CTkButton(
            button_container,
            text="Load Items",
            command=self._ok_clicked,
            font=ctk.CTkFont(size=14, weight="bold"),
            width=180,
            height=40,
            fg_color="#2E7D32",  # Dark green
            hover_color="#1B5E20"
        )
        load_btn.pack(pady=(0, 10))
        
        cancel_btn = ctk.CTkButton(
            button_container,
            text="Cancel",
            command=self._cancel_clicked,
            font=ctk.CTkFont(size=13),
            width=180,
            height=36,
            fg_color="#757575",  # Gray
            hover_color="#616161"
        )
        cancel_btn.pack()
        
        # RIGHT COLUMN - Item selection
        right_frame = ctk.CTkFrame(self.dialog)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)
        
        selection_title = ctk.CTkLabel(
            right_frame,
            text="Select Items",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        selection_title.grid(row=0, column=0, pady=(20, 15), sticky="w", padx=20)
        
        # Listbox container
        list_container = ctk.CTkFrame(right_frame)
        list_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 15))
        list_container.grid_columnconfigure(0, weight=1)
        list_container.grid_rowconfigure(0, weight=1)
        
        list_frame = tk.Frame(list_container, bg="#212121")
        list_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        
        self.items_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            height=22,
            font=("Arial", 14, "normal"),
            bg="#2b2b2b",
            fg="white",
            selectbackground="#0078d4",
            selectforeground="white",
            borderwidth=0,
            highlightthickness=0
        )
        
        scrollbar = tk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.items_listbox.yview,
            bg="#2b2b2b",
            troughcolor="#1a1a1a"
        )
        
        self.items_listbox.configure(yscrollcommand=scrollbar.set)
        self.items_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Populate items
        for item in available_items:
            self.items_listbox.insert(tk.END, f"Item {item}")
        
        # Selection controls
        controls_frame = ctk.CTkFrame(right_frame)
        controls_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        controls_title = ctk.CTkLabel(
            controls_frame,
            text="Quick Selection",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        controls_title.pack(pady=(12, 10))
        
        # Primary controls
        primary_controls = ctk.CTkFrame(controls_frame, fg_color="transparent")
        primary_controls.pack(pady=(0, 8))
        
        ctk.CTkButton(
            primary_controls,
            text="Select All",
            command=self._select_all,
            width=80,
            height=32,
            font=ctk.CTkFont(size=11)
        ).pack(side='left', padx=3)
        
        ctk.CTkButton(
            primary_controls,
            text="Clear All",
            command=self._clear_selection,
            width=80,
            height=32,
            font=ctk.CTkFont(size=11)
        ).pack(side='left', padx=3)
        
        ctk.CTkButton(
            primary_controls,
            text="Range",
            command=self._select_range,
            width=70,
            height=32,
            font=ctk.CTkFont(size=11)
        ).pack(side='left', padx=3)
        
        # Quick selection
        quick_controls = ctk.CTkFrame(controls_frame, fg_color="transparent")
        quick_controls.pack(pady=(0, 12))
        
        quick_buttons = [
            ("First 10", lambda: self._select_first_n(10)),
            ("First 50", lambda: self._select_first_n(50)),
            ("Last 10", lambda: self._select_last_n(10)),
            ("Last 50", lambda: self._select_last_n(50))
        ]
        
        for text, command in quick_buttons:
            ctk.CTkButton(
                quick_controls,
                text=text,
                command=command,
                width=65,
                height=30,
                font=ctk.CTkFont(size=10)
            ).pack(side='left', padx=2)
    
    def _select_all(self):
        """Select all items"""
        self.items_listbox.select_set(0, tk.END)
    
    def _clear_selection(self):
        """Clear all selections"""
        self.items_listbox.selection_clear(0, tk.END)
    
    def _select_range(self):
        """Show dialog to select a range with improved styling"""
        range_dialog = ctk.CTkToplevel(self.dialog)
        range_dialog.title("Select Range")
        range_dialog.geometry("400x250")
        range_dialog.transient(self.dialog)
        range_dialog.grab_set()
        
        # Center the range dialog
        range_dialog.update_idletasks()
        x = (range_dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (range_dialog.winfo_screenheight() // 2) - (250 // 2)
        range_dialog.geometry(f"400x250+{x}+{y}")
        
        # Main frame
        frame = ctk.CTkFrame(range_dialog)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title = ctk.CTkLabel(
            frame,
            text="Select Range",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(pady=(20, 20))
        
        # Start entry
        start_frame = ctk.CTkFrame(frame)
        start_frame.pack(fill='x', padx=20, pady=10)
        
        start_label = ctk.CTkLabel(start_frame, text="Start Item:")
        start_label.pack(side='left', padx=(10, 20))
        
        self.start_entry = ctk.CTkEntry(start_frame, width=100)
        self.start_entry.pack(side='left')
        self.start_entry.insert(0, "1")
        
        # End entry
        end_frame = ctk.CTkFrame(frame)
        end_frame.pack(fill='x', padx=20, pady=10)
        
        end_label = ctk.CTkLabel(end_frame, text="End Item:")
        end_label.pack(side='left', padx=(10, 27))
        
        self.end_entry = ctk.CTkEntry(end_frame, width=100)
        self.end_entry.pack(side='left')
        available_items = self.array_handler.get_available_items()
        if available_items:
            self.end_entry.insert(0, str(min(10, len(available_items))))
        
        # Buttons
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(pady=30)
        
        ok_range_btn = ctk.CTkButton(
            btn_frame,
            text="OK",
            command=lambda: self._apply_range(range_dialog),
            width=100,
            height=35
        )
        ok_range_btn.pack(side='left', padx=(0, 15))
        
        cancel_range_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=range_dialog.destroy,
            width=100,
            height=35
        )
        cancel_range_btn.pack(side='left')
    
    def _apply_range(self, range_dialog):
        """Apply range selection"""
        try:
            start = int(self.start_entry.get()) - 1  # Convert to 0-based index
            end = int(self.end_entry.get())  # End is exclusive
            
            available_items = self.array_handler.get_available_items()
            if start < 0 or end > len(available_items) or start >= end:
                messagebox.showerror("Error", "Invalid range", parent=range_dialog)
                return
            
            self.items_listbox.selection_clear(0, tk.END)
            for i in range(start, end):
                self.items_listbox.select_set(i)
            
            range_dialog.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers", parent=range_dialog)
    
    def _select_first_n(self, n):
        """Select first n items"""
        self.items_listbox.selection_clear(0, tk.END)
        available_count = len(self.array_handler.get_available_items())
        end_index = min(n, available_count)
        for i in range(end_index):
            self.items_listbox.select_set(i)
    
    def _select_last_n(self, n):
        """Select last n items"""
        self.items_listbox.selection_clear(0, tk.END)
        available_count = len(self.array_handler.get_available_items())
        start_index = max(0, available_count - n)
        for i in range(start_index, available_count):
            self.items_listbox.select_set(i)
    
    def _ok_clicked(self):
        """Handle OK button click"""
        selected_indices = self.items_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select at least one item.")
            return
        
        available_items = self.array_handler.get_available_items()
        selected_items = [available_items[i] for i in selected_indices]
        operation_mode = self.operation_mode.get()
        
        self.result = (selected_items, operation_mode)
        self.dialog.destroy()
    
    def _cancel_clicked(self):
        """Handle cancel button click"""
        self.result = None
        self.dialog.destroy()


class MultiItemAverageDialog:
    """Dialog for configuring multi-item averaging parameters"""
    
    def __init__(self, parent):
        self.parent = parent
        self.result = None
        
    def show(self, frame_numbers: List[int]) -> Optional[dict]:
        """Show averaging configuration dialog"""
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Frame Averaging Configuration")
        dialog.geometry("500x400")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (400 // 2)
        dialog.geometry(f"500x400+{x}+{y}")
        
        # Main frame
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="Frame Averaging Configuration",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(10, 20))
        
        # Frame info
        info_label = ctk.CTkLabel(
            main_frame,
            text=f"Selected Frames: {len(frame_numbers)} items\nRange: {min(frame_numbers)} - {max(frame_numbers)}",
            font=ctk.CTkFont(size=12)
        )
        info_label.pack(pady=(0, 20))
        
        # Averaging method
        method_frame = ctk.CTkFrame(main_frame)
        method_frame.pack(fill="x", padx=20, pady=10)
        
        method_label = ctk.CTkLabel(method_frame, text="Averaging Method:", font=ctk.CTkFont(size=14, weight="bold"))
        method_label.pack(pady=(10, 5))
        
        self.avg_method = tk.StringVar(value="mean")
        
        methods = [
            ("mean", "Arithmetic Mean - Standard averaging"),
            ("median", "Median - Less sensitive to outliers"),
            ("max", "Maximum - Brightest pixel values"),
            ("min", "Minimum - Darkest pixel values")
        ]
        
        for value, description in methods:
            radio = ctk.CTkRadioButton(
                method_frame,
                text=description,
                variable=self.avg_method,
                value=value,
                font=ctk.CTkFont(size=11)
            )
            radio.pack(pady=5, anchor="w", padx=20)
        
        # Output options
        output_frame = ctk.CTkFrame(main_frame)
        output_frame.pack(fill="x", padx=20, pady=10)
        
        output_label = ctk.CTkLabel(output_frame, text="Output Options:", font=ctk.CTkFont(size=14, weight="bold"))
        output_label.pack(pady=(10, 5))
        
        self.save_intermediate = tk.BooleanVar(value=False)
        save_check = ctk.CTkCheckBox(
            output_frame,
            text="Save intermediate calculations",
            variable=self.save_intermediate,
            font=ctk.CTkFont(size=11)
        )
        save_check.pack(pady=5, anchor="w", padx=20)
        
        self.show_progress = tk.BooleanVar(value=True)
        progress_check = ctk.CTkCheckBox(
            output_frame,
            text="Show progress during averaging",
            variable=self.show_progress,
            font=ctk.CTkFont(size=11)
        )
        progress_check.pack(pady=5, anchor="w", padx=20)
        
        # Buttons
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(pady=30)
        
        ok_btn = ctk.CTkButton(
            btn_frame,
            text="Start Averaging",
            command=lambda: self._ok_clicked(dialog),
            font=ctk.CTkFont(size=14, weight="bold"),
            width=150,
            height=40,
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        ok_btn.pack(side='left', padx=(0, 15))
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            font=ctk.CTkFont(size=14),
            width=100,
            height=40
        )
        cancel_btn.pack(side='left')
        
        dialog.wait_window()
        return self.result
    
    def _ok_clicked(self, dialog):
        """Handle OK button click"""
        self.result = {
            'method': self.avg_method.get(),
            'save_intermediate': self.save_intermediate.get(),
            'show_progress': self.show_progress.get()
        }
        dialog.destroy()


# Factory functions
def show_array_selection_dialog(parent, array_handler):
    """Show array selection dialog and return result"""
    dialog = ArraySelectionDialog(parent, array_handler)
    return dialog.show()

def show_averaging_dialog(parent, frame_numbers):
    """Show frame averaging configuration dialog"""
    dialog = MultiItemAverageDialog(parent)
    return dialog.show(frame_numbers)