"""
Array selection dialog for PixelProbe
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional, List, Tuple
import customtkinter as ctk


class ArraySelectionDialog:
    """Dialog for selecting array directory and item numbers"""
    
    def __init__(self, parent, array_handler):
        self.parent = parent
        self.array_handler = array_handler
        self.result = None
        self.dialog = None
        
    def show(self) -> Optional[Tuple[List[int], str]]:
        """
        Show the array selection dialog
        
        Returns:
            Tuple of (selected_items, operation_type) or None if cancelled
        """
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Select Array Data")
        self.dialog.geometry("600x500")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the window
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (500 // 2)
        self.dialog.geometry(f"600x500+{x}+{y}")
        
        self._create_widgets()
        
        # Wait for dialog to close
        self.dialog.wait_window()
        return self.result
    
    def _create_widgets(self):
        """Create dialog widgets"""
        main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title_label = tk.Label(
            main_frame, 
            text="Array Data Selection", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Directory info
        dir_frame = tk.LabelFrame(main_frame, text="Current Directory", font=("Arial", 12, "bold"))
        dir_frame.pack(fill='x', pady=(0, 15))
        
        if self.array_handler.current_directory:
            dir_path = str(self.array_handler.current_directory)
            available_count = len(self.array_handler.get_available_items())
        else:
            dir_path = "No directory selected"
            available_count = 0
        
        tk.Label(dir_frame, text=f"Path: {dir_path}", wraplength=500).pack(anchor='w', padx=10, pady=5)
        tk.Label(dir_frame, text=f"Available Items: {available_count}").pack(anchor='w', padx=10, pady=(0, 10))
        
        # Item selection
        selection_frame = tk.LabelFrame(main_frame, text="Item Selection", font=("Arial", 12, "bold"))
        selection_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # Available items list
        items_frame = tk.Frame(selection_frame)
        items_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        tk.Label(items_frame, text="Available Items:", font=("Arial", 10, "bold")).pack(anchor='w')
        
        # Listbox with scrollbar
        list_frame = tk.Frame(items_frame)
        list_frame.pack(fill='both', expand=True, pady=(5, 10))
        
        self.items_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=8)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.items_listbox.yview)
        self.items_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.items_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Populate items
        available_items = self.array_handler.get_available_items()
        for item in available_items:
            self.items_listbox.insert(tk.END, f"Item {item}")
        
        # Selection buttons
        button_frame = tk.Frame(items_frame)
        button_frame.pack(fill='x', pady=(0, 10))
        
        tk.Button(button_frame, text="Select All", command=self._select_all).pack(side='left', padx=(0, 10))
        tk.Button(button_frame, text="Clear Selection", command=self._clear_selection).pack(side='left', padx=(0, 10))
        tk.Button(button_frame, text="Select Range", command=self._select_range).pack(side='left')
        
        # Quick selection
        quick_frame = tk.Frame(items_frame)
        quick_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(quick_frame, text="Quick Selection:").pack(side='left')
        tk.Button(quick_frame, text="First 10", command=lambda: self._select_first_n(10)).pack(side='left', padx=(10, 5))
        tk.Button(quick_frame, text="First 50", command=lambda: self._select_first_n(50)).pack(side='left', padx=(0, 5))
        tk.Button(quick_frame, text="Last 10", command=lambda: self._select_last_n(10)).pack(side='left', padx=(0, 5))
        
        # Operation type
        operation_frame = tk.LabelFrame(main_frame, text="Operation", font=("Arial", 12, "bold"))
        operation_frame.pack(fill='x', pady=(0, 15))
        
        self.operation_var = tk.StringVar(value="single")
        
        tk.Radiobutton(
            operation_frame, 
            text="Load Single Item (select one)", 
            variable=self.operation_var, 
            value="single"
        ).pack(anchor='w', padx=10, pady=5)
        
        tk.Radiobutton(
            operation_frame, 
            text="Load Multiple Items", 
            variable=self.operation_var, 
            value="multiple"
        ).pack(anchor='w', padx=10, pady=5)
        
        tk.Radiobutton(
            operation_frame, 
            text="Average Selected Items", 
            variable=self.operation_var, 
            value="average"
        ).pack(anchor='w', padx=10, pady=5)
        
        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(15, 0))
        
        tk.Button(
            button_frame, 
            text="OK", 
            command=self._ok_clicked,
            font=("Arial", 12, "bold"),
            bg='#4CAF50',
            fg='white',
            padx=30,
            pady=8
        ).pack(side='right', padx=(10, 0))
        
        tk.Button(
            button_frame, 
            text="Cancel", 
            command=self._cancel_clicked,
            font=("Arial", 12),
            padx=30,
            pady=8
        ).pack(side='right')
        
        # Info label
        self.info_label = tk.Label(
            main_frame, 
            text="Select items and operation type, then click OK",
            fg="blue"
        )
        self.info_label.pack(pady=(10, 0))
    
    def _select_all(self):
        """Select all items"""
        self.items_listbox.select_set(0, tk.END)
    
    def _clear_selection(self):
        """Clear all selections"""
        self.items_listbox.selection_clear(0, tk.END)
    
    def _select_range(self):
        """Show dialog to select a range"""
        range_dialog = tk.Toplevel(self.dialog)
        range_dialog.title("Select Range")
        range_dialog.geometry("300x150")
        range_dialog.transient(self.dialog)
        range_dialog.grab_set()
        
        # Center the range dialog
        range_dialog.update_idletasks()
        x = (range_dialog.winfo_screenwidth() // 2) - (300 // 2)
        y = (range_dialog.winfo_screenheight() // 2) - (150 // 2)
        range_dialog.geometry(f"300x150+{x}+{y}")
        
        frame = tk.Frame(range_dialog, padx=20, pady=20)
        frame.pack(fill='both', expand=True)
        
        tk.Label(frame, text="Select Range:", font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        input_frame = tk.Frame(frame)
        input_frame.pack(fill='x', pady=(0, 15))
        
        tk.Label(input_frame, text="From:").pack(side='left')
        start_entry = tk.Entry(input_frame, width=10)
        start_entry.pack(side='left', padx=(5, 15))
        
        tk.Label(input_frame, text="To:").pack(side='left')
        end_entry = tk.Entry(input_frame, width=10)
        end_entry.pack(side='left', padx=(5, 0))
        
        def apply_range():
            try:
                start_idx = int(start_entry.get())
                end_idx = int(end_entry.get())
                
                available_items = self.array_handler.get_available_items()
                
                self.items_listbox.selection_clear(0, tk.END)
                for i, item in enumerate(available_items):
                    if start_idx <= item <= end_idx:
                        self.items_listbox.select_set(i)
                
                range_dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers", parent=range_dialog)
        
        button_frame = tk.Frame(frame)
        button_frame.pack(fill='x')
        
        tk.Button(button_frame, text="Apply", command=apply_range).pack(side='right', padx=(10, 0))
        tk.Button(button_frame, text="Cancel", command=range_dialog.destroy).pack(side='right')
    
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