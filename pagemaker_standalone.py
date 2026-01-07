"""
PageMaker - Standalone HTML Portfolio Generator
Fully standalone tkinter application for generating Handshake domain portfolio pages
No external dependencies on hnsell.py - all methods included directly

Supports: Namebase, Shakestation, Bob Wallet, and Firewallet CSV exports
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os
from datetime import datetime
import math
import codecs
import idna
import re
import unicodedata


class PageMakerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PageMaker - HNS Domain Portfolio Generator")
        self.root.geometry("900x950")
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # Create main container with canvas for scrolling
        main_container = tk.Frame(root)
        main_container.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(main_container)
        scrollbar = tk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Initialize variables
        self.pagemaker_files = []
        self.sort_state = 0
        self.custom_css_file = None
        self.footer_file = None
        self.credits_file = None
        
        # Build UI
        self.build_ui(scrollable_frame, root)
    
    def build_ui(self, scrollable_frame, root):
        """Build the user interface"""
        # Info section
        info_frame = tk.LabelFrame(scrollable_frame, text="Generate HTML Portfolio Page", padx=10, pady=10)
        info_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(info_frame, text="Select CSV files (Namebase, Shakestation, Bob Wallet, or Firewallet) to generate portfolio page:").pack(anchor='w')
        
        file_frame = tk.Frame(info_frame)
        file_frame.pack(fill='x', pady=5)
        
        tk.Button(file_frame, text="Select CSV Files", command=self.select_files).pack(side='left', padx=5)
        tk.Button(file_frame, text="Select Folder (Recursive)", command=self.select_folder).pack(side='left', padx=5)
        
        self.recursive_var = tk.BooleanVar(value=False)
        tk.Checkbutton(file_frame, text="Recursive Search", variable=self.recursive_var).pack(side='left', padx=5)
        
        # File list section
        list_frame = tk.LabelFrame(scrollable_frame, text="Selected CSV Files", padx=10, pady=10)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        button_row = tk.Frame(list_frame)
        button_row.pack(fill='x', pady=5)
        tk.Button(button_row, text="Select All", command=lambda: self.toggle_files(True)).pack(side='left', padx=5)
        tk.Button(button_row, text="Select None", command=lambda: self.toggle_files(False)).pack(side='left', padx=5)
        tk.Button(button_row, text="Remove Selected", bg="#ff6b6b", fg="white", command=self.remove_files).pack(side='left', padx=5)
        tk.Button(button_row, text="Clear All", bg="#ff8c00", fg="white", command=self.clear_files).pack(side='left', padx=5)
        
        list_scroll = tk.Scrollbar(list_frame)
        list_scroll.pack(side='right', fill='y')
        
        self.file_listbox = tk.Listbox(list_frame, selectmode='multiple', yscrollcommand=list_scroll.set, height=8)
        self.file_listbox.pack(side='left', fill='both', expand=True)
        list_scroll.config(command=self.file_listbox.yview)
        self.file_listbox.bind('<Delete>', lambda e: self.remove_files())
        
        # Sort section
        sort_frame = tk.Frame(scrollable_frame)
        sort_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Button(sort_frame, text="Sort TLDs", command=self.cycle_sort).pack(side='left', padx=5)
        self.sort_label = tk.Label(sort_frame, text="Current: Random")
        self.sort_label.pack(side='left', padx=10)
        
        # Theme section
        theme_frame = tk.LabelFrame(scrollable_frame, text="Theme Settings", padx=10, pady=10)
        theme_frame.pack(fill='x', padx=10, pady=5)
        
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
        
        # Footer & Credits section
        footer_frame = tk.LabelFrame(scrollable_frame, text="Footer & Credits (Optional)", padx=10, pady=10)
        footer_frame.pack(fill='x', padx=10, pady=5)
        
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
        
        # Output section
        output_frame = tk.LabelFrame(scrollable_frame, text="Output", padx=10, pady=10)
        output_frame.pack(fill='x', padx=10, pady=5)
        
        output_row = tk.Frame(output_frame)
        output_row.pack(fill='x', pady=5)
        tk.Button(output_row, text="Select Output File", command=self.select_output_file).pack(side='left', padx=5)
        self.output_filename_entry = tk.Entry(output_row, width=40)
        self.output_filename_entry.insert(0, "portfolio.html")
        self.output_filename_entry.pack(side='left', padx=5, fill='x', expand=True)
        
        # Display options section
        options_frame = tk.LabelFrame(scrollable_frame, text="Display Options", padx=10, pady=10)
        options_frame.pack(fill='x', padx=10, pady=5)
        
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
        
        # Bottom buttons
        button_frame = tk.Frame(root)
        button_frame.pack(side='bottom', fill='x', padx=10, pady=15)
        
        help_btn = tk.Button(button_frame, text="Help", bg="yellow", fg="black", 
                            font=("Arial", 12, "bold"), command=self.show_help, width=10, height=2)
        help_btn.pack(side='left', padx=5, pady=5)
        
        generate_btn = tk.Button(button_frame, text="Generate Portfolio", bg="green", fg="white", 
                               font=("Arial", 12, "bold"), command=self.generate_portfolio, width=15, height=2)
        generate_btn.pack(side='right', padx=5, pady=5)
        
        exit_btn = tk.Button(button_frame, text="Exit", bg="red", fg="white", 
                            font=("Arial", 12, "bold"), command=root.quit, width=10, height=2)
        exit_btn.pack(side='right', padx=5, pady=5)

    
    # File selection methods
    def select_files(self):
        files = filedialog.askopenfilenames(title="Select CSV Files", filetypes=[("CSV files", "*.csv")])
        if files:
            for file in files:
                if file not in self.pagemaker_files:
                    self.pagemaker_files.append(file)
                    self.file_listbox.insert(tk.END, os.path.basename(file))
    
    def select_folder(self):
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
            for file in files:
                if file not in self.pagemaker_files:
                    self.pagemaker_files.append(file)
                    self.file_listbox.insert(tk.END, os.path.basename(file))
    
    def toggle_files(self, select):
        if select:
            self.file_listbox.select_set(0, tk.END)
        else:
            self.file_listbox.select_clear(0, tk.END)
    
    def remove_files(self):
        selected_indices = list(self.file_listbox.curselection())
        for idx in reversed(selected_indices):
            self.file_listbox.delete(idx)
            del self.pagemaker_files[idx]
    
    def clear_files(self):
        self.file_listbox.delete(0, tk.END)
        self.pagemaker_files = []
    
    # UI helper methods
    def cycle_sort(self):
        sort_states = ["Random", "Alphabetical ▲", "Alphabetical ▼", "Price ▲", "Price ▼"]
        self.sort_state = (self.sort_state + 1) % 5
        self.sort_label.config(text=f"Current: {sort_states[self.sort_state]}")
    
    def on_theme_change(self, event=None):
        theme = self.theme_var.get()
        if theme == "3-way switch":
            self.color_picker_frame.pack(fill='x', pady=5)
        else:
            self.color_picker_frame.pack_forget()
    
    def pick_color(self, color_type):
        try:
            from tkinter import colorchooser
            current_color = self.light_color_entry.get() if color_type == 'light' else self.dark_color_entry.get()
            result = colorchooser.askcolor(color=current_color, title=f"Choose {color_type} color")
            if result and result[1]:
                if color_type == 'light':
                    self.light_color_entry.delete(0, tk.END)
                    self.light_color_entry.insert(0, result[1])
                else:
                    self.dark_color_entry.delete(0, tk.END)
                    self.dark_color_entry.insert(0, result[1])
        except Exception as e:
            messagebox.showerror("Color Picker Error", f"Failed to open color picker: {str(e)}")
    
    def select_custom_css(self):
        file = filedialog.askopenfilename(title="Select Custom CSS", filetypes=[("CSS files", "*.css"), ("All files", "*.*")])
        if file:
            self.custom_css_file = file
            self.css_label.config(text=os.path.basename(file))
    
    def select_footer(self):
        file = filedialog.askopenfilename(title="Select Footer HTML", filetypes=[("HTML files", "*.html")])
        if file:
            self.footer_file = file
            self.footer_label.config(text=os.path.basename(file))
    
    def remove_footer(self):
        self.footer_file = None
        self.footer_label.config(text="No footer file selected")
    
    def select_credits(self):
        file = filedialog.askopenfilename(title="Select Credits HTML", filetypes=[("HTML files", "*.html")])
        if file:
            self.credits_file = file
            self.credits_label.config(text=os.path.basename(file))
    
    def remove_credits(self):
        self.credits_file = None
        self.credits_label.config(text="No credits file selected")
    
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
    
    def detect_csv_source(self, filepath):
        """Detect the source type of a CSV file"""
        try:
            df = pd.read_csv(filepath, nrows=1)
            headers = df.columns.tolist()
            headers_lower = [h.lower() for h in headers]
            
            if 'extra.domain' in headers:
                return 'nb-tr'
            elif 'for_sale' in headers_lower:
                return 'ss-tld'
            elif 'coin' in headers_lower:
                return 'ss-tr'
            elif 'expiry' in headers_lower:
                return 'fw'
            elif 'price_hns' in headers_lower:
                return 'nb-tld'
            elif 'txhash' in headers_lower:
                return 'bob-tr'
            elif 'domains' in headers_lower:
                return 'bob-tld'
            elif len(headers) == 1:
                first_val = str(headers[0]).lower()
                if first_val in ['name', 'domain', 'time', 'action', 'coin', 'expiry', 'value', 'maxbid', 'price_hns', 'for_sale']:
                    return 'unknown'
                if first_val.startswith('xn--') or (len(first_val) <= 63 and all(c.isalnum() or c in '-_' for c in first_val)):
                    return 'bob-tld'
            return 'unknown'
        except:
            return 'unknown'

    
    def generate_portfolio(self):
        """Main method to generate HTML portfolio from selected CSV files"""
        selected_indices = list(range(len(self.pagemaker_files)))
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select CSV files to process")
            return
        
        try:
            all_domains = []
            bob_fw_without_contact = []
            
            for idx in selected_indices:
                filepath = self.pagemaker_files[idx]
                source_type = self.detect_csv_source(filepath)
                
                # Read CSV with error handling
                try:
                    df = pd.read_csv(filepath)
                except pd.errors.ParserError:
                    try:
                        df = pd.read_csv(filepath, quoting=1, escapechar='\\')
                    except:
                        df = pd.read_csv(filepath, on_bad_lines='skip')
                
                if source_type == 'ss-tld':
                    df = df[df['for_sale'] == True]
                    for _, row in df.iterrows():
                        domain = row['domain']
                        if isinstance(domain, float) and math.isnan(domain):
                            continue
                        domain = str(domain)
                        all_domains.append({
                            'name': domain,
                            'unicode': row.get('unicode', ''),
                            'tags': row.get('tags', 'All Names'),
                            'source': 'ss',
                            'email': row.get('email', ''),
                            'price': row.get('price', '')
                        })
                
                elif source_type == 'ss-tr':
                    for _, row in df.iterrows():
                        domain = row['domain']
                        if isinstance(domain, float) and math.isnan(domain):
                            continue
                        domain = str(domain)
                        email = str(row.get('email', '')).strip() if row.get('email', '') else ''
                        price = str(row.get('price', '')).strip() if row.get('price', '') else ''
                        if email.lower() in ['nan', '0']: email = ''
                        if price.lower() in ['nan', '0', '0.0']: price = ''
                        
                        all_domains.append({
                            'name': domain,
                            'unicode': row.get('unicode', ''),
                            'tags': row.get('tags', 'All Names'),
                            'source': 'ss',
                            'email': email,
                            'price': price
                        })
                
                elif source_type in ['nb-tld', 'nb-tr']:
                    for _, row in df.iterrows():
                        domain = row.get('name', row.get('extra.domain', ''))
                        if isinstance(domain, float) and math.isnan(domain):
                            continue
                        domain = str(domain)
                        email = str(row.get('email', '')).strip() if row.get('email', '') else ''
                        price = str(row.get('price', '')).strip() if row.get('price', '') else ''
                        if email.lower() in ['nan', '0']: email = ''
                        if price.lower() in ['nan', '0', '0.0']: price = ''
                        
                        all_domains.append({
                            'name': domain,
                            'unicode': row.get('unicode', ''),
                            'tags': row.get('tags', 'All Names'),
                            'source': 'nb',
                            'email': email,
                            'price': price
                        })
                
                elif source_type == 'bob-tld':
                    has_email_or_price = False
                    auto_email_base = self.auto_email_entry.get().strip()
                    for _, row in df.iterrows():
                        domain = row.get('domains', '')
                        if isinstance(domain, float) and math.isnan(domain):
                            continue
                        domain = str(domain)
                        email = str(row.get('email', '')).strip() if row.get('email', '') else ''
                        price = str(row.get('price', '')).strip() if row.get('price', '') else ''
                        if not email or email.lower() in ['nan', 'none', '0']: email = ''
                        if not price or price.lower() in ['nan', 'none', '0', '0.0']: price = ''
                        
                        # Auto-append email
                        if auto_email_base and not email and (price or self.list_all_var.get()):
                            if '@' in auto_email_base:
                                parts = auto_email_base.split('@')
                                if len(parts) == 2:
                                    user_part = parts[0]
                                    if user_part.endswith('+'):
                                        email = f"{user_part}{domain}@{parts[1]}"
                                    else:
                                        email = f"{user_part}+{domain}@{parts[1]}"
                        
                        if self.list_all_var.get() or email or price:
                            has_email_or_price = True
                            all_domains.append({
                                'name': domain,
                                'unicode': row.get('unicode', ''),
                                'tags': row.get('tags', 'All Names'),
                                'source': 'bob',
                                'email': email,
                                'price': price
                            })
                    if not has_email_or_price and not self.list_all_var.get():
                        bob_fw_without_contact.append(os.path.basename(filepath))
                
                elif source_type == 'fw':
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
                        if isinstance(domain, float) and math.isnan(domain):
                            continue
                        domain = str(domain)
                        
                        email = row.get('email', '') if has_email_col else ''
                        price = row.get('price', '') if has_price_col else ''
                        
                        if isinstance(email, float) and math.isnan(email): email = ''
                        if isinstance(price, float):
                            if math.isnan(price) or price == 0.0:
                                price = ''
                            else:
                                price = str(price)
                        else:
                            price = str(price).strip() if price else ''
                            if price.lower() in ['nan', 'none', '0', '0.0']: price = ''
                        
                        email = str(email).strip() if email else ''
                        if email.lower() in ['nan', 'none', '0']: email = ''
                        
                        # Auto-append email
                        if auto_email_base and not email and (price or self.list_all_var.get()):
                            if '@' in auto_email_base:
                                parts = auto_email_base.split('@')
                                if len(parts) == 2:
                                    user_part = parts[0]
                                    if user_part.endswith('+'):
                                        email = f"{user_part}{domain}@{parts[1]}"
                                    else:
                                        email = f"{user_part}+{domain}@{parts[1]}"
                        
                        if self.list_all_var.get() or email or price:
                            has_email_or_price = True
                            all_domains.append({
                                'name': domain,
                                'unicode': row.get('unicode', ''),
                                'tags': row.get('tags', 'All Names'),
                                'source': 'fw',
                                'email': email,
                                'price': price
                            })
                    if not has_email_or_price and not self.list_all_var.get():
                        bob_fw_without_contact.append(os.path.basename(filepath))
            
            if not all_domains:
                error_msg = "No domains found in selected files"
                if bob_fw_without_contact:
                    error_msg += f"\n\nBob/Firewallet files require 'email' or 'price' columns with values:\n" + "\n".join(f"  • {f}" for f in bob_fw_without_contact)
                messagebox.showwarning("No Domains", error_msg)
                return
            
            html_content = self.generate_portfolio_html(all_domains)
            
            output_filename = self.output_filename_entry.get()
            if not output_filename.endswith('.html'):
                output_filename += '.html'
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_path = os.path.join(script_dir, output_filename)
            
            if os.path.exists(output_path):
                result = messagebox.askyesno("File Exists", 
                    f"The file '{output_filename}' already exists.\nDo you want to overwrite it?")
                if not result:
                    return
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            messagebox.showinfo("Success", f"Portfolio page created: {output_path}\n\nTotal domains: {len(all_domains)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error creating portfolio:\n{str(e)}")

    
    def generate_portfolio_html(self, domains):
        """Generate the complete HTML content"""
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
                footer_content = f.read()
                footer_html = f'<footer>{footer_content}</footer>'
        
        credits_html = ""
        if self.credits_file:
            with open(self.credits_file, 'r', encoding='utf-8') as f:
                credits_content = f.read()
                credits_html = f'<div class="credits">{credits_content}</div>'
        
        css_style = self.get_portfolio_css()
        javascript_code = self.get_portfolio_js()
        
        theme = self.theme_var.get()
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
        """Format a single domain entry with proper linking and contact info"""
        name = row['name']
        if isinstance(name, float):
            if math.isnan(name):
                return ''
            name = str(name)
        name = str(name)
        unicode_val = str(row.get('unicode', ''))
        source = row.get('source', 'nb')
        email = row.get('email', '')
        price = row.get('price', '')
        
        if isinstance(email, float) and math.isnan(email): email = ''
        if isinstance(price, float) and math.isnan(price): price = ''
        if str(email).lower() == 'nan': email = ''
        if str(price).lower() == 'nan': price = ''
        
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
        
        # Build contact parts
        contact_parts = []
        if price:
            contact_parts.append(f"💰 {price}")
        if email:
            copy_btn = f'<button class="copy-email-btn" onclick="copyEmail(event, \'{email}\')" title="Copy {email}">eml</button>'
            contact_parts.append(copy_btn)
        
        # Determine base URL based on source
        if source == 'ss':
            base_url = f"https://shakestation.io/domain/{name}"
        elif source == 'nb':
            base_url = f"https://www.namebase.io/domains/{name}"
        elif source in ['bob', 'fw']:
            # No marketplace link for bob/fw
            if contact_parts:
                contact_str = ' '.join(contact_parts)
                return f'<span class="domain-with-contact" data-price="{price if price else ""}" data-email="{email if email else ""}">' + \
                       f'<div class="domain-name">{display_name}</div><div class="domain-contact">{contact_str}</div></span>'
            else:
                return f'<span class="domain-with-contact" data-price="" data-email=""><div class="domain-name">{display_name}</div></span>'
        else:
            base_url = f"https://www.namebase.io/domains/{name}"
        
        # For marketplace sources
        if contact_parts:
            contact_str = ' '.join(contact_parts)
            return f'<span class="domain-with-contact" data-price="{price if price else ""}" data-email="{email if email else ""}">' + \
                   f'<div class="domain-name"><a target="_blank" rel="noreferrer" href="{base_url}">{display_name}</a></div>' + \
                   f'<div class="domain-contact">{contact_str}</div></span>'
        else:
            return f'<a target="_blank" rel="noreferrer" href="{base_url}">{display_name}</a>'

    
    def get_portfolio_css(self):
        """Generate CSS based on selected theme"""
        theme = self.theme_var.get()
        
        # Custom CSS file
        if theme == "custom CSS" and self.custom_css_file:
            try:
                with open(self.custom_css_file, 'r', encoding='utf-8') as f:
                    custom_css = f.read()
                return f"<style>\n{custom_css}\n</style>"
            except:
                pass
        
        # 3-way theme
        if theme == "3-way switch":
            return self.get_threeway_css()
        
        # Default dark+light theme
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

    
    def get_threeway_css(self):
        """Generate CSS for 3-way theme (Light/Dark/Black)"""
        light_color = self.light_color_entry.get()
        dark_color = self.dark_color_entry.get()
        
        return f"""<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    background-color: {light_color};
    color: #3404f4;
    font-family: Arial, Helvetica, sans-serif;
    line-height: 1.6;
    padding: 20px;
    transition: background-color 0.3s ease, color 0.3s ease;
}}

body.dark-theme {{
    background-color: {dark_color};
    color: #99ddff;
}}

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

footer, .credits {{
    margin-top: 2em;
    padding: 1em;
    border-top: 2px solid currentColor;
}}

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

    
    def get_portfolio_js(self):
        """Generate JavaScript based on selected theme"""
        theme = self.theme_var.get()
        
        if theme == "3-way switch":
            return self.get_threeway_js()
        
        # Default dark+light JavaScript
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
    sortState = (sortState + 1) % 5;
    var currentSection = document.querySelector('.tag-section[style*="display: block"]');
    if (currentSection) {
        var grid = currentSection.querySelector('.grid');
        var cols = Array.from(grid.querySelectorAll('.col'));
        
        switch(sortState) {
            case 0:
                for (let i = cols.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [cols[i], cols[j]] = [cols[j], cols[i]];
                }
                this.textContent = 'Sort: Random';
                break;
            case 1:
                cols.sort((a, b) => a.textContent.toLowerCase().localeCompare(b.textContent.toLowerCase()));
                this.textContent = 'Sort: A-Z ▲';
                break;
            case 2:
                cols.sort((a, b) => b.textContent.toLowerCase().localeCompare(a.textContent.toLowerCase()));
                this.textContent = 'Sort: Z-A ▼';
                break;
            case 3:
                cols.sort((a, b) => {
                    const priceA = parseFloat(a.querySelector('.domain-with-contact')?.dataset?.price || '999999');
                    const priceB = parseFloat(b.querySelector('.domain-with-contact')?.dataset?.price || '999999');
                    return priceA - priceB;
                });
                this.textContent = 'Sort: Price ▲';
                break;
            case 4:
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
            
            var priceMatches = true;
            var domainSpan = names[i].querySelector('.domain-with-contact');
            if (domainSpan && (minVal !== null || maxVal !== null)) {
                var priceStr = domainSpan.dataset.price;
                if (priceStr) {
                    var price = parseFloat(priceStr);
                    if (minVal !== null && price < minVal) priceMatches = false;
                    if (maxVal !== null && price > maxVal) priceMatches = false;
                } else {
                    priceMatches = false;
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

    
    def get_threeway_js(self):
        """JavaScript for 3-way theme toggle (Light -> Dark -> Black)"""
        return """<script>
let currentTheme = 0;
let themeBtn;

window.addEventListener('DOMContentLoaded', () => {
    themeBtn = document.getElementById('themeBtn');
    
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
    if (!themeBtn) return;
    document.body.classList.remove('dark-theme', 'black-theme');
    switch(currentTheme) {
        case 0:
            themeBtn.textContent = '☀️ Light';
            break;
        case 1:
            document.body.classList.add('dark-theme');
            themeBtn.textContent = '🌙 Dark';
            break;
        case 2:
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
    sortState = (sortState + 1) % 5;
    var currentSection = document.querySelector('.tag-section[style*="display: block"]');
    if (currentSection) {
        var grid = currentSection.querySelector('.grid');
        var cols = Array.from(grid.querySelectorAll('.col'));
        
        switch(sortState) {
            case 0:
                for (let i = cols.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [cols[i], cols[j]] = [cols[j], cols[i]];
                }
                this.textContent = 'Sort: Random';
                break;
            case 1:
                cols.sort((a, b) => a.textContent.toLowerCase().localeCompare(b.textContent.toLowerCase()));
                this.textContent = 'Sort: A-Z ▲';
                break;
            case 2:
                cols.sort((a, b) => b.textContent.toLowerCase().localeCompare(a.textContent.toLowerCase()));
                this.textContent = 'Sort: Z-A ▼';
                break;
            case 3:
                cols.sort((a, b) => {
                    const priceA = parseFloat(a.querySelector('.domain-with-contact')?.dataset?.price || '999999');
                    const priceB = parseFloat(b.querySelector('.domain-with-contact')?.dataset?.price || '999999');
                    return priceA - priceB;
                });
                this.textContent = 'Sort: Price ▲';
                break;
            case 4:
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
            
            var priceMatches = true;
            var domainSpan = names[i].querySelector('.domain-with-contact');
            if (domainSpan && (minVal !== null || maxVal !== null)) {
                var priceStr = domainSpan.dataset.price;
                if (priceStr) {
                    var price = parseFloat(priceStr);
                    if (minVal !== null && price < minVal) priceMatches = false;
                    if (maxVal !== null && price > maxVal) priceMatches = false;
                } else {
                    priceMatches = false;
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
    
    def show_help(self):
        """Display help dialog with usage instructions"""
        help_window = tk.Toplevel(self.root)
        help_window.title("PageMaker Help")
        help_window.geometry("750x650")
        
        help_window.bind('<Escape>', lambda e: help_window.destroy())
        
        from tkinter import scrolledtext
        text = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, width=90, height=40)
        text.pack(padx=10, pady=10, fill='both', expand=True)
        
        help_text = """HNSell PageMaker - Standalone Portfolio Generator

OVERVIEW
Generate beautiful HTML portfolio pages from Handshake domain CSV exports.
Supports Namebase, Shakestation, Bob Wallet, and Firewallet formats.

FILE SELECTION
• Select Files: Choose individual CSV files to process
• Select Folder: Choose a folder with optional recursive search
• Recursive Search: When checked, searches all subdirectories for CSV files
• File List Controls:
  - Select All/None: Toggle selection of all files
  - Remove Selected: Remove highlighted files from list
  - Clear All: Remove all files from list

SUPPORTED CSV FORMATS
Automatically detected from file headers:
• Namebase (nb-tld): Domain exports with 'name' column
• Namebase (nb-tr): Transaction history with 'extra.domain' column
• Shakestation (ss-tld): Domain listings with 'for_sale' column
• Shakestation (ss-tr): Transaction history with 'coin' column
• Bob Wallet (bob-tld): Domain list (single column or 'domains' column)
• Bob Wallet (bob-tr): Transaction history with 'txhash' column
• Firewallet (fw): Exports with 'expiry' column

SORT OPTIONS
Click "Sort TLDs" to cycle through sorting modes:
• Random: Randomize domain order
• A-Z ▲: Sort alphabetically ascending
• Z-A ▼: Sort alphabetically descending
• Price ▲: Sort by price (low to high)
• Price ▼: Sort by price (high to low)

THEME SETTINGS
Three theme options available:
1. Dark + Light (default): Classic two-way toggle with gradients
2. 3-Way Switch: Light → Dark → Black theme cycle
   - Custom colors: Choose your own light/dark colors
   - Click color boxes to open color picker
3. Custom CSS: Load your own CSS file for complete control

FOOTER & CREDITS
Add optional HTML files to include at bottom of page:
• Footer: Main footer content (above credits)
• Credits: Attribution/credits section (very bottom)
• Use "Remove" buttons to clear selections

OUTPUT FILE
• Default: portfolio.html (saved in script directory)
• Click "Select Output File" to choose different location/name
• Existing files: Will prompt before overwriting

DISPLAY OPTIONS
• List all domains: Include Bob/Firewallet domains even without price/email
  (By default, Bob/FW domains require price or email to be listed)

• Auto-append email: Automatically add email addresses to domains with prices
  - Format: user@gmail.com OR user+@gmail.com
  - If user+ format: Creates user+domainname@gmail.com for each domain
  - If user format: Creates user+domainname@gmail.com for each domain
  - Only applies when domain has price but no email specified

ADDING PRICE/EMAIL TO BOB/FIREWALLET CSVS
Bob Wallet and Firewallet CSVs don't include price/email by default.
To add them:
1. Open CSV in Excel/spreadsheet editor
2. Add column named EXACTLY 'price' (lowercase) with HNS prices
3. Add column named EXACTLY 'email' (lowercase) with contact email
4. Save and process through PageMaker

Alternatively, use "List all domains" option with "Auto-append email"
to show all domains with auto-generated contact emails.

MARKETPLACE LINKS
Generated pages include links to:
• ShakeShift - HNS marketplace
• bobWallet - HNS wallet and trading
• Namebase - Domain marketplace
• ShakeStation - Domain marketplace  
• Fingertip - Browser extension
• Firewallet - Browser-based wallet

Domain links automatically point to correct marketplace:
• Namebase domains → namebase.io/domains/[name]
• Shakestation domains → shakestation.io/domain/[name]
• Bob/Firewallet domains → Show contact info only (no marketplace link)

GENERATED HTML FEATURES
• Search: Filter domains by name and price range
• Tag Navigation: Click tags to view filtered domain groups
• Dark/Light Mode: Theme toggle button (or 3-way cycle)
• Zoom Controls: +/- buttons to adjust text size
• Email Copy: Click 'eml' button to copy email to clipboard
• Responsive Design: Auto-adjusts for different screen sizes
• Tooltips: Hover over domains to see full name

NOTES
• Only Shakestation domains marked 'for_sale=TRUE' are included
• Punycode domains show Unicode characters when available
• Price filter requires domains to have price column populated
• Marketplace links are randomized on each page load for fairness
"""
        
        text.insert(tk.END, help_text)
        text.config(state=tk.DISABLED)
        
        btn_frame = tk.Frame(help_window)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Close", bg="#3404f4", fg="white",
                 font=("Arial", 10, "bold"), command=help_window.destroy, 
                 width=15).pack()


def main():
    """Main entry point for PageMaker standalone application"""
    root = tk.Tk()
    app = PageMakerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

# PageMaker Standalone - Complete
# Fully self-contained Handshake domain portfolio generator
# No external dependencies on hnsell.py - all functionality built-in
