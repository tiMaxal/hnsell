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
import logging
import traceback

# Translation library (install: pip install deep-translator)
try:
    from deep_translator import GoogleTranslator
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    print("Warning: deep-translator not installed. Translation features disabled.")
    print("Install with: pip install deep-translator")

class HNSellFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='HNSell - Handshake Domain Manager', size=(1000, 900))
        
        # Setup logging
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hnsell_processing.log')
        logging.basicConfig(
            filename=log_file,
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logging.info('='*60)
        logging.info('HNSell started')
        
        # Initialize translator
        self.translator = None
        if TRANSLATION_AVAILABLE:
            self.translator = GoogleTranslator(source='auto', target='en')
        
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
        
        # File list section with splitter for resizing
        list_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Selected Files")
        
        list_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        select_all_btn = wx.Button(panel, label="Select All")
        select_all_btn.Bind(wx.EVT_BUTTON, lambda e: [self.file_listbox.Select(i) for i in range(self.file_listbox.GetCount())])
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
        
        # Respect existing entries option
        self.respect_existing_var = wx.CheckBox(panel, label="Respect existing entries (skip domains with descript/translate values)")
        self.respect_existing_var.SetValue(True)
        options_box.Add(self.respect_existing_var, 0, wx.ALL, 5)
        
        help_label = wx.StaticText(panel, label="ℹ Uncheck to override and re-process all domains (useful for re-translation)")
        help_label.SetForegroundColour(wx.Colour(128, 128, 128))
        options_box.Add(help_label, 0, wx.ALL | wx.LEFT, 20)
        
        # Translation option
        translation_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.enable_translation_var = wx.CheckBox(panel, label="Enable translations (PUNY_IDNA only)")
        translation_sizer.Add(self.enable_translation_var, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        if not TRANSLATION_AVAILABLE:
            self.enable_translation_var.Enable(False)
            warning_text = wx.StaticText(panel, label="⚠ Install deep-translator")
            warning_text.SetForegroundColour(wx.Colour(255, 140, 0))
            translation_sizer.Add(warning_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        target_label = wx.StaticText(panel, label="Target:")
        translation_sizer.Add(target_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.target_lang_var = wx.TextCtrl(panel, value="en", size=(50, -1))
        translation_sizer.Add(self.target_lang_var, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        
        help_text = wx.StaticText(panel, label="(en, es, fr, de, ja, zh-CN, etc.)")
        help_text.SetForegroundColour(wx.Colour(128, 128, 128))
        translation_sizer.Add(help_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        
        options_box.Add(translation_sizer, 0, wx.EXPAND)
        
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
        select_all_btn.Bind(wx.EVT_BUTTON, lambda e: [self.puny2uni_listbox.Select(i) for i in range(self.puny2uni_listbox.GetCount())])
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
        # Use ScrolledPanel with better settings
        panel = scrolled.ScrolledPanel(self.notebook, style=wx.TAB_TRAVERSAL)
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
        
        # File list section - RESIZABLE
        list_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Selected CSV Files")
        
        list_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        select_all_btn = wx.Button(panel, label="Select All")
        select_all_btn.Bind(wx.EVT_BUTTON, lambda e: [self.pagemaker_listbox.Select(i) for i in range(self.pagemaker_listbox.GetCount())])
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
        
        # Make listbox resizable with min height
        self.pagemaker_listbox = wx.ListBox(panel, style=wx.LB_MULTIPLE | wx.LB_NEEDED_SB, size=(-1, 200))
        list_box.Add(self.pagemaker_listbox, 1, wx.EXPAND | wx.ALL, 5)
        
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
        
        self.include_descriptions_var = wx.CheckBox(panel, label="Include descriptions/translations (on-page grid/list toggle)")
        display_box.Add(self.include_descriptions_var, 0, wx.ALL, 5)
        
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
        # Setup scrolling with rate limits - key for smooth scrolling!
        panel.SetupScrolling(scroll_x=False, scroll_y=True, rate_x=20, rate_y=20)
        
        self.notebook.AddPage(panel, "PageMaker")
    
    # Event handlers for file selection
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
        # Force layout update for scrolled panel
        page = self.notebook.GetCurrentPage()
        page.Layout()
        if hasattr(page, 'SetupScrolling'):
            page.SetupScrolling(scroll_x=False, scroll_y=True, rate_x=20, rate_y=20)
    
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

TAB 2: PUNY ⟷ UNICODE
- Converts between punycode and unicode formats
- Supports .txt files with one domain per line

TAB 3: PAGEMAKER
- Generates HTML portfolio pages from domain CSV files
- PageMaker tab scrolls automatically - use mouse wheel!
- File selection listbox is resizable

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
    
    # CSV source detection
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
    
    # Helper methods for processing
    def should_skip_row(self, row, df):
        """Check if row should be skipped based on respect_existing setting"""
        if not self.respect_existing_var.GetValue():
            return False  # Override mode - process everything
        
        # Check for existing descript-IDNA or description
        if 'descript-IDNA' in df.columns:
            val = str(row.get('descript-IDNA', '')).strip()
            if val and val.lower() not in ['', 'nan']:
                return True
        
        if 'description' in df.columns:
            val = str(row.get('description', '')).strip()
            if val and val.lower() not in ['', 'nan']:
                return True
        
        # Check for existing translate-IDNA (only if translation is enabled)
        if self.enable_translation_var.GetValue() and 'translate-IDNA' in df.columns:
            val = str(row.get('translate-IDNA', '')).strip()
            if val and val.lower() not in ['', 'nan']:
                return True
        
        return False
    
    def is_emoji(self, char):
        try:
            char_name = unicodedata.name(char, '')
            return any(keyword in char_name for keyword in ['EMOJI', 'FACE', 'HEART', 'STAR', 'SYMBOL'])
        except:
            return False
    
    def get_char_description(self, char):
        try:
            return unicodedata.name(char, char)
        except:
            return char
    
    def detect_language(self, text):
        if not text:
            return None
        
        hawaiian_vowels = {'ā', 'ē', 'ī', 'ō', 'ū', 'Ā', 'Ē', 'Ī', 'Ō', 'Ū'}
        if any(char in hawaiian_vowels for char in text):
            latin_chars = sum(1 for c in text if c.isalpha() and ord(c) < 0x0180)
            if latin_chars > len(text) * 0.5:
                return 'Hawaiian'
        
        for char in text:
            if char.isspace():
                continue
            code_point = ord(char)
            
            if 0x4E00 <= code_point <= 0x9FFF:
                return 'Chinese/Japanese/Korean'
            elif 0x3040 <= code_point <= 0x309F or 0x30A0 <= code_point <= 0x30FF:
                return 'Japanese'
            elif 0x0600 <= code_point <= 0x06FF:
                return 'Arabic/Urdu/Uyghur'
            elif 0x0590 <= code_point <= 0x05FF:
                return 'Hebrew'
            elif 0x0400 <= code_point <= 0x04FF:
                return 'Cyrillic (Russian/Ukrainian)'
            elif 0x0370 <= code_point <= 0x03FF:
                return 'Greek'
            elif 0x0E00 <= code_point <= 0x0E7F:
                return 'Thai'
            elif 0x0900 <= code_point <= 0x097F:
                return 'Devanagari (Hindi)'
            elif 0x0B80 <= code_point <= 0x0BFF:
                return 'Tamil'
            elif 0x0D00 <= code_point <= 0x0D7F:
                return 'Malayalam'
            elif 0x10A0 <= code_point <= 0x10FF:
                return 'Georgian'
            elif 0x0530 <= code_point <= 0x058F:
                return 'Armenian'
            elif 0x0100 <= code_point <= 0x017F or 0x0180 <= code_point <= 0x024F:
                return 'European (Latin Extended)'
        
        return None
    
    def generate_description(self, unicode_str, tag):
        if tag != 'PUNY_IDNA' or not unicode_str:
            return ''
        
        is_all_emoji = all(self.is_emoji(c) or c.isspace() for c in unicode_str if not c.isalnum())
        has_emoji = any(self.is_emoji(c) for c in unicode_str)
        
        if is_all_emoji and has_emoji:
            names = []
            for char in unicode_str:
                if not char.isspace():
                    names.append(self.get_char_description(char))
            return ' + '.join(names)
        
        lang = self.detect_language(unicode_str)
        if lang:
            return lang
        
        if has_emoji or any(ord(c) > 127 for c in unicode_str):
            char_names = []
            for char in unicode_str:
                if ord(char) > 127 and not char.isspace():
                    char_names.append(self.get_char_description(char))
            if char_names:
                return f"Letters + {', '.join(char_names)}"
        
        return unicode_str
    
    def get_language_tag(self, unicode_str):
        if not unicode_str:
            return ''
        
        lang = self.detect_language(unicode_str)
        if not lang:
            return ''
        
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
    
    def translate_text(self, text, target_lang='en'):
        """Translate text to target language using Google Translate"""
        if not TRANSLATION_AVAILABLE or not self.translator:
            return ''
        
        try:
            # Skip translation if already in English or empty
            if not text or text.isascii():
                return ''
            
            # Update target language
            self.translator.target = target_lang
            translated = self.translator.translate(text)
            return translated if translated else ''
        except Exception:
            # Silently fail - translation is optional
            return ''
    
    def add_categorization_tags(self, df, domain_col):
        def is_pure_alpha(s):
            return str(s).isalpha()
        
        def get_display_length(domain, unicode_col):
            """Get display length - uses unicode for punycode domains"""
            if str(domain).startswith('xn--') and 'unicode' in df.columns:
                unicode_val = df.loc[df[domain_col] == domain, 'unicode'].iloc[0] if not df[df[domain_col] == domain].empty else ''
                if unicode_val and str(unicode_val).lower() not in ['nan', '']:
                    return len(str(unicode_val))
            return len(str(domain))
        
        # For punycode domains, check unicode length; for others, use domain length
        df['1D'] = df[domain_col].apply(lambda x: 1 if str(x).isdigit() and len(str(x)) == 1 else '')
        df['1L'] = df[domain_col].apply(lambda x: 1 if is_pure_alpha(x) and len(str(x)) == 1 else '')
        # 1C: single char (including emoji/unicode via punycode)
        df['1C'] = df.apply(lambda row: 1 if (len(str(row[domain_col])) == 1 or (str(row[domain_col]).startswith('xn--') and row.get('unicode') and len(str(row.get('unicode', ''))) == 1)) and not row.get('1L') and not row.get('1D') else '', axis=1)
        
        df['2D'] = df[domain_col].apply(lambda x: 1 if str(x).isdigit() and len(str(x)) == 2 else '')
        df['2L'] = df[domain_col].apply(lambda x: 1 if is_pure_alpha(x) and len(str(x)) == 2 else '')
        # 2C: two chars (including emoji/unicode via punycode)
        df['2C'] = df.apply(lambda row: 1 if (len(str(row[domain_col])) == 2 or (str(row[domain_col]).startswith('xn--') and row.get('unicode') and len(str(row.get('unicode', ''))) == 2)) and not row.get('2L') and not row.get('2D') else '', axis=1)
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
    
    def unicode_to_punycode(self, unicode_string):
        try:
            punycode_encoder = codecs.getencoder('punycode')
            punycode_string, _ = punycode_encoder(unicode_string)
            return f"xn--{punycode_string.decode('ascii')}"
        except:
            return unicode_string
    
    # Processing methods - FULL IMPLEMENTATION
    def process_punytag(self):
        # Validate selection
        if not self.file_listbox.GetSelections():
            wx.MessageBox("Please select files to process", "No Selection", wx.OK | wx.ICON_WARNING)
            return
        
        logging.info('Starting punytag processing')
        date_suffix = datetime.now().strftime("%Y%m%d")
        processed_count = 0
        skipped_count = 0
        
        selections = self.file_listbox.GetSelections()
        for idx in selections:
            file_info = self.file_data[idx]
            filepath = file_info['path']
            source_type = file_info['source']
            logging.info(f'Processing file: {os.path.basename(filepath)} (type: {source_type})')
            
            file_dir = os.path.dirname(filepath)
            file_name = os.path.basename(filepath)
            file_base, file_ext = os.path.splitext(file_name)
            
            # Skip if already marked as original
            if '_orig' in file_base:
                skipped_count += 1
                continue
            
            # Check if already processed
            if re.search(r'_\d{8}$', file_base):
                skipped_count += 1
                continue
            
            output_name = f"{file_base}_{date_suffix}{file_ext}"
            output_path = os.path.join(file_dir, output_name)
            
            # Skip if output already exists
            if os.path.exists(output_path):
                skipped_count += 1
                continue
            
            try:
                # Process based on source type
                logging.info(f'  Starting {source_type} processing: {output_name}')
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
                    logging.warning(f'  Unknown source type: {source_type}')
                    wx.MessageBox(f"Processing for {source_type} not yet fully implemented", "Info", wx.OK | wx.ICON_INFORMATION)
                    continue
                
                if self.rename_orig_var.GetValue():
                    orig_name = f"{file_base}_orig{file_ext}"
                    orig_path = os.path.join(file_dir, orig_name)
                    os.rename(filepath, orig_path)
                
                if self.delete_orig_var.GetValue():
                    orig_path = os.path.join(file_dir, f"{file_base}_orig{file_ext}")
                    if os.path.exists(orig_path):
                        os.remove(orig_path)
                
                logging.info(f'  Successfully processed: {output_name}')
                processed_count += 1
            
            except Exception as e:
                error_trace = traceback.format_exc()
                logging.error(f'ERROR processing {file_name}:')
                logging.error(f'  Error type: {type(e).__name__}')
                logging.error(f'  Error message: {str(e)}')
                logging.error(f'  Full traceback:\n{error_trace}')
                wx.MessageBox(f"Error processing {file_name}:\n{str(e)}\n\nSee hnsell_processing.log for details", "Error", wx.OK | wx.ICON_ERROR)
        
        logging.info(f'Punytag processing complete: {processed_count} processed, {skipped_count} skipped')
        logging.info('='*60)
        
        result_msg = f"Processed {processed_count} file(s)"
        if skipped_count > 0:
            result_msg += f"\nSkipped {skipped_count} file(s) (already processed or marked as original)"
        result_msg += f"\n\nLog file: hnsell_processing.log"
        wx.MessageBox(result_msg, "Complete", wx.OK | wx.ICON_INFORMATION)
    
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
        
        df = self.add_categorization_tags(df, 'extra.domain')
        
        df['PUNY_INVALID'] = [1 if (info[0] != df.at[i, 'unicode']) or (info[0] and df.at[i, 'unicode'] == df.at[i, 'extra.domain']) else '' for i, info in enumerate(punycode_info)]
        df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
        df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
        df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
        
        df['LANG_TAG'] = [self.get_language_tag(df.at[i, 'unicode']) for i in range(len(df))]
        
        tags_columns = ['3D', '3L', '3C', '4D', '4L', '4C', '5D', '5L', '5C', '6D', '7D', 'PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
        df['tags'] = df.apply(lambda row: ','.join(filter(None, [tag if row.get(tag) == 1 else '' for tag in tags_columns] + [row.get('LANG_TAG', '')])), axis=1)
        df.drop(columns=tags_columns + ['LANG_TAG'], inplace=True)
        
        # Add descript-IDNA and translate-IDNA columns with respect_existing logic
        respect_existing = self.respect_existing_var.GetValue()
        enable_translation = self.enable_translation_var.GetValue() and TRANSLATION_AVAILABLE
        target_lang = self.target_lang_var.GetValue()
        
        descript_list = []
        translate_list = []
        skipped_count = 0
        
        for i, info in enumerate(punycode_info):
            if respect_existing and self.should_skip_row(df.iloc[i], df):
                skipped_count += 1
                existing_descript = str(df.at[i, 'descript-IDNA']).strip() if 'descript-IDNA' in df.columns else ''
                existing_translate = str(df.at[i, 'translate-IDNA']).strip() if 'translate-IDNA' in df.columns else ''
                descript_list.append(existing_descript if existing_descript.lower() != 'nan' else '')
                translate_list.append(existing_translate if existing_translate.lower() != 'nan' else '')
            else:
                descript_list.append(self.generate_description(df.at[i, 'unicode'], info[1]))
                if enable_translation and info[1] == 'PUNY_IDNA' and df.at[i, 'unicode']:
                    translation = self.translate_text(df.at[i, 'unicode'], target_lang)
                    translate_list.append(translation if translation else '')
                else:
                    translate_list.append('')
        
        df['descript-IDNA'] = descript_list
        df['translate-IDNA'] = translate_list
        
        if skipped_count > 0:
            print(f"ℹ Skipped {skipped_count} domains (already have descript/translate values)")
        
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
        
        df = self.add_categorization_tags(df, domain_col)
        
        df['PUNY_INVALID'] = [1 if (info[0] != df.at[i, 'unicode']) or (info[0] and df.at[i, 'unicode'] == df.at[i, domain_col]) else '' for i, info in enumerate(punycode_info)]
        df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
        df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
        df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
        
        df['LANG_TAG'] = [self.get_language_tag(df.at[i, 'unicode']) for i in range(len(df))]
        
        tags_columns = ['3D', '3L', '3C', '4D', '4L', '4C', '5D', '5L', '5C', '6D', '7D', 'PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
        df['tags'] = df.apply(lambda row: ','.join(filter(None, [tag if row.get(tag) == 1 else '' for tag in tags_columns] + [row.get('LANG_TAG', '')])), axis=1)
        df.drop(columns=tags_columns + ['LANG_TAG'], inplace=True)
        
        # Add descript-IDNA and translate-IDNA columns with respect_existing logic
        respect_existing = self.respect_existing_var.GetValue()
        enable_translation = self.enable_translation_var.GetValue() and TRANSLATION_AVAILABLE
        target_lang = self.target_lang_var.GetValue()
        
        descript_list = []
        translate_list = []
        skipped_count = 0
        
        for i, info in enumerate(punycode_info):
            if respect_existing and self.should_skip_row(df.iloc[i], df):
                skipped_count += 1
                existing_descript = str(df.at[i, 'descript-IDNA']).strip() if 'descript-IDNA' in df.columns else ''
                existing_translate = str(df.at[i, 'translate-IDNA']).strip() if 'translate-IDNA' in df.columns else ''
                descript_list.append(existing_descript if existing_descript.lower() != 'nan' else '')
                translate_list.append(existing_translate if existing_translate.lower() != 'nan' else '')
            else:
                descript_list.append(self.generate_description(df.at[i, 'unicode'], info[1]))
                if enable_translation and info[1] == 'PUNY_IDNA' and df.at[i, 'unicode']:
                    translation = self.translate_text(df.at[i, 'unicode'], target_lang)
                    translate_list.append(translation if translation else '')
                else:
                    translate_list.append('')
        
        df['descript-IDNA'] = descript_list
        df['translate-IDNA'] = translate_list
        
        if skipped_count > 0:
            print(f"ℹ Skipped {skipped_count} domains (already have descript/translate values)")
        
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
            
            df = self.add_categorization_tags(df, name_col)
            
            df['PUNY_INVALID'] = [1 if (info[0] != df.at[i, 'unicode']) or (info[0] and df.at[i, 'unicode'] == df.at[i, name_col]) else '' for i, info in enumerate(punycode_info)]
            df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
            df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
            df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
            
            df['LANG_TAG'] = [self.get_language_tag(df.at[i, 'unicode']) for i in range(len(df))]
            
            tags_columns = ['1D', '1L', '1C', '2D', '2L', '2C', '3D', '3L', '3C', '4D', '4L', '4C', '5D', '5L', '5C', '6D', '7D', 'PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
            new_tag_str = df.apply(lambda row: ','.join(filter(None, [tag if row.get(tag) == 1 else '' for tag in tags_columns] + [row.get('LANG_TAG', '')])), axis=1)
            
            if 'tags' in df.columns:
                existing_tags = df['tags'].fillna('')
                df['tags'] = df.apply(lambda row: ','.join(filter(None, [str(row['tags']), new_tag_str[row.name]])), axis=1)
            else:
                df['tags'] = new_tag_str
            df.drop(columns=tags_columns + ['LANG_TAG'], inplace=True)
            
            # Add descript-IDNA and translate-IDNA columns with respect_existing logic
            respect_existing = self.respect_existing_var.GetValue()
            enable_translation = self.enable_translation_var.GetValue() and TRANSLATION_AVAILABLE
            target_lang = self.target_lang_var.GetValue()
            
            descript_list = []
            translate_list = []
            skipped_count = 0
            
            for i, info in enumerate(punycode_info):
                if respect_existing and self.should_skip_row(df.iloc[i], df):
                    skipped_count += 1
                    existing_descript = str(df.at[i, 'descript-IDNA']).strip() if 'descript-IDNA' in df.columns else ''
                    existing_translate = str(df.at[i, 'translate-IDNA']).strip() if 'translate-IDNA' in df.columns else ''
                    descript_list.append(existing_descript if existing_descript.lower() != 'nan' else '')
                    translate_list.append(existing_translate if existing_translate.lower() != 'nan' else '')
                else:
                    descript_list.append(self.generate_description(df.at[i, 'unicode'], info[1]))
                    if enable_translation and info[1] == 'PUNY_IDNA' and df.at[i, 'unicode']:
                        translation = self.translate_text(df.at[i, 'unicode'], target_lang)
                        translate_list.append(translation if translation else '')
                    else:
                        translate_list.append('')
            
            df['descript-IDNA'] = descript_list
            df['translate-IDNA'] = translate_list
            
            if skipped_count > 0:
                print(f"ℹ Skipped {skipped_count} domains (already have descript/translate values)")
            
            col_order = [name_col, 'unicode', 'descript-IDNA', 'translate-IDNA', 'tags'] + [col for col in df.columns if col not in [name_col, 'unicode', 'descript-IDNA', 'translate-IDNA', 'tags']]
            df = df[col_order]
        
        df.to_csv(output_path, index=False)
    
    def process_bob_tld(self, filepath, output_path):
        df = pd.read_csv(filepath, header=None, names=['domains'])
        
        if 'domains' not in df.columns:
            raise ValueError("No 'domains' column found in Bob TLD CSV")
        
        punycode_info = df['domains'].apply(lambda x: self.punycode_convert_validate(x) if isinstance(x, str) else ('', ''))
        
        # Use iloc with enumerate index, not at with integer
        df['unicode'] = [re.sub(r'(?:\\x[\da-fA-F]{2})+|\\u(?:[\da-fA-F]{4})+', '', info[0]) if info[0] and info[0] != df.iloc[i]['domains'] else '' for i, info in enumerate(punycode_info)]
        
        df = self.add_categorization_tags(df, 'domains')
        
        df['PUNY_INVALID'] = [1 if (info[0] != df.iloc[i]['unicode']) or (info[0] and df.iloc[i]['unicode'] == df.iloc[i]['domains']) else '' for i, info in enumerate(punycode_info)]
        df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
        df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
        df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
        
        df['LANG_TAG'] = [self.get_language_tag(df.iloc[i]['unicode']) for i in range(len(df))]
        
        tags_columns = ['3D', '3L', '3C', '4D', '4L', '4C', '5D', '5L', '5C', '6D', '7D', 'PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
        df['tags'] = df.apply(lambda row: ','.join(filter(None, [tag if row.get(tag) == 1 else '' for tag in tags_columns] + [row.get('LANG_TAG', '')])), axis=1)
        df.drop(columns=tags_columns + ['LANG_TAG'], inplace=True)
        
        # Add descript-IDNA and translate-IDNA columns with respect_existing logic
        respect_existing = self.respect_existing_var.GetValue()
        enable_translation = self.enable_translation_var.GetValue() and TRANSLATION_AVAILABLE
        target_lang = self.target_lang_var.GetValue()
        
        descript_list = []
        translate_list = []
        skipped_count = 0
        
        for i, info in enumerate(punycode_info):
            if respect_existing and self.should_skip_row(df.iloc[i], df):
                skipped_count += 1
                existing_descript = str(df.iloc[i]['descript-IDNA']).strip() if 'descript-IDNA' in df.columns else ''
                existing_translate = str(df.iloc[i]['translate-IDNA']).strip() if 'translate-IDNA' in df.columns else ''
                descript_list.append(existing_descript if existing_descript.lower() != 'nan' else '')
                translate_list.append(existing_translate if existing_translate.lower() != 'nan' else '')
            else:
                descript_list.append(self.generate_description(df.iloc[i]['unicode'], info[1]))
                if enable_translation and info[1] == 'PUNY_IDNA' and df.iloc[i]['unicode']:
                    translation = self.translate_text(df.iloc[i]['unicode'], target_lang)
                    translate_list.append(translation if translation else '')
                else:
                    translate_list.append('')
        
        df['descript-IDNA'] = descript_list
        df['translate-IDNA'] = translate_list
        
        if skipped_count > 0:
            print(f"ℹ Skipped {skipped_count} domains (already have descript/translate values)")
        
        df = df[['domains', 'unicode', 'descript-IDNA', 'translate-IDNA', 'tags']]
        
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
        
        df = self.add_categorization_tags(df, domain_col)
        
        df['PUNY_INVALID'] = [1 if (info[0] != df.at[i, 'unicode']) or (info[0] and df.at[i, 'unicode'] == df.at[i, domain_col]) else '' for i, info in enumerate(punycode_info)]
        df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
        df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
        df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
        
        df['LANG_TAG'] = [self.get_language_tag(df.at[i, 'unicode']) for i in range(len(df))]
        
        tags_columns = ['3D', '3L', '3C', '4D', '4L', '4C', '5D', '5L', '5C', '6D', '7D', 'PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
        df['tags'] = df.apply(lambda row: ','.join(filter(None, [tag if row.get(tag) == 1 else '' for tag in tags_columns] + [row.get('LANG_TAG', '')])), axis=1)
        df.drop(columns=tags_columns + ['LANG_TAG'], inplace=True)
        
        # Add descript-IDNA and translate-IDNA columns with respect_existing logic
        respect_existing = self.respect_existing_var.GetValue()
        enable_translation = self.enable_translation_var.GetValue() and TRANSLATION_AVAILABLE
        target_lang = self.target_lang_var.GetValue()
        
        descript_list = []
        translate_list = []
        skipped_count = 0
        
        for i, info in enumerate(punycode_info):
            if respect_existing and self.should_skip_row(df.iloc[i], df):
                skipped_count += 1
                existing_descript = str(df.at[i, 'descript-IDNA']).strip() if 'descript-IDNA' in df.columns else ''
                existing_translate = str(df.at[i, 'translate-IDNA']).strip() if 'translate-IDNA' in df.columns else ''
                descript_list.append(existing_descript if existing_descript.lower() != 'nan' else '')
                translate_list.append(existing_translate if existing_translate.lower() != 'nan' else '')
            else:
                descript_list.append(self.generate_description(df.at[i, 'unicode'], info[1]))
                if enable_translation and info[1] == 'PUNY_IDNA' and df.at[i, 'unicode']:
                    translation = self.translate_text(df.at[i, 'unicode'], target_lang)
                    translate_list.append(translation if translation else '')
                else:
                    translate_list.append('')
        
        df['descript-IDNA'] = descript_list
        df['translate-IDNA'] = translate_list
        
        if skipped_count > 0:
            print(f"ℹ Skipped {skipped_count} domains (already have descript/translate values)")
        
        # Preserve original column order, append new columns at end
        new_cols = ['unicode', 'descript-IDNA', 'translate-IDNA', 'tags']
        col_order = original_cols + [col for col in new_cols if col not in original_cols]
        df = df[col_order]
        
        df.to_csv(output_path, index=False)
    
    def process_fw(self, filepath, output_path):
        df = pd.read_csv(filepath)
        
        domain_col = df.columns[0] if len(df.columns) > 0 else None
        if not domain_col:
            raise ValueError("No columns found in Firewallet CSV")
        
        punycode_info = df[domain_col].apply(lambda x: self.punycode_convert_validate(x) if isinstance(x, str) else ('', ''))
        
        df['unicode'] = [re.sub(r'(?:\\x[\da-fA-F]{2})+|\\u(?:[\da-fA-F]{4})+', '', info[0]) if info[0] and info[0] != df.at[i, domain_col] else '' for i, info in enumerate(punycode_info)]
        
        df = self.add_categorization_tags(df, domain_col)
        
        df['PUNY_INVALID'] = [1 if (info[0] != df.at[i, 'unicode']) or (info[0] and df.at[i, 'unicode'] == df.at[i, domain_col]) else '' for i, info in enumerate(punycode_info)]
        df['PUNY_IDNA'] = [1 if info[1] == 'PUNY_IDNA' else '' for info in punycode_info]
        df['PUNY_ALT'] = [1 if info[1] == 'PUNY_ALT' and info[0] else '' for info in punycode_info]
        df.loc[df['unicode'] == '', 'PUNY_ALT'] = ''
        
        df['LANG_TAG'] = [self.get_language_tag(df.at[i, 'unicode']) for i in range(len(df))]
        
        tags_columns = ['3D', '3L', '3C', '4D', '4L', '4C', '5D', '5L', '5C', '6D', '7D', 'PUNY_IDNA', 'PUNY_ALT', 'PUNY_INVALID']
        df['tags'] = df.apply(lambda row: ','.join(filter(None, [tag if row.get(tag) == 1 else '' for tag in tags_columns] + [row.get('LANG_TAG', '')])), axis=1)
        df.drop(columns=tags_columns + ['LANG_TAG'], inplace=True)
        
        # Add descript-IDNA and translate-IDNA columns with respect_existing logic
        respect_existing = self.respect_existing_var.GetValue()
        enable_translation = self.enable_translation_var.GetValue() and TRANSLATION_AVAILABLE
        target_lang = self.target_lang_var.GetValue()
        
        descript_list = []
        translate_list = []
        skipped_count = 0
        
        for i, info in enumerate(punycode_info):
            if respect_existing and self.should_skip_row(df.iloc[i], df):
                skipped_count += 1
                existing_descript = str(df.at[i, 'descript-IDNA']).strip() if 'descript-IDNA' in df.columns else ''
                existing_translate = str(df.at[i, 'translate-IDNA']).strip() if 'translate-IDNA' in df.columns else ''
                descript_list.append(existing_descript if existing_descript.lower() != 'nan' else '')
                translate_list.append(existing_translate if existing_translate.lower() != 'nan' else '')
            else:
                descript_list.append(self.generate_description(df.at[i, 'unicode'], info[1]))
                if enable_translation and info[1] == 'PUNY_IDNA' and df.at[i, 'unicode']:
                    translation = self.translate_text(df.at[i, 'unicode'], target_lang)
                    translate_list.append(translation if translation else '')
                else:
                    translate_list.append('')
        
        df['descript-IDNA'] = descript_list
        df['translate-IDNA'] = translate_list
        
        if skipped_count > 0:
            print(f"ℹ Skipped {skipped_count} domains (already have descript/translate values)")
        
        col_order = [domain_col, 'unicode', 'descript-IDNA', 'translate-IDNA', 'tags'] + [col for col in df.columns if col not in [domain_col, 'unicode', 'descript-IDNA', 'translate-IDNA', 'tags']]
        df = df[col_order]
        
        df.to_csv(output_path, index=False)
    
    def process_puny2uni(self):
        # Validate selection
        selections = self.puny2uni_listbox.GetSelections()
        if not selections:
            wx.MessageBox("Please select files to process", "No Selection", wx.OK | wx.ICON_WARNING)
            return
        
        processed_count = 0
        
        for idx in selections:
            filepath = self.puny2uni_files[idx]
            
            try:
                if not filepath.endswith('.txt'):
                    wx.MessageBox(f"Skipping {os.path.basename(filepath)} - only .txt files are supported", "Invalid File", wx.OK | wx.ICON_WARNING)
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
                wx.MessageBox(f"Error processing {os.path.basename(filepath)}:\n{str(e)}", "Error", wx.OK | wx.ICON_ERROR)
        
        wx.MessageBox(f"Processed {processed_count} file(s)", "Complete", wx.OK | wx.ICON_INFORMATION)
    
    def generate_portfolio_html_wx(self, domains):
        """Generate portfolio HTML with grid/list toggle support"""
        include_descriptions = self.include_descriptions_var.GetValue()
        
        # Map wx choice index to theme names
        theme_names = ["dark+light", "3-way switch", "custom CSS"]
        theme_var = self.theme_var.GetSelection()
        theme_name = theme_names[theme_var] if theme_var < len(theme_names) else "dark+light"
        
        # Generate HTML using the same logic as hnsell.py
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
                tags_dict[tag].append(self.format_domain_link_wx(row, include_descriptions))
        
        tags_sorted = ['All Names'] + sorted(set(tags_dict.keys()) - {'All Names'})
        
        # Build single grid with all domains (no sections)
        all_names_html = ''.join(f'<div class="col">{name}</div>' for tag in tags_sorted for name in tags_dict[tag])
        tag_groups_content = f'<div class="grid">{all_names_html}</div>'
        
        # Build tag dropdown options
        tag_options_html = '<option value="">All Names</option>'
        tag_options_html += '<option value="__NO_PUNY__">No PUNY</option>'
        tag_options_html += '<option disabled>\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500</option>'
        for tag in tags_sorted:
            if tag != 'All Names':
                tag_options_html += f'<option value="{tag}">{tag}</option>'
        navigation_links_html = f'<select id="tag-filter" onchange="filterDomainsWithPagination()">{tag_options_html}</select>'
        
        css_style = self.get_portfolio_css_wx(theme_name)
        javascript_code = self.get_portfolio_js_wx(theme_name)
        
        # Determine theme button
        if theme_name == "3-way switch":
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
<div class="view-toggle">
    <button id="toggle-view">📊 Grid / 📋 List</button>
</div>
<div class="desc-toggle">
    <button id="desc-toggle" onclick="toggleDescriptions()">Hide Descripts</button>
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
<div class="filter-controls">
    <div class="search-container">
        <input type="text" id="search-input" placeholder="Search names...">
        <input type="number" id="min-price" placeholder="Min price" step="0.01">
        <input type="number" id="max-price" placeholder="Max price" step="0.01">
        <label for="tag-filter">Filter:</label>
        {navigation_links_html}
        <button id="clear-filters">Clear</button>
        <label for="per-page" style="margin-left: 1em;">Per page:</label>
        <select id="per-page">
            <option value="50">50</option>
            <option value="100" selected>100</option>
            <option value="500">500</option>
            <option value="all">All</option>
        </select>
    </div>
    <div id="pagination-controls" style="text-align: center; padding: 0.5em;">
        <button id="prev-page" disabled>← Prev</button>
        <span id="page-info" style="margin: 0 1em;">Page 1</span>
        <button id="next-page">Next →</button>
    </div>
</div>
<div class="content">
    {tag_groups_content}
</div>
{javascript_code}
</body>
</html>"""
        
        return html_content
    
    def format_domain_link_wx(self, row, include_descriptions):
        """Format domain link with unicode → puny → descriptions → price/email layout"""
        name = row['name']
        if isinstance(name, float) and math.isnan(name):
            return ''
        name = str(name)
        unicode_val = str(row.get('unicode', ''))
        source = row.get('source', 'nb')
        email = row.get('email', '')
        price = row.get('price', '')
        tags = row.get('tags', '')
        descript = str(row.get('descript-IDNA', ''))
        translate = str(row.get('translate-IDNA', ''))
        
        # Clean up nan values
        if isinstance(email, float) and math.isnan(email):
            email = ''
        if isinstance(price, float) and math.isnan(price):
            price = ''
        if str(email).lower() == 'nan':
            email = ''
        if str(price).lower() == 'nan':
            price = ''
        if str(descript).lower() == 'nan':
            descript = ''
        if str(translate).lower() == 'nan':
            translate = ''
        
        # Determine URL or contact display
        if source == 'ss':
            base_url = f"https://shakestation.io/domain/{name}"
        elif source == 'nb':
            base_url = f"https://www.namebase.io/domains/{name}"
        elif source == 'bob' or source == 'fw':
            # Bob/FW: No marketplace link
            unicode_display = ''
            if name.startswith('xn--') and unicode_val and unicode_val.lower() != 'nan':
                try:
                    unicode_bytes = codecs.decode(unicode_val, 'unicode_escape')
                    unicode_display = unicode_bytes.encode('latin-1').decode('utf-8')
                except:
                    unicode_display = unicode_val
            
            contact_parts = []
            if price:
                contact_parts.append(f"💰 {price}")
            if email:
                contact_parts.append(f'<button class="copy-email-btn" onclick="copyEmail(event, \'{email}\')" title="Copy {email}">eml</button>')
            
            # Layout: unicode → puny → descriptions → price/email (bottom)
            html_parts = []
            if unicode_display:
                html_parts.append(f'<div class="domain-unicode">{unicode_display}</div>')
            html_parts.append(f'<div class="domain-puny">{name}</div>')
            
            if include_descriptions:
                desc_parts = []
                if descript:
                    desc_parts.append(f'<span class="desc-text">"{descript}"</span>')
                if translate:
                    desc_parts.append(f'<span class="translate-text"><i>{translate}</i></span>')
                if desc_parts:
                    html_parts.append(f'<div class="domain-descriptions">{" ".join(desc_parts)}</div>')
            
            if contact_parts:
                html_parts.append(f'<div class="domain-contact">{" ".join(contact_parts)}</div>')
            
            is_puny = "true" if name.startswith('xn--') else "false"
            return f'<span class="domain-with-contact" data-price="{price}" data-email="{email}" data-tags="{tags}" data-puny="{is_puny}">' + ''.join(html_parts) + '</span>'
        else:
            base_url = f"https://www.namebase.io/domains/{name}"
        
        # SS/NB: with marketplace links
        unicode_display = ''
        if name.startswith('xn--') and unicode_val and unicode_val.lower() != 'nan':
            try:
                unicode_bytes = codecs.decode(unicode_val, 'unicode_escape')
                unicode_display = unicode_bytes.encode('latin-1').decode('utf-8')
            except:
                unicode_display = unicode_val
        
        contact_parts = []
        if price:
            contact_parts.append(f"💰 {price}")
        if email:
            contact_parts.append(f'<button class="copy-email-btn" onclick="copyEmail(event, \'{email}\')" title="Copy {email}">eml</button>')
        
        # Layout: unicode → puny link → descriptions → price/email (bottom)
        html_parts = []
        if unicode_display:
            html_parts.append(f'<div class="domain-unicode">{unicode_display}</div>')
        html_parts.append(f'<div class="domain-puny"><a target="_blank" rel="noreferrer" href="{base_url}">{name}</a></div>')
        
        if include_descriptions:
            desc_parts = []
            if descript:
                desc_parts.append(f'<span class="desc-text">"{descript}"</span>')
            if translate:
                desc_parts.append(f'<span class="translate-text"><i>{translate}</i></span>')
            if desc_parts:
                html_parts.append(f'<div class="domain-descriptions">{" ".join(desc_parts)}</div>')
        
        if contact_parts:
            html_parts.append(f'<div class="domain-contact">{" ".join(contact_parts)}</div>')
        
        is_puny = "true" if name.startswith('xn--') else "false"
        return f'<span class="domain-with-contact" data-price="{price}" data-email="{email}" data-tags="{tags}" data-puny="{is_puny}">' + ''.join(html_parts) + '</span>'
    
    def get_portfolio_css_wx(self, theme_name):
        """Get CSS for portfolio page"""
        return """<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    background-color: #ffffff;
    color: #000000;
    font-family: Arial, Helvetica, sans-serif;
    padding: 20px;
}
body.dark-mode {
    background-color: #000000;
    color: #ffffff;
}
.buttons-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 10px;
}
button {
    padding: 8px 16px;
    background-color: rgba(52, 4, 244, 0.2);
    border: 2px solid currentColor;
    border-radius: 8px;
    cursor: pointer;
}
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 0.5em;
    padding: 0.5em;
}
.grid.list-view {
    display: flex;
    flex-direction: column;
}
.grid.list-view .col {
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    max-width: 100%;
}
.grid.list-view .domain-with-contact {
    flex-direction: row;
    width: 100%;
}
.grid.list-view .domain-unicode {
    display: inline;
    margin-right: 0.3em;
}
.grid.list-view .domain-puny {
    display: inline;
    margin-right: 0.5em;
}
.grid.list-view .domain-contact {
    display: inline-flex;
    margin: 0 0.5em;
}
.grid.list-view .domain-descriptions {
    margin-left: auto;
    flex-direction: row;
    text-align: right;
}
.col {
    padding: 0.7em;
    background-color: rgba(111, 111, 111, 0.1);
    border: 1px solid currentColor;
    border-radius: 8px;
    text-align: center;
}
body.hide-descriptions .domain-descriptions {
    display: none;
}
.filter-controls {
    margin: 10px 0;
}
#tag-filter {
    padding: 8px;
    margin: 0 5px;
    border: 2px solid currentColor;
    border-radius: 8px;
    background-color: rgba(52, 4, 244, 0.1);
    color: inherit;
    cursor: pointer;
}
.domain-with-contact {
    display: flex;
    flex-direction: column;
    gap: 0.3em;
}
.domain-unicode {
    font-weight: bold;
    font-size: 1.1em;
}
.domain-puny {
    font-size: 0.85em;
    opacity: 0.8;
}
.domain-contact {
    font-size: 0.9em;
    display: flex;
    gap: 0.5em;
    justify-content: center;
}
.domain-descriptions {
    font-size: 0.85em;
    margin-top: 0.3em;
    display: flex;
    flex-direction: column;
    gap: 0.2em;
}
.desc-text {
    color: inherit;
}
.translate-text {
    color: inherit;
    opacity: 0.9;
}

.marketplace-links {
    display: flex;
    justify-content: center;
    gap: 1.5em;
    padding: 1em;
    margin: 10px 0 20px 0;
    flex-wrap: wrap;
}
.search-container {
    display: flex;
    gap: 0.5em;
    padding: 1em;
    justify-content: center;
    flex-wrap: wrap;
}
.copy-email-btn {
    padding: 0.2em 0.5em;
    margin-left: 0.3em;
    background-color: rgba(111, 111, 111, 0.15);
    border: 1px solid currentColor;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9em;
}
</style>"""
    
    def get_portfolio_js_wx(self, theme_name):
        """Get JavaScript for portfolio page - adapted from hnsell.py"""
        return """<script>
let darkMode = true;
function toggleDarkMode() {
    darkMode = !darkMode;
    document.body.classList.toggle("dark-mode");
}
const modeToggle = document.getElementById('mode-toggle');
if (modeToggle) {
    modeToggle.addEventListener('click', toggleDarkMode);
}

// Grid/List toggle
const toggleViewBtn = document.getElementById('toggle-view');
if (toggleViewBtn) {
    toggleViewBtn.addEventListener('click', function() {
        const grids = document.querySelectorAll('.grid');
        grids.forEach(grid => grid.classList.toggle('list-view'));
        this.textContent = document.querySelector('.grid.list-view') ? '📋 List' : '📊 Grid';
    });
}

// Description toggle
function toggleDescriptions() {
    const descToggleBtn = document.getElementById('desc-toggle');
    document.body.classList.toggle('hide-descriptions');
    if (document.body.classList.contains('hide-descriptions')) {
        descToggleBtn.textContent = 'Show Descripts';
    } else {
        descToggleBtn.textContent = 'Hide Descripts';
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
    var grid = document.querySelector('.grid');
    if (grid) {
        var items = Array.from(grid.querySelectorAll('.col'));
        
        switch(sortState) {
            case 0:
                for (let i = items.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [items[i], items[j]] = [items[j], items[i]];
                }
                this.textContent = 'Sort: Random';
                break;
            case 1:
                items.sort((a, b) => a.textContent.toLowerCase().localeCompare(b.textContent.toLowerCase()));
                this.textContent = 'Sort: A-Z ▲';
                break;
            case 2:
                items.sort((a, b) => b.textContent.toLowerCase().localeCompare(a.textContent.toLowerCase()));
                this.textContent = 'Sort: Z-A ▼';
                break;
            case 3:
                items.sort((a, b) => {
                    const priceA = parseFloat(a.querySelector('.domain-with-contact')?.dataset?.price || '999999');
                    const priceB = parseFloat(b.querySelector('.domain-with-contact')?.dataset?.price || '999999');
                    return priceA - priceB;
                });
                this.textContent = 'Sort: Price ▲';
                break;
            case 4:
                items.sort((a, b) => {
                    const priceA = parseFloat(a.querySelector('.domain-with-contact')?.dataset?.price || '0');
                    const priceB = parseFloat(b.querySelector('.domain-with-contact')?.dataset?.price || '0');
                    return priceB - priceA;
                });
                this.textContent = 'Sort: Price ▼';
                break;
        }
        
        grid.innerHTML = '';
        items.forEach(item => grid.appendChild(item));
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

function filterDomains() {
    const searchInput = document.getElementById('search-input').value.toLowerCase();
    const minPrice = parseFloat(document.getElementById('min-price').value) || null;
    const maxPrice = parseFloat(document.getElementById('max-price').value) || null;
    const tagFilter = document.getElementById('tag-filter').value;
    
    const items = document.querySelectorAll('.col');
    
    items.forEach(item => {
        const domainSpan = item.querySelector('.domain-with-contact');
        if (!domainSpan) {
            item.style.display = 'none';
            return;
        }
        
        // Text search
        const domainText = item.textContent.toLowerCase();
        let textMatch = searchInput === '' || domainText.includes(searchInput);
        
        // Price filter
        let priceMatch = true;
        if (minPrice !== null || maxPrice !== null) {
            const priceData = domainSpan.dataset.price;
            if (priceData) {
                const price = parseFloat(priceData);
                if (minPrice !== null && price < minPrice) priceMatch = false;
                if (maxPrice !== null && price > maxPrice) priceMatch = false;
            } else {
                priceMatch = false;
            }
        }
        
        // Tag filter with No PUNY support
        let tagMatch = true;
        if (tagFilter) {
            if (tagFilter === '__NO_PUNY__') {
                // Special case: hide punycode domains
                const isPuny = domainSpan.dataset.puny === 'true';
                if (isPuny) {
                    tagMatch = false;
                }
            } else {
                // Regular tag filtering
                const tags = (domainSpan.dataset.tags || '').split(',').map(t => t.trim());
                tagMatch = tags.includes(tagFilter);
            }
        }
        
        item.style.display = (textMatch && priceMatch && tagMatch) ? '' : 'none';
    });
}

function searchNames() {
    filterDomainsWithPagination();
}

document.getElementById('search-input').addEventListener('keyup', filterDomainsWithPagination);
document.getElementById('min-price').addEventListener('input', filterDomainsWithPagination);
document.getElementById('max-price').addEventListener('input', filterDomainsWithPagination);
document.getElementById('clear-filters').addEventListener('click', function() {
    document.getElementById('search-input').value = '';
    document.getElementById('min-price').value = '';
    document.getElementById('max-price').value = '';
    document.getElementById('tag-filter').value = '';
    filterDomainsWithPagination();
});

// Pagination
let currentPage = 1;
let itemsPerPage = 100;
let allVisibleItems = [];

function updatePagination() {
    const perPageSelect = document.getElementById('per-page');
    const value = perPageSelect.value;
    itemsPerPage = value === 'all' ? Infinity : parseInt(value);
    currentPage = 1;
    showPage();
}

function showPage() {
    const items = document.querySelectorAll('.col');
    allVisibleItems = Array.from(items).filter(item => item.style.display !== 'none');
    
    const totalPages = Math.ceil(allVisibleItems.length / itemsPerPage);
    const start = (currentPage - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    
    // Hide all first
    items.forEach(item => {
        if (item.style.display !== 'none') {
            item.style.display = 'none';
        }
    });
    
    // Show current page
    allVisibleItems.slice(start, end).forEach(item => {
        item.style.display = '';
    });
    
    // Update pagination controls
    document.getElementById('prev-page').disabled = currentPage === 1;
    document.getElementById('next-page').disabled = currentPage >= totalPages || itemsPerPage === Infinity;
    document.getElementById('page-info').textContent = itemsPerPage === Infinity ? 
        `Showing all ${allVisibleItems.length} names` : 
        `Page ${currentPage} of ${totalPages} (${allVisibleItems.length} names)`;
}

function filterDomainsWithPagination() {
    filterDomains();
    currentPage = 1;
    showPage();
}

document.getElementById('per-page').addEventListener('change', updatePagination);
document.getElementById('prev-page').addEventListener('click', function() {
    if (currentPage > 1) {
        currentPage--;
        showPage();
        window.scrollTo(0, 0);
    }
});
document.getElementById('next-page').addEventListener('click', function() {
    const totalPages = Math.ceil(allVisibleItems.length / itemsPerPage);
    if (currentPage < totalPages) {
        currentPage++;
        showPage();
        window.scrollTo(0, 0);
    }
});

// Initialize - show all domains with pagination
filterDomains();
showPage();
</script>"""
    
    def process_pagemaker(self):
        # Validate selection
        selections = self.pagemaker_listbox.GetSelections()
        if not selections:
            wx.MessageBox("Please select CSV files to process", "No Selection", wx.OK | wx.ICON_WARNING)
            return
        
        try:
            all_domains = []
            bob_fw_without_contact = []
            
            for idx in selections:
                filepath = self.pagemaker_files[idx]
                source_type = self.detect_csv_source(filepath)
                
                try:
                    df = pd.read_csv(filepath)
                except pd.errors.ParserError:
                    try:
                        df = pd.read_csv(filepath, quoting=1, escapechar='\\\\')
                    except:
                        df = pd.read_csv(filepath, on_bad_lines='skip')
                
                if source_type == 'ss-tld':
                    # Shakestation TLD: only include for_sale=True (unless list_all is checked)
                    if not self.list_all_var.GetValue():
                        df = df[df['for_sale'] == True]
                    for _, row in df.iterrows():
                        domain = row['domain']
                        if isinstance(domain, float) and math.isnan(domain):
                            continue
                        domain = str(domain)
                        unicode_val = row.get('unicode', '')
                        tags = row.get('tags', 'All Names')
                        email = row.get('email', '')
                        price = row.get('price', '')
                        descript = row.get('descript-IDNA', '')
                        translate = row.get('translate-IDNA', '')
                        all_domains.append({
                            'name': domain,
                            'unicode': unicode_val,
                            'tags': tags,
                            'source': 'ss',
                            'email': email,
                            'price': price,
                            'descript-IDNA': descript,
                            'translate-IDNA': translate
                        })
                elif source_type == 'ss-tr':
                    for _, row in df.iterrows():
                        domain = row['domain']
                        if isinstance(domain, float) and math.isnan(domain):
                            continue
                        domain = str(domain)
                        unicode_val = row.get('unicode', '')
                        tags = row.get('tags', 'All Names')
                        email = row.get('email', '')
                        price = row.get('price', '')
                        if isinstance(email, float) and math.isnan(email):
                            email = ''
                        if isinstance(price, float) and math.isnan(price):
                            price = ''
                        email = str(email).strip() if email else ''
                        price = str(price).strip() if price else ''
                        if email.lower() == 'nan' or email == '0':
                            email = ''
                        if price.lower() == 'nan' or price == '0' or price == '0.0':
                            price = ''
                        descript = row.get('descript-IDNA', '')
                        translate = row.get('translate-IDNA', '')
                        all_domains.append({
                            'name': domain,
                            'unicode': unicode_val,
                            'tags': tags,
                            'source': 'ss',
                            'email': email,
                            'price': price,
                            'descript-IDNA': descript,
                            'translate-IDNA': translate
                        })
                elif source_type == 'nb-tld' or source_type == 'nb-tr':
                    for _, row in df.iterrows():
                        domain = row.get('name', row.get('extra.domain', ''))
                        if isinstance(domain, float) and math.isnan(domain):
                            continue
                        domain = str(domain)
                        unicode_val = row.get('unicode', '')
                        tags = row.get('tags', 'All Names')
                        email = row.get('email', '')
                        price = row.get('price', '')
                        if isinstance(email, float) and math.isnan(email):
                            email = ''
                        if isinstance(price, float) and math.isnan(price):
                            price = ''
                        email = str(email).strip() if email else ''
                        price = str(price).strip() if price else ''
                        if email.lower() == 'nan' or email == '0':
                            email = ''
                        if price.lower() == 'nan' or price == '0' or price == '0.0':
                            price = ''
                        descript = row.get('descript-IDNA', '')
                        translate = row.get('translate-IDNA', '')
                        all_domains.append({
                            'name': domain,
                            'unicode': unicode_val,
                            'tags': tags,
                            'source': 'nb',
                            'email': email,
                            'price': price,
                            'descript-IDNA': descript,
                            'translate-IDNA': translate
                        })
                elif source_type == 'bob-tld':
                    has_email_or_price = False
                    auto_email_base = self.auto_email_entry.GetValue().strip()
                    for _, row in df.iterrows():
                        domain = row.get('domains', '')
                        if isinstance(domain, float) and math.isnan(domain):
                            continue
                        domain = str(domain)
                        unicode_val = row.get('unicode', '')
                        tags = row.get('tags', 'All Names')
                        email = row.get('email', '')
                        price = row.get('price', '')
                        if isinstance(email, float) and math.isnan(email):
                            email = ''
                        if isinstance(price, float) and math.isnan(price):
                            price = ''
                        email = str(email).strip() if email else ''
                        price = str(price).strip() if price else ''
                        if not email or email.lower() in ['nan', 'none', '0']:
                            email = ''
                        if not price or price.lower() in ['nan', 'none', '0', '0.0']:
                            price = ''
                        
                        if auto_email_base and not email and (price or self.list_all_var.GetValue()):
                            if '@' in auto_email_base:
                                parts = auto_email_base.split('@')
                                if len(parts) == 2:
                                    user_part = parts[0]
                                    if user_part.endswith('+'):
                                        email = f"{user_part}{domain}@{parts[1]}"
                                    else:
                                        email = f"{user_part}+{domain}@{parts[1]}"
                        
                        if self.list_all_var.GetValue() or email or price:
                            has_email_or_price = True
                            descript = row.get('descript-IDNA', '')
                            translate = row.get('translate-IDNA', '')
                            all_domains.append({
                                'name': domain,
                                'unicode': unicode_val,
                                'tags': tags,
                                'source': 'bob',
                                'email': email,
                                'price': price,
                                'descript-IDNA': descript,
                                'translate-IDNA': translate
                            })
                    if not has_email_or_price and not self.list_all_var.GetValue():
                        bob_fw_without_contact.append(os.path.basename(filepath))
                elif source_type == 'fw':
                    has_price_col = 'price' in df.columns
                    has_email_col = 'email' in df.columns
                    if not has_price_col and not self.list_all_var.GetValue():
                        wx.MessageBox(f"Firewallet CSV '{os.path.basename(filepath)}' has no 'price' column.\\n\\n" +
                                    "Please add a 'price' column with values for domains you want to list,\\n" +
                                    "OR check 'List all domains' to show all domains with contact email only.",
                                    "Missing Price Column", wx.OK | wx.ICON_WARNING)
                        continue
                    has_email_or_price = False
                    auto_email_base = self.auto_email_entry.GetValue().strip()
                    for _, row in df.iterrows():
                        domain = row.get('name', row.get(df.columns[0], ''))
                        if isinstance(domain, float) and math.isnan(domain):
                            continue
                        domain = str(domain)
                        unicode_val = row.get('unicode', '')
                        tags = row.get('tags', 'All Names')
                        email = row.get('email', '') if has_email_col else ''
                        price = row.get('price', '') if has_price_col else ''
                        if isinstance(email, float) and math.isnan(email):
                            email = ''
                        if isinstance(price, float):
                            if math.isnan(price):
                                price = ''
                            elif price == 0.0:
                                price = ''
                            else:
                                price = str(price)
                        else:
                            price = str(price).strip() if price else ''
                            if price.lower() in ['nan', 'none', '0', '0.0']:
                                price = ''
                        email = str(email).strip() if email else ''
                        if email.lower() in ['nan', 'none', '0']:
                            email = ''
                        
                        if auto_email_base and not email and (price or self.list_all_var.GetValue()):
                            if '@' in auto_email_base:
                                parts = auto_email_base.split('@')
                                if len(parts) == 2:
                                    user_part = parts[0]
                                    if user_part.endswith('+'):
                                        email = f"{user_part}{domain}@{parts[1]}"
                                    else:
                                        email = f"{user_part}+{domain}@{parts[1]}"
                        
                        if self.list_all_var.GetValue() or email or price:
                            has_email_or_price = True
                            descript = row.get('descript-IDNA', '')
                            translate = row.get('translate-IDNA', '')
                            all_domains.append({
                                'name': domain,
                                'unicode': unicode_val,
                                'tags': tags,
                                'source': 'fw',
                                'email': email,
                                'price': price,
                                'descript-IDNA': descript,
                                'translate-IDNA': translate
                            })
                    if not has_email_or_price and not self.list_all_var.GetValue():
                        bob_fw_without_contact.append(os.path.basename(filepath))
            
            if not all_domains:
                error_msg = "No domains found in selected files"
                if bob_fw_without_contact:
                    error_msg += f"\\n\\nBob/Firewallet files require 'email' or 'price' columns with values:\\n" + "\\n".join(f"  • {f}" for f in bob_fw_without_contact)
                wx.MessageBox(error_msg, "No Domains", wx.OK | wx.ICON_WARNING)
                return
            
            html_content = self.generate_portfolio_html_wx(all_domains)
            
            output_filename = self.output_filename_entry.GetValue()
            if not output_filename.endswith('.html'):
                output_filename += '.html'
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_path = os.path.join(script_dir, output_filename)
            
            if os.path.exists(output_path):
                dlg = wx.MessageDialog(None, f"The file '{output_filename}' already exists.\nDo you want to overwrite it?",
                                      "File Exists", wx.YES_NO | wx.ICON_QUESTION)
                result = dlg.ShowModal()
                dlg.Destroy()
                if result != wx.ID_YES:
                    return
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            wx.MessageBox(f"Portfolio page created: {output_path}\n\nTotal domains: {len(all_domains)}",
                         "Success", wx.OK | wx.ICON_INFORMATION)
        
        except Exception as e:
            wx.MessageBox(f"Error creating portfolio:\n{str(e)}", "Error", wx.OK | wx.ICON_ERROR)

if __name__ == '__main__':
    app = wx.App()
    frame = HNSellFrame()
    app.MainLoop()
