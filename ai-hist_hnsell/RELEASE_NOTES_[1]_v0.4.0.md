# HNSell v0.4.0 Update Summary - Major Feature Release

## **Overview**
Significant feature additions, architectural reorganization, and improvements to the main application including translation support, data preservation logic, and enhanced CSV processing capabilities.

---

## **🏗️ ARCHITECTURAL CHANGES**

### **Primary Application Consolidation**
- **hnsell.py (tkinter)** → renamed to `hnsell.py.old2` and moved to `ai-hist_hnsell/`
- **hnsell_wx.py (wxPython)** → **renamed to `hnsell.py`** as the **PRIMARY version**
- **Rationale**: wxPython version has superior PageMaker tab scrolling and better performance
- **Impact**: `hnsell.py` now refers to the wxPython implementation (not tkinter)

### **Project Reorganization**
```
hnsell[junct]/
├── hnsell.py                    ← PRIMARY (formerly hnsell_wx.py)
├── hnsell.README.md
├── requirements.txt
│
├── pagemaker/                   ← NEW directory
│   ├── pagemaker2.py           ← Standalone HTML generator (moved)
│   └── pagemaker.README.md     ← NEW comprehensive documentation
│
├── puny2uni/                    ← NEW directory
│   ├── puny2uni2.py            ← CLI converter (moved)
│   ├── puny2uni2gui.py         ← GUI converter (moved)
│   ├── puny2uni2.README.md     ← Documentation (moved)
│   ├── puny2uni2.QUICKSTART.md
│   ├── puny2uni2.CSV_TEST_RESULTS.md
│   └── requirements_puny2uni2.txt
│
├── csv-s/                       ← Example CSV files
│   ├── csv-bob/
│   │   ├── csv_bob-tr/
│   │   │   └── EXAMPLE_bob-tr_transactions.csv
│   │   └── csv_bob-tld/
│   │       ├── EXAMPLE_bob-tld_domains.csv
│   │       └── EXAMPLE_bob-tld_domains_with_price_email.csv
│   ├── csv-nb/ (similar structure)
│   ├── csv-ss/ (similar structure)
│   └── csv-fw/ (similar structure)
│
└── ai-hist_hnsell/              ← Historical versions
    └── hnsell.py.old2           ← Former tkinter version
```

**Benefits:**
- ✅ Clearer project structure
- ✅ Standalone tools isolated in subdirectories
- ✅ Example files organized by wallet type
- ✅ GitHub-ready (private CSVs excluded via .gitignore)
- ✅ No relative path dependencies between tools

---

## **🆕 NEW FEATURES**

### **1. Respect Existing Entries (Data Preservation)**
- **Checkbox option** (default: **CHECKED**) to preserve manual edits during reprocessing
- Skips domains that already have `descript-IDNA`, `description`, or `translate-IDNA` values
- Prevents overwriting user-customized descriptions and translations
- Displays skip counter: `ℹ Skipped {n} domains (already have descript/translate values)`
- **Location**: Punytag Processor tab → Output Options section
- **Implementation**: All 6 CSV processing methods in `hnsell.py`

### **2. Translation Integration (Google Translate API)**
- **Optional translation** of PUNY_IDNA unicode domains to target language
- Adds `translate-IDNA` column with translated text
- **UI Controls**: 
  - Enable/disable checkbox
  - Target language field (default: 'en')
  - Supported formats: en, es, fr, de, ja, zh-CN, etc.
- **Dependency**: `deep-translator` package (optional - graceful fallback if not installed)
- Translation only applies to PUNY_IDNA tagged domains with unicode values

### **3. Language & Script Detection
Automatic language identification for unicode domains:
CJK Scripts: Chinese/Japanese/Korean (U+4E00-9FFF)
Japanese: Hiragana (U+3040-309F), Katakana (U+30A0-30FF)
Middle Eastern: Arabic/Urdu/Uyghur (U+0600-06FF), Hebrew (U+0590-05FF)
European: Cyrillic (U+0400-04FF), Greek (U+0370-03FF), Latin Extended (U+0100-024F)
South Asian: Devanagari/Hindi (U+0900-097F), Tamil (U+0B80-0BFF), Malayalam (U+0D00-0D7F)
  - **Pacific**: Hawaiian (macron vowels: ā ē ī ō ū)
  - **Other**: Thai, Georgian, Armenian
- Language tags added to domain `tags` column for filtering

### **4. Example CSV Files**
- **11 comprehensive examples** covering all supported wallet formats
- Both basic and user-column-enhanced variants
- Smart description generation:
  - Pure emoji → "💰 MONEY BAG + 🏠 HOUSE"
  - Language-specific → "Japanese", "Arabic", "Hawaiian"
  - Mixed content → "Letters + SPARKLES, HEART"

---haracter name descriptions
Official Unicode character names via unicodedata.name()
Smart description generation:
Pure emoji domains → "💰 MONEY BAG + 🏠 HOUSE"
Language-specific → "Japanese", "Arabic", "Hawaiian"
Mixed content → "Letters + SPARKLES, HEART"
🔧 IMPROVEMENTS
CSV Processing Enhancements
Categorization tags now included in all processing methods:
Digit tags: 3D, 4D, 5D, 6D, 7D (pure numeric domains)
Letter tags: 3L, 4L, 5L (pure alphabetic, no hyphens/underscores)
Character tags: 3C, 4C, 5C (mixed with hyphens/underscores)
Punycode validation levels: PUNY_IDNA, PUNY_ALT, PUNY_INVALID
Column order preservation:
Original columns remain in place (critical for Shakestation CSV uploads)
New columns (unicode, descript-IDNA, translate-IDNA, tags) appended at end
wxPython Version (hnsell_wx.py) - PRODUCTION
Fully functional PageMaker tab scrolling (resolved scrolling issues)
Uses wx.lib.scrolledpanel.ScrolledPanel with optimized scroll rates
.GetValue() syntax for checkbox/textctrl state retrieval
Better performance and native OS look-and-feel
Recommended for production use
Tkinter Version (hnsell.py) - SECONDARY
Complete feature parity with wxPython version
Known issue: PageMaker tab scrolling not optimal
.get() syntax for variable retrieval
Cross-platform fallback option
📦 DEPENDENCIES
Required:

pandas >= 2.2.0 - CSV manipulation
idna >= 3.6 - Punycode encoding/decoding
wxPython (for hnsell_wx.py) OR tkinter (for hnsell.py)
Optional:

deep-translator - Google Translate API integration
Install: pip install deep-translator
If missing: Translation checkbox disabled, graceful fallback
## **💾 DATA SAFETY**

### **File Handling**
- Date-stamped outputs: `filename_YYYYMMDD.csv`
- Already-processed files automatically skipped
- `_orig` suffix option for source file backup
- Optional original file deletion after successful processing
- Unicode escape sequence cleanup

### **Default Behavior**
**Respect Existing = CHECKED** (default)
- Preserves manual edits to `descript-IDNA` and `translate-IDNA`
- Only new/empty rows get auto-generated values
- Re-run processor safely without losing work

**Override Mode** (uncheck Respect Existing)
- All domains regenerated
- Useful for language retargeting, bulk corrections

---

**PageMaker (pagemaker/pagemaker2.py):**
## **🐛 BUG FIXES**

1. **PageMaker tab scrolling** - Fully functional in wxPython version
2. **F-string syntax errors** - Removed escaped quotes
3. **Multiple identical patterns** - Added unique context
4. **CSV malformed data** - Fallback parsing with `quoting=1, escapechar='\\'`
5. **Column name case sensitivity** - Case-insensitive header detection

---
- `tkinter` (GUI version only)

---
Smooth scrolling in PageMaker tab
Native color picker dialogs for 3-way theme customization
Better button styling with color-coded actions
🐛 BUG FIXES
F-string syntax errors - Removed escaped quotes causing SyntaxError
Multiple identical patterns - Added unique context to avoid ambiguous replacements
Tab3 scrolling - Resolved in wxPython version with proper ScrolledPanel setup
CSV malformed data - Added fallback parsing with quoting=1, escapechar='\\'
## **📊 CSV FORMAT SUPPORT**

**Auto-Detection for:**
- **Bob Wallet**: Transactions, Domain list
- **Namebase**: Transactions, Domain list
- **Shakestation**: Transactions, Domain list
- **Firewallet**: Domain exports

**Example Files**: See `csv-s/**/EXAMPLE_*.csv`

---previous versions
Output filename format unchanged
🚀 MIGRATION NOTES
From GitHub version → Local development version:

NEW in local:

✅ respect_existing_var checkbox + should_skip_row() method
✅ translate_text() method + enable_translation_var checkbox
✅ Language detection methods: detect_language(), get_language_tag()
✅ Enhanced descriptions: generate_description() with emoji/language support
✅ add_categorization_tags() - 3D-7D, 3L-5L, 3C-4C tagging
✅ Progress tracking with skip counters
Unchanged:

Core punycode validation logic
CSV source detection
File management (rename, delete, sort to subdirs)
PageMaker HTML generation
Puny↔Unicode conversion
📖 TESTING RECOMMENDATIONS
Test with sample files: Use new csv-s/**/EXAMPLE_*.csv files
Verify respect_existing:
Process once → manually edit descript/translate → reprocess → confirm preservation
## **🚀 MIGRATION NOTES**

### **From GitHub Version → v0.4.0**

**File Renames:**
- `hnsell_wx.py` → `hnsell.py` (primary)
- `hnsell.py` → `hnsell.py.old2` (moved to ai-hist)
- `pagemaker_standalone.py` → `pagemaker2.py` (moved to pagemaker/)

**New Structure:**
- `pagemaker/` directory created
- `puny2uni/` directory created
- Example CSV files in `csv-s/` subdirectories

**Code Changes:**
- ✅ `respect_existing_var` checkbox + `should_skip_row()` method
- ✅ `translate_text()` method + translation controls
- ✅ Language detection: `detect_language()`, `get_language_tag()`
- ✅ Enhanced `generate_description()` with emoji/language support
## **📖 TESTING RECOMMENDATIONS**

1. **Use example CSVs**: `csv-s/**/EXAMPLE_*.csv` files provided
2. **Test respect_existing**: 
   - Process → manually edit → reprocess → confirm preservation
3. **Test translation**: Requires `deep-translator` + internet
4. **Compare standalone tools**: Verify pagemaker2.py and puny2uni2.py work from new locations

---

## **VERSION INFO**

- **Version**: v0.4.0
- **Release Date**: January 11, 2026
- **Primary Application**: `hnsell.py` (wxPython - 2264 lines)
- **Legacy Version**: `ai-hist_hnsell/hnsell.py.old2` (tkinter - 3438 lines)
- **Status**: Production ready

---

## **SUMMARY OF CHANGES**

### **Renamed/Moved Files**
| Old Location | New Location | Notes |
|-------------|--------------|-------|
| `hnsell.py` | `ai-hist_hnsell/hnsell.py.old2` | Legacy tkinter version |
| `hnsell_wx.py` | `hnsell.py` | **PRIMARY** wxPython version |
| `pagemaker_standalone.py` → `pagemaker2.py` | `pagemaker/pagemaker2.py` | Standalone HTML generator |
| `puny2uni2.py` | `puny2uni/puny2uni2.py` | CLI converter |
| `puny2uni2gui.py` | `puny2uni/puny2uni2gui.py` | GUI converter |
| `puny2uni2.*.md` | `puny2uni/puny2uni2.*.md` | Documentation |
| `requirements_puny2uni2.txt` | `puny2uni/requirements_puny2uni2.txt` | Dependencies |

### **New Files**
- `pagemaker/pagemaker.README.md` - Comprehensive standalone documentation
- `csv-s/**/EXAMPLE_*.csv` - 11 example CSV files (all wallet formats)
- Updated `.gitignore` - Excludes all CSVs except EXAMPLE_*.csv

### **Feature Additions**
- ✅ Respect existing entries (data preservation)
- ✅ Translation integration (Google Translate API)
- ✅ Language & script detection (20+ languages/scripts)
- ✅ Enhanced emoji/character descriptions
- ✅ Categorization tags (3D-7D, 3L-5L, 3C-5C, language tags)

### **Infrastructure**
- ✅ Project reorganized into logical subdirectories
- ✅ All standalone tools isolated
- ✅ No relative path dependencies
- ✅ GitHub-ready structure with privacy-aware .gitignore
- ✅ Comprehensive documentation for all components

---

## **BACKWARDS COMPATIBILITY**

✅ **Fully backward compatible:**
- Old CSV files process identically
- Output format unchanged
- All existing features preserved
- New features opt-in only

⚠️ **Path changes only:**
- Update import paths if programmatically calling standalone tools
- Update shell scripts/shortcuts to use new file locations
- Main application now `hnsell.py` instead of `hnsell_wx.py`

---

**End of v0.4.0 Update Summary**
## **📝 WORKFLOW CHANGES**

### **Running Applications**

**Main Application (CHANGED):**
```bash
python hnsell.py          # Now runs wxPython version (was hnsell_wx.py)
```

**Standalone Tools (PATHS CHANGED):**
```bash
python pagemaker/pagemaker2.py         # Formerly in root directory
python puny2uni/puny2uni2.py          # Formerly in root directory  
python puny2uni/puny2uni2gui.py       # Formerly in root directory
```

**Legacy tkinter version:**
```bash
python ai-hist_hnsell/hnsell.py.old2  # Former primary version
```

### **No Relative Path Issues**
- ✅ All standalone tools fully independent
- ✅ No imports between directories
- ✅ Each tool contains all required methods
- ✅ READMEs updated with correct paths

---