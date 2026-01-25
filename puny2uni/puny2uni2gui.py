#!/usr/bin/env python3
"""
puny2uni2gui.py - GUI for Punycode ⟷ Unicode Converter
Graphical interface for the puny2uni2 converter with translation support

Features:
- Single domain conversion with live preview
- Batch file processing (.txt and .csv)
- Automatic language detection
- Translation support (requires deep-translator)
- Interactive GUI with tabbed interface
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
from pathlib import Path

# Import the converter from puny2uni2
try:
    from puny2uni2 import Puny2UniConverter, TRANSLATION_AVAILABLE, CSV_AVAILABLE
except ImportError:
    print("Error: Could not import puny2uni2.py")
    print("Make sure puny2uni2.py is in the same directory as puny2uni2gui.py")
    import sys
    sys.exit(1)


class Puny2UniGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Punycode ⟷ Unicode Converter")
        self.root.geometry("800x700")
        
        # Initialize converter
        self.converter = Puny2UniConverter()
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Create bottom buttons first
        self.create_bottom_buttons()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=(5, 5))
        
        # Create tabs
        self.create_single_converter_tab()
        self.create_batch_processor_tab()
        self.create_csv_processor_tab()
        
    def create_bottom_buttons(self):
        """Create bottom action buttons"""
        button_frame = tk.Frame(self.root, height=60)
        button_frame.pack(side='bottom', fill='x', padx=10, pady=15)
        button_frame.pack_propagate(False)
        
        help_btn = tk.Button(button_frame, text="Help", bg="yellow", fg="black",
                            font=("Arial", 12, "bold"), command=self.show_help, width=10, height=2)
        help_btn.pack(side='left', padx=5, pady=5)
        
        exit_btn = tk.Button(button_frame, text="Exit", bg="red", fg="white",
                            font=("Arial", 12, "bold"), command=self.root.quit, width=10, height=2)
        exit_btn.pack(side='right', padx=5, pady=5)
        
        process_btn = tk.Button(button_frame, text="Convert", bg="green", fg="white",
                               font=("Arial", 12, "bold"), command=self.process_action, width=15, height=2)
        process_btn.pack(side='right', padx=5, pady=5)
    
    def create_single_converter_tab(self):
        """Tab 1: Single domain conversion with live preview"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Single Convert")
        
        # Info frame
        info_frame = tk.LabelFrame(tab, text="Single Domain Converter", padx=10, pady=10)
        info_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(info_frame, text="Convert individual domains between punycode and unicode").pack(anchor='w')
        tk.Label(info_frame, text="Direction is detected automatically (xn-- = punycode → unicode)").pack(anchor='w')
        
        # Input frame
        input_frame = tk.LabelFrame(tab, text="Input", padx=10, pady=10)
        input_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(input_frame, text="Enter domain:").pack(anchor='w')
        self.single_input_entry = tk.Entry(input_frame, font=("Arial", 12))
        self.single_input_entry.pack(fill='x', pady=5)
        self.single_input_entry.bind('<KeyRelease>', self.on_single_input_change)
        
        # Live convert button
        convert_btn = tk.Button(input_frame, text="Convert", command=self.convert_single,
                               bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        convert_btn.pack(pady=5)
        
        # Translation options
        trans_frame = tk.Frame(input_frame)
        trans_frame.pack(fill='x', pady=5)
        
        self.single_translate_var = tk.BooleanVar(value=False)
        trans_check = tk.Checkbutton(trans_frame, text="Enable translation",
                                     variable=self.single_translate_var,
                                     command=self.convert_single)
        trans_check.pack(side='left')
        
        if not TRANSLATION_AVAILABLE:
            trans_check.config(state='disabled')
            tk.Label(trans_frame, text="⚠ Install deep-translator", fg="orange", font=("Arial", 8)).pack(side='left', padx=5)
        
        tk.Label(trans_frame, text="Target:", font=("Arial", 9)).pack(side='left', padx=5)
        self.single_target_lang_var = tk.StringVar(value='en')
        lang_entry = tk.Entry(trans_frame, textvariable=self.single_target_lang_var, width=5)
        lang_entry.pack(side='left', padx=2)
        lang_entry.bind('<KeyRelease>', lambda e: self.convert_single())
        
        # Output frame with scrolled text
        output_frame = tk.LabelFrame(tab, text="Output", padx=10, pady=10)
        output_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.single_output_text = scrolledtext.ScrolledText(output_frame, height=15, font=("Consolas", 10))
        self.single_output_text.pack(fill='both', expand=True)
        
        # Copy button
        copy_btn = tk.Button(output_frame, text="Copy Result", command=self.copy_single_result,
                            bg="#2196F3", fg="white")
        copy_btn.pack(pady=5)
    
    def create_batch_processor_tab(self):
        """Tab 2: Batch file processing (.txt files)"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Batch TXT Files")
        
        # Info frame
        info_frame = tk.LabelFrame(tab, text="Batch Text File Processing", padx=10, pady=10)
        info_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(info_frame, text="Process .txt files with one domain per line").pack(anchor='w')
        tk.Label(info_frame, text="Direction is auto-detected from the first line").pack(anchor='w')
        
        # File selection
        file_frame = tk.Frame(info_frame)
        file_frame.pack(fill='x', pady=5)
        
        tk.Button(file_frame, text="Select TXT Files", command=self.select_txt_files).pack(side='left', padx=5)
        tk.Button(file_frame, text="Select Folder", command=self.select_txt_folder).pack(side='left', padx=5)
        
        self.recursive_txt_var = tk.BooleanVar(value=False)
        tk.Checkbutton(file_frame, text="Recursive Search", variable=self.recursive_txt_var).pack(side='left', padx=5)
        
        # File list
        list_frame = tk.LabelFrame(tab, text="Selected Files", padx=10, pady=10)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        button_row = tk.Frame(list_frame)
        button_row.pack(fill='x', pady=5)
        tk.Button(button_row, text="Select All", command=lambda: self.toggle_txt_files(True)).pack(side='left', padx=5)
        tk.Button(button_row, text="Select None", command=lambda: self.toggle_txt_files(False)).pack(side='left', padx=5)
        tk.Button(button_row, text="Remove Selected", bg="#ff6b6b", fg="white",
                 command=self.remove_txt_files).pack(side='left', padx=5)
        tk.Button(button_row, text="Clear All", bg="#ff8c00", fg="white",
                 command=self.clear_txt_files).pack(side='left', padx=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.txt_listbox = tk.Listbox(list_frame, selectmode='multiple', yscrollcommand=scrollbar.set)
        self.txt_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.txt_listbox.yview)
        
        self.txt_listbox.bind('<Delete>', lambda e: self.remove_txt_files())
        
        self.txt_files = []
        
        # Options
        options_frame = tk.LabelFrame(tab, text="Options", padx=10, pady=10)
        options_frame.pack(fill='x', padx=10, pady=5)
        
        self.txt_translate_var = tk.BooleanVar(value=False)
        trans_check = tk.Checkbutton(options_frame, text="Enable translation",
                                     variable=self.txt_translate_var)
        trans_check.pack(anchor='w')
        
        if not TRANSLATION_AVAILABLE:
            trans_check.config(state='disabled')
            tk.Label(options_frame, text="⚠ Install deep-translator for translation support", 
                    fg="orange", font=("Arial", 8)).pack(anchor='w')
        
        lang_row = tk.Frame(options_frame)
        lang_row.pack(fill='x', pady=5)
        tk.Label(lang_row, text="Target language:").pack(side='left', padx=5)
        self.txt_target_lang_var = tk.StringVar(value='en')
        tk.Entry(lang_row, textvariable=self.txt_target_lang_var, width=5).pack(side='left')
        tk.Label(lang_row, text="(en, es, fr, de, ja, zh-CN, etc.)", font=("Arial", 8), fg="gray").pack(side='left', padx=5)
    
    def create_csv_processor_tab(self):
        """Tab 3: CSV file processing"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="CSV Files")
        
        # Info frame
        info_frame = tk.LabelFrame(tab, text="CSV File Processing", padx=10, pady=10)
        info_frame.pack(fill='x', padx=10, pady=5)
        
        if CSV_AVAILABLE:
            tk.Label(info_frame, text="Process CSV exports from Bob Wallet, Namebase, Shakestation, or Firewallet").pack(anchor='w')
            tk.Label(info_frame, text="Adds unicode, description, and translation columns").pack(anchor='w')
        else:
            tk.Label(info_frame, text="⚠ CSV processing requires pandas", fg="red", font=("Arial", 10, "bold")).pack(anchor='w')
            tk.Label(info_frame, text="Install with: pip install pandas", fg="gray").pack(anchor='w')
        
        # File selection
        file_frame = tk.Frame(info_frame)
        file_frame.pack(fill='x', pady=5)
        
        tk.Button(file_frame, text="Select CSV Files", command=self.select_csv_files,
                 state='normal' if CSV_AVAILABLE else 'disabled').pack(side='left', padx=5)
        tk.Button(file_frame, text="Select Folder", command=self.select_csv_folder,
                 state='normal' if CSV_AVAILABLE else 'disabled').pack(side='left', padx=5)
        
        self.recursive_csv_var = tk.BooleanVar(value=False)
        tk.Checkbutton(file_frame, text="Recursive Search", variable=self.recursive_csv_var,
                      state='normal' if CSV_AVAILABLE else 'disabled').pack(side='left', padx=5)
        
        # File list
        list_frame = tk.LabelFrame(tab, text="Selected Files", padx=10, pady=10)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        button_row = tk.Frame(list_frame)
        button_row.pack(fill='x', pady=5)
        tk.Button(button_row, text="Select All", command=lambda: self.toggle_csv_files(True),
                 state='normal' if CSV_AVAILABLE else 'disabled').pack(side='left', padx=5)
        tk.Button(button_row, text="Select None", command=lambda: self.toggle_csv_files(False),
                 state='normal' if CSV_AVAILABLE else 'disabled').pack(side='left', padx=5)
        tk.Button(button_row, text="Remove Selected", bg="#ff6b6b", fg="white",
                 command=self.remove_csv_files, state='normal' if CSV_AVAILABLE else 'disabled').pack(side='left', padx=5)
        tk.Button(button_row, text="Clear All", bg="#ff8c00", fg="white",
                 command=self.clear_csv_files, state='normal' if CSV_AVAILABLE else 'disabled').pack(side='left', padx=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.csv_listbox = tk.Listbox(list_frame, selectmode='multiple', yscrollcommand=scrollbar.set)
        self.csv_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.csv_listbox.yview)
        
        self.csv_listbox.bind('<Delete>', lambda e: self.remove_csv_files())
        
        self.csv_files = []
        
        # Options
        options_frame = tk.LabelFrame(tab, text="Options", padx=10, pady=10)
        options_frame.pack(fill='x', padx=10, pady=5)
        
        self.csv_translate_var = tk.BooleanVar(value=True if TRANSLATION_AVAILABLE else False)
        trans_check = tk.Checkbutton(options_frame, text="Enable translation",
                                     variable=self.csv_translate_var,
                                     state='normal' if CSV_AVAILABLE else 'disabled')
        trans_check.pack(anchor='w')
        
        if not TRANSLATION_AVAILABLE:
            tk.Label(options_frame, text="⚠ Install deep-translator for translation support",
                    fg="orange", font=("Arial", 8)).pack(anchor='w')
        
        lang_row = tk.Frame(options_frame)
        lang_row.pack(fill='x', pady=5)
        tk.Label(lang_row, text="Target language:").pack(side='left', padx=5)
        self.csv_target_lang_var = tk.StringVar(value='en')
        tk.Entry(lang_row, textvariable=self.csv_target_lang_var, width=5,
                state='normal' if CSV_AVAILABLE else 'disabled').pack(side='left')
        tk.Label(lang_row, text="(en, es, fr, de, ja, zh-CN, etc.)", font=("Arial", 8), fg="gray").pack(side='left', padx=5)
        
        # Respect existing entries option
        self.csv_respect_existing_var = tk.BooleanVar(value=True)
        respect_check = tk.Checkbutton(options_frame, 
                                      text="Respect existing entries (skip domains with descript/translate values)",
                                      variable=self.csv_respect_existing_var,
                                      state='normal' if CSV_AVAILABLE else 'disabled')
        respect_check.pack(anchor='w', pady=2)
        
        help_label = tk.Label(options_frame, 
                            text="ℹ Uncheck to override and re-process all domains (useful for re-translation)",
                            font=("Arial", 8), fg="gray")
        help_label.pack(anchor='w', padx=20)
    
    def on_single_input_change(self, event):
        """Auto-convert on input change"""
        # Optional: Auto-convert as user types (may be too aggressive)
        pass
    
    def convert_single(self):
        """Convert single domain and display result"""
        domain = self.single_input_entry.get().strip()
        
        if not domain:
            self.single_output_text.delete('1.0', tk.END)
            return
        
        translate = self.single_translate_var.get() and TRANSLATION_AVAILABLE
        target_lang = self.single_target_lang_var.get()
        
        # Show processing message
        self.single_output_text.delete('1.0', tk.END)
        self.single_output_text.insert('1.0', "Converting...")
        self.root.update_idletasks()
        
        # Convert
        result = self.converter.convert_domain(domain, translate=translate, target_lang=target_lang, verbose=False)
        
        if not result:
            self.single_output_text.delete('1.0', tk.END)
            self.single_output_text.insert('1.0', "Error: Invalid domain")
            return
        
        # Format output
        output_lines = []
        output_lines.append("="*60)
        
        if result['direction'] == 'puny→uni':
            output_lines.append(f"Input (Punycode):  {result['input']}")
            output_lines.append(f"Output (Unicode):  {result['output']}")
            output_lines.append(f"Validation Level:  {result['validation']}")
        else:
            output_lines.append(f"Input (Unicode):   {result['input']}")
            output_lines.append(f"Output (Punycode): {result['output']}")
        
        # Show tags (new feature!)
        if result.get('tags'):
            tags_str = ', '.join(result['tags'])
            output_lines.append(f"Tags:              {tags_str}")
        
        if result['language']:
            output_lines.append(f"Detected Language: {result['language']}")
        
        # Show translation status
        if translate:
            if result['translation']:
                output_lines.append(f"Translation ({target_lang}): {result['translation']}")
                output_lines.append(f"✓ Translation successful")
            else:
                if result['validation'] == 'PUNY_IDNA' or result['direction'] == 'uni→puny':
                    output_lines.append(f"Translation ({target_lang}): (not available or same as source)")
                else:
                    output_lines.append(f"Translation: Skipped (only PUNY_IDNA domains are translated)")
        
        output_lines.append("="*60)
        
        # Display
        self.single_output_text.delete('1.0', tk.END)
        self.single_output_text.insert('1.0', '\n'.join(output_lines))
    
    def copy_single_result(self):
        """Copy the converted result to clipboard"""
        content = self.single_output_text.get('1.0', tk.END).strip()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            messagebox.showinfo("Copied", "Result copied to clipboard!")
    
    # TXT file handlers
    def select_txt_files(self):
        files = filedialog.askopenfilenames(title="Select TXT Files", filetypes=[("Text files", "*.txt")])
        if files:
            for file in files:
                if file not in self.txt_files:
                    self.txt_files.append(file)
                    self.txt_listbox.insert(tk.END, os.path.basename(file))
    
    def select_txt_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            files = []
            if self.recursive_txt_var.get():
                for root, dirs, filenames in os.walk(folder):
                    for filename in filenames:
                        if filename.endswith('.txt'):
                            files.append(os.path.join(root, filename))
            else:
                files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.txt')]
            
            for file in files:
                if file not in self.txt_files:
                    self.txt_files.append(file)
                    self.txt_listbox.insert(tk.END, os.path.basename(file))
    
    def toggle_txt_files(self, select):
        if select:
            self.txt_listbox.select_set(0, tk.END)
        else:
            self.txt_listbox.select_clear(0, tk.END)
    
    def remove_txt_files(self):
        selected_indices = list(self.txt_listbox.curselection())
        for idx in reversed(selected_indices):
            self.txt_listbox.delete(idx)
            del self.txt_files[idx]
    
    def clear_txt_files(self):
        self.txt_listbox.delete(0, tk.END)
        self.txt_files = []
    
    # CSV file handlers
    def select_csv_files(self):
        files = filedialog.askopenfilenames(title="Select CSV Files", filetypes=[("CSV files", "*.csv")])
        if files:
            for file in files:
                if file not in self.csv_files:
                    self.csv_files.append(file)
                    source_type = self.converter.detect_csv_source(file)
                    self.csv_listbox.insert(tk.END, f"[{source_type}] {os.path.basename(file)}")
    
    def select_csv_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            files = []
            if self.recursive_csv_var.get():
                for root, dirs, filenames in os.walk(folder):
                    for filename in filenames:
                        if filename.endswith('.csv'):
                            files.append(os.path.join(root, filename))
            else:
                files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.csv')]
            
            for file in files:
                if file not in self.csv_files:
                    self.csv_files.append(file)
                    source_type = self.converter.detect_csv_source(file)
                    self.csv_listbox.insert(tk.END, f"[{source_type}] {os.path.basename(file)}")
    
    def toggle_csv_files(self, select):
        if select:
            self.csv_listbox.select_set(0, tk.END)
        else:
            self.csv_listbox.select_clear(0, tk.END)
    
    def remove_csv_files(self):
        selected_indices = list(self.csv_listbox.curselection())
        for idx in reversed(selected_indices):
            self.csv_listbox.delete(idx)
            del self.csv_files[idx]
    
    def clear_csv_files(self):
        self.csv_listbox.delete(0, tk.END)
        self.csv_files = []
    
    def process_action(self):
        """Process based on current tab"""
        current_tab = self.notebook.index(self.notebook.select())
        
        if current_tab == 0:
            # Single converter - just convert
            self.convert_single()
        elif current_tab == 1:
            # Batch TXT files
            self.process_txt_batch()
        elif current_tab == 2:
            # CSV files
            self.process_csv_batch()
    
    def process_txt_batch(self):
        """Process batch TXT files"""
        selected_indices = self.txt_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select files to process")
            return
        
        translate = self.txt_translate_var.get() and TRANSLATION_AVAILABLE
        target_lang = self.txt_target_lang_var.get()
        
        # Show translation status
        if translate and not TRANSLATION_AVAILABLE:
            messagebox.showwarning("Translation Unavailable", 
                "deep-translator is not installed.\nProcessing without translation.")
            translate = False
        
        processed_count = 0
        error_count = 0
        total_translated = 0
        
        # Create progress window
        progress_win = tk.Toplevel(self.root)
        progress_win.title("Processing...")
        progress_win.geometry("400x150")
        progress_win.transient(self.root)
        progress_win.grab_set()
        
        progress_label = tk.Label(progress_win, text="Processing files...", font=("Arial", 10))
        progress_label.pack(pady=10)
        
        status_label = tk.Label(progress_win, text="", font=("Arial", 9), fg="gray")
        status_label.pack(pady=5)
        
        translation_label = tk.Label(progress_win, text="", font=("Arial", 9), fg="blue")
        translation_label.pack(pady=5)
        
        for i, idx in enumerate(selected_indices, 1):
            filepath = self.txt_files[idx]
            filename = os.path.basename(filepath)
            
            progress_label.config(text=f"Processing file {i}/{len(selected_indices)}")
            status_label.config(text=f"{filename}")
            if translate:
                translation_label.config(text=f"Translation enabled (target: {target_lang})")
            progress_win.update()
            
            try:
                # Capture stdout to get translation count
                import io
                import sys
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()
                
                success = self.converter.process_file(filepath, translate=translate, target_lang=target_lang)
                
                # Get output
                output = sys.stdout.getvalue()
                sys.stdout = old_stdout
                
                # Extract translation count from output
                if "Translated:" in output:
                    import re
                    match = re.search(r'Translated: (\d+)', output)
                    if match:
                        total_translated += int(match.group(1))
                
                if success:
                    processed_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                sys.stdout = old_stdout
                messagebox.showerror("Error", f"Error processing {filename}:\n{str(e)}")
        
        progress_win.destroy()
        
        result_msg = f"Processed {processed_count} file(s)"
        if translate and total_translated > 0:
            result_msg += f"\n\nSuccessfully translated {total_translated} domains to {target_lang}"
        if error_count > 0:
            result_msg += f"\n\nErrors: {error_count} file(s)"
        messagebox.showinfo("Complete", result_msg)
    
    def process_csv_batch(self):
        """Process batch CSV files"""
        if not CSV_AVAILABLE:
            messagebox.showerror("Error", "CSV processing requires pandas.\nInstall with: pip install pandas")
            return
        
        selected_indices = self.csv_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select files to process")
            return
        
        translate = self.csv_translate_var.get() and TRANSLATION_AVAILABLE
        target_lang = self.csv_target_lang_var.get()
        respect_existing = self.csv_respect_existing_var.get()
        
        # Show translation status
        if translate and not TRANSLATION_AVAILABLE:
            messagebox.showwarning("Translation Unavailable",
                "deep-translator is not installed.\nProcessing without translation.")
            translate = False
        
        processed_count = 0
        error_count = 0
        total_translated = 0
        
        # Create progress window
        progress_win = tk.Toplevel(self.root)
        progress_win.title("Processing CSV Files...")
        progress_win.geometry("450x150")
        progress_win.transient(self.root)
        progress_win.grab_set()
        
        progress_label = tk.Label(progress_win, text="Processing CSV files...", font=("Arial", 10))
        progress_label.pack(pady=10)
        
        status_label = tk.Label(progress_win, text="", font=("Arial", 9), fg="gray")
        status_label.pack(pady=5)
        
        translation_label = tk.Label(progress_win, text="", font=("Arial", 9), fg="blue")
        translation_label.pack(pady=5)
        
        for i, idx in enumerate(selected_indices, 1):
            filepath = self.csv_files[idx]
            filename = os.path.basename(filepath)
            
            progress_label.config(text=f"Processing file {i}/{len(selected_indices)}")
            status_label.config(text=f"{filename}")
            if translate:
                translation_label.config(text=f"Translation enabled (target: {target_lang})")
            progress_win.update()
            
            try:
                # Capture stdout to get translation count
                import io
                import sys
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()
                
                success = self.converter.process_csv(filepath, translate=translate, target_lang=target_lang, respect_existing=respect_existing)
                
                # Get output
                output = sys.stdout.getvalue()
                sys.stdout = old_stdout
                
                # Extract translation count from output
                if "translated" in output.lower():
                    import re
                    match = re.search(r'Successfully translated (\d+)', output)
                    if match:
                        total_translated += int(match.group(1))
                
                if success:
                    processed_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                sys.stdout = old_stdout
                messagebox.showerror("Error", f"Error processing {filename}:\n{str(e)}")
        
        progress_win.destroy()
        
        result_msg = f"Processed {processed_count} CSV file(s)"
        if translate and total_translated > 0:
            result_msg += f"\n\nSuccessfully translated {total_translated} domains to {target_lang}"
        if error_count > 0:
            result_msg += f"\n\nErrors: {error_count} file(s)"
        messagebox.showinfo("Complete", result_msg)
    
    def show_help(self):
        """Show help dialog"""
        help_window = tk.Toplevel(self.root)
        help_window.title("Help - Punycode ⟷ Unicode Converter")
        help_window.geometry("700x600")
        
        help_window.bind('<Escape>', lambda e: help_window.destroy())
        
        text = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, width=80, height=35)
        text.pack(padx=10, pady=10, fill='both', expand=True)
        
        help_text = """Punycode ⟷ Unicode Converter - Help

TAB 1: SINGLE CONVERT
- Convert individual domains between punycode and unicode
- Direction is automatically detected:
  • xn-- prefix → Punycode to Unicode
  • Otherwise → Unicode to Punycode
- Shows validation level for punycode:
  • PUNY_IDNA: Fully compliant (safe)
  • PUNY_ALT: Alternative encoding (check carefully)
  • PUNY_INVALID: Contains invalid characters
- Language detection for supported scripts:
  • CJK, Japanese, Arabic, Hebrew, Russian, Greek, Thai, Hindi, and more
- Optional translation to English or other languages

TAB 2: BATCH TXT FILES
- Process text files with one domain per line
- Supports both punycode → unicode and unicode → punycode
- Direction is auto-detected from the first line
- Creates output files:
  • filename_uni.txt (if input was punycode)
  • filename_puny.txt (if input was unicode)
  • filename_uni_translations.txt (if translation enabled)
- Select Files: Choose individual files
- Select Folder: Choose all .txt files in a folder
- Recursive Search: Include subfolders

TAB 3: CSV FILES
- Process CSV exports from Handshake platforms:
  • Bob Wallet (bob-tr, bob-tld)
  • Namebase (nb-tr, nb-tld)
  • Shakestation (ss-tr, ss-tld)
  • Firewallet (fw)
- Automatically detects CSV format from headers
- Adds three new columns:
  • unicode: Converted unicode text
  • descript-IDNA: Language/description (for PUNY_IDNA only)
  • translate-IDNA: Translation (for PUNY_IDNA only)
- Output file: original_name_YYYYMMDD_translated.csv
- Preserves original column order (Shakestation first 6 columns intact)
- RESPECT EXISTING ENTRIES:
  • By default, skips domains that already have descript/translate values
  • This prevents overwriting manual edits or existing translations
  • Uncheck "Respect existing entries" to re-process all domains
  • Useful when changing target language or updating translations

TRANSLATION
- Requires: pip install deep-translator
- Supports 100+ languages
- Default: English (en)
- Common codes: es (Spanish), fr (French), de (German), ja (Japanese), zh-CN (Chinese)
- Only translates PUNY_IDNA validated domains

BUTTONS
- Green "Convert": Process the current tab's action
- Yellow "Help": Show this help dialog
- Red "Exit": Close the application

SUPPORTED LANGUAGES (Auto-Detection)
Chinese/Japanese/Korean (CJK), Japanese (Hiragana/Katakana), Arabic, Hebrew,
Russian/Cyrillic, Greek, Thai, Hindi (Devanagari), Tamil, Malayalam, Georgian,
Armenian, Hawaiian, European (Latin Extended), and more!

TIPS
1. Test with a single domain first before batch processing
2. Translation is optional - core conversion works without it
3. Check validation levels - PUNY_IDNA is safest
4. CSV processing preserves original data structure
5. Use recursive search to process nested folders

EXAMPLE WORKFLOW
1. Export domains from your Handshake wallet (Bob, Namebase, etc.)
2. Select the CSV file in Tab 3
3. Enable translation if desired
4. Click "Convert" to process
5. Check output file with _translated suffix
"""
        text.insert(tk.END, help_text)
        text.config(state=tk.DISABLED)
        
        exit_btn = tk.Button(help_window, text="Close", bg="red", fg="white",
                            font=("Arial", 10, "bold"), command=help_window.destroy)
        exit_btn.pack(pady=5)


def main():
    root = tk.Tk()
    app = Puny2UniGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
