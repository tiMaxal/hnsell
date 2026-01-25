# HNSell GUI Application (hnsell.py)

**Primary wxPython GUI** for managing Handshake (HNS) domain CSV exports from multiple wallet sources.

*This document covers the main hnsell.py application. For standalone tools, see [README.md](README.md)*

## Version

**v0.4.0** (January 11, 2026) - wxPython version with enhanced features

*Voding [vibe-coding] by copilot[20251227]timaxal*

## What's New in v0.4.0

### **Data Preservation**

- ✅ **Respect Existing Entries**: Checkbox option (default: checked) to preserve manual edits during reprocessing
- Skips domains that already have `descript-IDNA`, `description`, or `translate-IDNA` values
- Uncheck to override and re-process all domains
- Shows skip counter: `ℹ Skipped {n} domains (already have descript/translate values)`

### **Translation Integration**

- ✅ **Google Translate API**: Optional translation of PUNY_IDNA unicode domains
- Target language selection: en, es, fr, de, ja, zh-CN, etc.
- Requires `deep-translator` package (graceful fallback if missing)
- Adds `translate-IDNA` column to processed CSVs

### **Enhanced Language Detection**

- 20+ languages/scripts: CJK, Japanese, Arabic, Hebrew, Cyrillic, Greek, Thai, Hindi, Tamil, Malayalam, Georgian, Armenian, Hawaiian, European Latin Extended
- Automatic language tagging in `tags` column
- Smart emoji character name descriptions

### **UI/UX Improvements**

- Fully functional PageMaker tab scrolling (wxPython ScrolledPanel)
- Better performance and native OS look-and-feel
- Color-coded buttons for actions
- Help text for new features

## Credits & Origin

**Forked from**: [Punytag](https://github.com/i1li/punytag) by [@i1li](https://github.com/i1li)

Core punycode validation logic remains based on @i1li's original implementation.

## Application Architecture

**GUI Framework**: wxPython (production version)

- Superior PageMaker tab scrolling performance
- Native OS look-and-feel (Windows/Linux/Mac)
- Better responsive design for complex layouts

**Note**: Legacy tkinter version available at `ai-hist_hnsell/hnsell.py.old2`

## Features

### 3-Tab Interface

#### Tab 1: Punytag Processor

- **Multi-Source Support**: Automatically processes CSV files from:
  - Bob Wallet (transaction history and TLD exports)
  - Namebase.io (transaction history and domain exports)
  - Shakestation.io (domain exports)
  - Firewallet (exports)
- **Automatic Source Detection**: Identifies source format from CSV headers
- **Punycode Conversion**: Converts punycode domains (xn--) to Unicode with proper tagging
- **Batch Processing**: Select individual files or entire folders
- **Recursive Search**: Option to search subdirectories for CSV files
- **Smart Duplicate Prevention**: Skips already processed files
- **Data Preservation** (v0.4.0):
  - **Respect existing entries** checkbox (default: checked)
  - Skips domains with existing `descript-IDNA` or `translate-IDNA` values
  - Prevents overwriting manual edits during reprocessing
  - Uncheck to force re-processing (useful for language retargeting)
- **Translation Support** (v0.4.0):
  - **Enable translations** checkbox (requires `deep-translator`)
  - Target language field (default: 'en')
  - Supports 100+ languages: en, es, fr, de, ja, zh-CN, ar, he, ru, etc.
  - Only applies to PUNY_IDNA tagged domains
  - Adds `translate-IDNA` column to output CSV
- **Flexible Output Options**:
  - Rename originals with '_orig' suffix
  - Sort outputs to subdirectories by source
  - Delete original files after processing
  - Automatic date stamping (yyyymmdd)

#### Tab 2: Puny ⟷ Unicode Converter

- **Bidirectional Conversion**: Convert between Punycode and Unicode
- **Text File Processing**: Works exclusively with .txt files (one domain per line)
- **Batch Processing**: Convert multiple files at once
- **Automatic Detection**: Detects direction based on first line (xn-- prefix = punycode to unicode)

#### Tab 3: PageMaker

- **HTML Portfolio Generation**: Create beautiful portfolio pages from domain lists
- **Multi-Source Compilation**: Combine domains from Namebase, Shakestation, and non-custodial wallets (Firewallet or Bob exports)
- **Smart Linking**: Automatically links to appropriate marketplace:
  - <https://www.namebase.io/domains/[tld>]
  - <https://shakestation.io/domain/[tld>]
  - Or displays personal email for non-custodial wallet domains
- **For-Sale Filter**: Only includes Shakestation domains marked 'for_sale=TRUE'
- **Flexible Sorting**:  
  - Random (default)
  - Alphabetical ascending
  - Alphabetical descending
  - By price (low to high)
  - By price (high to low)
  - Cycle through options with Sort button
- **Tag-Based Navigation**: Name-type selection buttons automatically added when file is processed with Punytag Processor (3D, 3L, PUNY_IDNA, language tags, etc.)
- **Customization Options**:
  - Optional footer HTML
  - Optional credits HTML
  - Theme selection (dark+light, 3-way switch, custom CSS)
- **Update Existing Pages**: Add or remove domains from existing portfolio HTML
- **Responsive Design**: Dark/light mode toggle, zoom controls, search functionality with price filtering

## Installation

### Requirements

- **Python 3.7+**
- **wxPython** (GUI framework)
- Required packages (install via pip):

```bash
pip install -r requirements.txt
```

**Required packages** (`requirements.txt`):

- `wxPython` - GUI framework (PRIMARY)
- `pandas>=2.2.0` - CSV processing
- `idna>=3.6` - Punycode conversion

**Optional packages**:

- `deep-translator` - Translation features (graceful fallback if missing)
  - Install: `pip install deep-translator`
  - If missing: Translation checkbox disabled with warning message

**Platform-specific notes**:

- **Windows**: wxPython installs via pip automatically
- **Linux**: `sudo apt-get install python3-wxgtk4.0`
- **Mac**: `pip install wxPython` (may require Xcode Command Line Tools)

### Running the Application

```bash
python hnsell.py
```

## Usage Guide

### Processing CSV Files (Tab 1)

1. **Select Files**:
   - Click "Select Files" to choose individual CSV files
   - OR click "Select Folder" to process all CSVs in a directory
   - Enable "Recursive Search" to include subdirectories

2. **Review Selection**:
   - Selected files appear in the list with source type detection [bob-tr], [nb-tld], etc.
   - Use "Select All" / "Select None" to manage selections

3. **Configure Options**:
   - ☑ **Respect existing entries** (default: CHECKED) - Preserves manual edits to descript/translate columns
     - ℹ Uncheck to override and re-process all domains (useful for re-translation)
   - ☑ **Enable translations** (requires deep-translator)
     - Target language: `en` (English), `es` (Spanish), `fr` (French), `de` (German), `ja` (Japanese), `zh-CN` (Chinese), etc.
     - Only translates PUNY_IDNA domains with unicode values
   - ☑ Rename original files with '_orig' suffix
   - ☑ Sort processed files to subdirectories by source
   - ☑ Delete original files (use with caution!)

4. **Process**:
   - Click the green "Process" button
   - Files are processed with date stamp appended
   - Success message shows number of files processed

### Converting Punycode (Tab 2)

1. Click "Select Files" and choose .txt files (one domain per line)
2. Files are automatically detected as puny→unicode (if starts with xn--) or unicode→puny
3. Click the green "Process" button
4. Converted files are saved with '_uni.txt' or '_puny.txt' suffix

### Creating Portfolio Pages (Tab 3)

1. **Select Domain CSVs**:
   - Click "Select C, Shakestation, Bob Wallet, or Firewallet domain exports
   - For Bob/Firewallet: Add 'price' and 'email' columns for contact display

2. **Configure Sorting** (optional):
   - Click "Sort TLDs" to cycle through sort options
   - Random → Alphabetical ▲ → Alphabetical ▼ → Price ▲ → Price ▼

3. **Select Theme** (optional):
   - Dark + Light (default 2-way toggle)
   - 3-Way Switch (Light → Dark → Black with custom colors)
   - Custom CSS (load your own stylesheet)

4. **Add Custom Content** (optional):
   - Select Footer HTML file
   - Select Credits HTML file

5. **Set Output**:
   - Enter desired filename (default: portfolio.html)
   - Or click "Select Output File" to choose location

6. **Generate**:
   - Click the green "Process" button
   - HTML file is created with embedded styles and JavaScript
   - Tag navigation automatically included if files processed with Punytag Processor
   - HTML file is created in the current directory

### Updating Existing Portfolios

1. In PageMaker tab, click "Select HTML File" under "Update Existing Page"
2. Select CSV files to add/remove domains
3. Process as normal

## Button Reference

- **🟢 Process**: Execute the current tab's action
- **🟡 Help**: Display detailed usage instructions
- **🔴 Exit**: Close the application

## File Format Detection

The application automatically detects source formats based on CSV headers:

- **Bob-TR**: `time`, `txhash`, `domains` columns
- **Bob-TLD**: Single `domains` column
- **Namebase-TR**: `extra.domain`, `extra.action` columns
- **Namebase-TLD**: `name`, `tags` columns
- **Shakestation**: `domain`, `for_sale` columns
- **Firewallet**: Other formats

## Output Files

txt`

- Unicode to Punycode:

- Format: `original_name_YYYYMMDD.csv`
- Original files renamed to: `original_name_orig.csv` (if option selected)

### Converted Files

- Punycode to Unicode: `original_name_uni.csv` or `original_name_uni.txt`
- Unicode to Punycode: `original_name_puny.csv` or `original_name_puny.txt`

### Portfolio HTML

- User-defined filename (default: `portfolio.html`)
- Includes embedded CSS and JavaScript
- Responsive design with dark mode support

## Punycode Tagging System

The processor adds tags to identify conversion methods:

- **PUNY_IDNA**: Successfully decoded using IDNA standard
- **PUNY_ALT**: Decoded using alternative method
- **PUNY_INVALID**: Contains invalid Unicode characters

## Tips

- Test with a small batch first before processing large numbers of files
- Use the "Rename original" option to preserve original files
- Enable recursive search to find all CSVs in a project directory
- Portfolio pages include search functionality and tag filtering
- Use the Help button for quick reference while working

## Generated Portfolio Features

- **Dark/Light Mode**: Toggle with 🌙 / ☀️ button (or 3-way cycle with custom colors)
- **Zoom Controls**: +/- buttons for text size
- **Tag Navigation**: Click tags to filter domains (3D, 3L, PUNY_IDNA, language tags, etc.)
- **Search Function**: Real-time domain search with price range filtering
- **Sort Options**: Random, A-Z, Z-A, Price Low-High, Price High-Low
- **Email Copy**: Click 'eml' button to copy contact email to clipboard
- **Smart Linking**:
  - Namebase/Shakestation domains link to marketplace
  - Bob/Firewallet domains show price and email contact only
- **Responsive Design**: Auto-adjusts for mobile/desktop
- **Tooltips**: Hover over domain names to see full text

## Application Data

The application stores settings, profiles, and logs in the `hnsell_data/` subdirectory:

- **hnsell_settings.json** - Last used settings (auto-saved on exit)
- **hnsell_profile_*.json** - Named profiles saved via Settings Manager
- **hnsell_processing.log** - Processing history with timestamps and error details

These files are automatically created and gitignored for privacy.

## Troubleshooting

### Common Issues

1. **"No module named 'wx'" or "No module named 'wxPython'"**:
   - Install wxPython: `pip install wxPython`
   - On Linux: `sudo apt-get install python3-wxgtk4.0`
   - On Mac: May require Xcode Command Line Tools
   - **Fallback**: Use legacy tkinter version at `ai-hist_hnsell/hnsell.py.old2`

2. **Translation features disabled**:
   - Install deep-translator: `pip install deep-translator`
   - Requires internet connection for Google Translate API
   - Translation checkbox will be enabled after installation

3. **CSV not detected correctly**:
   - Check that CSV has proper headers
   - Verify file is valid CSV format

4. **Punycode conversion errors**:
   - Some punycode domains may be invalid
   - Check the PUNY_INVALID tag in output

5. **Log file location**:
   - Processing log: `hnsell_data/hnsell_processing.log`
   - Check this file for detailed error messages and timestamps

## Related Documentation

- **[README.md](README.md)** - Main project overview with all tools
- **[RELEASE_NOTES_v0.4.0.md](RELEASE_NOTES_v0.4.0.md)** - Complete v0.4.0 feature list and migration guide
- **[pagemaker/pagemaker.README.md](pagemaker/pagemaker.README.md)** - Standalone PageMaker documentation
- **[puny2uni/puny2uni2.README.md](puny2uni/puny2uni2.README.md)** - CLI converter documentation

## Standalone Tools

For specific workflows, consider these standalone alternatives:

- **PageMaker**: `pagemaker/pagemaker2.py` - HTML generation only
- **Puny2Uni CLI**: `puny2uni/puny2uni2.py` - Command-line conversion with translation
- **Puny2Uni GUI**: `puny2uni/puny2uni2gui.py` - Simple converter interface

## Author

Based on original punycode processing scripts by [@i1li](https://github.com/i1li)

Expanded and maintained by timaxal

## Version History

- **v0.4.0** (2026-01-11) - wxPython production version, translation support, data preservation, architectural reorganization
- **v0.3.x** - Language detection, enhanced descriptions
- **v0.2.x** - PageMaker integration, multi-source support  
- **v0.1.0** (2025-12-26) - Initial GUI release (tkinter)
