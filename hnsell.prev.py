import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import idna
import re
import os
from datetime import datetime
import math
import codecs
from pathlib import Path

class HNSellApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HNSell - Handshake Domain Manager")
        self.root.geometry("900x700")
        
        style = ttk.Style()
        style.theme_use('clam')
        
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.create_punytag_tab()
        self.create_puny2uni_tab()
        self.create_pagemaker_tab()
        
        self.create_bottom_buttons()
        
        self.sort_state = 0
        
    def create_bottom_buttons(self):
        button_frame = tk.Frame(self.root)
        button_frame.pack(side='bottom', fill='x', padx=10, pady=10)
        
        help_btn = tk.Button(button_frame, text="Help", bg="yellow", fg="black", 
                            font=("Arial", 12, "bold"), command=self.show_help, width=10)
        help_btn.pack(side='left', padx=5)
        
        exit_btn = tk.Button(button_frame, text="Exit", bg="red", fg="white", 
                            font=("Arial", 12, "bold"), command=self.root.quit, width=10)
        exit_btn.pack(side='right', padx=5)
        
        process_btn = tk.Button(button_frame, text="Process", bg="green", fg="white", 
                               font=("Arial", 12, "bold"), command=self.process_action, width=15)
        process_btn.pack(side='right', padx=5)
        
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
        
        list_frame = tk.LabelFrame(tab, text="Selected Files", padx=10, pady=10)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        button_row = tk.Frame(list_frame)
        button_row.pack(fill='x', pady=5)
        tk.Button(button_row, text="Select All", command=lambda: self.toggle_all_files(True)).pack(side='left', padx=5)
        tk.Button(button_row, text="Select None", command=lambda: self.toggle_all_files(False)).pack(side='left', padx=5)
        
        self.file_listbox_frame = tk.Frame(list_frame)
        self.file_listbox_frame.pack(fill='both', expand=True)
        
        scrollbar = tk.Scrollbar(self.file_listbox_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.file_listbox = tk.Listbox(self.file_listbox_frame, selectmode='multiple', yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        self.file_data = []
        
        options_frame = tk.LabelFrame(tab, text="Output Options", padx=10, pady=10)
        options_frame.pack(fill='x', padx=10, pady=5)
        
        self.rename_orig_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="Rename original files with '_orig' suffix", variable=self.rename_orig_var).pack(anchor='w')
        
        self.sort_to_subdirs_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="Sort processed files to subdirectories by source", variable=self.sort_to_subdirs_var).pack(anchor='w')
        
        self.delete_orig_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="Delete original files", variable=self.delete_orig_var).pack(anchor='w')
        
    def create_puny2uni_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Puny ⟷ Unicode")
        
        info_frame = tk.LabelFrame(tab, text="Convert between Punycode and Unicode", padx=10, pady=10)
        info_frame.pack(fill='both', expand=False, padx=10, pady=5)
        
        tk.Label(info_frame, text="Select .txt files (list format) for conversion:").pack(anchor='w')
        tk.Label(info_frame, text="• TXT files only: Pure uni2puny or puny2uni conversion").pack(anchor='w')
        tk.Label(info_frame, text="• Each line should contain one domain name").pack(anchor='w')
        
        file_frame = tk.Frame(info_frame)
        file_frame.pack(fill='x', pady=5)
        
        tk.Button(file_frame, text="Select Files", command=self.select_puny2uni_files).pack(side='left', padx=5)
        
        list_frame = tk.LabelFrame(tab, text="Selected Files", padx=10, pady=10)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.puny2uni_listbox = tk.Listbox(list_frame, selectmode='multiple', yscrollcommand=scrollbar.set)
        self.puny2uni_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.puny2uni_listbox.yview)
        
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
        
        list_frame = tk.LabelFrame(tab, text="Selected CSV Files", padx=10, pady=10)
        list_frame.pack(fill='both', expand=False, padx=10, pady=5)
        
        self.pagemaker_listbox = tk.Listbox(list_frame, height=5)
        self.pagemaker_listbox.pack(fill='both', expand=True, pady=5)
        
        self.pagemaker_files = []
        
        sort_frame = tk.Frame(tab)
        sort_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Button(sort_frame, text="Sort TLDs", command=self.cycle_sort).pack(side='left', padx=5)
        self.sort_label = tk.Label(sort_frame, text="Current: Random")
        self.sort_label.pack(side='left', padx=10)
        
        footer_frame = tk.LabelFrame(tab, text="Footer & Credits (Optional)", padx=10, pady=10)
        footer_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Button(footer_frame, text="Select Footer HTML", command=self.select_footer).pack(side='left', padx=5)
        self.footer_label = tk.Label(footer_frame, text="No footer file selected")
        self.footer_label.pack(side='left', padx=10)
        
        tk.Button(footer_frame, text="Select Credits HTML", command=self.select_credits).pack(side='left', padx=5)
        self.credits_label = tk.Label(footer_frame, text="No credits file selected")
        self.credits_label.pack(side='left', padx=10)
        
        self.footer_file = None
        self.credits_file = None
        
        update_frame = tk.LabelFrame(tab, text="Update Existing Page", padx=10, pady=10)
        update_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(update_frame, text="Select existing HTML page to update:").pack(anchor='w')
        tk.Button(update_frame, text="Select HTML File", command=self.select_html_to_update).pack(side='left', padx=5)
        self.html_update_label = tk.Label(update_frame, text="No HTML file selected")
        self.html_update_label.pack(side='left', padx=10)
        
        self.html_to_update = None
        
        output_frame = tk.LabelFrame(tab, text="Output", padx=10, pady=10)
        output_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(output_frame, text="Output filename:").pack(side='left')
        self.output_filename_entry = tk.Entry(output_frame, width=30)
        self.output_filename_entry.insert(0, "portfolio.html")
        self.output_filename_entry.pack(side='left', padx=5)
        
    def cycle_sort(self):
        sort_states = ["Random", "Alphabetical ▲", "Alphabetical ▼"]
        self.sort_state = (self.sort_state + 1) % 3
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
            
            if 'extra.domain' in headers or 'extra.action' in headers:
                return 'nb-tr'
            elif 'domain' in headers_lower and 'for_sale' in headers_lower:
                return 'ss-tld'
            elif 'domain' in headers_lower and len(headers) >= 8:
                return 'ss-tr'
            elif 'name' in headers_lower and 'tags' in headers_lower:
                return 'nb-tld'
            elif 'time' in headers_lower and 'txhash' in headers_lower and 'domains' in headers_lower:
                return 'bob-tr'
            elif 'domains' in headers_lower and len(headers) == 1:
                return 'bob-tld'
            else:
                return 'fw'
        except:
            return 'unknown'
            
    def toggle_all_files(self, select):
        if select:
            self.file_listbox.select_set(0, tk.END)
        else:
            self.file_listbox.select_clear(0, tk.END)
            
    def select_puny2uni_files(self):
        files = filedialog.askopenfilenames(title="Select TXT Files", 
                                           filetypes=[("Text files", "*.txt"), 
                                                     ("All files", "*.*")])
        if files:
            for file in files:
                if file not in self.puny2uni_files:
                    self.puny2uni_files.append(file)
                    self.puny2uni_listbox.insert(tk.END, os.path.basename(file))
                    
    def select_pagemaker_files(self):
        files = filedialog.askopenfilenames(title="Select CSV Files", filetypes=[("CSV files", "*.csv")])
        if files:
            for file in files:
                if file not in self.pagemaker_files:
                    self.pagemaker_files.append(file)
                    self.pagemaker_listbox.insert(tk.END, os.path.basename(file))
                    
    def show_help(self):
        help_window = tk.Toplevel(self.root)
        help_window.title("Help - How to Use HNSell")
        help_window.geometry("700x600")
        
        text = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, width=80, height=35)
        text.pack(padx=10, pady=10, fill='both', expand=True)
        
        help_text = """HNSell - Handshake Domain Manager
        
TAB 1: PUNYTAG PROCESSOR
- Processes CSV exports from Bob Wallet, Namebase, Shakestation, and Firewallet
- Automatically detects source format from CSV headers
- Converts punycode domains to unicode with tagging
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
        
        close_btn = tk.Button(help_window, text="Close", command=help_window.destroy)
        close_btn.pack(pady=5)
        
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
        df.to_csv(output_path, index=False)
        
    def process_nb_tr(self, filepath, output_path):
        df = pd.read_csv(filepath)
        
        punycode_info = df['extra.domain'].apply(lambda x: self.punycode_convert_validate(x) if isinstance(x, str) else ('', ''))
        
        df['unicode'] = [re.sub(r'(?:\\x[\da-fA-F]{2})+|\\u(?:[\da-fA-F]{4})+', '', info[0]) if info[0] and info[0] != df.at[i, 'extra.domain'] else '' for i, info in enumerate(punycode_info)]
        df['PUNY_INVALID'] = [1 if (info[0] != df.at[i, 'unicode']) or (info[0] and df.at[i, 'unicode'] == df.at[i, 'extra.domain']) else '' for i, info in enumerate(punycode_info)]
        df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
        df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
        df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
        
        tags_columns = ['PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
        df['tags'] = df.apply(lambda row: ','.join(tag for tag in tags_columns if row[tag] == 1), axis=1)
        df.drop(columns=tags_columns, inplace=True)
        df = df[['extra.domain', 'unicode', 'tags'] + [col for col in df.columns if col not in ['extra.domain', 'unicode', 'tags']]]
        
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
        
        punycode_info = df[domain_col].apply(lambda x: self.punycode_convert_validate(x) if isinstance(x, str) else ('', ''))
        
        df['unicode'] = [re.sub(r'(?:\\x[\da-fA-F]{2})+|\\u(?:[\da-fA-F]{4})+', '', info[0]) if info[0] and info[0] != df.at[i, domain_col] else '' for i, info in enumerate(punycode_info)]
        df['PUNY_INVALID'] = [1 if (info[0] != df.at[i, 'unicode']) or (info[0] and df.at[i, 'unicode'] == df.at[i, domain_col]) else '' for i, info in enumerate(punycode_info)]
        df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
        df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
        df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
        
        tags_columns = ['PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
        df['tags'] = df.apply(lambda row: ','.join(tag for tag in tags_columns if row[tag] == 1), axis=1)
        df.drop(columns=tags_columns, inplace=True)
        
        col_order = [domain_col, 'unicode', 'tags'] + [col for col in df.columns if col not in [domain_col, 'unicode', 'tags']]
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
        
        punycode_info = df[domain_col].apply(lambda x: self.punycode_convert_validate(x) if isinstance(x, str) else ('', ''))
        
        df['unicode'] = [re.sub(r'(?:\\x[\da-fA-F]{2})+|\\u(?:[\da-fA-F]{4})+', '', info[0]) if info[0] and info[0] != df.at[i, domain_col] else '' for i, info in enumerate(punycode_info)]
        df['PUNY_INVALID'] = [1 if (info[0] != df.at[i, 'unicode']) or (info[0] and df.at[i, 'unicode'] == df.at[i, domain_col]) else '' for i, info in enumerate(punycode_info)]
        df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
        df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
        df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
        
        tags_columns = ['PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
        df['tags'] = df.apply(lambda row: ','.join(tag for tag in tags_columns if row[tag] == 1), axis=1)
        df.drop(columns=tags_columns, inplace=True)
        
        col_order = [domain_col, 'unicode', 'tags'] + [col for col in df.columns if col not in [domain_col, 'unicode', 'tags']]
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
            
            df['PUNY_INVALID'] = [1 if (info[0] != df.at[i, 'unicode']) or (info[0] and df.at[i, 'unicode'] == df.at[i, name_col]) else '' for i, info in enumerate(punycode_info)]
            df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
            df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
            df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
            
            tags_columns = ['PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
            if 'tags' in df.columns:
                existing_tags = df['tags'].fillna('')
                new_tags = df.apply(lambda row: ','.join(tag for tag in tags_columns if row[tag] == 1), axis=1)
                df['tags'] = df.apply(lambda row: ','.join(filter(None, [str(row['tags']), new_tags[row.name]])), axis=1)
            else:
                df['tags'] = df.apply(lambda row: ','.join(tag for tag in tags_columns if row[tag] == 1), axis=1)
            df.drop(columns=tags_columns, inplace=True)
            
            col_order = [name_col, 'unicode', 'tags'] + [col for col in df.columns if col not in [name_col, 'unicode', 'tags']]
            df = df[col_order]
        
        df.to_csv(output_path, index=False)
        
    def process_bob_tld(self, filepath, output_path):
        df = pd.read_csv(filepath)
        
        if 'domains' not in df.columns:
            raise ValueError("No 'domains' column found in Bob TLD CSV")
        
        punycode_info = df['domains'].apply(lambda x: self.punycode_convert_validate(x) if isinstance(x, str) else ('', ''))
        
        df['unicode'] = [re.sub(r'(?:\\x[\da-fA-F]{2})+|\\u(?:[\da-fA-F]{4})+', '', info[0]) if info[0] and info[0] != df.at[i, 'domains'] else '' for i, info in enumerate(punycode_info)]
        df['PUNY_INVALID'] = [1 if (info[0] != df.at[i, 'unicode']) or (info[0] and df.at[i, 'unicode'] == df.at[i, 'domains']) else '' for i, info in enumerate(punycode_info)]
        df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
        df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
        df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
        
        tags_columns = ['PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
        df['tags'] = df.apply(lambda row: ','.join(tag for tag in tags_columns if row[tag] == 1), axis=1)
        df.drop(columns=tags_columns, inplace=True)
        df = df[['domains', 'unicode', 'tags']]
        
        df.to_csv(output_path, index=False)
        
    def process_fw(self, filepath, output_path):
        df = pd.read_csv(filepath)
        
        domain_col = df.columns[0] if len(df.columns) > 0 else None
        if not domain_col:
            raise ValueError("No columns found in Firewallet CSV")
        
        punycode_info = df[domain_col].apply(lambda x: self.punycode_convert_validate(x) if isinstance(x, str) else ('', ''))
        
        df['unicode'] = [re.sub(r'(?:\\x[\da-fA-F]{2})+|\\u(?:[\da-fA-F]{4})+', '', info[0]) if info[0] and info[0] != df.at[i, domain_col] else '' for i, info in enumerate(punycode_info)]
        df['PUNY_INVALID'] = [1 if (info[0] != df.at[i, 'unicode']) or (info[0] and df.at[i, 'unicode'] == df.at[i, domain_col]) else '' for i, info in enumerate(punycode_info)]
        df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
        df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
        df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
        
        tags_columns = ['PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
        df['tags'] = df.apply(lambda row: ','.join(tag for tag in tags_columns if row[tag] == 1), axis=1)
        df.drop(columns=tags_columns, inplace=True)
        
        col_order = [domain_col, 'unicode', 'tags'] + [col for col in df.columns if col not in [domain_col, 'unicode', 'tags']]
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
        if not self.pagemaker_files:
            messagebox.showwarning("No Files", "Please select CSV files to process")
            return
            
        try:
            all_domains = []
            
            for filepath in self.pagemaker_files:
                df = pd.read_csv(filepath)
                source_type = self.detect_csv_source(filepath)
                
                if source_type == 'ss-tld' or source_type == 'ss-tr':
                    df = df[df['for_sale'] == True]
                    for _, row in df.iterrows():
                        domain = row['domain']
                        unicode_val = row.get('unicode', '')
                        tags = row.get('tags', 'All Names')
                        all_domains.append({
                            'name': domain,
                            'unicode': unicode_val,
                            'tags': tags,
                            'source': 'ss'
                        })
                elif source_type == 'nb-tld' or 'name' in df.columns:
                    for _, row in df.iterrows():
                        domain = row['name']
                        unicode_val = row.get('unicode', '')
                        tags = row.get('tags', 'All Names')
                        all_domains.append({
                            'name': domain,
                            'unicode': unicode_val,
                            'tags': tags,
                            'source': 'nb'
                        })
                        
            if not all_domains:
                messagebox.showwarning("No Domains", "No domains found in selected files")
                return
                
            html_content = self.generate_portfolio_html(all_domains)
            
            output_filename = self.output_filename_entry.get()
            if not output_filename.endswith('.html'):
                output_filename += '.html'
                
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            messagebox.showinfo("Success", f"Portfolio page created: {output_filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error creating portfolio:\n{str(e)}")
            
    def generate_portfolio_html(self, domains):
        df = pd.DataFrame(domains)
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
                footer_html = f.read()
                
        credits_html = ""
        if self.credits_file:
            with open(self.credits_file, 'r', encoding='utf-8') as f:
                credits_html = f.read()
                
        css_style = self.get_portfolio_css()
        javascript_code = self.get_portfolio_js()
        
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
    <button id="mode-toggle">🌙 / ☀️</button>
</div>
<div class="zoom-buttons">
    <button id="zoom-out">-</button>
    <button id="zoom-in">+</button>
</div>
<div class="sort-button">
    <button id="sort-tlds">Sort TLDs</button>
</div>
</div>
<div class="navigation-container">
{navigation_links_html}
</div>
<div class="content">
    <input type="text" id="search-input" placeholder="Search...">
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
        unicode_val = str(row.get('unicode', ''))
        source = row.get('source', 'nb')
        
        if source == 'ss':
            base_url = f"https://shakestation.io/domain/{name}"
        else:
            base_url = f"https://www.namebase.io/domains/{name}"
            
        if name.startswith('xn--'):
            if unicode_val and unicode_val.lower() != 'nan' and unicode_val.strip():
                try:
                    unicode_bytes = codecs.decode(unicode_val, 'unicode_escape')
                    unicode_char = unicode_bytes.encode('latin-1').decode('utf-8')
                except:
                    unicode_char = unicode_val
                return f'<a target="_blank" rel="noreferrer" class="dark-mode" href="{base_url}">{unicode_char} ({name})</a>'.replace("'", "")
            else:
                return f'<a target="_blank" rel="noreferrer" class="dark-mode" href="{base_url}">{name}</a>'
        else:
            return f'<a target="_blank" rel="noreferrer" href="{base_url}">{name}</a>'
            
    def get_portfolio_css(self):
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
</style>"""
        
    def get_portfolio_js(self):
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
document.getElementById("sort-tlds").addEventListener("click", function() {
    sortState = (sortState + 1) % 2;
    var currentSection = document.querySelector('.tag-section[style*="display: block"]');
    if (currentSection) {
        var grid = currentSection.querySelector('.grid');
        var cols = Array.from(grid.querySelectorAll('.col'));
        
        if (sortState === 0) {
            cols.sort((a, b) => {
                var textA = a.textContent.toLowerCase();
                var textB = b.textContent.toLowerCase();
                return textA.localeCompare(textB);
            });
            this.textContent = 'Sort TLDs ▼';
        } else {
            cols.sort((a, b) => {
                var textA = a.textContent.toLowerCase();
                var textB = b.textContent.toLowerCase();
                return textB.localeCompare(textA);
            });
            this.textContent = 'Sort TLDs ▲';
        }
        
        grid.innerHTML = '';
        cols.forEach(col => grid.appendChild(col));
    }
});
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
    if (input) {
        var filter = input.value.toLowerCase();
        var names = document.getElementsByClassName('col');
        for (var i = 0; i < names.length; i++) {
            var name = names[i].innerText.toLowerCase();
            if (name.includes(filter)) {
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
});
</script>"""

def main():
    root = tk.Tk()
    app = HNSellApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()