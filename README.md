# HNSell - Handshake Domain Manager

A comprehensive application suite for managing Handshake (HNS) domain CSV exports from multiple wallet sources, with punycode conversion, language detection, translation, and HTML portfolio generation.

*Voding [vibe-coding] by copilot[20251227]timaxal*

## Credits & Origin

**Forked from**: [Punytag](https://github.com/i1li/punytag) by [@i1li](https://github.com/i1li)

Original Punytag functionality (Namebase/Bob Wallet punycode processing) has been expanded with:

- Multi-platform support (Shakestation, Firewallet)
- Language detection system (20+ languages/scripts)
- Translation integration (Google Translate API)
- Data preservation logic (respect existing entries)
- Auto-generated descriptions and categorization
- HTML portfolio generator with advanced filtering
- Comprehensive GUI interface (wxPython primary, standalone tkinter tools)

Core punycode validation logic remains based on @i1li's original implementation.

## Version

**v0.4.0** (January 11, 2026) - Major architectural reorganization and feature additions

- Primary application: `hnsell.py` (wxPython - superior scrolling and performance)
- Legacy version: `ai-hist_hnsell/hnsell.py.old2` (tkinter)
- See [RELEASE_NOTES_v0.4.0.md](RELEASE_NOTES_v0.4.0.md) for complete migration details

## Project Structure

```
./  (repository root)
├── hnsell.py                    ← PRIMARY GUI (wxPython)
├── requirements.txt
├── RELEASE_NOTES_v0.4.0.md
│
├── hnsell_data/                 ← Application data (gitignored)
│   ├── hnsell_settings.json    (user settings)
│   ├── hnsell_profile_*.json   (saved profiles)
│   └── hnsell_processing.log   (processing log)
│
├── pagemaker/                   ← Standalone HTML generator
│   ├── pagemaker2.py
│   └── pagemaker.README.md
│
├── puny2uni/                    ← Conversion tools
│   ├── puny2uni2.py            (CLI)
│   ├── puny2uni2gui.py         (GUI)
│   ├── puny2uni2.README.md
│   └── requirements_puny2uni2.txt
│
├── csv-s/                       ← Example CSV files
│   └── **/EXAMPLE_*.csv        (only these tracked in git)
│
└── ai-hist_hnsell/              ← Historical versions
    └── hnsell.py.old2          (legacy tkinter version)
```

## Applications Suite

This project includes complementary applications for different workflows:

### **1. hnsell.py** (Primary - wxPython GUI)

Full-featured 3-tab interface for CSV processing, conversion, and HTML portfolio generation

- **Best for**: Complete workflow from CSV import to portfolio generation
- **GUI**: wxPython (superior PageMaker scrolling)
- **Status**: Production ready v0.4.0

### **2. pagemaker/pagemaker2.py** (Standalone)

HTML portfolio generator with theme customization

- **Best for**: Generating portfolios without full CSV processing pipeline
- **GUI**: tkinter
- **See**: [pagemaker/pagemaker.README.md](pagemaker/pagemaker.README.md)

### **3. puny2uni/puny2uni2.py** (CLI)

Command-line punycode/unicode converter with translation

- **Best for**: Scripting, batch automation, single-domain conversion
- **Interface**: CLI with interactive mode
- **See**: [puny2uni/puny2uni2.README.md](puny2uni/puny2uni2.README.md)

### **4. puny2uni/puny2uni2gui.py** (GUI)

Graphical batch converter with CSV processing

- **Best for**: Standalone conversion without full hnsell.py interface
- **GUI**: tkinter

## Features

## Key Features (v0.4.0)

### **New in v0.4.0**

- ✅ **Respect Existing Entries**: Preserve manual edits during reprocessing (checkbox option)
- ✅ **Translation Integration**: Google Translate API for PUNY_IDNA domains
- ✅ **Enhanced Language Detection**: 20+ languages/scripts (CJK, Arabic, Hebrew, Cyrillic, Hawaiian, etc.)
- ✅ **Smart Descriptions**: Emoji character names, language identification
- ✅ **Project Reorganization**: Standalone tools in subdirectories
- ✅ **Example CSV Files**: 11 generic examples (git-tracked, private CSVs excluded)

### HNSell GUI (hnsell.py - wxPython)

#### 3-Tab Interface

##### Tab 1: Punytag Processor

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
- **Data Preservation** (New in v0.4.0):
  - Respect existing entries checkbox (default: checked)
  - Skips domains with existing descript-IDNA or translate-IDNA values
  - Prevents overwriting manual edits during reprocessing
- **Translation Support** (New in v0.4.0):
  - Optional Google Translate API integration
  - Target language selection (en, es, fr, de, ja, zh-CN, etc.)
  - Requires `deep-translator` package (graceful fallback if missing)
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

### Puny2uni2 CLI (puny2uni2.py)

Standalone command-line tool for advanced punycode conversion with translation support.

**Features**:

- Single domain conversion
- Batch file processing (.txt and .csv)
- Automatic language detection (50+ languages including CJK, Arabic, Hebrew, Russian, Greek, Thai, Hindi, Hawaiian, etc.)
- Translation to 100+ languages via Google Translate (requires deep-translator)
- Interactive mode for exploratory conversion
- CSV processing with respect for existing values
- Validation level tagging (PUNY_IDNA, PUNY_ALT, PUNY_INVALID)

**Usage Examples**:

```bash
# Convert single domain
python puny2uni2.py xn--wgv71a

# Convert with translation
python puny2uni2.py xn--wgv71a --translate

# Process text file
python puny2uni2.py domains.txt

# Process CSV with translation
python puny2uni2.py domains.csv -t -l es

# Override existing values in CSV
python puny2uni2.py domains.csv -t --override

# Interactive mode
python puny2uni2.py -i
```

**CSV Processing Options**:

- `--translate` or `-t`: Enable translation
- `--lang XX` or `-l XX`: Set target language (default: en)
- `--override`: Re-process domains even if they have existing descript/translate values
- Default behavior: Respects existing entries to preserve manual edits

### Puny2uni2 GUI (puny2uni2gui.py)

Graphical interface for puny2uni2 with three tabs:

**Tab 1: Single Convert**:

- Live single domain conversion
- Real-time translation (optional)
- Shows validation level and detected language
- Copy result to clipboard

**Tab 2: Batch TXT Files**:

- Process multiple .txt files at once
- Recursive folder scanning
- Progress tracking with translation counter
- Creates `_uni.txt` or `_puny.txt` output files

**Tab 3: CSV Files**:

- Auto-detects CSV format (Bob, Namebase, Shakestation, Firewallet)
- Adds unicode, descript-IDNA, and translate-IDNA columns
- **Respects existing entries** by default (checkbox option)
- Uncheck to override and re-process all domains
- Progress window with translation counter

**Usage**:

```bash
python puny2uni2gui.py
```

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
- **Required packages**:

```bash
# For HNSell GUI (hnsell.py)
pip install -r requirements.txt
```

**Main Application Dependencies** (`requirements.txt`):

- `wxPython` - GUI framework (PRIMARY)
- `pandas>=2.2.0` - CSV processing
- `idna>=3.6` - Punycode conversion
- `deep-translator` - Translation (optional - graceful fallback)

**Standalone Tools**:

```bash
# For puny2uni2 CLI/GUI
pip install -r puny2uni/requirements_puny2uni2.txt

# For pagemaker2 (uses system tkinter)
pip install pandas idna
```

**Notes**:

- `tkinter` usually included with Python (required for standalone tools)
- `deep-translator` optional for translation features
- On Linux: `sudo apt-get install python3-tk python3-wxgtk4.0`

### Running the Applications

```bash
# PRIMARY: HNSell full GUI (wxPython)
python hnsell.py

# Standalone PageMaker HTML generator
python pagemaker/pagemaker2.py

# Puny2uni2 CLI (with translation support)
python puny2uni/puny2uni2.py -h

# Puny2uni2 GUI (batch converter)
python puny2uni/puny2uni2gui.py

# Legacy tkinter version (if needed)
python ai-hist_hnsell/hnsell.py.old2
```

**Important**: Paths changed in v0.4.0 - standalone tools moved to subdirectories. See [RELEASE_NOTES_v0.4.0.md](RELEASE_NOTES_v0.4.0.md) for migration details.

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
   - ☑ **Respect existing entries** (default: checked) - Preserves manual edits
   - ☑ **Enable translations** (requires deep-translator) - Target language: en, es, fr, etc.
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

### HNSell GUI (hnsell.py)

The main application stores settings, profiles, and logs in the `hnsell_data/` subdirectory:

- **hnsell_settings.json** - Auto-saved settings (last session)
- **hnsell_profile_*.json** - Named profiles (via Settings Manager)
- **hnsell_processing.log** - Processing history with timestamps

These files are automatically created and gitignored.

## Troubleshooting

### Common Issues

1. **"No module named 'wx'" or "No module named 'wxPython'"** (hnsell.py):
   - Install wxPython: `pip install wxPython`
   - On Linux: `sudo apt-get install python3-wxgtk4.0`
   - **Fallback**: Use legacy tkinter version at `ai-hist_hnsell/hnsell.py.old2`

2. **"No module named 'tkinter'"** (standalone tools):
   - On Linux: `sudo apt-get install python3-tk`
   - On Mac: Tkinter should be included with Python
   - On Windows: Reinstall Python with tkinter option selected

3. **Translation features disabled**:
   - Install deep-translator: `pip install deep-translator`
   - Requires internet connection for Google Translate API

4. **CSV not detected correctly**:
   - Check that CSV has proper headers
   - Verify file is valid CSV format

5. **Punycode conversion errors**:
   - Some punycode domains may be invalid
   - Check the PUNY_INVALID tag in output

6. **Log file location** (hnsell.py):
   - Processing log: `hnsell_data/hnsell_processing.log`
   - Check for detailed error messages and timestamps

## Additional Documentation

- **[RELEASE_NOTES_v0.4.0.md](RELEASE_NOTES_v0.4.0.md)** - Complete migration guide and feature list
- **[pagemaker/pagemaker.README.md](pagemaker/pagemaker.README.md)** - Standalone PageMaker documentation
- **[puny2uni/puny2uni2.README.md](puny2uni/puny2uni2.README.md)** - CLI converter documentation
- **[hnsell.README.md](hnsell.README.md)** - hnsell.py-specific application guide

## Author

Based on original punycode processing scripts by [@i1li](https://github.com/i1li)

Expanded and maintained by timaxal

## Version History

- **v0.4.0** (2026-01-11) - Major architectural reorganization, translation support, data preservation
- **v0.3.x** - Language detection, enhanced descriptions
- **v0.2.x** - PageMaker integration, multi-source support
- **v0.1.0** (2025-12-26) - Initial GUI release
