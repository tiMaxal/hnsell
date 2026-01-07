# HNS Punycode processor and Pagemaker

## 20251226

### Add FireWallet / ShakeStation functionality

- the apps in this dir manage Handshake HNS + TLD csv export files from
  - Namebase.io ['nb' - csv files in \HNS_PUNYTAG-PAGEMAKE\csv-s\csv-nb\csv_nb-tr + csv_nb-tld, for punytag_nb_tr.py and punytag_nb.py respectively]
  - and Bob-wallet ['bob' - csv files in \HNS_PUNYTAG-PAGEMAKE\csv-s\csv-bob\csv_bob-tr + csv_bob-tld, for punytag_bob_tr.py and punytag_bob.py respectively]
- an example processed bob_tr.csv exists, derived from hns_punytag-pagemake\csv-s\csv-bob\csv_bob-tr\hns_bob_22catchall.20251226.csv

- since the app was created [by github user @i1li], Firewallet ['fw' - csv files in \HNS_PUNYTAG-PAGEMAKE\csv-s\csv-fw] and Shakestation.io ['ss' - csv files in \HNS_PUNYTAG-PAGEMAKE\csv-s\csv-ss\csv_ss-tr + csv_ss-tld] have come into existence, and it is desired to have new facility to process export files from those sources also
- at least one example file is present in each csv dir, for each type

- generate independent apps to process ss + fw exports, based on punytag_*.py
- adapt the code, for all apps, to delineate exports by headers, so explicit filenames are not needed [allowing individual export naming for user file-identification and sorting - the files may not always be in segregated dir's]

### create amalgamated GUI

- then, amalgamate all the apps into a gui, that will recognise the origin of picked [and/or dropped?] file[s] from their csv-headers and process each appropriately
- rename processed files with suffix `_orig` and output a new file with the required processing
- potentially include sorting the processed file[s] to sub-dir[s] according to source, with options to delete original, or move it too, or leave it in place
  - append date [yyyymmdd] to output filename

- enable recursive search for files to process
  - match already processed files if present, to not duplicate
  - provide checkbox processing
    - have 'select all/none' available

- incorporate facility for puny2uni.py, as another tab, similarly without need for explicit file-naming protocols if possible
  - headers may not be adequate for delineation
    - assume uni- or puny-code naming from single column [if csv] is 'bob-tld' file
    - only accept .txt files for purely uni2puny or puny2uni actions

- have a separate tab for 'pagemaker' action
- assess how tld sorting is assessed in pagemaker.py and provide
  - should be random initially, with button to sort alphanumerically[alph-num]
  - each press of 'sort' cycles random/alph-num-up/alph-num-down
  - the sort should only show already chosen category of tld [if any]
- pagemaker should be able to make the page from any format of csv, just using the tld column [ie, nb='name' or ss='domain']
  - if providing more than one file, links should go to the appropriate target site page, nb or ss, where the site sales pages addresses are as
    - <https://shakestation.io/domain/[tld>]
    - <https://www.namebase.io/domains/[tld>]
  - only add ss tlds if 'for_sale=TRUE'
- provide facility to update a page by
  - adding another nb csv to include tlds
  - processing a ss csv to remove tlds if marked 'for_sale=FALSE'
  - processing a custom csv to remove nb tlds
    - col's name,sell[as TRUE/FALSE]
    - do not change any tld not listed in the csv
- enable adding personalised footer/credits files

- provide the app with with a green 'process' button, yellow 'help' button with 'howto info' and red 'exit' button
- call the app hnsell

- an example html file \html\nb-sell.html is included for reference
  - it is an edited for personal use version of pagemaker output
- derive separate footer.html + credit.html files from 'footer' and 'credits' divs in nb-sell.html, for use with the pagemaker tab

### step 2

- 'sort TLDs' button should be available on the produced .html page [not as an app button .. tho useful - sort all additions to be processed, cycling by simply alph-num up/down, and separated by import file up/down]
- puny<=>uni should not process csv at all, only accept 'list' txt file[s]

## 20260102

### Initial Portfolio HTML Generation Testing

- First portfolio page generation (portfolio.1.html)
  - Basic dark/light mode toggle implementation
  - Sort button with 3-state cycling (Random → A-Z ▲ → Z-A ▼)
  - Simple marketplace linking (Namebase/Shakestation)
  - Foundation for tag-based navigation
  
- Theme system expansion (portfolio.5.html)
  - Introduced 3-way theme switching (Light → Dark → Black)
  - Added `body.black-theme` CSS styling
  - Custom color selection foundations

## 20260103

### Email/Contact Feature Development

- Portfolio 6-8 series: Contact information display testing
  - Testing Firewallet/Bob Wallet domain integration
  - Developing `domain-with-contact` span structure
  - Experimenting with email display alongside marketplace links
  - File naming pattern `[6+7]` indicates multi-source combination testing

## 20260104

### Email Copy Feature Implementation

- Portfolio.9 series: Email copy button functionality
  - Implemented `copyEmail(event, email)` JavaScript function
  - Added `copy-email-btn` CSS styling with hover effects
  - One-click clipboard copy with visual feedback (✓ confirmation)
  - Refined `cycleTheme()` function for 3-way theme toggle
  - Testing email display with and without prices (`[6+7]eml` variants)

## 20260105

### Price Filtering and GUI Version Consolidation

- Price range filtering feature (portfolio.10var+eml.html)
  - Added `min-price` and `max-price` input fields
  - Implemented price filtering in `searchNames()` function
  - `data-price` and `data-email` attributes for filtering logic
  - Clear filters button functionality
  
- Version 0-2-0 GUI implementation with Grok assistance
  - ScrollableFrame class for tall option-heavy tabs
  - Notebook-level canvas scrolling debugging
  - Multiple GUI layout iterations (hnsell.0-2-0.grok20260105.py)
  
- Feature testing and validation
  - test_description.py: Description/language tag feature testing
  - Generated portfolio.10var+eml.html and variants: Variable combinations testing
  - Firewallet-specific portfolios (portfolio.fw11eml+all.html series)
  
- Version snapshots created
  - hnsell_wx_full.0-1-0.py: wxPython version baseline
  - pagemaker_standalone.py: Standalone pagemaker functionality extraction
  - hnsell.py.old.py: Backup of previous working version

## 20260107

### Phase 1: Shakestation CSV Column Ordering Issue

- Problem identified: Tab1 Punytag Processor column placement incompatible with Shakestation uploads
  - User report: "ss reads first 6 col's on uploading an update for prices/descripts, etc"
  - Root cause: New columns (unicode, descript-IDNA, translate-IDNA, tags) were prepended at beginning of CSV
  - Impact: Disrupted Shakestation's reading of first 6 columns for price/description updates

### Phase 2: Column Ordering Solution Implementation

- Solution designed: Preserve original column order, append new columns at end
  - Store original columns before processing: `original_cols = df.columns.tolist()`
  - Apply all processing (unicode conversion, tag generation, PUNY validation)
  - Rebuild with appended columns: `col_order = original_cols + [col for col in new_cols if col not in original_cols]`

- Implementation in hnsell.py:
  - Modified `process_ss_tld()` function (lines 877-923)
    - Added line 892-893: Store original column order
    - Changed lines 914-917: Apply new column ordering logic
  - Modified `process_ss_tr()` function (lines 925-971)
    - Added line 939-940: Store original columns
    - Changed lines 962-965: Same appending logic

### Phase 3: Syntax Error Resolution

- Fixed syntax errors discovered during implementation in hnsell.py:
  - Line 917: Missing closing bracket `]` on `col_order` assignment
  - Missing: Complete `descript-IDNA` assignment line
  - Lines 937-940: Indentation error in `process_ss_tr()` - `if not domain_col:` and `original_cols` out of order
  - All errors resolved, code now syntactically correct

### Phase 4: Apply Fixes to WX Version

- User request: "perform the same fixes for hnsell_wx.py"
- Applied identical column ordering fixes to hnsell_wx_full.py:
  - Modified `process_ss_tld()` function (lines 1002-1042)
    - Added line 1017-1018: Store original columns
    - Changed lines 1036-1039: Append new columns at end
  - Modified `process_ss_tr()` function (lines 1115-1155)
    - Added line 1130-1131: Store original columns
    - Changed lines 1148-1151: Same appending logic
- Confirmed: Tab3 PageMaker uses headers for column identification (position-independent, no issues)

### Phase 5: In-App Help Text Updates

- Updated help text in hnsell.py (lines 742-757):
  - Added: "New columns (unicode, descript-IDNA, translate-IDNA, tags) are added at the END of the CSV to preserve original column order"
  - Added: "Shakestation compatibility: Original first 6 columns remain in place for upload updates"
  - Updated Tab 2 description: Clarified .txt-only processing for Puny ⟷ Unicode conversion
  - Updated Tab 3 description: Added non-custodial wallet support (Bob/Firewallet), price sorting options, tag navigation, theme selection

- Applied identical help text updates to hnsell_wx_full.py

### Phase 6: README.md Comprehensive Documentation Update

- User request: "check if readme/help need updating" with verification of all current features

#### Tab 2 (Puny ⟷ Unicode) - Verified .txt-only Processing
- Code verification: Lines 1182-1184 in hnsell.py confirm .txt file requirement
- Updated documentation:
  - Changed: "Multiple Format Support: TXT files/CSV files"
  - To: "Text File Processing: Works exclusively with .txt files (one domain per line)"
  - Added automatic direction detection explanation (xn-- prefix triggers puny-to-unicode)
  - Corrected output format: _uni.txt or _puny.txt (removed CSV references)

#### Tab 3 (PageMaker) - Expanded Feature Documentation
- Multi-source CSV support:
  - Changed: "Combine domains from Namebase and Shakestation"
  - To: "...Namebase, Shakestation, and non-custodial wallets (Firewallet or Bob exports)"
  - Added: "Or displays personal email for non-custodial wallet domains"

- Sorting functionality:
  - Expanded from 3 to 5 options: Random → A-Z ▲ → Z-A ▼ → Price ▲ → Price ▼
  - Documented button cycles through all sort modes

- Tag-based navigation:
  - Added: "Tag-Based Navigation: Name-type selection buttons automatically added when file is processed with Punytag Processor"
  - Examples: 3D, 3L, PUNY_IDNA, language tags (Chinese/Japanese/Korean, Arabic, Hebrew, etc.)

- Theme system:
  - Dark+Light toggle (default, automatic based on system preference)
  - 3-way switch (Light → Dark → Black with custom color selection)
  - Custom CSS file option

- Search and filtering:
  - Real-time domain name search
  - Price range filtering (min/max inputs)
  - Clear filters button

- Contact features:
  - Email copy button ('eml') with one-click clipboard copy
  - Smart linking system:
    - Namebase/Shakestation domains → Link to marketplace listing
    - Bob/Firewallet domains → Display contact info (price + email, no external link)

#### Usage Instructions Updates
- Converting Punycode section:
  - File selection: Changed to .txt files only
  - Automatic detection: Documented xn-- prefix logic
  - Output format: Corrected to .txt only

- Creating Portfolio Pages section:
  - Expanded from 5 to 6 detailed steps
  - Added Bob/Firewallet CSV preparation: "Add 'price' and 'email' columns for contact display"
  - Documented 5-option sort cycle
  - Added theme selection step
  - Added output file selection option
  - Added note about tag navigation from Punytag processing

#### Output Files Section
- Converted Files: Removed all CSV format references, .txt outputs only

#### Generated Portfolio Features Section
- Added 3-way theme toggle documentation
- Added specific tag examples with categories
- Added search function with price range filtering
- Added all 5 sort options explicitly
- Added email copy feature
- Added smart linking distinction (marketplace vs contact display)
- Removed outdated features: "Random Colors", generic "External Links"

### Result: Complete Documentation Synchronization

- All three documentation sources now consistent and current:
  - hnsell.py in-app help: ✅ Updated
  - hnsell_wx_full.py in-app help: ✅ Updated
  - hnsell.README.md: ✅ Comprehensive update (6 major sections revised)
- Shakestation CSV compatibility: ✅ Confirmed (first 6 columns preserved)
- All current features accurately documented: ✅ Complete
