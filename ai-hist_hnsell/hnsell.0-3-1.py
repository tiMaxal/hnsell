import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinter.scrolledtext import ScrolledText
import pandas as pd
import idna
import re
import os
from datetime import datetime
import math
import codecs
from pathlib import Path
import unicodedata

class HNSellApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HNSell - Handshake Domain Manager")
        self.root.geometry("900x950")
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # Create bottom buttons first so they claim their space
        self.create_bottom_buttons()
        
        # Create notebook directly (no canvas wrapper)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=(5, 5))
        
        self.create_punytag_tab()
        self.create_puny2uni_tab()
        self.create_pagemaker_tab()
        
        self.sort_state = 0
    
    def is_emoji(self, char):
        """Check if character is an emoji"""
        try:
            char_name = unicodedata.name(char, '')
            return any(keyword in char_name for keyword in ['EMOJI', 'FACE', 'HEART', 'STAR', 'SYMBOL'])
        except:
            return False
    
    def get_char_description(self, char):
        """Get official Unicode character name"""
        try:
            return unicodedata.name(char, char)
        except:
            return char
    
    def detect_language(self, text):
        """Detect language based on Unicode blocks"""
        if not text:
            return None
        
        # Check for Hawaiian (uses macrons/kahakō: ā ē ī ō ū)
        hawaiian_vowels = {'ā', 'ē', 'ī', 'ō', 'ū', 'Ā', 'Ē', 'Ī', 'Ō', 'Ū'}
        if any(char in hawaiian_vowels for char in text):
            # Check if it's mostly Latin letters (Hawaiian characteristic)
            latin_chars = sum(1 for c in text if c.isalpha() and ord(c) < 0x0180)
            if latin_chars > len(text) * 0.5:  # More than 50% Latin-based
                return 'Hawaiian'
        
        # Check first character for language detection
        for char in text:
            if char.isspace():
                continue
            code_point = ord(char)
            
            # CJK Unified Ideographs
            if 0x4E00 <= code_point <= 0x9FFF:
                return 'Chinese/Japanese/Korean'
            # Hiragana
            elif 0x3040 <= code_point <= 0x309F:
                return 'Japanese'
            # Katakana
            elif 0x30A0 <= code_point <= 0x30FF:
                return 'Japanese'
            # Arabic (includes Urdu, Uyghur)
            elif 0x0600 <= code_point <= 0x06FF:
                return 'Arabic/Urdu/Uyghur'
            # Hebrew
            elif 0x0590 <= code_point <= 0x05FF:
                return 'Hebrew'
            # Cyrillic (Russian, Ukrainian, etc.)
            elif 0x0400 <= code_point <= 0x04FF:
                return 'Cyrillic (Russian/Ukrainian)'
            # Greek
            elif 0x0370 <= code_point <= 0x03FF:
                return 'Greek'
            # Thai
            elif 0x0E00 <= code_point <= 0x0E7F:
                return 'Thai'
            # Devanagari (Hindi/Sanskrit)
            elif 0x0900 <= code_point <= 0x097F:
                return 'Devanagari (Hindi)'
            # Tamil
            elif 0x0B80 <= code_point <= 0x0BFF:
                return 'Tamil'
            # Malayalam
            elif 0x0D00 <= code_point <= 0x0D7F:
                return 'Malayalam'
            # Georgian
            elif 0x10A0 <= code_point <= 0x10FF:
                return 'Georgian'
            # Armenian
            elif 0x0530 <= code_point <= 0x058F:
                return 'Armenian'
            # Latin Extended-A (European languages with diacritics)
            elif 0x0100 <= code_point <= 0x017F:
                return 'European (Latin Extended)'
            # Latin Extended-B
            elif 0x0180 <= code_point <= 0x024F:
                return 'European (Latin Extended)'
        
        return None
    
    def generate_description(self, unicode_str, tag):
        """Generate description based on unicode content for PUNY_IDNA only"""
        if tag != 'PUNY_IDNA' or not unicode_str:
            return ''
        
        # Check if purely emoji
        is_all_emoji = all(self.is_emoji(c) or c.isspace() for c in unicode_str if not c.isalnum())
        has_emoji = any(self.is_emoji(c) for c in unicode_str)
        
        if is_all_emoji and has_emoji:
            # Purely emoji - show character names
            names = []
            for char in unicode_str:
                if not char.isspace():
                    names.append(self.get_char_description(char))
            return ' + '.join(names)
        
        # Check for recognized language
        lang = self.detect_language(unicode_str)
        if lang:
            return lang
        
        # Mixed letters + unicode chars - show as it appears
        if has_emoji or any(ord(c) > 127 for c in unicode_str):
            # Has special unicode characters
            char_names = []
            for char in unicode_str:
                if ord(char) > 127 and not char.isspace():
                    char_names.append(self.get_char_description(char))
            if char_names:
                return f"Letters + {', '.join(char_names)}"
        
        return unicode_str
    
    def get_language_tag(self, unicode_str):
        """Get language tag for tagging purposes (returns simple language name or empty string)"""
        if not unicode_str:
            return ''
        
        lang = self.detect_language(unicode_str)
        if not lang:
            return ''
        
        # Simplify language names for tags
        lang_map = {
            'Chinese/Japanese/Korean': 'CJK',
            'Japanese': 'Japanese',
            'Arabic/Urdu/Uyghur': 'Arabic',
            'Hebrew': 'Hebrew',
            'Cyrillic (Russian/Ukrainian)': 'Cyrillic',
            'Greek': 'Greek',
            'Thai': 'Thai',
            'Devanagari (Hindi)': 'Hindi',
            'Tamil': 'Tamil',
            'Malayalam': 'Malayalam',
            'Georgian': 'Georgian',
            'Armenian': 'Armenian',
            'European (Latin Extended)': 'European',
            'Hawaiian': 'Hawaiian'
        }
        
        return lang_map.get(lang, '')
    
    def add_categorization_tags(self, df, domain_col):
        """Add categorization tags (3D-7D, 3L-5L, 3C-4C) to the dataframe
        Note: L tags require pure letters (no hyphens/underscores)
        C tags include hyphens/underscores in character count
        """
        # Helper: check if string is pure letters (no hyphen/underscore)
        def is_pure_alpha(s):
            return str(s).isalpha()
        
        # Create columns for each tag - 3D = 3 digits, 3L = 3 letters, 3C = 3 characters, etc
        df['3D'] = df[domain_col].apply(lambda x: 1 if str(x).isdigit() and len(str(x)) == 3 else '')
        df['3L'] = df[domain_col].apply(lambda x: 1 if is_pure_alpha(x) and len(str(x)) == 3 else '')
        df['3C'] = df.apply(lambda x: 1 if len(str(x[domain_col])) == 3 and not x['3L'] and not x['3D'] else '', axis=1)
        df['4D'] = df[domain_col].apply(lambda x: 1 if str(x).isdigit() and len(str(x)) == 4 else '')
        df['4L'] = df[domain_col].apply(lambda x: 1 if is_pure_alpha(x) and len(str(x)) == 4 else '')
        df['4C'] = df.apply(lambda x: 1 if len(str(x[domain_col])) == 4 and not x['4L'] and not x['4D'] else '', axis=1)
        df['5D'] = df[domain_col].apply(lambda x: 1 if str(x).isdigit() and len(str(x)) == 5 else '')
        df['5L'] = df[domain_col].apply(lambda x: 1 if is_pure_alpha(x) and len(str(x)) == 5 else '')
        df['5C'] = df.apply(lambda x: 1 if len(str(x[domain_col])) == 5 and not x['5L'] and not x['5D'] else '', axis=1)
        df['6D'] = df[domain_col].apply(lambda x: 1 if str(x).isdigit() and len(str(x)) == 6 else '')
        df['7D'] = df[domain_col].apply(lambda x: 1 if str(x).isdigit() and len(str(x)) == 7 else '')
        return df
    
    def create_bottom_buttons(self):
        button_frame = tk.Frame(self.root, height=60)
        button_frame.pack(side='bottom', fill='x', padx=10, pady=15)
        button_frame.pack_propagate(False)
        
        help_btn = tk.Button(button_frame, text="Help", bg="yellow", fg="black", 
                            font=("Arial", 12, "bold"), command=self.show_help, width=10, height=2)
        help_btn.pack(side='left', padx=5, pady=5)
        
        exit_btn = tk.Button(button_frame, text="Exit", bg="red", fg="white", 
                            font=("Arial", 12, "bold"), command=self.root.quit, width=10, height=2)
        exit_btn.pack(side='right', padx=5, pady=5)
        
        process_btn = tk.Button(button_frame, text="Process", bg="green", fg="white", 
                               font=("Arial", 12, "bold"), command=self.process_action, width=15, height=2)
        process_btn.pack(side='right', padx=5, pady=5)
        
    def create_punytag_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Punytag Processor")
        
        info_frame = tk.LabelFrame(tab, text="CSV File Processing", padx=10, pady=10)
        info_frame.pack(fill='both', expand=False, padx=10, pady=5)
        
        tk.Label(info_frame, text="Select CSV files to process (Bob, Namebase, Shakestation, or Firewallet exports):").pack(anchor='w')
        
        file_frame = tk.Frame(info_frame)
        file_frame.pack(fill='x', pady=5)
        
        tk.Button(file_frame, text="Select Files", command=self.select_punytag_files).pack(side='left', padx=5)
        tk.Button(file_frame, text="Select Folder (Recursive)", command=self.select_punytag_folder).pack(side='left', padx=5)
        
        self.recursive_var = tk.BooleanVar(value=False)
        tk.Checkbutton(file_frame, text="Recursive Search", variable=self.recursive_var).pack(side='left', padx=5)
        
        # Create PanedWindow for resizable file list
        paned = ttk.PanedWindow(tab, orient=tk.VERTICAL)
        paned.pack(fill='both', expand=True, padx=10, pady=5)
        
        list_frame = tk.LabelFrame(paned, text="Selected Files", padx=10, pady=10)
        paned.add(list_frame, weight=0)
        
        button_row = tk.Frame(list_frame)
        button_row.pack(fill='x', pady=5)
        tk.Button(button_row, text="Select All", command=lambda: self.toggle_all_files(True)).pack(side='left', padx=5)
        tk.Button(button_row, text="Select None", command=lambda: self.toggle_all_files(False)).pack(side='left', padx=5)
        tk.Button(button_row, text="Remove Selected", bg="#ff6b6b", fg="white", command=self.remove_punytag_files).pack(side='left', padx=5)
        tk.Button(button_row, text="Clear All", bg="#ff8c00", fg="white", command=self.clear_all_files).pack(side='left', padx=5)
        
        self.file_listbox_frame = tk.Frame(list_frame, height=200)
        self.file_listbox_frame.pack(fill='both', expand=True)
        self.file_listbox_frame.pack_propagate(False)
        
        scrollbar = tk.Scrollbar(self.file_listbox_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.file_listbox = tk.Listbox(self.file_listbox_frame, selectmode='multiple', yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        # Bind Del key to remove selected files
        self.file_listbox.bind('<Delete>', lambda e: self.remove_punytag_files())
        
        self.file_data = []
        
        options_frame = tk.LabelFrame(paned, text="Output Options", padx=10, pady=10)
        paned.add(options_frame, weight=0)
        
        self.rename_orig_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="Rename original files with '_orig' suffix", variable=self.rename_orig_var).pack(anchor='w')
        
        self.sort_to_subdirs_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="Sort processed files to subdirectories by source", variable=self.sort_to_subdirs_var).pack(anchor='w')
        
        self.delete_orig_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="Delete original files", variable=self.delete_orig_var).pack(anchor='w')
        
    def create_puny2uni_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Puny to Unicode")
        
        info_frame = tk.LabelFrame(tab, text="Convert between Punycode and Unicode", padx=10, pady=10)
        info_frame.pack(fill='both', expand=False, padx=10, pady=5)
        
        tk.Label(info_frame, text="Select .txt files (list format) for conversion:").pack(anchor='w')
        tk.Label(info_frame, text="• TXT files only: Pure uni2puny or puny2uni conversion").pack(anchor='w')
        tk.Label(info_frame, text="• Each line should contain one domain name").pack(anchor='w')
        
        file_frame = tk.Frame(info_frame)
        file_frame.pack(fill='x', pady=5)
        
        tk.Button(file_frame, text="Select Files", command=self.select_puny2uni_files).pack(side='left', padx=5)
        tk.Button(file_frame, text="Select Folder (Recursive)", command=self.select_puny2uni_folder).pack(side='left', padx=5)
        
        self.recursive_puny2uni_var = tk.BooleanVar(value=False)
        tk.Checkbutton(file_frame, text="Recursive Search", variable=self.recursive_puny2uni_var).pack(side='left', padx=5)
        
        # Create resizable file list section
        list_frame = tk.LabelFrame(tab, text="Selected Files", padx=10, pady=10)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        button_row = tk.Frame(list_frame)
        button_row.pack(fill='x', pady=5)
        tk.Button(button_row, text="Select All", command=lambda: self.toggle_puny2uni_files(True)).pack(side='left', padx=5)
        tk.Button(button_row, text="Select None", command=lambda: self.toggle_puny2uni_files(False)).pack(side='left', padx=5)
        tk.Button(button_row, text="Remove Selected", bg="#ff6b6b", fg="white", command=self.remove_puny2uni_files).pack(side='left', padx=5)
        tk.Button(button_row, text="Clear All", bg="#ff8c00", fg="white", command=self.clear_puny2uni_files).pack(side='left', padx=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.puny2uni_listbox = tk.Listbox(list_frame, selectmode='multiple', yscrollcommand=scrollbar.set)
        self.puny2uni_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.puny2uni_listbox.yview)
        
        # Bind Del key to remove selected files
        self.puny2uni_listbox.bind('<Delete>', lambda e: self.remove_puny2uni_files())
        
        self.puny2uni_files = []
        
    def create_pagemaker_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="PageMaker")
        
        info_frame = tk.LabelFrame(tab, text="Generate HTML Portfolio Page", padx=10, pady=10)
        info_frame.pack(fill='both', expand=False, padx=10, pady=5)
        
        tk.Label(info_frame, text="Select CSV files (Namebase or Shakestation) to generate portfolio page:").pack(anchor='w')
        
        file_frame = tk.Frame(info_frame)
        file_frame.pack(fill='x', pady=5)
        
        tk.Button(file_frame, text="Select CSV Files", command=self.select_pagemaker_files).pack(side='left', padx=5)
        tk.Button(file_frame, text="Select Folder (Recursive)", command=self.select_pagemaker_folder).pack(side='left', padx=5)
        
        self.recursive_pagemaker_var = tk.BooleanVar(value=False)
        tk.Checkbutton(file_frame, text="Recursive Search", variable=self.recursive_pagemaker_var).pack(side='left', padx=5)
        
        # Create PanedWindow for resizable file list
        paned = ttk.PanedWindow(tab, orient=tk.VERTICAL)
        paned.pack(fill='both', expand=True, padx=10, pady=5)
        
        list_frame = tk.LabelFrame(paned, text="Selected CSV Files", padx=10, pady=10)
        paned.add(list_frame, weight=0)  # Don't auto-expand
        
        button_row = tk.Frame(list_frame)
        button_row.pack(fill='x', pady=5)
        tk.Button(button_row, text="Select All", command=lambda: self.toggle_pagemaker_files(True)).pack(side='left', padx=5)
        tk.Button(button_row, text="Select None", command=lambda: self.toggle_pagemaker_files(False)).pack(side='left', padx=5)
        tk.Button(button_row, text="Remove Selected", bg="#ff6b6b", fg="white", 
                 command=self.remove_pagemaker_files).pack(side='left', padx=5)
        tk.Button(button_row, text="Clear All", bg="#ff8c00", fg="white", 
                 command=self.clear_pagemaker_files).pack(side='left', padx=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.pagemaker_listbox = tk.Listbox(list_frame, selectmode='multiple', yscrollcommand=scrollbar.set)
        self.pagemaker_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.pagemaker_listbox.yview)
        
        # Bind Del key to remove selected files
        self.pagemaker_listbox.bind('<Delete>', lambda e: self.remove_pagemaker_files())
        
        self.pagemaker_files = []
        
        # Create container for remaining options
        options_container = tk.Frame(tab)
        options_container.pack(fill='x', padx=10, pady=5)
        
        sort_frame = tk.Frame(options_container)
        sort_frame.pack(fill='x', padx=0, pady=5)
        
        tk.Button(sort_frame, text="Sort TLDs", command=self.cycle_sort).pack(side='left', padx=5)
        self.sort_label = tk.Label(sort_frame, text="Current: Random")
        self.sort_label.pack(side='left', padx=10)
        
        # Theme selection
        theme_frame = tk.LabelFrame(options_container, text="Theme Settings", padx=10, pady=10)
        theme_frame.pack(fill='x', padx=0, pady=5)
        
        theme_row1 = tk.Frame(theme_frame)
        theme_row1.pack(fill='x', pady=2)
        
        tk.Label(theme_row1, text="Theme:").pack(side='left', padx=5)
        self.theme_var = tk.StringVar(value="dark+light")
        theme_options = ["dark+light", "3-way switch", "custom CSS"]
        theme_menu = ttk.Combobox(theme_row1, textvariable=self.theme_var, values=theme_options, state='readonly', width=20)
        theme_menu.pack(side='left', padx=5)
        theme_menu.bind('<<ComboboxSelected>>', self.on_theme_change)
        
        tk.Button(theme_row1, text="Select CSS File", command=self.select_custom_css).pack(side='left', padx=5)
        self.css_label = tk.Label(theme_row1, text="No CSS file selected")
        self.css_label.pack(side='left', padx=10)
        
        # Color picker row (hidden by default)
        self.color_picker_frame = tk.Frame(theme_frame)
        
        tk.Label(self.color_picker_frame, text="Light color:").pack(side='left', padx=5)
        self.light_color_entry = tk.Entry(self.color_picker_frame, width=10)
        self.light_color_entry.insert(0, "#ccffff")
        self.light_color_entry.pack(side='left', padx=2)
        tk.Button(self.color_picker_frame, text="Pick", command=lambda: self.pick_color('light')).pack(side='left', padx=2)
        
        tk.Label(self.color_picker_frame, text="Dark color:").pack(side='left', padx=5)
        self.dark_color_entry = tk.Entry(self.color_picker_frame, width=10)
        self.dark_color_entry.insert(0, "#003366")
        self.dark_color_entry.pack(side='left', padx=2)
        tk.Button(self.color_picker_frame, text="Pick", command=lambda: self.pick_color('dark')).pack(side='left', padx=2)
        
        self.custom_css_file = None
        
        footer_frame = tk.LabelFrame(options_container, text="Footer & Credits (Optional)", padx=10, pady=10)
        footer_frame.pack(fill='x', padx=0, pady=5)
        
        footer_row = tk.Frame(footer_frame)
        footer_row.pack(fill='x', pady=2)
        tk.Button(footer_row, text="Select Footer HTML", command=self.select_footer).pack(side='left', padx=5)
        self.footer_label = tk.Label(footer_row, text="No footer file selected", width=25, anchor='w')
        self.footer_label.pack(side='left', padx=5)
        tk.Button(footer_row, text="Remove", bg="#ff6b6b", fg="white", command=self.remove_footer).pack(side='left', padx=5)
        
        credits_row = tk.Frame(footer_frame)
        credits_row.pack(fill='x', pady=2)
        tk.Button(credits_row, text="Select Credits HTML", command=self.select_credits).pack(side='left', padx=5)
        self.credits_label = tk.Label(credits_row, text="No credits file selected", width=25, anchor='w')
        self.credits_label.pack(side='left', padx=5)
        tk.Button(credits_row, text="Remove", bg="#ff6b6b", fg="white", command=self.remove_credits).pack(side='left', padx=5)
        
        self.footer_file = None
        self.credits_file = None
        
        update_frame = tk.LabelFrame(options_container, text="Update Existing Page", padx=10, pady=10)
        update_frame.pack(fill='x', padx=0, pady=5)
        
        update_row = tk.Frame(update_frame)
        update_row.pack(fill='x', pady=2)
        tk.Button(update_row, text="Select HTML File", command=self.select_html_to_update).pack(side='left', padx=5)
        self.html_update_label = tk.Label(update_row, text="No HTML file selected", width=25, anchor='w')
        self.html_update_label.pack(side='left', padx=5)
        tk.Button(update_row, text="Remove", bg="#ff6b6b", fg="white", command=self.remove_html_to_update).pack(side='left', padx=5)
        
        self.html_to_update = None
        
        output_frame = tk.LabelFrame(options_container, text="Output", padx=10, pady=10)
        output_frame.pack(fill='x', padx=0, pady=5)
        
        output_row = tk.Frame(output_frame)
        output_row.pack(fill='x', pady=5)
        tk.Button(output_row, text="Select Output File", command=self.select_output_file).pack(side='left', padx=5)
        self.output_filename_entry = tk.Entry(output_row, width=40)
        self.output_filename_entry.insert(0, "portfolio.html")
        self.output_filename_entry.pack(side='left', padx=5, fill='x', expand=True)
        
        # List all and email options
        options_frame = tk.LabelFrame(options_container, text="Display Options", padx=10, pady=10)
        options_frame.pack(fill='x', padx=0, pady=5)
        
        checkbox_row = tk.Frame(options_frame)
        checkbox_row.pack(fill='x', pady=2)
        
        self.list_all_var = tk.BooleanVar(value=False)
        tk.Checkbutton(checkbox_row, text="List all domains (ignore email/price requirement for bob/fw)", variable=self.list_all_var).pack(side='left', padx=5)
        
        email_row = tk.Frame(options_frame)
        email_row.pack(fill='x', pady=5)
        tk.Label(email_row, text="Auto-append email for domains with price (leave empty to skip):").pack(side='left', padx=5)
        self.auto_email_entry = tk.Entry(email_row, width=30)
        self.auto_email_entry.pack(side='left', padx=5)
        tk.Label(email_row, text="Format: user@gmail.com or user+@gmail.com", font=("Arial", 8), fg="gray").pack(side='left', padx=5)
        
    def cycle_sort(self):
        sort_states = ["Random", "Alphabetical ▲", "Alphabetical ▼", "Price ▲", "Price ▼"]
        self.sort_state = (self.sort_state + 1) % 5
        self.sort_label.config(text=f"Current: {sort_states[self.sort_state]}")
        
    def select_footer(self):
        file = filedialog.askopenfilename(title="Select Footer HTML", filetypes=[("HTML files", "*.html")])
        if file:
            self.footer_file = file
            self.footer_label.config(text=os.path.basename(file))
            
    def select_credits(self):
        file = filedialog.askopenfilename(title="Select Credits HTML", filetypes=[("HTML files", "*.html")])
        if file:
            self.credits_file = file
            self.credits_label.config(text=os.path.basename(file))
    
    def remove_footer(self):
        self.footer_file = None
        self.footer_label.config(text="No footer file selected")
        
    def remove_credits(self):
        self.credits_file = None
        self.credits_label.config(text="No credits file selected")
    
    def remove_html_to_update(self):
        self.html_to_update = None
        self.html_update_label.config(text="No HTML file selected")
    
    def on_theme_change(self, event=None):
        """Show/hide color picker based on theme selection"""
        theme = self.theme_var.get()
        if theme == "3-way switch":
            self.color_picker_frame.pack(fill='x', pady=5)
        else:
            self.color_picker_frame.pack_forget()
    
    def pick_color(self, color_type):
        """Open color picker dialog"""
        try:
            from tkinter import colorchooser
            current_color = self.light_color_entry.get() if color_type == 'light' else self.dark_color_entry.get()
            result = colorchooser.askcolor(color=current_color, title=f"Choose {color_type} color")
            if result and result[1]:  # result[1] is the hex value
                if color_type == 'light':
                    self.light_color_entry.delete(0, tk.END)
                    self.light_color_entry.insert(0, result[1])
                else:
                    self.dark_color_entry.delete(0, tk.END)
                    self.dark_color_entry.insert(0, result[1])
        except Exception as e:
            messagebox.showerror("Color Picker Error", f"Failed to open color picker: {str(e)}")
    
    def select_output_file(self):
        file = filedialog.asksaveasfilename(
            title="Select Output File",
            defaultextension=".html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
            initialfile="portfolio.html"
        )
        if file:
            self.output_filename_entry.delete(0, tk.END)
            self.output_filename_entry.insert(0, file)
    
    def select_custom_css(self):
        file = filedialog.askopenfilename(title="Select Custom CSS", filetypes=[("CSS files", "*.css"), ("All files", "*.*")])
        if file:
            self.custom_css_file = file
            self.css_label.config(text=os.path.basename(file))
            
    def select_html_to_update(self):
        file = filedialog.askopenfilename(title="Select HTML to Update", filetypes=[("HTML files", "*.html")])
        if file:
            self.html_to_update = file
            self.html_update_label.config(text=os.path.basename(file))
            
    def select_punytag_files(self):
        files = filedialog.askopenfilenames(title="Select CSV Files", filetypes=[("CSV files", "*.csv")])
        if files:
            self.add_files_to_list(files)
            
    def select_punytag_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            files = []
            if self.recursive_var.get():
                for root, dirs, filenames in os.walk(folder):
                    for filename in filenames:
                        if filename.endswith('.csv'):
                            files.append(os.path.join(root, filename))
            else:
                files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.csv')]
            self.add_files_to_list(files)
            
    def add_files_to_list(self, files):
        for file in files:
            if file not in [f['path'] for f in self.file_data]:
                source_type = self.detect_csv_source(file)
                self.file_data.append({'path': file, 'source': source_type, 'selected': True})
                display_text = f"[{source_type}] {os.path.basename(file)}"
                self.file_listbox.insert(tk.END, display_text)
                self.file_listbox.select_set(tk.END)
                
    def detect_csv_source(self, filepath):
        try:
            df = pd.read_csv(filepath, nrows=1)
            headers = df.columns.tolist()
            headers_lower = [h.lower() for h in headers]
            
            # Each format uses ONLY ONE unique identifier for efficiency
            # Namebase Transactions: extra.domain (dot notation) is UNIQUE
            if 'extra.domain' in headers:
                return 'nb-tr'
            # Shakestation TLD: for_sale column is UNIQUE
            elif 'for_sale' in headers_lower:
                return 'ss-tld'
            # Shakestation Transactions: coin column is UNIQUE
            elif 'coin' in headers_lower:
                return 'ss-tr'
            # Firewallet: expiry column is UNIQUE (date format, only FW has this)
            elif 'expiry' in headers_lower:
                return 'fw'
            # Namebase TLD: price_hns is UNIQUE to Namebase
            elif 'price_hns' in headers_lower:
                return 'nb-tld'
            # Bob Wallet Transactions: txhash column is UNIQUE
            elif 'txhash' in headers_lower:
                return 'bob-tr'
            # Bob Wallet TLD (processed): domains column (plural) - only after txhash ruled out
            elif 'domains' in headers_lower:
                return 'bob-tld'
            # Bob Wallet TLD (unprocessed): NO header, single column of domain names
            # - CSV with single column (not .txt file)
            # - First entry is domain name (alphanumeric/hyphen/underscore, no dot)
            # - Can be used in PageMaker with auto-email feature for contact
            elif len(headers) == 1:
                first_val = str(headers[0]).lower()
                # Exclude if first value is a known column name from other formats
                if first_val in ['name', 'domain', 'time', 'action', 'coin', 'expiry', 'value', 'maxbid', 'price_hns', 'for_sale']:
                    return 'unknown'
                # Accept if looks like domain: xn-- prefix OR alphanumeric/hyphen/underscore <= 63 chars
                if first_val.startswith('xn--') or (len(first_val) <= 63 and all(c.isalnum() or c in '-_' for c in first_val)):
                    return 'bob-tld'
            return 'unknown'
        except:
            return 'unknown'
            
    def toggle_all_files(self, select):
        if select:
            self.file_listbox.select_set(0, tk.END)
        else:
            self.file_listbox.select_clear(0, tk.END)
    
    def remove_punytag_files(self):
        """Remove selected files from punytag list"""
        selected_indices = list(self.file_listbox.curselection())
        # Remove in reverse order to avoid index shifting
        for idx in reversed(selected_indices):
            self.file_listbox.delete(idx)
            del self.file_data[idx]
    
    def clear_all_files(self):
        """Clear all files from punytag list"""
        self.file_listbox.delete(0, tk.END)
        self.file_data = []
            
    def select_puny2uni_files(self):
        files = filedialog.askopenfilenames(title="Select TXT Files", 
                                           filetypes=[("Text files", "*.txt"), 
                                                     ("All files", "*.*")])
        if files:
            for file in files:
                if file not in self.puny2uni_files:
                    self.puny2uni_files.append(file)
                    self.puny2uni_listbox.insert(tk.END, os.path.basename(file))
    
    def select_puny2uni_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            files = []
            if self.recursive_puny2uni_var.get():
                for root, dirs, filenames in os.walk(folder):
                    for filename in filenames:
                        if filename.endswith('.txt'):
                            files.append(os.path.join(root, filename))
            else:
                files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.txt')]
            for file in files:
                if file not in self.puny2uni_files:
                    self.puny2uni_files.append(file)
                    self.puny2uni_listbox.insert(tk.END, os.path.basename(file))
    
    def toggle_puny2uni_files(self, select):
        if select:
            self.puny2uni_listbox.select_set(0, tk.END)
        else:
            self.puny2uni_listbox.select_clear(0, tk.END)
    
    def remove_puny2uni_files(self):
        """Remove selected files from puny2uni list"""
        selected_indices = list(self.puny2uni_listbox.curselection())
        # Remove in reverse order to avoid index shifting
        for idx in reversed(selected_indices):
            self.puny2uni_listbox.delete(idx)
            del self.puny2uni_files[idx]
    
    def clear_puny2uni_files(self):
        """Clear all files from puny2uni list"""
        self.puny2uni_listbox.delete(0, tk.END)
        self.puny2uni_files = []
                    
    def select_pagemaker_files(self):
        files = filedialog.askopenfilenames(title="Select CSV Files", filetypes=[("CSV files", "*.csv")])
        if files:
            for file in files:
                if file not in self.pagemaker_files:
                    self.pagemaker_files.append(file)
                    self.pagemaker_listbox.insert(tk.END, os.path.basename(file))
    
    def select_pagemaker_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            files = []
            if self.recursive_pagemaker_var.get():
                for root, dirs, filenames in os.walk(folder):
                    for filename in filenames:
                        if filename.endswith('.csv'):
                            files.append(os.path.join(root, filename))
            else:
                files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.csv')]
            for file in files:
                if file not in self.pagemaker_files:
                    self.pagemaker_files.append(file)
                    self.pagemaker_listbox.insert(tk.END, os.path.basename(file))
    
    def toggle_pagemaker_files(self, select):
        if select:
            self.pagemaker_listbox.select_set(0, tk.END)
        else:
            self.pagemaker_listbox.select_clear(0, tk.END)
    
    def remove_pagemaker_files(self):
        """Remove selected files from pagemaker list"""
        selected_indices = list(self.pagemaker_listbox.curselection())
        # Remove in reverse order to avoid index shifting
        for idx in reversed(selected_indices):
            self.pagemaker_listbox.delete(idx)
            del self.pagemaker_files[idx]
    
    def clear_pagemaker_files(self):
        """Clear all files from pagemaker list"""
        self.pagemaker_listbox.delete(0, tk.END)
        self.pagemaker_files = []
                    
    def show_help(self):
        help_window = tk.Toplevel(self.root)
        help_window.title("Help - How to Use HNSell")
        help_window.geometry("700x600")
        
        # Bind ESC key to close window
        help_window.bind('<Escape>', lambda e: help_window.destroy())
        
        text = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, width=80, height=35)
        text.pack(padx=10, pady=10, fill='both', expand=True)
        
        help_text = """HNSell - Handshake Domain Manager
        
TAB 1: PUNYTAG PROCESSOR
- Processes CSV exports from Bob Wallet, Namebase, Shakestation, and Firewallet
- Automatically detects source format from CSV headers
- Converts punycode domains to unicode with tagging
- New columns (unicode, descript-IDNA, translate-IDNA, tags) are added at the END
  of the CSV to preserve original column order
- Shakestation compatibility: Original first 6 columns remain in place for upload updates
- Options:
  • Select Files: Choose individual CSV files
  • Select Folder: Choose a folder (with optional recursive search)
  • Select All/None: Toggle selection of all files
  • Rename original: Adds '_orig' suffix to source files
  • Sort to subdirs: Organizes outputs by source type
  • Delete original: Removes original files after processing

TAB 2: PUNY ⟷ UNICODE
- Converts between punycode and unicode formats
- Supports .txt and .csv files
- TXT files: Pure conversion based on content
- CSV files: Assumes Bob-TLD format with single column

TAB 3: PAGEMAKER
- Generates HTML portfolio pages from domain CSV files
- Features:
  • Select CSV files from Namebase or Shakestation
  • Sort TLDs: Cycles through Random → Alphabetical ▲ → Alphabetical ▼
  • Optional footer and credits HTML files
  • Update existing HTML: Add/remove domains from existing page
  • For Shakestation: Only includes domains marked 'for_sale=TRUE'
  • Links point to appropriate marketplace (Namebase or Shakestation)
  • Bob/Firewallet: Displays contact info (no marketplace links)

ADDING PRICE/EMAIL COLUMNS:
To add pricing and contact info to Bob Wallet or Firewallet CSVs:
- Add a column named EXACTLY 'price' (lowercase) with HNS values
- Add a column named EXACTLY 'email' OR 'eml' (lowercase) with contact email
- Use these exact names - other variations will not be recognized
- Process with Punytag Processor first, then use in PageMaker

BUTTONS:
- Green "Process": Execute the current tab's action
- Yellow "Help": Show this help dialog
- Red "Exit": Close the application

OUTPUT:
- Processed files include date stamp (yyyymmdd)
- Already processed files are skipped to avoid duplication
"""
        text.insert(tk.END, help_text)
        text.config(state=tk.DISABLED)
        
        exit_btn = tk.Button(help_window, text="Exit", bg="red", fg="white", 
                            font=("Arial", 10, "bold"), command=help_window.destroy)
        exit_btn.pack(pady=5)
        
    def process_action(self):
        current_tab = self.notebook.index(self.notebook.select())
        
        if current_tab == 0:
            self.process_punytag()
        elif current_tab == 1:
            self.process_puny2uni()
        elif current_tab == 2:
            self.process_pagemaker()
            
    def punycode_convert_validate(self, punycode_str):
        if punycode_str.startswith("xn--"):
            try:
                decoded = punycode_str.encode('ascii').decode('idna', errors='strict')
                return decoded, 'PUNY_IDNA'
            except UnicodeError:
                try:
                    unicode_str = idna.decode(punycode_str)
                    return unicode_str, 'PUNY_ALT'
                except Exception as e:
                    error_message = str(e)
                    unicode_match = re.search(r"'([^']*)'", error_message)
                    if unicode_match:
                        return unicode_match.group(1), 'PUNY_ALT'
                    else:
                        return punycode_str, 'PUNY_INVALID'
        else:
            return '', ''
            
    def process_bob_tr(self, filepath, output_path):
        df = pd.read_csv(filepath)
        
        def process_row(row):
            if isinstance(row['domains'], str):
                names = row['domains'].split(',')
                puny_names = []
                for name in names:
                    unicode_name, tag = self.punycode_convert_validate(name.strip())
                    if tag.startswith('PUNY'):
                        puny_names.append(f"{name.strip()} ({unicode_name})")
                    else:
                        puny_names.append(name.strip())
                return ', '.join(puny_names)
            elif isinstance(row['domains'], float) and math.isnan(row['domains']):
                return ''
            else:
                return str(row['domains'])
                
        df['domains'] = df.apply(process_row, axis=1)
        df['descript-IDNA'] = ''
        df['translate-IDNA'] = ''
        df.to_csv(output_path, index=False)
        
    def process_nb_tr(self, filepath, output_path):
        df = pd.read_csv(filepath)
        
        punycode_info = df['extra.domain'].apply(lambda x: self.punycode_convert_validate(x) if isinstance(x, str) else ('', ''))
        
        df['unicode'] = [re.sub(r'(?:\\x[\da-fA-F]{2})+|\\u(?:[\da-fA-F]{4})+', '', info[0]) if info[0] and info[0] != df.at[i, 'extra.domain'] else '' for i, info in enumerate(punycode_info)]
        
        # Add categorization tags (3D-7D, 3L-5L, 3C-4C)
        df = self.add_categorization_tags(df, 'extra.domain')
        
        df['PUNY_INVALID'] = [1 if (info[0] != df.at[i, 'unicode']) or (info[0] and df.at[i, 'unicode'] == df.at[i, 'extra.domain']) else '' for i, info in enumerate(punycode_info)]
        df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
        df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
        df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
        
        # Add language tags
        df['LANG_TAG'] = [self.get_language_tag(df.at[i, 'unicode']) for i in range(len(df))]
        
        tags_columns = ['3D', '3L', '3C', '4D', '4L', '4C', '5D', '5L', '5C', '6D', '7D', 'PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
        df['tags'] = df.apply(lambda row: ','.join(filter(None, [tag if row.get(tag) == 1 else '' for tag in tags_columns] + [row.get('LANG_TAG', '')])), axis=1)
        df.drop(columns=tags_columns + ['LANG_TAG'], inplace=True)
        
        # Add descript-IDNA and translate-IDNA columns
        df['descript-IDNA'] = [self.generate_description(df.at[i, 'unicode'], info[1]) for i, info in enumerate(punycode_info)]
        df['translate-IDNA'] = ''
        
        df = df[['extra.domain', 'unicode', 'descript-IDNA', 'translate-IDNA', 'tags'] + [col for col in df.columns if col not in ['extra.domain', 'unicode', 'descript-IDNA', 'translate-IDNA', 'tags']]]
        
        df.to_csv(output_path, index=False)
        
    def process_ss_tld(self, filepath, output_path):
        try:
            df = pd.read_csv(filepath, quoting=1, escapechar='\\')
        except:
            df = pd.read_csv(filepath, on_bad_lines='skip')
        
        domain_col = None
        for col in df.columns:
            if col.lower() == 'domain':
                domain_col = col
                break
        
        if not domain_col:
            raise ValueError("No 'domain' column found in Shakestation CSV")
        
        # Store original columns order
        original_cols = df.columns.tolist()
        
        punycode_info = df[domain_col].apply(lambda x: self.punycode_convert_validate(x) if isinstance(x, str) else ('', ''))
        
        df['unicode'] = [re.sub(r'(?:\\x[\da-fA-F]{2})+|\\u(?:[\da-fA-F]{4})+', '', info[0]) if info[0] and info[0] != df.at[i, domain_col] else '' for i, info in enumerate(punycode_info)]
        
        # Add categorization tags (3D-7D, 3L-5L, 3C-4C)
        df = self.add_categorization_tags(df, domain_col)
        
        df['PUNY_INVALID'] = [1 if (info[0] != df.at[i, 'unicode']) or (info[0] and df.at[i, 'unicode'] == df.at[i, domain_col]) else '' for i, info in enumerate(punycode_info)]
        df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
        df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
        df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
        
        # Add language tags
        df['LANG_TAG'] = [self.get_language_tag(df.at[i, 'unicode']) for i in range(len(df))]
        
        tags_columns = ['3D', '3L', '3C', '4D', '4L', '4C', '5D', '5L', '5C', '6D', '7D', 'PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
        df['tags'] = df.apply(lambda row: ','.join(filter(None, [tag if row.get(tag) == 1 else '' for tag in tags_columns] + [row.get('LANG_TAG', '')])), axis=1)
        df.drop(columns=tags_columns + ['LANG_TAG'], inplace=True)
        
        # Add descript-IDNA and translate-IDNA columns
        df['descript-IDNA'] = [self.generate_description(df.at[i, 'unicode'], info[1]) for i, info in enumerate(punycode_info)]
        df['translate-IDNA'] = ''
        
        # Preserve original column order, append new columns at end
        new_cols = ['unicode', 'descript-IDNA', 'translate-IDNA', 'tags']
        col_order = original_cols + [col for col in new_cols if col not in original_cols]
        df = df[col_order]
        
        df.to_csv(output_path, index=False)
        
    def process_ss_tr(self, filepath, output_path):
        try:
            df = pd.read_csv(filepath, quoting=1, escapechar='\\')
        except:
            df = pd.read_csv(filepath, on_bad_lines='skip')
        
        domain_col = None
        for col in df.columns:
            if col.lower() == 'domain':
                domain_col = col
                break
        
        if not domain_col:
            raise ValueError("No 'domain' column found in Shakestation TR CSV")
        
        # Store original columns order
        original_cols = df.columns.tolist()
        
        punycode_info = df[domain_col].apply(lambda x: self.punycode_convert_validate(x) if isinstance(x, str) else ('', ''))
        
        df['unicode'] = [re.sub(r'(?:\\x[\da-fA-F]{2})+|\\u(?:[\da-fA-F]{4})+', '', info[0]) if info[0] and info[0] != df.at[i, domain_col] else '' for i, info in enumerate(punycode_info)]
        
        # Add categorization tags (3D-7D, 3L-5L, 3C-4C)
        df = self.add_categorization_tags(df, domain_col)
        
        df['PUNY_INVALID'] = [1 if (info[0] != df.at[i, 'unicode']) or (info[0] and df.at[i, 'unicode'] == df.at[i, domain_col]) else '' for i, info in enumerate(punycode_info)]
        df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
        df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
        df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
        
        # Add language tags
        df['LANG_TAG'] = [self.get_language_tag(df.at[i, 'unicode']) for i in range(len(df))]
        
        tags_columns = ['3D', '3L', '3C', '4D', '4L', '4C', '5D', '5L', '5C', '6D', '7D', 'PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
        df['tags'] = df.apply(lambda row: ','.join(filter(None, [tag if row.get(tag) == 1 else '' for tag in tags_columns] + [row.get('LANG_TAG', '')])), axis=1)
        df.drop(columns=tags_columns + ['LANG_TAG'], inplace=True)
        
        # Add descript-IDNA and translate-IDNA columns
        df['descript-IDNA'] = [self.generate_description(df.at[i, 'unicode'], info[1]) for i, info in enumerate(punycode_info)]
        df['translate-IDNA'] = ''
        
        # Preserve original column order, append new columns at end
        new_cols = ['unicode', 'descript-IDNA', 'translate-IDNA', 'tags']
        col_order = original_cols + [col for col in new_cols if col not in original_cols]
        df = df[col_order]
        
        df.to_csv(output_path, index=False)
        
    def process_nb_tld(self, filepath, output_path):
        df = pd.read_csv(filepath)
        
        name_col = None
        for col in df.columns:
            if col.lower() == 'name':
                name_col = col
                break
        
        if not name_col:
            raise ValueError("No 'name' column found in Namebase TLD CSV")
        
        if 'unicode' not in df.columns:
            punycode_info = df[name_col].apply(lambda x: self.punycode_convert_validate(x) if isinstance(x, str) else ('', ''))
            df['unicode'] = [re.sub(r'(?:\\x[\da-fA-F]{2})+|\\u(?:[\da-fA-F]{4})+', '', info[0]) if info[0] and info[0] != df.at[i, name_col] else '' for i, info in enumerate(punycode_info)]
            
            # Add categorization tags (3D-7D, 3L-5L, 3C-4C)
            df = self.add_categorization_tags(df, name_col)
            
            df['PUNY_INVALID'] = [1 if (info[0] != df.at[i, 'unicode']) or (info[0] and df.at[i, 'unicode'] == df.at[i, name_col]) else '' for i, info in enumerate(punycode_info)]
            df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
            df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
            df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
            
            # Add language tags
            df['LANG_TAG'] = [self.get_language_tag(df.at[i, 'unicode']) for i in range(len(df))]
            
            tags_columns = ['3D', '3L', '3C', '4D', '4L', '4C', '5D', '5L', '5C', '6D', '7D', 'PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
            new_tag_str = df.apply(lambda row: ','.join(filter(None, [tag if row.get(tag) == 1 else '' for tag in tags_columns] + [row.get('LANG_TAG', '')])), axis=1)
            
            if 'tags' in df.columns:
                existing_tags = df['tags'].fillna('')
                df['tags'] = df.apply(lambda row: ','.join(filter(None, [str(row['tags']), new_tag_str[row.name]])), axis=1)
            else:
                df['tags'] = new_tag_str
            df.drop(columns=tags_columns + ['LANG_TAG'], inplace=True)
            
            # Add descript-IDNA and translate-IDNA columns
            df['descript-IDNA'] = [self.generate_description(df.at[i, 'unicode'], info[1]) for i, info in enumerate(punycode_info)]
            df['translate-IDNA'] = ''
            
            col_order = [name_col, 'unicode', 'descript-IDNA', 'translate-IDNA', 'tags'] + [col for col in df.columns if col not in [name_col, 'unicode', 'descript-IDNA', 'translate-IDNA', 'tags']]
            df = df[col_order]
        
        df.to_csv(output_path, index=False)
        
    def process_bob_tld(self, filepath, output_path):
        # Bob TLD files often have no header, just domain names
        df = pd.read_csv(filepath, header=None, names=['domains'])
        
        if 'domains' not in df.columns:
            raise ValueError("No 'domains' column found in Bob TLD CSV")
        
        punycode_info = df['domains'].apply(lambda x: self.punycode_convert_validate(x) if isinstance(x, str) else ('', ''))
        
        df['unicode'] = [re.sub(r'(?:\\x[\da-fA-F]{2})+|\\u(?:[\da-fA-F]{4})+', '', info[0]) if info[0] and info[0] != df.at[i, 'domains'] else '' for i, info in enumerate(punycode_info)]
        
        # Add categorization tags (3D-7D, 3L-5L, 3C-4C)
        df = self.add_categorization_tags(df, 'domains')
        
        df['PUNY_INVALID'] = [1 if (info[0] != df.at[i, 'unicode']) or (info[0] and df.at[i, 'unicode'] == df.at[i, 'domains']) else '' for i, info in enumerate(punycode_info)]
        df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
        df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
        df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
        
        # Add language tags
        df['LANG_TAG'] = [self.get_language_tag(df.at[i, 'unicode']) for i in range(len(df))]
        
        tags_columns = ['3D', '3L', '3C', '4D', '4L', '4C', '5D', '5L', '5C', '6D', '7D', 'PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
        df['tags'] = df.apply(lambda row: ','.join(filter(None, [tag if row.get(tag) == 1 else '' for tag in tags_columns] + [row.get('LANG_TAG', '')])), axis=1)
        df.drop(columns=tags_columns + ['LANG_TAG'], inplace=True)
        
        # Add descript-IDNA and translate-IDNA columns
        df['descript-IDNA'] = [self.generate_description(df.at[i, 'unicode'], info[1]) for i, info in enumerate(punycode_info)]
        df['translate-IDNA'] = ''
        
        df = df[['domains', 'unicode', 'descript-IDNA', 'translate-IDNA', 'tags']]
        
        df.to_csv(output_path, index=False)
        
    def process_fw(self, filepath, output_path):
        df = pd.read_csv(filepath)
        
        domain_col = df.columns[0] if len(df.columns) > 0 else None
        if not domain_col:
            raise ValueError("No columns found in Firewallet CSV")
        
        punycode_info = df[domain_col].apply(lambda x: self.punycode_convert_validate(x) if isinstance(x, str) else ('', ''))
        
        df['unicode'] = [re.sub(r'(?:\\x[\da-fA-F]{2})+|\\u(?:[\da-fA-F]{4})+', '', info[0]) if info[0] and info[0] != df.at[i, domain_col] else '' for i, info in enumerate(punycode_info)]
        
        # Add categorization tags (3D-7D, 3L-5L, 3C-4C)
        df = self.add_categorization_tags(df, domain_col)
        
        df['PUNY_INVALID'] = [1 if (info[0] != df.at[i, 'unicode']) or (info[0] and df.at[i, 'unicode'] == df.at[i, domain_col]) else '' for i, info in enumerate(punycode_info)]
        df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
        df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
        df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
        
        # Add language tags
        df['LANG_TAG'] = [self.get_language_tag(df.at[i, 'unicode']) for i in range(len(df))]
        
        tags_columns = ['3D', '3L', '3C', '4D', '4L', '4C', '5D', '5L', '5C', '6D', '7D', 'PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
        df['tags'] = df.apply(lambda row: ','.join(filter(None, [tag if row.get(tag) == 1 else '' for tag in tags_columns] + [row.get('LANG_TAG', '')])), axis=1)
        df.drop(columns=tags_columns + ['LANG_TAG'], inplace=True)
        
        # Add descript-IDNA and translate-IDNA columns
        df['descript-IDNA'] = [self.generate_description(df.at[i, 'unicode'], info[1]) for i, info in enumerate(punycode_info)]
        df['translate-IDNA'] = ''
        
        col_order = [domain_col, 'unicode', 'descript-IDNA', 'translate-IDNA', 'tags'] + [col for col in df.columns if col not in [domain_col, 'unicode', 'descript-IDNA', 'translate-IDNA', 'tags']]
        df = df[col_order]
        
        df.to_csv(output_path, index=False)
        
    def process_punytag(self):
        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select files to process")
            return
            
        date_suffix = datetime.now().strftime("%Y%m%d")
        processed_count = 0
        skipped_count = 0
        
        for idx in selected_indices:
            file_info = self.file_data[idx]
            filepath = file_info['path']
            source_type = file_info['source']
            
            file_dir = os.path.dirname(filepath)
            file_name = os.path.basename(filepath)
            file_base, file_ext = os.path.splitext(file_name)
            
            # Skip if already marked as original
            if '_orig' in file_base:
                skipped_count += 1
                continue
            
            # Check if this file was already processed (has date stamp at end)
            # Pattern: filename_YYYYMMDD.csv or filename.date_YYYYMMDD.csv
            import re as regex_module
            if regex_module.search(r'_\d{8}$', file_base):
                skipped_count += 1
                continue
                
            output_name = f"{file_base}_{date_suffix}{file_ext}"
            output_path = os.path.join(file_dir, output_name)
            
            # Skip if output already exists
            if os.path.exists(output_path):
                skipped_count += 1
                continue
                
            try:
                if source_type == 'bob-tr':
                    self.process_bob_tr(filepath, output_path)
                elif source_type == 'nb-tr':
                    self.process_nb_tr(filepath, output_path)
                elif source_type == 'ss-tld':
                    self.process_ss_tld(filepath, output_path)
                elif source_type == 'ss-tr':
                    self.process_ss_tr(filepath, output_path)
                elif source_type == 'nb-tld':
                    self.process_nb_tld(filepath, output_path)
                elif source_type == 'bob-tld':
                    self.process_bob_tld(filepath, output_path)
                elif source_type == 'fw':
                    self.process_fw(filepath, output_path)
                else:
                    messagebox.showinfo("Info", f"Processing for {source_type} not yet implemented")
                    continue
                    
                if self.rename_orig_var.get():
                    orig_name = f"{file_base}_orig{file_ext}"
                    orig_path = os.path.join(file_dir, orig_name)
                    os.rename(filepath, orig_path)
                    
                if self.delete_orig_var.get():
                    orig_path = os.path.join(file_dir, f"{file_base}_orig{file_ext}")
                    if os.path.exists(orig_path):
                        os.remove(orig_path)
                        
                processed_count += 1
                
            except Exception as e:
                messagebox.showerror("Error", f"Error processing {file_name}:\n{str(e)}")
                
        result_msg = f"Processed {processed_count} file(s)"
        if skipped_count > 0:
            result_msg += f"\nSkipped {skipped_count} file(s) (already processed or marked as original)"
        messagebox.showinfo("Complete", result_msg)
        
    def process_puny2uni(self):
        selected_indices = self.puny2uni_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select files to process")
            return
            
        processed_count = 0
        
        for idx in selected_indices:
            filepath = self.puny2uni_files[idx]
            
            try:
                if not filepath.endswith('.txt'):
                    messagebox.showwarning("Invalid File", f"Skipping {os.path.basename(filepath)} - only .txt files are supported")
                    continue
                    
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                results = []
                first_line = lines[0].strip() if lines else ''
                
                if first_line.startswith('xn--'):
                    for line in lines:
                        domain = line.strip()
                        if domain:
                            unicode_val = self.punycode_convert_validate(domain)[0]
                            results.append(unicode_val if unicode_val else domain)
                    output_path = filepath.replace('.txt', '_uni.txt')
                else:
                    for line in lines:
                        domain = line.strip()
                        if domain:
                            puny_val = self.unicode_to_punycode(domain)
                            results.append(puny_val)
                    output_path = filepath.replace('.txt', '_puny.txt')
                    
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(results))
                    
                processed_count += 1
                
            except Exception as e:
                messagebox.showerror("Error", f"Error processing {os.path.basename(filepath)}:\n{str(e)}")
                
        messagebox.showinfo("Complete", f"Processed {processed_count} file(s)")
        
    def unicode_to_punycode(self, unicode_string):
        try:
            punycode_encoder = codecs.getencoder('punycode')
            punycode_string, _ = punycode_encoder(unicode_string)
            return f"xn--{punycode_string.decode('ascii')}"
        except:
            return unicode_string
            
    def process_pagemaker(self):
        selected_indices = self.pagemaker_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select CSV files to process")
            return
        
        # Initialize file logging
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug.hnsell.log')
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== HNSell Debug Log - {datetime.now()} ===\n\n")
            
        try:
            all_domains = []
            bob_fw_without_contact = []  # Track bob/fw files without email/price
            debug_log = []  # Collect debug messages for display
            
            for idx in selected_indices:
                filepath = self.pagemaker_files[idx]
                source_type = self.detect_csv_source(filepath)
                
                # Read CSV with appropriate error handling for malformed files
                try:
                    df = pd.read_csv(filepath)
                except pd.errors.ParserError:
                    # Try with different quoting settings for malformed CSVs (e.g., Shakestation)
                    try:
                        df = pd.read_csv(filepath, quoting=1, escapechar='\\')
                    except:
                        df = pd.read_csv(filepath, on_bad_lines='skip')
                
                if source_type == 'ss-tld':
                    # Shakestation TLD: only include for_sale=True
                    df = df[df['for_sale'] == True]
                    for _, row in df.iterrows():
                        domain = row['domain']
                        # Convert domain to string and handle NaN
                        if isinstance(domain, float) and math.isnan(domain):
                            continue  # Skip rows with NaN domain
                        domain = str(domain)
                        unicode_val = row.get('unicode', '')
                        tags = row.get('tags', 'All Names')
                        email = row.get('email', '')
                        price = row.get('price', '')
                        all_domains.append({
                            'name': domain,
                            'unicode': unicode_val,
                            'tags': tags,
                            'source': 'ss',
                            'email': email,
                            'price': price
                        })
                elif source_type == 'ss-tr':
                    # Shakestation transactions: no for_sale column
                    for _, row in df.iterrows():
                        domain = row['domain']
                        # Convert domain to string and handle NaN
                        if isinstance(domain, float) and math.isnan(domain):
                            continue  # Skip rows with NaN domain
                        domain = str(domain)
                        unicode_val = row.get('unicode', '')
                        tags = row.get('tags', 'All Names')
                        email = row.get('email', '')
                        price = row.get('price', '')
                        
                        # Clean up nan values
                        if isinstance(email, float) and math.isnan(email):
                            email = ''
                        if isinstance(price, float) and math.isnan(price):
                            price = ''
                        # Clean up string values and strip whitespace
                        email = str(email).strip() if email else ''
                        price = str(price).strip() if price else ''
                        if email.lower() == 'nan' or email == '0':
                            email = ''
                        if price.lower() == 'nan' or price == '0' or price == '0.0':
                            price = ''
                        
                        all_domains.append({
                            'name': domain,
                            'unicode': unicode_val,
                            'tags': tags,
                            'source': 'ss',
                            'email': email,
                            'price': price
                        })
                elif source_type == 'nb-tld' or source_type == 'nb-tr':
                    # Namebase: use 'name' column
                    for _, row in df.iterrows():
                        domain = row.get('name', row.get('extra.domain', ''))
                        # Convert domain to string and handle NaN
                        if isinstance(domain, float) and math.isnan(domain):
                            continue  # Skip rows with NaN domain
                        domain = str(domain)
                        unicode_val = row.get('unicode', '')
                        tags = row.get('tags', 'All Names')
                        email = row.get('email', '')
                        price = row.get('price', '')
                        
                        # Clean up nan values
                        if isinstance(email, float) and math.isnan(email):
                            email = ''
                        if isinstance(price, float) and math.isnan(price):
                            price = ''
                        # Clean up string values and strip whitespace
                        email = str(email).strip() if email else ''
                        price = str(price).strip() if price else ''
                        if email.lower() == 'nan' or email == '0':
                            email = ''
                        if price.lower() == 'nan' or price == '0' or price == '0.0':
                            price = ''
                        
                        all_domains.append({
                            'name': domain,
                            'unicode': unicode_val,
                            'tags': tags,
                            'source': 'nb',
                            'email': email,
                            'price': price
                        })
                elif source_type == 'bob-tld':
                    # Bob Wallet: use 'domains' column, only include if email or price specified (unless list_all)
                    has_email_or_price = False
                    auto_email_base = self.auto_email_entry.get().strip()
                    for _, row in df.iterrows():
                        domain = row.get('domains', '')
                        # Convert domain to string and handle NaN
                        if isinstance(domain, float) and math.isnan(domain):
                            continue  # Skip rows with NaN domain
                        domain = str(domain)
                        unicode_val = row.get('unicode', '')
                        tags = row.get('tags', 'All Names')
                        email = row.get('email', '')
                        price = row.get('price', '')
                        
                        # Clean up nan values
                        if isinstance(email, float) and math.isnan(email):
                            email = ''
                        if isinstance(price, float) and math.isnan(price):
                            price = ''
                        # Clean up string values and strip whitespace
                        email = str(email).strip() if email else ''
                        price = str(price).strip() if price else ''
                        # Check for truly empty or invalid values
                        if not email or email.lower() in ['nan', 'none', '0']:
                            email = ''
                        if not price or price.lower() in ['nan', 'none', '0', '0.0']:
                            price = ''
                        
                        # DEBUG: Print for troubleshooting
                        if email or price:
                            print(f"BOB domain: {domain}, email='{email}', price='{price}', list_all={self.list_all_var.get()}")
                        
                        # Auto-append email if auto_email_base is entered and:
                        # - email is empty, AND
                        # - (price exists OR list_all is checked)
                        if auto_email_base and not email and (price or self.list_all_var.get()):
                            if '@' in auto_email_base:
                                # Format: user@gmail.com OR user+@gmail.com
                                parts = auto_email_base.split('@')
                                if len(parts) == 2:
                                    user_part = parts[0]
                                    # If user_part ends with +, replace it; otherwise append +domain
                                    if user_part.endswith('+'):
                                        email = f"{user_part}{domain}@{parts[1]}"
                                    else:
                                        email = f"{user_part}+{domain}@{parts[1]}"
                        
                        # Only include if list_all OR (email or price is provided)
                        if self.list_all_var.get() or email or price:
                            has_email_or_price = True
                            all_domains.append({
                                'name': domain,
                                'unicode': unicode_val,
                                'tags': tags,
                                'source': 'bob',
                                'email': email,
                                'price': price
                            })
                    if not has_email_or_price and not self.list_all_var.get():
                        bob_fw_without_contact.append(os.path.basename(filepath))
                elif source_type == 'fw':
                    # Firewallet: use 'name' column with 'price' and 'email' columns
                    # Note: User must manually add 'price' and 'email' columns to FW CSV
                    # (unless only using list_all to show domains for contact offers)
                    
                    # Check if price column exists
                    has_price_col = 'price' in df.columns
                    has_email_col = 'email' in df.columns
                    
                    if not has_price_col and not self.list_all_var.get():
                        messagebox.showwarning("Missing Price Column",
                            f"Firewallet CSV '{os.path.basename(filepath)}' has no 'price' column.\n\n" +
                            "Please add a 'price' column with values for domains you want to list,\n" +
                            "OR check 'List all domains' to show all domains with contact email only.")
                        continue
                    
                    has_email_or_price = False
                    auto_email_base = self.auto_email_entry.get().strip()
                    for _, row in df.iterrows():
                        domain = row.get('name', row.get(df.columns[0], ''))
                        # Convert domain to string and handle NaN
                        if isinstance(domain, float) and math.isnan(domain):
                            continue  # Skip rows with NaN domain
                        domain = str(domain)
                        unicode_val = row.get('unicode', '')
                        tags = row.get('tags', 'All Names')
                        
                        # Get email and price from columns if they exist
                        email = row.get('email', '') if has_email_col else ''
                        price = row.get('price', '') if has_price_col else ''
                        
                        # Clean up nan values for email and price
                        if isinstance(email, float) and math.isnan(email):
                            email = ''
                        if isinstance(price, float):
                            if math.isnan(price):
                                price = ''
                            elif price == 0.0:
                                price = ''  # Zero price = no price
                            else:
                                price = str(price)  # Convert to string for display
                        else:
                            price = str(price).strip() if price else ''
                            if price.lower() in ['nan', 'none', '0', '0.0']:
                                price = ''
                        
                        # Clean up email string
                        email = str(email).strip() if email else ''
                        if email.lower() in ['nan', 'none', '0']:
                            email = ''
                        
                        # DEBUG: Print for troubleshooting
                        debug_msg = f"FW domain: {domain}, email='{email}', price='{price}', list_all={self.list_all_var.get()}"
                        print(debug_msg)
                        debug_log.append(debug_msg)
                        with open(log_file, 'a', encoding='utf-8') as f:
                            f.write(debug_msg + '\n')
                        
                        # Auto-append email if auto_email_base is entered and:
                        # - email is empty, AND
                        # - (price exists OR list_all is checked)
                        if auto_email_base and not email and (price or self.list_all_var.get()):
                            if '@' in auto_email_base:
                                # Format: user@gmail.com OR user+@gmail.com
                                parts = auto_email_base.split('@')
                                if len(parts) == 2:
                                    user_part = parts[0]
                                    # If user_part ends with +, replace it; otherwise append +domain
                                    if user_part.endswith('+'):
                                        email = f"{user_part}{domain}@{parts[1]}"
                                    else:
                                        email = f"{user_part}+{domain}@{parts[1]}"
                        
                        # Only include if list_all OR (email or price is provided)
                        if self.list_all_var.get() or email or price:
                            has_email_or_price = True
                            add_msg = f"  -> Adding FW domain: {domain}, email={bool(email)}, price={bool(price)}, source='fw'"
                            print(add_msg)
                            debug_log.append(add_msg)
                            with open(log_file, 'a', encoding='utf-8') as f:
                                f.write(add_msg + '\n')
                            domain_dict = {
                                'name': domain,
                                'unicode': unicode_val,
                                'tags': tags,
                                'source': 'fw',
                                'email': email,
                                'price': price
                            }
                            all_domains.append(domain_dict)
                            # Verify dict has source
                            verify_msg = f"    Dict keys: {list(domain_dict.keys())}, source={domain_dict.get('source', 'MISSING')}"
                            with open(log_file, 'a', encoding='utf-8') as f:
                                f.write(verify_msg + '\n')
                        else:
                            skip_msg = f"  -> SKIPPING FW domain: {domain} (no email, no price, list_all=False)"
                            print(skip_msg)
                            debug_log.append(skip_msg)
                    if not has_email_or_price and not self.list_all_var.get():
                        bob_fw_without_contact.append(os.path.basename(filepath))
                    else:
                        summary_msg = f"  FW file '{os.path.basename(filepath)}' added {sum(1 for d in all_domains if d['source'] == 'fw')} domains"
                        print(summary_msg)
                        debug_log.append(summary_msg)
                        
            if not all_domains:
                error_msg = "No domains found in selected files"
                if bob_fw_without_contact:
                    error_msg += f"\n\nBob/Firewallet files require 'email' or 'price' columns with values:\n" + "\n".join(f"  • {f}" for f in bob_fw_without_contact)
                if debug_log:
                    error_msg += f"\n\nDebug log (first 10 entries):\n" + "\n".join(debug_log[:10])
                messagebox.showwarning("No Domains", error_msg)
                return
                
            html_content = self.generate_portfolio_html(all_domains)
            
            output_filename = self.output_filename_entry.get()
            if not output_filename.endswith('.html'):
                output_filename += '.html'
            
            # Save in the script directory, not working directory (fixes junction issue)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_path = os.path.join(script_dir, output_filename)
            
            # Warn if file exists
            if os.path.exists(output_path):
                result = messagebox.askyesno("File Exists", 
                    f"The file '{output_filename}' already exists.\nDo you want to overwrite it?")
                if not result:
                    return
                
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Show debug summary
            success_msg = f"Portfolio page created: {output_path}\n\n"
            success_msg += f"Total domains: {len(all_domains)}\n"
            fw_count = sum(1 for d in all_domains if d.get('source') == 'fw')
            if fw_count > 0:
                success_msg += f"FW domains: {fw_count}\n\n"
                if debug_log:
                    success_msg += "Debug log (first 15 entries):\n" + "\n".join(debug_log[:15])
            messagebox.showinfo("Success", success_msg)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error creating portfolio:\n{str(e)}")
            
    def generate_portfolio_html(self, domains):
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug.hnsell.log')
        
        # DEBUG: Log all_domains before DataFrame creation
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n=== all_domains list has {len(domains)} items\n")
            if len(domains) > 0:
                f.write(f"First domain dict: {domains[0]}\n")
        
        df = pd.DataFrame(domains)
        
        # DEBUG: Check what columns the DataFrame has
        df_msg = f"\n=== DataFrame columns: {df.columns.tolist()}\n"
        print(df_msg)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(df_msg)
            
        if len(df) > 0:
            sample_msg = f"=== Sample row (first domain):\n    name={df.iloc[0]['name']}, source={df.iloc[0].get('source', 'MISSING')}, email={df.iloc[0].get('email', 'MISSING')}, price={df.iloc[0].get('price', 'MISSING')}\n"
            print(sample_msg)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(sample_msg)
        
        df['tags'] = df['tags'].apply(lambda x: x.strip() + ', All Names' if isinstance(x, str) and len(x.strip()) > 0 else 'All Names')
        
        if self.sort_state == 1:
            df = df.sort_values('name')
        elif self.sort_state == 2:
            df = df.sort_values('name', ascending=False)
            
        navigation_links_html = ""
        tag_groups_content = ""
        tags_dict = {}
        
        for _, row in df.iterrows():
            tags_list = str(row['tags']).split(',')
            for tag in tags_list:
                tag = tag.strip()
                if tag not in tags_dict:
                    tags_dict[tag] = []
                tags_dict[tag].append(self.format_domain_link(row))
                
        tags_sorted = ['All Names'] + sorted(set(tags_dict.keys()) - {'All Names'})
        
        for tag in tags_sorted:
            section_id = tag.lower().replace(' ', '-')
            names_under_tag = ''.join(f'<div class="col" data-tags="{tag}">{name}</div>' for name in tags_dict[tag])
            tag_groups_content += f'<div id="{section_id}" class="tag-section"><h2>{tag}</h2><div class="grid">{names_under_tag}</div></div>'
            navigation_links_html += f'<div class="navigation" onclick="showTagSection(\'{tag}\')">{tag}</div>'
            
        footer_html = ""
        if self.footer_file:
            with open(self.footer_file, 'r', encoding='utf-8') as f:
                footer_content = f.read()
                footer_html = f'<footer>{footer_content}</footer>'
                
        credits_html = ""
        if self.credits_file:
            with open(self.credits_file, 'r', encoding='utf-8') as f:
                credits_content = f.read()
                credits_html = f'<div class="credits">{credits_content}</div>'
                
        css_style = self.get_portfolio_css()
        javascript_code = self.get_portfolio_js()
        
        # Determine theme button based on selected theme
        theme = self.theme_var.get() if hasattr(self, 'theme_var') else "dark+light"
        if theme == "3-way switch":
            theme_button = '<button id="themeBtn" onclick="cycleTheme()">☀️ Light</button>'
        else:
            theme_button = '<button id="mode-toggle">🌙 / ☀️</button>'
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portfolio</title>
{css_style}
</head>
<body>
<div class="buttons-container">
<div class="mode-toggle">
    {theme_button}
</div>
<div class="zoom-buttons">
    <button id="zoom-out">-</button>
    <button id="zoom-in">+</button>
</div>
<div class="sort-button">
    <button id="sort-tlds">Sort TLDs</button>
</div>
</div>
<div class="marketplace-links">
    <a href="https://shakeshift.com/names" target="_blank" rel="noreferrer">ShakeShift</a>
    <a href="https://bobwallet.io" target="_blank" rel="noreferrer">bobWallet</a>
    <a href="https://www.namebase.io" target="_blank" rel="noreferrer">Namebase</a>
    <a href="https://shakestation.io" target="_blank" rel="noreferrer">ShakeStation</a>
    <a href="https://impervious.com/fingertip" target="_blank" rel="noreferrer">Fingertip</a>
    <a href="https://git.woodburn.au/nathanwoodburn/firewalletbrowser" target="_blank" rel="noreferrer">Firewallet</a>
</div>
<div class="navigation-container">
{navigation_links_html}
</div>
<div class="content">
    <div class="search-container">
        <input type="text" id="search-input" placeholder="Search names...">
        <input type="number" id="min-price" placeholder="Min price" step="0.01">
        <input type="number" id="max-price" placeholder="Max price" step="0.01">
        <button id="clear-filters">Clear</button>
    </div>
    {tag_groups_content}
</div>
{footer_html}
{credits_html}
{javascript_code}
</body>
</html>"""
        
        return html_content
        
    def format_domain_link(self, row):
        name = row['name']
        # Convert name to string and handle NaN
        if isinstance(name, float):
            if math.isnan(name):
                return ''  # Skip NaN domains
            name = str(name)
        name = str(name)  # Ensure it's always a string
        unicode_val = str(row.get('unicode', ''))
        source = row.get('source', 'nb')
        email = row.get('email', '')
        price = row.get('price', '')
        
        # DEBUG: Print source for ALL domains to verify routing
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug.hnsell.log')
        format_msg = f"  format_domain_link: domain '{name}' with source='{source}' (type={type(source)})\n"
        print(format_msg.strip())
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(format_msg)
        
        # Clean up nan display
        if isinstance(email, float) and math.isnan(email):
            email = ''
        if isinstance(price, float) and math.isnan(price):
            price = ''
        if str(email).lower() == 'nan':
            email = ''
        if str(price).lower() == 'nan':
            price = ''
        
        # Determine base URL or contact info based on source
        if source == 'ss':
            base_url = f"https://shakestation.io/domain/{name}"
        elif source == 'nb':
            base_url = f"https://www.namebase.io/domains/{name}"
        elif source == 'bob' or source == 'fw':
            # Bob/Firewallet: No marketplace link, show contact info
            # DEBUG: Confirm we're in bob/fw block
            print(f"    -> In bob/fw block for '{name}', source='{source}'")
            # Format display name first
            if name.startswith('xn--'):
                if unicode_val and unicode_val.lower() != 'nan' and unicode_val.strip():
                    try:
                        unicode_bytes = codecs.decode(unicode_val, 'unicode_escape')
                        unicode_char = unicode_bytes.encode('latin-1').decode('utf-8')
                    except:
                        unicode_char = unicode_val
                    display_name = f"{unicode_char} ({name})"
                else:
                    display_name = name
            else:
                display_name = name
            
            # Build contact line below name
            contact_parts = []
            if price:
                contact_parts.append(f"💰 {price}")
            if email:
                # Only show copy icon with tooltip
                copy_btn = f'<button class="copy-email-btn" onclick="copyEmail(event, \'{email}\')" title="Copy {email}">eml</button>'
                contact_parts.append(copy_btn)
            
            if contact_parts:
                contact_str = ' '.join(contact_parts)
                return f'<span class="domain-with-contact" data-price="{price if price else ""}" data-email="{email if email else ""}">' + \
                       f'<div class="domain-name">{display_name}</div><div class="domain-contact">{contact_str}</div></span>'
            else:
                return f'<span class="domain-with-contact" data-price="" data-email=""><div class="domain-name">{display_name}</div></span>'
        else:
            # Default to Namebase
            base_url = f"https://www.namebase.io/domains/{name}"
            
        # For sources with marketplace links (ss, nb)
        # Format display name
        if name.startswith('xn--'):
            if unicode_val and unicode_val.lower() != 'nan' and unicode_val.strip():
                try:
                    unicode_bytes = codecs.decode(unicode_val, 'unicode_escape')
                    unicode_char = unicode_bytes.encode('latin-1').decode('utf-8')
                except:
                    unicode_char = unicode_val
                display_name = f"{unicode_char} ({name})"
            else:
                display_name = name
        else:
            display_name = name
        
        # Build contact info below name
        contact_parts = []
        if price:
            contact_parts.append(f"💰 {price}")
        if email:
            copy_btn = f'<button class="copy-email-btn" onclick="copyEmail(event, \'{email}\')" title="Copy {email}">eml</button>'
            contact_parts.append(copy_btn)
        
        if contact_parts:
            contact_str = ' '.join(contact_parts)
            return f'<span class="domain-with-contact" data-price="{price if price else ""}" data-email="{email if email else ""}">' + \
                   f'<div class="domain-name"><a target="_blank" rel="noreferrer" href="{base_url}">{display_name}</a></div>' + \
                   f'<div class="domain-contact">{contact_str}</div></span>'
        else:
            return f'<a target="_blank" rel="noreferrer" href="{base_url}">{display_name}</a>'
            
    def get_portfolio_css(self):
        """Get CSS based on selected theme"""
        theme = self.theme_var.get() if hasattr(self, 'theme_var') else "dark+light"
        
        # If custom CSS file is selected, load it
        if theme == "custom CSS" and self.custom_css_file:
            try:
                with open(self.custom_css_file, 'r', encoding='utf-8') as f:
                    custom_css = f.read()
                return f"<style>\n{custom_css}\n</style>"
            except:
                pass  # Fall back to default
        
        # 3-way theme with custom colors
        if theme == "3-way switch":
            light_color = self.light_color_entry.get() if hasattr(self, 'light_color_entry') else "#ccffff"
            dark_color = self.dark_color_entry.get() if hasattr(self, 'dark_color_entry') else "#003366"
            
            # DEBUG: Print colors being used
            print(f"Theme colors: light={light_color}, dark={dark_color}")
            
            return f"""<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

/* Light theme (default) */
body {{
    background-color: {light_color};
    color: #3404f4;
    font-family: Arial, Helvetica, sans-serif;
    line-height: 1.6;
    padding: 20px;
    transition: background-color 0.3s ease, color 0.3s ease;
}}

/* Dark theme */
body.dark-theme {{
    background-color: {dark_color};
    color: #99ddff;
}}

/* Black theme */
body.black-theme {{
    background-color: #000000;
    color: #ffffff;
}}

a:link {{ color: #0000ee; text-decoration: none; }}
a:visited {{ color: #551a8b; }}
a:hover {{ color: #3404f4; text-decoration: underline; }}

body.dark-theme a:link {{ color: #66bbff; }}
body.dark-theme a:visited {{ color: #9988ff; }}
body.dark-theme a:hover {{ color: #99ddff; }}

body.black-theme a:link {{ color: #66bbff; }}
body.black-theme a:visited {{ color: #9999ff; }}
body.black-theme a:hover {{ color: #ffffff; }}

.buttons-container {{
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 10px;
    align-items: flex-end;
}}

.mode-toggle button {{
    padding: 10px 20px;
    background-color: rgba(52, 4, 244, 0.8);
    color: white;
    border: none;
    border-radius: 20px;
    cursor: pointer;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 0.9em;
    font-weight: bold;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
    transition: all 0.3s ease;
}}

.mode-toggle button:hover {{
    transform: scale(1.05);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.4);
}}

body.dark-theme .mode-toggle button {{
    background-color: rgba(153, 221, 255, 0.8);
    color: #003366;
}}

body.black-theme .mode-toggle button {{
    background-color: rgba(255, 255, 255, 0.8);
    color: #000000;
}}

.zoom-buttons, .sort-button {{
    /* Positioned via buttons-container */
}}

.domain-with-contact {{
    display: flex;
    flex-direction: column;
    gap: 0.3em;
}}

.domain-name {{
    font-weight: bold;
}}

.domain-contact {{
    font-size: 0.9em;
    display: flex;
    gap: 0.5em;
    justify-content: center;
    align-items: center;
}}

button {{
    padding: 8px 16px;
    margin: 2px;
    background-color: rgba(52, 4, 244, 0.2);
    color: inherit;
    border: 2px solid currentColor;
    border-radius: 8px;
    cursor: pointer;
    font-family: inherit;
}}

body.dark-theme button {{
    background-color: rgba(153, 221, 255, 0.2);
}}

body.black-theme button {{
    background-color: rgba(255, 255, 255, 0.2);
}}

input {{
    padding: .7em;
    font-size: 1em;
    border: 2px solid currentColor;
    border-radius: 8px;
    background-color: rgba(255, 255, 255, 0.1);
    color: inherit;
}}

.grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: .5em;
    padding: .5em;
}}

.col {{
    padding: .7em;
    background-color: rgba(52, 4, 244, 0.05);
    border: 1px solid currentColor;
    border-radius: 8px;
    text-align: center;
    transition: all 0.3s ease;
}}

.col:hover {{
    background-color: rgba(52, 4, 244, 0.15);
    transform: translateY(-3px);
}}

body.dark-theme .col {{
    background-color: rgba(153, 221, 255, 0.05);
}}

body.dark-theme .col:hover {{
    background-color: rgba(153, 221, 255, 0.15);
}}

body.black-theme .col {{
    background-color: rgba(255, 255, 255, 0.05);
}}

body.black-theme .col:hover {{
    background-color: rgba(255, 255, 255, 0.15);
}}

.navigation-container {{
    display: flex;
    flex-wrap: wrap;
    gap: .5em;
    padding: .5em;
    background-color: rgba(52, 4, 244, 0.1);
    border-radius: 10px;
    margin: 20px 0;
}}

body.dark-theme .navigation-container {{
    background-color: rgba(153, 221, 255, 0.1);
}}

body.black-theme .navigation-container {{
    background-color: rgba(255, 255, 255, 0.1);
}}

.navigation {{
    padding: .5em;
    min-width: 150px;
    cursor: pointer;
    background-color: rgba(52, 4, 244, 0.15);
    color: inherit;
    border: 2px solid currentColor;
    border-radius: 8px;
    text-align: center;
    transition: all 0.3s ease;
}}

.navigation:hover {{
    background-color: rgba(52, 4, 244, 0.3);
    transform: translateY(-2px);
}}

body.dark-theme .navigation {{
    background-color: rgba(153, 221, 255, 0.15);
}}

body.dark-theme .navigation:hover {{
    background-color: rgba(153, 221, 255, 0.3);
}}

body.black-theme .navigation {{
    background-color: rgba(255, 255, 255, 0.15);
}}

body.black-theme .navigation:hover {{
    background-color: rgba(255, 255, 255, 0.3);
}}

.marketplace-links {{
    display: flex;
    justify-content: center;
    gap: 1.5em;
    padding: 1em;
    background-color: rgba(52, 4, 244, 0.08);
    border-radius: 10px;
    margin: 10px 0 20px 0;
    flex-wrap: wrap;
}}

body.dark-theme .marketplace-links {{
    background-color: rgba(153, 221, 255, 0.08);
}}

body.black-theme .marketplace-links {{
    background-color: rgba(255, 255, 255, 0.08);
}}

.marketplace-links a {{
    padding: 0.5em 1em;
    background-color: rgba(52, 4, 244, 0.2);
    color: inherit;
    border: 2px solid currentColor;
    border-radius: 8px;
    text-decoration: none;
    font-weight: bold;
    transition: all 0.3s ease;
}}

.marketplace-links a:hover {{
    background-color: rgba(52, 4, 244, 0.4);
    transform: scale(1.05);
}}

body.dark-theme .marketplace-links a {{
    background-color: rgba(153, 221, 255, 0.2);
}}

body.dark-theme .marketplace-links a:hover {{
    background-color: rgba(153, 221, 255, 0.4);
}}

body.black-theme .marketplace-links a {{
    background-color: rgba(255, 255, 255, 0.2);
}}

body.black-theme .marketplace-links a:hover {{
    background-color: rgba(255, 255, 255, 0.4);
}}

.search-container {{
    display: flex;
    gap: 0.5em;
    padding: 1em;
    justify-content: center;
    flex-wrap: wrap;
}}

.search-container input {{
    padding: 0.5em;
    border: 2px solid currentColor;
    border-radius: 8px;
    background-color: rgba(255, 255, 255, 0.1);
    color: inherit;
    font-family: inherit;
}}

.search-container button {{
    padding: 0.5em 1em;
    background-color: rgba(52, 4, 244, 0.2);
    color: inherit;
    border: 2px solid currentColor;
    border-radius: 8px;
    cursor: pointer;
    font-weight: bold;
    transition: all 0.3s ease;
}}

.search-container button:hover {{
    background-color: rgba(52, 4, 244, 0.4);
}}

body.dark-theme .search-container button {{
    background-color: rgba(153, 221, 255, 0.2);
}}

body.dark-theme .search-container button:hover {{
    background-color: rgba(153, 221, 255, 0.4);
}}

body.black-theme .search-container button {{
    background-color: rgba(255, 255, 255, 0.2);
}}

body.black-theme .search-container button:hover {{
    background-color: rgba(255, 255, 255, 0.4);
}}

.copy-email-btn {{
    padding: 0.2em 0.5em;
    margin-left: 0.3em;
    background-color: rgba(52, 4, 244, 0.15);
    border: 1px solid currentColor;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9em;
    transition: all 0.2s ease;
}}

.copy-email-btn:hover {{
    background-color: rgba(52, 4, 244, 0.3);
    transform: scale(1.1);
}}

body.dark-theme .copy-email-btn {{
    background-color: rgba(153, 221, 255, 0.15);
}}

body.dark-theme .copy-email-btn:hover {{
    background-color: rgba(153, 221, 255, 0.3);
}}

body.black-theme .copy-email-btn {{
    background-color: rgba(255, 255, 255, 0.15);
}}

body.black-theme .copy-email-btn:hover {{
    background-color: rgba(255, 255, 255, 0.3);
}}

.email-link {{
    color: inherit;
    text-decoration: none;
    border-bottom: 1px dashed currentColor;
}}

.email-link:hover {{
    text-decoration: underline;
}}

/* Footer and credits theming */
footer, .credits {{
    margin-top: 2em;
    padding: 1em;
    border-top: 2px solid currentColor;
}}

/* Light theme (default) */
body footer, body .credits {{
    color: {dark_color};
    background-color: {light_color};
}}

body.dark-theme footer, body.dark-theme .credits {{
    color: {light_color};
    background-color: {dark_color};
}}

body.black-theme footer, body.black-theme .credits {{
    color: #ffffff;
    background-color: #000000;
}}

footer *, .credits * {{
    color: inherit !important;
}}
</style>"""
        
        # Default theme (original dark/light mode)
        return """<style>
.zoom-buttons {
    position: absolute;
    top: 50px;
    right: 10px;
    z-index: 1000;
}
.mode-toggle {
    position: absolute;
    top: 10px;
    right: 10px;
    z-index: 1000;
}
.sort-button {
    position: absolute;
    top: 90px;
    right: 10px;
    z-index: 1000;
}
button {
    font-size: .9em;
    font-weight: 555;
    background-image: radial-gradient( circle farthest-corner at 22.4% 21.7%, rgba(4,189,228,1) 0%, rgba(2,83,185,1) 100.2% );
}
body {
    background-color: #ffffff;
    color: #000000;
}
body.dark-mode, a:link.dark-mode, a:visited.dark-mode {
    background-color: #000000;
    color: #ffffff;
}
body {
    padding: .7em;
    font-weight: 600;
    text-align: center;
    text-transform: full-size-kana;
}
a:link, a:visited {
    color: black;
    text-decoration: overline dashed;
    text-decoration-thickness: 1px;
}
a:hover {
    text-decoration: wavy underline;
    text-decoration-thickness: 1px;
}
input {
    padding: .7em;
    font-size: 1em;
    font-weight: bold;
    background-image: radial-gradient( circle farthest-corner at 22.4% 21.7%, rgba(4,189,228,1) 0%, rgba(2,83,185,1) 100.2% );
}
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: .5em;
    padding: .5em;
}
.col {
    padding: .7em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.col:hover {
    text-transform: full-width;
    text-transform: uppercase;
    text-overflow: ellipsis;
    font-size: 1.1em;
    overflow: clip;
    margin: -1em;
    margin-top: -.1em;
}
.navigation-container {
    display: flex;
    flex-wrap: wrap;
    gap: .5em;
    padding: .5em;
    background-image: linear-gradient(to right, #33001b, #C70039);
    border-color: #ff0084;
    border: #ff0084;
    border-style: dotted; 
}
.navigation {
    padding: .5em;
    min-width: 150px;
    cursor: pointer;
    color: blue;
    text-transform: full-width;
    text-shadow: 1px 1px 2px red, 0 0 1em blue, 0 0 0.2em blue;
    text-shadow: .5px .5px 1px gray, 0 0 .1em silver, 0 0 0.1em green;
    background-color: rgba(111, 111, 111, 0.5);
}
.navigation:hover {
    text-decoration: dashed underline;
    text-transform: full-width;
    text-shadow: 1px 1px 2px blue, 0 0 1em red, 0 0 0.2em red;
    text-shadow: .5px .5px 1px red, 0 0 .5em silver, 0 0 0.1em orange;
    border-color: rgba( 255, 151, 0 , .5);
    border-style: double;
    margin: -3px;
    background-color: rgba( 97, 0, 255 , 0.6 );
}
.marketplace-links {
    display: flex;
    justify-content: center;
    gap: 1.5em;
    padding: 1em;
    background-image: linear-gradient(to right, #1a0033, #6b0039);
    border-radius: 10px;
    margin: 10px 0 20px 0;
    flex-wrap: wrap;
}
.marketplace-links a {
    padding: 0.5em 1em;
    background-color: rgba(111, 111, 111, 0.5);
    color: inherit;
    border: 2px solid currentColor;
    border-radius: 8px;
    text-decoration: none;
    font-weight: bold;
    text-shadow: .5px .5px 1px gray, 0 0 .1em silver, 0 0 0.1em green;
    transition: all 0.3s ease;
}
.marketplace-links a:hover {
    background-color: rgba(97, 0, 255, 0.6);
    transform: scale(1.05);
    text-shadow: .5px .5px 1px red, 0 0 .5em silver, 0 0 0.1em orange;
    border-color: rgba(255, 151, 0, .5);
    border-style: double;
}
.search-container {
    display: flex;
    gap: 0.5em;
    padding: 1em;
    justify-content: center;
    flex-wrap: wrap;
}
.search-container input {
    padding: 0.7em;
    font-size: 1em;
    font-weight: bold;
    border: 2px solid currentColor;
    border-radius: 8px;
    background-image: radial-gradient(circle farthest-corner at 22.4% 21.7%, rgba(4,189,228,1) 0%, rgba(2,83,185,1) 100.2%);
}
.search-container button {
    padding: 0.7em 1em;
    font-weight: bold;
    background-image: radial-gradient(circle farthest-corner at 22.4% 21.7%, rgba(4,189,228,1) 0%, rgba(2,83,185,1) 100.2%);
    border: 2px solid currentColor;
    border-radius: 8px;
    cursor: pointer;
}
.copy-email-btn {
    padding: 0.2em 0.5em;
    margin-left: 0.3em;
    background-color: rgba(111, 111, 111, 0.5);
    border: 1px solid currentColor;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9em;
    transition: all 0.2s ease;
}
.copy-email-btn:hover {
    background-color: rgba(97, 0, 255, 0.6);
    transform: scale(1.1);
}
.email-link {
    color: inherit;
    text-decoration: none;
    border-bottom: 1px dashed currentColor;
}
.email-link:hover {
    text-decoration: underline;
}
.domain-with-contact {
    display: flex;
    flex-direction: column;
    gap: 0.3em;
}
.domain-name {
    font-weight: bold;
}
.domain-contact {
    font-size: 0.9em;
    display: flex;
    gap: 0.5em;
    justify-content: center;
    align-items: center;
}
/* Footer and credits theming */
footer, .credits {
    margin-top: 2em;
    padding: 1em;
    border-top: 2px solid currentColor;
}

body footer, body .credits {
    color: #000000;
    background-color: rgba(255, 255, 255, 0.5);
}

body.dark-mode footer, body.dark-mode .credits {
    color: #ffffff;
    background-color: rgba(0, 0, 0, 0.3);
}

footer *, .credits * {
    color: inherit !important;
}
</style>"""
        
    def get_portfolio_js(self):
        """Get JavaScript based on selected theme"""
        theme = self.theme_var.get() if hasattr(self, 'theme_var') else "dark+light"
        
        # 3-way theme with 3-way switcher
        if theme == "3-way switch":
            return """<script>
// 3-way theme switcher (Light -> Dark -> Black)
let currentTheme = 0; // 0=light, 1=dark, 2=black
let themeBtn;

// Initialize after DOM loads
window.addEventListener('DOMContentLoaded', () => {
    themeBtn = document.getElementById('themeBtn');
    
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || '0';
    currentTheme = parseInt(savedTheme);
    applyTheme();
});

function cycleTheme() {
    currentTheme = (currentTheme + 1) % 3;
    localStorage.setItem('theme', currentTheme.toString());
    applyTheme();
}

function applyTheme() {
    if (!themeBtn) return; // Safety check
    document.body.classList.remove('dark-theme', 'black-theme');
    switch(currentTheme) {
        case 0: // Light
            themeBtn.textContent = '☀️ Light';
            break;
        case 1: // Dark
            document.body.classList.add('dark-theme');
            themeBtn.textContent = '🌙 Dark';
            break;
        case 2: // Black
            document.body.classList.add('black-theme');
            themeBtn.textContent = '⚫ Black';
            break;
    }
}

document.getElementById("zoom-in").addEventListener("click", function() {
    document.body.style.fontSize = parseInt(window.getComputedStyle(document.body).fontSize) + 3 + "px";
});
document.getElementById("zoom-out").addEventListener("click", function() {
    document.body.style.fontSize = parseInt(window.getComputedStyle(document.body).fontSize) - 3 + "px";
});

let sortState = 0;
const sortButton = document.getElementById("sort-tlds");
sortButton.addEventListener("click", function() {
    sortState = (sortState + 1) % 5; // 0=random, 1=a-z, 2=z-a, 3=price-low, 4=price-high
    var currentSection = document.querySelector('.tag-section[style*="display: block"]');
    if (currentSection) {
        var grid = currentSection.querySelector('.grid');
        var cols = Array.from(grid.querySelectorAll('.col'));
        
        switch(sortState) {
            case 0: // Random
                for (let i = cols.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [cols[i], cols[j]] = [cols[j], cols[i]];
                }
                this.textContent = 'Sort: Random';
                break;
            case 1: // A-Z
                cols.sort((a, b) => a.textContent.toLowerCase().localeCompare(b.textContent.toLowerCase()));
                this.textContent = 'Sort: A-Z ▲';
                break;
            case 2: // Z-A
                cols.sort((a, b) => b.textContent.toLowerCase().localeCompare(a.textContent.toLowerCase()));
                this.textContent = 'Sort: Z-A ▼';
                break;
            case 3: // Price Low-High
                cols.sort((a, b) => {
                    const priceA = parseFloat(a.querySelector('.domain-with-contact')?.dataset?.price || '999999');
                    const priceB = parseFloat(b.querySelector('.domain-with-contact')?.dataset?.price || '999999');
                    return priceA - priceB;
                });
                this.textContent = 'Sort: Price ▲';
                break;
            case 4: // Price High-Low
                cols.sort((a, b) => {
                    const priceA = parseFloat(a.querySelector('.domain-with-contact')?.dataset?.price || '0');
                    const priceB = parseFloat(b.querySelector('.domain-with-contact')?.dataset?.price || '0');
                    return priceB - priceA;
                });
                this.textContent = 'Sort: Price ▼';
                break;
        }
        
        grid.innerHTML = '';
        cols.forEach(col => grid.appendChild(col));
    }
});

function copyEmail(event, email) {
    event.preventDefault();
    event.stopPropagation();
    navigator.clipboard.writeText(email).then(() => {
        const btn = event.target;
        const originalText = btn.textContent;
        btn.textContent = '✓';
        setTimeout(() => { btn.textContent = originalText; }, 1000);
    });
}

function showTagSection(tag) {
    var sectionId = tag.toLowerCase().replace(' ', '-');
    var section = document.getElementById(sectionId);
    if (section) {
        var sections = document.getElementsByClassName('tag-section');
        for (var i = 0; i < sections.length; i++) {
            sections[i].style.display = "none";
        }
        section.style.display = "block";
    }
}

function searchNames() {
    var input = document.getElementById('search-input');
    var minPrice = document.getElementById('min-price');
    var maxPrice = document.getElementById('max-price');
    
    if (input) {
        var filter = input.value.toLowerCase();
        var minVal = minPrice && minPrice.value ? parseFloat(minPrice.value) : null;
        var maxVal = maxPrice && maxPrice.value ? parseFloat(maxPrice.value) : null;
        
        var names = document.getElementsByClassName('col');
        for (var i = 0; i < names.length; i++) {
            var name = names[i].innerText.toLowerCase();
            var nameMatches = name.includes(filter);
            
            // Check price filter
            var priceMatches = true;
            var domainSpan = names[i].querySelector('.domain-with-contact');
            if (domainSpan && (minVal !== null || maxVal !== null)) {
                var priceStr = domainSpan.dataset.price;
                if (priceStr) {
                    var price = parseFloat(priceStr);
                    if (minVal !== null && price < minVal) priceMatches = false;
                    if (maxVal !== null && price > maxVal) priceMatches = false;
                } else {
                    priceMatches = false; // No price, hide if price filter active
                }
            }
            
            if (nameMatches && priceMatches) {
                names[i].style.display = "block";
            } else {
                names[i].style.display = "none";
            }
        }
    }
}

var searchInput = document.getElementById('search-input');
if (searchInput) {
    searchInput.addEventListener('keyup', function() {
        searchNames();
    });
}

var minPriceInput = document.getElementById('min-price');
var maxPriceInput = document.getElementById('max-price');
if (minPriceInput) {
    minPriceInput.addEventListener('input', searchNames);
}
if (maxPriceInput) {
    maxPriceInput.addEventListener('input', searchNames);
}

var clearBtn = document.getElementById('clear-filters');
if (clearBtn) {
    clearBtn.addEventListener('click', function() {
        if (searchInput) searchInput.value = '';
        if (minPriceInput) minPriceInput.value = '';
        if (maxPriceInput) maxPriceInput.value = '';
        searchNames();
    });
}

showTagSection('All Names');

window.addEventListener('DOMContentLoaded', () => {
    const addTooltipToNames = () => {
        const cols = document.querySelectorAll('.col');
        cols.forEach(col => {
            col.setAttribute('title', col.textContent.trim());
        });
    };
    addTooltipToNames();
    
    // Randomize marketplace links order
    const marketplaceLinks = document.querySelector('.marketplace-links');
    if (marketplaceLinks) {
        const links = Array.from(marketplaceLinks.querySelectorAll('a'));
        for (let i = links.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [links[i], links[j]] = [links[j], links[i]];
        }
        marketplaceLinks.innerHTML = '';
        links.forEach(link => marketplaceLinks.appendChild(link));
    }
});
</script>"""
        
        # Default theme (2-way dark/light)
        return """<script>
let darkMode = true;
const prefersLightMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
if (prefersLightMode) {
    toggleDarkMode();
}
function toggleDarkMode() {
    darkMode = !darkMode;
    document.body.classList.toggle("dark-mode");
    const links = document.querySelectorAll('a');
    links.forEach((link) => {
        if (darkMode) {
            link.classList.add('dark-mode');
        } else {
            link.classList.remove('dark-mode');
        }
    });
}
const modeToggle = document.getElementById('mode-toggle');
modeToggle.addEventListener('click', toggleDarkMode);
document.getElementById("zoom-in").addEventListener("click", function() {
    document.body.style.fontSize = parseInt(window.getComputedStyle(document.body).fontSize) + 3 + "px";
});
document.getElementById("zoom-out").addEventListener("click", function() {
    document.body.style.fontSize = parseInt(window.getComputedStyle(document.body).fontSize) - 3 + "px";
});
let sortState = 0;
const sortButton = document.getElementById("sort-tlds");
sortButton.addEventListener("click", function() {
    sortState = (sortState + 1) % 5; // 0=random, 1=a-z, 2=z-a, 3=price-low, 4=price-high
    var currentSection = document.querySelector('.tag-section[style*="display: block"]');
    if (currentSection) {
        var grid = currentSection.querySelector('.grid');
        var cols = Array.from(grid.querySelectorAll('.col'));
        
        switch(sortState) {
            case 0: // Random
                for (let i = cols.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [cols[i], cols[j]] = [cols[j], cols[i]];
                }
                this.textContent = 'Sort: Random';
                break;
            case 1: // A-Z
                cols.sort((a, b) => a.textContent.toLowerCase().localeCompare(b.textContent.toLowerCase()));
                this.textContent = 'Sort: A-Z ▲';
                break;
            case 2: // Z-A
                cols.sort((a, b) => b.textContent.toLowerCase().localeCompare(a.textContent.toLowerCase()));
                this.textContent = 'Sort: Z-A ▼';
                break;
            case 3: // Price Low-High
                cols.sort((a, b) => {
                    const priceA = parseFloat(a.querySelector('.domain-with-contact')?.dataset?.price || '999999');
                    const priceB = parseFloat(b.querySelector('.domain-with-contact')?.dataset?.price || '999999');
                    return priceA - priceB;
                });
                this.textContent = 'Sort: Price ▲';
                break;
            case 4: // Price High-Low
                cols.sort((a, b) => {
                    const priceA = parseFloat(a.querySelector('.domain-with-contact')?.dataset?.price || '0');
                    const priceB = parseFloat(b.querySelector('.domain-with-contact')?.dataset?.price || '0');
                    return priceB - priceA;
                });
                this.textContent = 'Sort: Price ▼';
                break;
        }
        
        grid.innerHTML = '';
        cols.forEach(col => grid.appendChild(col));
    }
});

function copyEmail(event, email) {
    event.preventDefault();
    event.stopPropagation();
    navigator.clipboard.writeText(email).then(() => {
        const btn = event.target;
        const originalText = btn.textContent;
        btn.textContent = '✓';
        setTimeout(() => { btn.textContent = originalText; }, 1000);
    });
}

function showTagSection(tag) {
    var sectionId = tag.toLowerCase().replace(' ', '-');
    var section = document.getElementById(sectionId);
    if (section) {
        var sections = document.getElementsByClassName('tag-section');
        for (var i = 0; i < sections.length; i++) {
            sections[i].style.display = "none";
        }
        section.style.display = "block";
    }
}
function shuffleNames() {
    var tagSections = document.querySelectorAll('.tag-section');
    tagSections.forEach(function (section) {
        var names = Array.from(section.querySelectorAll('.col'));
        var currentIndex = names.length, randomIndex;
        while (currentIndex > 0) {
            randomIndex = Math.floor(Math.random() * currentIndex);
            currentIndex--;
            [names[currentIndex], names[randomIndex]] = [names[randomIndex], names[currentIndex]];
        }
        var grid = section.querySelector('.grid');
        grid.innerHTML = '';
        names.forEach(function (name) {
            grid.appendChild(name);
        });
    });
}
function searchNames() {
    var input = document.getElementById('search-input');
    var minPrice = document.getElementById('min-price');
    var maxPrice = document.getElementById('max-price');
    
    if (input) {
        var filter = input.value.toLowerCase();
        var minVal = minPrice && minPrice.value ? parseFloat(minPrice.value) : null;
        var maxVal = maxPrice && maxPrice.value ? parseFloat(maxPrice.value) : null;
        
        var names = document.getElementsByClassName('col');
        for (var i = 0; i < names.length; i++) {
            var name = names[i].innerText.toLowerCase();
            var nameMatches = name.includes(filter);
            
            // Check price filter
            var priceMatches = true;
            var domainSpan = names[i].querySelector('.domain-with-contact');
            if (domainSpan && (minVal !== null || maxVal !== null)) {
                var priceStr = domainSpan.dataset.price;
                if (priceStr) {
                    var price = parseFloat(priceStr);
                    if (minVal !== null && price < minVal) priceMatches = false;
                    if (maxVal !== null && price > maxVal) priceMatches = false;
                } else {
                    priceMatches = false; // No price, hide if price filter active
                }
            }
            
            if (nameMatches && priceMatches) {
                names[i].style.display = "block";
            } else {
                names[i].style.display = "none";
            }
        }
    }
}

var searchInput = document.getElementById('search-input');
if (searchInput) {
    searchInput.addEventListener('keyup', function() {
        searchNames();
    });
}

var minPriceInput = document.getElementById('min-price');
var maxPriceInput = document.getElementById('max-price');
if (minPriceInput) {
    minPriceInput.addEventListener('input', searchNames);
}
if (maxPriceInput) {
    maxPriceInput.addEventListener('input', searchNames);
}

var clearBtn = document.getElementById('clear-filters');
if (clearBtn) {
    clearBtn.addEventListener('click', function() {
        if (searchInput) searchInput.value = '';
        if (minPriceInput) minPriceInput.value = '';
        if (maxPriceInput) maxPriceInput.value = '';
        searchNames();
    });
}

showTagSection('All Names');
if (Math.random() < 0.5) shuffleNames();
function getRandomColor() {
    let color = Math.floor(Math.random() * 16777215).toString(16);
    while (color.length < 6) {
        color = '0' + color;
    }
    return '#' + color;
}
const links = document.querySelectorAll('a');
links.forEach((link) => {
    const randomColor = getRandomColor();
    link.style.textDecorationColor = randomColor;
    if (darkMode) {
        document.body.classList.add("dark-mode");
        link.classList.add('dark-mode');
    } else {
        document.body.classList.remove("dark-mode");
        link.classList.remove('dark-mode');
    }
});
window.addEventListener('DOMContentLoaded', () => {
    const addTooltipToNames = () => {
        const cols = document.querySelectorAll('.col');
        cols.forEach(col => {
            col.setAttribute('title', col.textContent.trim());
        });
    };
    addTooltipToNames();
    
    // Randomize marketplace links order
    const marketplaceLinks = document.querySelector('.marketplace-links');
    if (marketplaceLinks) {
        const links = Array.from(marketplaceLinks.querySelectorAll('a'));
        for (let i = links.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [links[i], links[j]] = [links[j], links[i]];
        }
        marketplaceLinks.innerHTML = '';
        links.forEach(link => marketplaceLinks.appendChild(link));
    }
});
</script>"""

def main():
    root = tk.Tk()
    app = HNSellApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
