import wx
import wx.lib.scrolledpanel as scrolled
import pandas as pd
import idna
import re
import os
from datetime import datetime
import math
import codecs
from pathlib import Path
import unicodedata

class HNSellFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='HNSell - Handshake Domain Manager', size=(900, 950))
        
        # Create main panel
        main_panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Create notebook for tabs
        self.notebook = wx.Notebook(main_panel)
        
        # Create tabs
        self.create_punytag_tab()
        self.create_puny2uni_tab()
        self.create_pagemaker_tab()
        
        main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 10)
        
        # Create bottom buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        help_btn = wx.Button(main_panel, label="Help", size=(100, 40))
        help_btn.SetBackgroundColour(wx.Colour(255, 255, 0))
        help_btn.Bind(wx.EVT_BUTTON, self.on_help)
        
        process_btn = wx.Button(main_panel, label="Process", size=(150, 40))
        process_btn.SetBackgroundColour(wx.Colour(0, 255, 0))
        process_btn.Bind(wx.EVT_BUTTON, self.on_process)
        
        exit_btn = wx.Button(main_panel, label="Exit", size=(100, 40))
        exit_btn.SetBackgroundColour(wx.Colour(255, 0, 0))
        exit_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        exit_btn.Bind(wx.EVT_BUTTON, self.on_exit)
        
        button_sizer.Add(help_btn, 0, wx.ALL, 5)
        button_sizer.AddStretchSpacer()
        button_sizer.Add(process_btn, 0, wx.ALL, 5)
        button_sizer.Add(exit_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        main_panel.SetSizer(main_sizer)
        
        # Initialize state
        self.sort_state = 0
        self.file_data = []
        self.puny2uni_files = []
        self.pagemaker_files = []
        
        self.Centre()
        self.Show()
    
    def create_punytag_tab(self):
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Info section
        info_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "CSV File Processing")
        info_text = wx.StaticText(panel, label="Select CSV files to process (Bob, Namebase, Shakestation, or Firewallet exports):")
        info_box.Add(info_text, 0, wx.ALL, 5)
        
        # File selection buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        select_files_btn = wx.Button(panel, label="Select Files")
        select_files_btn.Bind(wx.EVT_BUTTON, self.on_select_punytag_files)
        btn_sizer.Add(select_files_btn, 0, wx.ALL, 5)
        
        select_folder_btn = wx.Button(panel, label="Select Folder (Recursive)")
        select_folder_btn.Bind(wx.EVT_BUTTON, self.on_select_punytag_folder)
        btn_sizer.Add(select_folder_btn, 0, wx.ALL, 5)
        
        self.recursive_var = wx.CheckBox(panel, label="Recursive Search")
        btn_sizer.Add(self.recursive_var, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        info_box.Add(btn_sizer, 0, wx.EXPAND)
        sizer.Add(info_box, 0, wx.EXPAND | wx.ALL, 10)
        
        # File list section
        list_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Selected Files")
        
        list_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        select_all_btn = wx.Button(panel, label="Select All")
        select_all_btn.Bind(wx.EVT_BUTTON, lambda e: self.file_listbox.SetSelection(wx.NOT_FOUND))
        list_btn_sizer.Add(select_all_btn, 0, wx.ALL, 5)
        
        select_none_btn = wx.Button(panel, label="Select None")
        select_none_btn.Bind(wx.EVT_BUTTON, lambda e: self.file_listbox.DeselectAll())
        list_btn_sizer.Add(select_none_btn, 0, wx.ALL, 5)
        
        remove_btn = wx.Button(panel, label="Remove Selected")
        remove_btn.SetBackgroundColour(wx.Colour(255, 107, 107))
        remove_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        remove_btn.Bind(wx.EVT_BUTTON, self.on_remove_punytag_files)
        list_btn_sizer.Add(remove_btn, 0, wx.ALL, 5)
        
        clear_btn = wx.Button(panel, label="Clear All")
        clear_btn.SetBackgroundColour(wx.Colour(255, 140, 0))
        clear_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear_punytag_files)
        list_btn_sizer.Add(clear_btn, 0, wx.ALL, 5)
        
        list_box.Add(list_btn_sizer, 0, wx.EXPAND)
        
        self.file_listbox = wx.ListBox(panel, style=wx.LB_MULTIPLE | wx.LB_NEEDED_SB)
        list_box.Add(self.file_listbox, 1, wx.EXPAND | wx.ALL, 5)
        
        sizer.Add(list_box, 1, wx.EXPAND | wx.ALL, 10)
        
        # Options section
        options_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Output Options")
        
        self.rename_orig_var = wx.CheckBox(panel, label="Rename original files with '_orig' suffix")
        self.rename_orig_var.SetValue(True)
        options_box.Add(self.rename_orig_var, 0, wx.ALL, 5)
        
        self.sort_to_subdirs_var = wx.CheckBox(panel, label="Sort processed files to subdirectories by source")
        options_box.Add(self.sort_to_subdirs_var, 0, wx.ALL, 5)
        
        self.delete_orig_var = wx.CheckBox(panel, label="Delete original files")
        options_box.Add(self.delete_orig_var, 0, wx.ALL, 5)
        
        sizer.Add(options_box, 0, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "Punytag Processor")
    
    def create_puny2uni_tab(self):
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Info section
        info_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Convert between Punycode and Unicode")
        
        info_text1 = wx.StaticText(panel, label="Select .txt files (list format) for conversion:")
        info_box.Add(info_text1, 0, wx.ALL, 5)
        
        info_text2 = wx.StaticText(panel, label="• TXT files only: Pure uni2puny or puny2uni conversion")
        info_box.Add(info_text2, 0, wx.LEFT, 5)
        
        info_text3 = wx.StaticText(panel, label="• Each line should contain one domain name")
        info_box.Add(info_text3, 0, wx.LEFT, 5)
        
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        select_files_btn = wx.Button(panel, label="Select Files")
        select_files_btn.Bind(wx.EVT_BUTTON, self.on_select_puny2uni_files)
        btn_sizer.Add(select_files_btn, 0, wx.ALL, 5)
        
        select_folder_btn = wx.Button(panel, label="Select Folder (Recursive)")
        select_folder_btn.Bind(wx.EVT_BUTTON, self.on_select_puny2uni_folder)
        btn_sizer.Add(select_folder_btn, 0, wx.ALL, 5)
        
        self.recursive_puny2uni_var = wx.CheckBox(panel, label="Recursive Search")
        btn_sizer.Add(self.recursive_puny2uni_var, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        info_box.Add(btn_sizer, 0, wx.EXPAND)
        sizer.Add(info_box, 0, wx.EXPAND | wx.ALL, 10)
        
        # File list section
        list_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Selected Files")
        
        list_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        select_all_btn = wx.Button(panel, label="Select All")
        select_all_btn.Bind(wx.EVT_BUTTON, lambda e: self.puny2uni_listbox.SetSelection(wx.NOT_FOUND))
        list_btn_sizer.Add(select_all_btn, 0, wx.ALL, 5)
        
        select_none_btn = wx.Button(panel, label="Select None")
        select_none_btn.Bind(wx.EVT_BUTTON, lambda e: self.puny2uni_listbox.DeselectAll())
        list_btn_sizer.Add(select_none_btn, 0, wx.ALL, 5)
        
        remove_btn = wx.Button(panel, label="Remove Selected")
        remove_btn.SetBackgroundColour(wx.Colour(255, 107, 107))
        remove_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        remove_btn.Bind(wx.EVT_BUTTON, self.on_remove_puny2uni_files)
        list_btn_sizer.Add(remove_btn, 0, wx.ALL, 5)
        
        clear_btn = wx.Button(panel, label="Clear All")
        clear_btn.SetBackgroundColour(wx.Colour(255, 140, 0))
        clear_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear_puny2uni_files)
        list_btn_sizer.Add(clear_btn, 0, wx.ALL, 5)
        
        list_box.Add(list_btn_sizer, 0, wx.EXPAND)
        
        self.puny2uni_listbox = wx.ListBox(panel, style=wx.LB_MULTIPLE | wx.LB_NEEDED_SB)
        list_box.Add(self.puny2uni_listbox, 1, wx.EXPAND | wx.ALL, 5)
        
        sizer.Add(list_box, 1, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "Puny to Unicode")
    
    def create_pagemaker_tab(self):
        # Use ScrolledPanel for automatic scrolling
        panel = scrolled.ScrolledPanel(self.notebook)
        panel.SetupScrolling(scroll_x=False, scroll_y=True)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Info section
        info_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Generate HTML Portfolio Page")
        info_text = wx.StaticText(panel, label="Select CSV files (Namebase or Shakestation) to generate portfolio page:")
        info_box.Add(info_text, 0, wx.ALL, 5)
        
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        select_files_btn = wx.Button(panel, label="Select CSV Files")
        select_files_btn.Bind(wx.EVT_BUTTON, self.on_select_pagemaker_files)
        btn_sizer.Add(select_files_btn, 0, wx.ALL, 5)
        
        select_folder_btn = wx.Button(panel, label="Select Folder (Recursive)")
        select_folder_btn.Bind(wx.EVT_BUTTON, self.on_select_pagemaker_folder)
        btn_sizer.Add(select_folder_btn, 0, wx.ALL, 5)
        
        self.recursive_pagemaker_var = wx.CheckBox(panel, label="Recursive Search")
        btn_sizer.Add(self.recursive_pagemaker_var, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        info_box.Add(btn_sizer, 0, wx.EXPAND)
        sizer.Add(info_box, 0, wx.EXPAND | wx.ALL, 10)
        
        # File list section
        list_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Selected CSV Files")
        
        list_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        select_all_btn = wx.Button(panel, label="Select All")
        select_all_btn.Bind(wx.EVT_BUTTON, lambda e: self.pagemaker_listbox.SetSelection(wx.NOT_FOUND))
        list_btn_sizer.Add(select_all_btn, 0, wx.ALL, 5)
        
        select_none_btn = wx.Button(panel, label="Select None")
        select_none_btn.Bind(wx.EVT_BUTTON, lambda e: self.pagemaker_listbox.DeselectAll())
        list_btn_sizer.Add(select_none_btn, 0, wx.ALL, 5)
        
        remove_btn = wx.Button(panel, label="Remove Selected")
        remove_btn.SetBackgroundColour(wx.Colour(255, 107, 107))
        remove_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        remove_btn.Bind(wx.EVT_BUTTON, self.on_remove_pagemaker_files)
        list_btn_sizer.Add(remove_btn, 0, wx.ALL, 5)
        
        clear_btn = wx.Button(panel, label="Clear All")
        clear_btn.SetBackgroundColour(wx.Colour(255, 140, 0))
        clear_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear_pagemaker_files)
        list_btn_sizer.Add(clear_btn, 0, wx.ALL, 5)
        
        list_box.Add(list_btn_sizer, 0, wx.EXPAND)
        
        self.pagemaker_listbox = wx.ListBox(panel, style=wx.LB_MULTIPLE | wx.LB_NEEDED_SB, size=(-1, 150))
        list_box.Add(self.pagemaker_listbox, 0, wx.EXPAND | wx.ALL, 5)
        
        sizer.Add(list_box, 0, wx.EXPAND | wx.ALL, 10)
        
        # Sort section
        sort_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sort_btn = wx.Button(panel, label="Sort TLDs")
        sort_btn.Bind(wx.EVT_BUTTON, self.on_cycle_sort)
        sort_sizer.Add(sort_btn, 0, wx.ALL, 5)
        
        self.sort_label = wx.StaticText(panel, label="Current: Random")
        sort_sizer.Add(self.sort_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        sizer.Add(sort_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        
        # Theme section
        theme_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Theme Settings")
        
        theme_row1 = wx.BoxSizer(wx.HORIZONTAL)
        theme_label = wx.StaticText(panel, label="Theme:")
        theme_row1.Add(theme_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.theme_var = wx.Choice(panel, choices=["dark+light", "3-way switch", "custom CSS"])
        self.theme_var.SetSelection(0)
        self.theme_var.Bind(wx.EVT_CHOICE, self.on_theme_change)
        theme_row1.Add(self.theme_var, 0, wx.ALL, 5)
        
        css_btn = wx.Button(panel, label="Select CSS File")
        css_btn.Bind(wx.EVT_BUTTON, self.on_select_css)
        theme_row1.Add(css_btn, 0, wx.ALL, 5)
        
        self.css_label = wx.StaticText(panel, label="No CSS file selected")
        theme_row1.Add(self.css_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        theme_box.Add(theme_row1, 0, wx.EXPAND)
        
        # Color picker row (initially hidden)
        self.color_picker_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        light_label = wx.StaticText(panel, label="Light color:")
        self.color_picker_sizer.Add(light_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.light_color_entry = wx.TextCtrl(panel, value="#ccffff", size=(80, -1))
        self.color_picker_sizer.Add(self.light_color_entry, 0, wx.ALL, 2)
        
        light_pick_btn = wx.Button(panel, label="Pick")
        light_pick_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_pick_color('light'))
        self.color_picker_sizer.Add(light_pick_btn, 0, wx.ALL, 2)
        
        dark_label = wx.StaticText(panel, label="Dark color:")
        self.color_picker_sizer.Add(dark_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.dark_color_entry = wx.TextCtrl(panel, value="#003366", size=(80, -1))
        self.color_picker_sizer.Add(self.dark_color_entry, 0, wx.ALL, 2)
        
        dark_pick_btn = wx.Button(panel, label="Pick")
        dark_pick_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_pick_color('dark'))
        self.color_picker_sizer.Add(dark_pick_btn, 0, wx.ALL, 2)
        
        theme_box.Add(self.color_picker_sizer, 0, wx.EXPAND)
        self.color_picker_sizer.ShowItems(False)  # Hide initially
        
        sizer.Add(theme_box, 0, wx.EXPAND | wx.ALL, 10)
        
        self.custom_css_file = None
        
        # Footer & Credits section
        footer_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Footer & Credits (Optional)")
        
        footer_row = wx.BoxSizer(wx.HORIZONTAL)
        footer_btn = wx.Button(panel, label="Select Footer HTML")
        footer_btn.Bind(wx.EVT_BUTTON, self.on_select_footer)
        footer_row.Add(footer_btn, 0, wx.ALL, 5)
        
        self.footer_label = wx.StaticText(panel, label="No footer file selected", size=(250, -1))
        footer_row.Add(self.footer_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        footer_remove_btn = wx.Button(panel, label="Remove")
        footer_remove_btn.SetBackgroundColour(wx.Colour(255, 107, 107))
        footer_remove_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        footer_remove_btn.Bind(wx.EVT_BUTTON, self.on_remove_footer)
        footer_row.Add(footer_remove_btn, 0, wx.ALL, 5)
        
        footer_box.Add(footer_row, 0, wx.EXPAND)
        
        credits_row = wx.BoxSizer(wx.HORIZONTAL)
        credits_btn = wx.Button(panel, label="Select Credits HTML")
        credits_btn.Bind(wx.EVT_BUTTON, self.on_select_credits)
        credits_row.Add(credits_btn, 0, wx.ALL, 5)
        
        self.credits_label = wx.StaticText(panel, label="No credits file selected", size=(250, -1))
        credits_row.Add(self.credits_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        credits_remove_btn = wx.Button(panel, label="Remove")
        credits_remove_btn.SetBackgroundColour(wx.Colour(255, 107, 107))
        credits_remove_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        credits_remove_btn.Bind(wx.EVT_BUTTON, self.on_remove_credits)
        credits_row.Add(credits_remove_btn, 0, wx.ALL, 5)
        
        footer_box.Add(credits_row, 0, wx.EXPAND)
        
        sizer.Add(footer_box, 0, wx.EXPAND | wx.ALL, 10)
        
        self.footer_file = None
        self.credits_file = None
        
        # Update existing page section
        update_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Update Existing Page")
        
        update_row = wx.BoxSizer(wx.HORIZONTAL)
        update_btn = wx.Button(panel, label="Select HTML File")
        update_btn.Bind(wx.EVT_BUTTON, self.on_select_html_to_update)
        update_row.Add(update_btn, 0, wx.ALL, 5)
        
        self.html_update_label = wx.StaticText(panel, label="No HTML file selected", size=(250, -1))
        update_row.Add(self.html_update_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        update_remove_btn = wx.Button(panel, label="Remove")
        update_remove_btn.SetBackgroundColour(wx.Colour(255, 107, 107))
        update_remove_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        update_remove_btn.Bind(wx.EVT_BUTTON, self.on_remove_html_to_update)
        update_row.Add(update_remove_btn, 0, wx.ALL, 5)
        
        update_box.Add(update_row, 0, wx.EXPAND)
        
        sizer.Add(update_box, 0, wx.EXPAND | wx.ALL, 10)
        
        self.html_to_update = None
        
        # Output section
        output_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Output")
        
        output_row = wx.BoxSizer(wx.HORIZONTAL)
        output_btn = wx.Button(panel, label="Select Output File")
        output_btn.Bind(wx.EVT_BUTTON, self.on_select_output_file)
        output_row.Add(output_btn, 0, wx.ALL, 5)
        
        self.output_filename_entry = wx.TextCtrl(panel, value="portfolio.html", size=(300, -1))
        output_row.Add(self.output_filename_entry, 1, wx.ALL | wx.EXPAND, 5)
        
        output_box.Add(output_row, 0, wx.EXPAND)
        
        sizer.Add(output_box, 0, wx.EXPAND | wx.ALL, 10)
        
        # Display options section
        display_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Display Options")
        
        self.list_all_var = wx.CheckBox(panel, label="List all domains (ignore email/price requirement for bob/fw)")
        display_box.Add(self.list_all_var, 0, wx.ALL, 5)
        
        email_row = wx.BoxSizer(wx.HORIZONTAL)
        email_label = wx.StaticText(panel, label="Auto-append email for domains with price (leave empty to skip):")
        email_row.Add(email_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.auto_email_entry = wx.TextCtrl(panel, size=(250, -1))
        email_row.Add(self.auto_email_entry, 0, wx.ALL, 5)
        
        email_hint = wx.StaticText(panel, label="Format: user@gmail.com or user+@gmail.com")
        email_hint.SetForegroundColour(wx.Colour(128, 128, 128))
        email_row.Add(email_hint, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        display_box.Add(email_row, 0, wx.EXPAND)
        
        sizer.Add(display_box, 0, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(sizer)
        self.notebook.AddPage(panel, "PageMaker")
    
    # Event handlers
    def on_select_punytag_files(self, event):
        wildcard = "CSV files (*.csv)|*.csv|All files (*.*)|*.*"
        dlg = wx.FileDialog(self, "Select CSV Files", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE)
        if dlg.ShowModal() == wx.ID_OK:
            paths = dlg.GetPaths()
            self.add_files_to_list(paths)
        dlg.Destroy()
    
    def on_select_punytag_folder(self, event):
        dlg = wx.DirDialog(self, "Select Folder")
        if dlg.ShowModal() == wx.ID_OK:
            folder = dlg.GetPath()
            files = []
            if self.recursive_var.GetValue():
                for root, dirs, filenames in os.walk(folder):
                    for filename in filenames:
                        if filename.endswith('.csv'):
                            files.append(os.path.join(root, filename))
            else:
                files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.csv')]
            self.add_files_to_list(files)
        dlg.Destroy()
    
    def add_files_to_list(self, files):
        for file in files:
            if file not in [f['path'] for f in self.file_data]:
                source_type = self.detect_csv_source(file)
                self.file_data.append({'path': file, 'source': source_type, 'selected': True})
                display_text = f"[{source_type}] {os.path.basename(file)}"
                self.file_listbox.Append(display_text)
    
    def on_remove_punytag_files(self, event):
        selections = list(self.file_listbox.GetSelections())
        selections.reverse()
        for idx in selections:
            self.file_listbox.Delete(idx)
            del self.file_data[idx]
    
    def on_clear_punytag_files(self, event):
        self.file_listbox.Clear()
        self.file_data = []
    
    def on_select_puny2uni_files(self, event):
        wildcard = "Text files (*.txt)|*.txt|All files (*.*)|*.*"
        dlg = wx.FileDialog(self, "Select TXT Files", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE)
        if dlg.ShowModal() == wx.ID_OK:
            paths = dlg.GetPaths()
            for file in paths:
                if file not in self.puny2uni_files:
                    self.puny2uni_files.append(file)
                    self.puny2uni_listbox.Append(os.path.basename(file))
        dlg.Destroy()
    
    def on_select_puny2uni_folder(self, event):
        dlg = wx.DirDialog(self, "Select Folder")
        if dlg.ShowModal() == wx.ID_OK:
            folder = dlg.GetPath()
            files = []
            if self.recursive_puny2uni_var.GetValue():
                for root, dirs, filenames in os.walk(folder):
                    for filename in filenames:
                        if filename.endswith('.txt'):
                            files.append(os.path.join(root, filename))
            else:
                files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.txt')]
            for file in files:
                if file not in self.puny2uni_files:
                    self.puny2uni_files.append(file)
                    self.puny2uni_listbox.Append(os.path.basename(file))
        dlg.Destroy()
    
    def on_remove_puny2uni_files(self, event):
        selections = list(self.puny2uni_listbox.GetSelections())
        selections.reverse()
        for idx in selections:
            self.puny2uni_listbox.Delete(idx)
            del self.puny2uni_files[idx]
    
    def on_clear_puny2uni_files(self, event):
        self.puny2uni_listbox.Clear()
        self.puny2uni_files = []
    
    def on_select_pagemaker_files(self, event):
        wildcard = "CSV files (*.csv)|*.csv|All files (*.*)|*.*"
        dlg = wx.FileDialog(self, "Select CSV Files", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE)
        if dlg.ShowModal() == wx.ID_OK:
            paths = dlg.GetPaths()
            for file in paths:
                if file not in self.pagemaker_files:
                    self.pagemaker_files.append(file)
                    self.pagemaker_listbox.Append(os.path.basename(file))
        dlg.Destroy()
    
    def on_select_pagemaker_folder(self, event):
        dlg = wx.DirDialog(self, "Select Folder")
        if dlg.ShowModal() == wx.ID_OK:
            folder = dlg.GetPath()
            files = []
            if self.recursive_pagemaker_var.GetValue():
                for root, dirs, filenames in os.walk(folder):
                    for filename in filenames:
                        if filename.endswith('.csv'):
                            files.append(os.path.join(root, filename))
            else:
                files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.csv')]
            for file in files:
                if file not in self.pagemaker_files:
                    self.pagemaker_files.append(file)
                    self.pagemaker_listbox.Append(os.path.basename(file))
        dlg.Destroy()
    
    def on_remove_pagemaker_files(self, event):
        selections = list(self.pagemaker_listbox.GetSelections())
        selections.reverse()
        for idx in selections:
            self.pagemaker_listbox.Delete(idx)
            del self.pagemaker_files[idx]
    
    def on_clear_pagemaker_files(self, event):
        self.pagemaker_listbox.Clear()
        self.pagemaker_files = []
    
    def on_cycle_sort(self, event):
        sort_states = ["Random", "Alphabetical ▲", "Alphabetical ▼", "Price ▲", "Price ▼"]
        self.sort_state = (self.sort_state + 1) % 5
        self.sort_label.SetLabel(f"Current: {sort_states[self.sort_state]}")
    
    def on_theme_change(self, event):
        theme = self.theme_var.GetStringSelection()
        if theme == "3-way switch":
            self.color_picker_sizer.ShowItems(True)
        else:
            self.color_picker_sizer.ShowItems(False)
        self.notebook.GetCurrentPage().Layout()
    
    def on_pick_color(self, color_type):
        if color_type == 'light':
            current = self.light_color_entry.GetValue()
        else:
            current = self.dark_color_entry.GetValue()
        
        data = wx.ColourData()
        data.SetChooseFull(True)
        
        dlg = wx.ColourDialog(self, data)
        if dlg.ShowModal() == wx.ID_OK:
            color = dlg.GetColourData().GetColour()
            hex_color = '#%02x%02x%02x' % (color.Red(), color.Green(), color.Blue())
            if color_type == 'light':
                self.light_color_entry.SetValue(hex_color)
            else:
                self.dark_color_entry.SetValue(hex_color)
        dlg.Destroy()
    
    def on_select_css(self, event):
        wildcard = "CSS files (*.css)|*.css|All files (*.*)|*.*"
        dlg = wx.FileDialog(self, "Select Custom CSS", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.custom_css_file = dlg.GetPath()
            self.css_label.SetLabel(os.path.basename(self.custom_css_file))
        dlg.Destroy()
    
    def on_select_footer(self, event):
        wildcard = "HTML files (*.html)|*.html|All files (*.*)|*.*"
        dlg = wx.FileDialog(self, "Select Footer HTML", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.footer_file = dlg.GetPath()
            self.footer_label.SetLabel(os.path.basename(self.footer_file))
        dlg.Destroy()
    
    def on_remove_footer(self, event):
        self.footer_file = None
        self.footer_label.SetLabel("No footer file selected")
    
    def on_select_credits(self, event):
        wildcard = "HTML files (*.html)|*.html|All files (*.*)|*.*"
        dlg = wx.FileDialog(self, "Select Credits HTML", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.credits_file = dlg.GetPath()
            self.credits_label.SetLabel(os.path.basename(self.credits_file))
        dlg.Destroy()
    
    def on_remove_credits(self, event):
        self.credits_file = None
        self.credits_label.SetLabel("No credits file selected")
    
    def on_select_html_to_update(self, event):
        wildcard = "HTML files (*.html)|*.html|All files (*.*)|*.*"
        dlg = wx.FileDialog(self, "Select HTML to Update", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.html_to_update = dlg.GetPath()
            self.html_update_label.SetLabel(os.path.basename(self.html_to_update))
        dlg.Destroy()
    
    def on_remove_html_to_update(self, event):
        self.html_to_update = None
        self.html_update_label.SetLabel("No HTML file selected")
    
    def on_select_output_file(self, event):
        wildcard = "HTML files (*.html)|*.html|All files (*.*)|*.*"
        dlg = wx.FileDialog(self, "Select Output File", defaultFile="portfolio.html", wildcard=wildcard, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            self.output_filename_entry.SetValue(dlg.GetPath())
        dlg.Destroy()
    
    def on_help(self, event):
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
        dlg = wx.MessageDialog(self, help_text, "Help - How to Use HNSell", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
    
    def on_process(self, event):
        current_tab = self.notebook.GetSelection()
        
        if current_tab == 0:
            self.process_punytag()
        elif current_tab == 1:
            self.process_puny2uni()
        elif current_tab == 2:
            self.process_pagemaker()
    
    def on_exit(self, event):
        self.Close()
    
    # Processing methods (importing from original hnsell.py logic)
    def detect_csv_source(self, filepath):
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
    
    def process_punytag(self):
        wx.MessageBox("Punytag processing will be implemented with full logic from hnsell.py", "Info", wx.OK | wx.ICON_INFORMATION)
    
    def process_puny2uni(self):
        wx.MessageBox("Puny2Uni processing will be implemented with full logic from hnsell.py", "Info", wx.OK | wx.ICON_INFORMATION)
    
    def process_pagemaker(self):
        wx.MessageBox("PageMaker processing will be implemented with full logic from hnsell.py", "Info", wx.OK | wx.ICON_INFORMATION)

if __name__ == '__main__':
    app = wx.App()
    frame = HNSellFrame()
    app.MainLoop()
