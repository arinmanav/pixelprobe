"""
Array selection dialog for PixelProbe - Updated with CustomTkinter theming and proper sizing
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
        
        # Set window size - taller for better organization
        self.dialog.geometry("900x850")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Set minimum size to prevent shrinking
        self.dialog.minsize(900, 850)
        
        # Center the window
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (850 // 2)
        self.dialog.geometry(f"900x850+{x}+{y}")
        
        # Configure grid weights
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(0, weight=1)
        
        self._create_widgets()
        self.dialog.wait_window()
        return self.result
    
    def _create_widgets(self):
        """Create dialog widgets with better organization"""
        # Main frame 
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)  # Make item selection expandable
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame, 
            text="Array Data Selection", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 25), sticky="ew")
        
        # Top section: Directory info + Operation selection (side by side)
        top_section = ctk.CTkFrame(main_frame)
        top_section.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 20))
        top_section.grid_columnconfigure(0, weight=1)
        top_section.grid_columnconfigure(1, weight=1)
        
        # Left: Directory info 
        dir_frame = ctk.CTkFrame(top_section)
        dir_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        dir_frame.grid_columnconfigure(0, weight=1)
        
        dir_title = ctk.CTkLabel(
            dir_frame,
            text="Current Directory",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        dir_title.pack(pady=(15, 10))
        
        if self.array_handler.current_directory:
            dir_path = str(self.array_handler.current_directory)
            available_count = len(self.array_handler.get_available_items())
        else:
            dir_path = "No directory selected"
            available_count = 0
        
        ctk.CTkLabel(
            dir_frame,
            text=f"Path: {dir_path}",
            font=ctk.CTkFont(size=11),
            wraplength=380
        ).pack(padx=15, pady=(0, 8))
        
        ctk.CTkLabel(
            dir_frame,
            text=f"Available Items: {available_count}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#4CAF50"
        ).pack(padx=15, pady=(0, 15))
        
        # Right: Operation selection
        operation_frame = ctk.CTkFrame(top_section)
        operation_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        
        op_title = ctk.CTkLabel(
            operation_frame,
            text="Operation Mode",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        op_title.pack(pady=(15, 15))
        
        self.operation_var = tk.StringVar(value="single")
        
        operations = [
            ("single", "Single Item"),
            ("multiple", "Multiple Items"), 
            ("average", "Average Items")
        ]
        
        for value, text in operations:
            radio = ctk.CTkRadioButton(
                operation_frame,
                text=text,
                variable=self.operation_var,
                value=value,
                font=ctk.CTkFont(size=12)
            )
            radio.pack(pady=8)
        
        # Middle section: Item selection (expandable)
        selection_frame = ctk.CTkFrame(main_frame)
        selection_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=(0, 20))
        selection_frame.grid_columnconfigure(0, weight=1)
        selection_frame.grid_rowconfigure(1, weight=1)  # Make listbox expandable
        
        selection_title = ctk.CTkLabel(
            selection_frame,
            text="Select Items",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        selection_title.grid(row=0, column=0, pady=(15, 10), sticky="w", padx=20)
        
        # Listbox container with scrollbar
        list_container = ctk.CTkFrame(selection_frame)
        list_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 15))
        list_container.grid_columnconfigure(0, weight=1)
        list_container.grid_rowconfigure(0, weight=1)
        
        # Use a regular tkinter Listbox inside CTkFrame
        list_frame = tk.Frame(list_container, bg="#212121")
        list_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        
        self.items_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            height=15,
            font=("Arial", 11),
            bg="#404040",
            fg="white",
            selectbackground="#1f538d",
            selectforeground="white",
            borderwidth=0,
            highlightthickness=0
        )
        
        scrollbar = tk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.items_listbox.yview,
            bg="#404040",
            troughcolor="#212121",
            activebackground="#606060"
        )
        
        self.items_listbox.configure(yscrollcommand=scrollbar.set)
        self.items_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Populate items
        available_items = self.array_handler.get_available_items()
        for item in available_items:
            self.items_listbox.insert(tk.END, f"Item {item}")
        
        # Bottom section: Selection controls
        controls_frame = ctk.CTkFrame(selection_frame)
        controls_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        controls_title = ctk.CTkLabel(
            controls_frame,
            text="Selection Controls",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        controls_title.pack(pady=(15, 12))
        
        # Basic controls row
        basic_controls = ctk.CTkFrame(controls_frame)
        basic_controls.pack(pady=(0, 10))
        
        ctk.CTkButton(
            basic_controls,
            text="Select All",
            command=self._select_all,
            width=100, height=32
        ).pack(side='left', padx=8)
        
        ctk.CTkButton(
            basic_controls,
            text="Clear All",
            command=self._clear_selection,
            width=100, height=32
        ).pack(side='left', padx=8)
        
        ctk.CTkButton(
            basic_controls,
            text="Range Select",
            command=self._select_range,
            width=100, height=32
        ).pack(side='left', padx=8)
        
        # Quick selection row
        quick_controls = ctk.CTkFrame(controls_frame)
        quick_controls.pack(pady=(0, 15))
        
        quick_btns = [
            ("First 10", lambda: self._select_first_n(10)),
            ("First 50", lambda: self._select_first_n(50)),
            ("Last 10", lambda: self._select_last_n(10)),
            ("Last 50", lambda: self._select_last_n(50))
        ]
        
        for text, command in quick_btns:
            ctk.CTkButton(
                quick_controls,
                text=text,
                command=command,
                width=85, height=30
            ).pack(side='left', padx=6)
        
        # Bottom: Action buttons
        button_container = ctk.CTkFrame(main_frame)
        button_container.grid(row=3, column=0, sticky="ew", padx=0, pady=(0, 0))
        
        btn_frame = ctk.CTkFrame(button_container)
        btn_frame.pack(pady=20)
        
        ok_btn = ctk.CTkButton(
            btn_frame,
            text="Load Selected Items",
            command=self._ok_clicked,
            font=ctk.CTkFont(size=15, weight="bold"),
            width=180,
            height=42,
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        ok_btn.pack(side='left', padx=(0, 20))
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=self._cancel_clicked,
            font=ctk.CTkFont(size=15),
            width=130,
            height=42,
            fg_color="#f44336",
            hover_color="#da190b"
        )
        cancel_btn.pack(side='left')
        
        # Info label
        self.info_label = ctk.CTkLabel(
            main_frame,
            text="Choose operation mode, select items from the list, then click 'Load Selected Items'",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        )
        self.info_label.grid(row=4, column=0, pady=(10, 0))
    
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
        count = min(n, self.items_listbox.size())
        for i in range(count):
            self.items_listbox.select_set(i)
    
    def _select_last_n(self, n):
        """Select last n items"""
        self.items_listbox.selection_clear(0, tk.END)
        size = self.items_listbox.size()
        start = max(0, size - n)
        for i in range(start, size):
            self.items_listbox.select_set(i)
    
    def _ok_clicked(self):
        """Handle OK button click"""
        selected_indices = self.items_listbox.curselection()
        
        if not selected_indices:
            messagebox.showerror("Error", "Please select at least one item", parent=self.dialog)
            return
        
        operation = self.operation_var.get()
        
        if operation == "single" and len(selected_indices) > 1:
            messagebox.showerror("Error", "Please select only one item for single item operation", parent=self.dialog)
            return
        
        if operation == "average" and len(selected_indices) < 2:
            messagebox.showerror("Error", "Please select at least two items for averaging", parent=self.dialog)
            return
        
        # Get selected item numbers
        available_items = self.array_handler.get_available_items()
        selected_items = [available_items[i] for i in selected_indices]
        
        self.result = (selected_items, operation)
        self.dialog.destroy()
    
    def _cancel_clicked(self):
        """Handle Cancel button click"""
        self.result = None
        self.dialog.destroy()


def update_status_persistent(parent, message: str):
    """Helper function to update status with persistent message"""
    if hasattr(parent, 'update_status'):
        parent.update_status(message)
    elif hasattr(parent, 'status_label'):
        parent.status_label.configure(text=message)
    
    # Schedule removal of the message after 10 seconds
    parent.after(10000, lambda: update_status_clear(parent))

def update_status_clear(parent):
    """Helper function to clear persistent status message"""
    if hasattr(parent, 'update_status'):
        parent.update_status("Ready")
    elif hasattr(parent, 'status_label'):
        parent.status_label.configure(text="Ready")