# PageMaker - Standalone HTML Portfolio Generator

**Version:** 2.0 (Standalone)  
**Status:** Fully independent - no external project dependencies

## Overview

PageMaker is a **fully standalone** tkinter application for generating beautiful, responsive HTML portfolio pages from Handshake domain CSV exports. Unlike the integrated PageMaker tab in the main HNSell application, this version can run completely independently without any other project files.

## Features

- ✅ **Standalone Operation** - All processing methods included directly (no imports from hnsell.py)
- 📊 **Multi-Source Support** - Namebase, Shakestation, Bob Wallet, and Firewallet CSV exports
- 🎨 **Theme Customization** - Dark/light toggle, 3-way theme switch, or custom CSS
- 🏷️ **Smart Tagging** - Automatic categorization by character type, length, and language
- 🌍 **Unicode Support** - Full punycode validation with PUNY_IDNA, PUNY_ALT, and PUNY_INVALID tagging
- 📧 **Contact Integration** - Price and email display with copy-to-clipboard functionality
- 🔍 **Advanced Filtering** - Search by name, filter by price range, tag-based navigation
- 📱 **Responsive Design** - Mobile-friendly grid/list toggle view

## Usage

### Launch the Application

```bash
python pagemaker2.py
```

### Select CSV Files

1. Click **"Select CSV Files"** or use **"Select Folder (Recursive)"** to find CSV exports
2. Multiple files can be selected and processed together
3. Supported formats auto-detected:
   - Namebase TLD/transactions
   - Shakestation TLD/transactions  
   - Bob Wallet TLD
   - Firewallet exports

### Configure Options

**Sort Order:**
- Random (default)
- Alphabetical ▲/▼
- Price ▲/▼

**Theme:**
- dark+light (default toggle)
- 3-way switch (light/medium/dark with custom colors)
- Custom CSS file

**Display:**
- ☑ List all domains (ignore email/price requirements for Bob/Firewallet)
- ☑ Include descriptions/translations (grid/list toggle on page)
- Auto-append email format: `user@gmail.com` or `user+@gmail.com` (for price-tagged domains)

### Generate Portfolio

1. Set output filename (default: `portfolio.html`)
2. Click **"Generate Portfolio"**
3. Open the generated HTML file in any modern browser

## Output Format

### HTML Features

- **Navigation Bar** - Tag-based filtering (All Names, PUNY_IDNA, 3L, CJK, etc.)
- **Search Bar** - Real-time name filtering with price range inputs
- **Grid/List Toggle** - Switch between compact grid and detailed list views
- **Marketplace Links** - Direct links to Namebase/Shakestation listings
- **Dark Mode** - User-controlled theme switching
- **Zoom Controls** - Font size adjustment buttons
- **Sort Functionality** - Client-side sorting (Random, A-Z, Z-A, Price ▲▼)

### Domain Display

**Grid View:**
- Unicode display (if punycode)
- Punycode domain with marketplace link
- Descriptions/translations (optional)
- Price and email button (bottom)

**List View:**
- Horizontal layout with all info inline
- Descriptions aligned right
- Better for scanning long lists

## CSV Format Requirements

### Namebase TLD
```csv
name,price_hns,status
example,100.0,ACTIVE
xn--e1afmkfd,250.0,ACTIVE
```

### Shakestation TLD
```csv
domain,for_sale,price,description
example,TRUE,100.0,Example domain
xn--e1afmkfd,TRUE,250.0,Premium unicode
```

### Bob Wallet TLD
```csv
domains
example
xn--e1afmkfd
```

### Firewallet
```csv
name,expiry,state,value
example,2025-12-31,REGISTERED,5.5
xn--e1afmkfd,2025-12-31,REGISTERED,7.25
```

### User-Added Columns

PageMaker recognizes these optional columns:
- `email` - Contact email for inquiries
- `price` - Price in HNS (Bob/FW only, others have built-in)
- `descript-IDNA` - Custom description text
- `translate-IDNA` - Translation text
- `unicode` - Pre-converted unicode representation
- `tags` - Comma-separated tag list

## Advanced Features

### Email Auto-Append

**Format:** `user@gmail.com` or `user+@gmail.com`

For Bob Wallet and Firewallet exports without email columns:
- Plain format: `user@gmail.com` → all domains get same email
- Plus format: `user+@gmail.com` → becomes `user+domainname@gmail.com`

Example: `seller+@gmail.com` for domain `example` → `seller+example@gmail.com`

### Custom CSS

Select a `.css` file to completely override the default styling:
- Must include all required classes (`.col`, `.grid`, `.domain-puny`, etc.)
- JavaScript functionality remains unchanged
- Useful for branding/corporate themes

### HTML Update Mode

Select an existing HTML file to **add new domains** without regenerating:
- Preserves existing domains
- Adds only new entries from selected CSVs
- Useful for incremental portfolio updates

**Note:** Shakestation domains with `for_sale=FALSE` are removed on update.

### Footer & Credits

Optional HTML snippets injected into the portfolio:
- **Footer** - Added after domain grid (contact info, legal, etc.)
- **Credits** - Added at bottom (attributions, powered-by, etc.)

Must be valid HTML fragments (no `<html>`, `<body>` tags).

## Tag System

PageMaker automatically generates tags for filtering:

### Length Tags
- `3D`, `4D`, `5D`, `6D`, `7D` - Pure digit domains
- `3L`, `4L`, `5L` - Pure letter domains (no hyphens)
- `3C`, `4C`, `5C` - Mixed character domains

### Punycode Tags
- `PUNY_IDNA` - Strict IDNA-compliant unicode (safe for all browsers)
- `PUNY_ALT` - Alternative punycode (may have inconsistent rendering)
- `PUNY_INVALID` - Contains invalid/non-rendering characters

### Language Tags
- `CJK` - Chinese/Japanese/Korean
- `Japanese` - Hiragana/Katakana
- `Arabic` - Arabic script
- `Hebrew` - Hebrew script
- `Cyrillic` - Russian/Ukrainian
- `Greek`, `Thai`, `Hindi`, `Tamil`, `Malayalam`, `Georgian`, `Armenian`, `European`, `Hawaiian`

## Dependencies

**Required:**
- `pandas` - CSV processing
- `idna` - Punycode validation

**Install:**
```bash
pip install pandas idna
```

Or use requirements file:
```bash
pip install -r requirements.txt
```

## Comparison: Standalone vs Integrated

| Feature | PageMaker (Standalone) | HNSell Tab 3 |
|---------|------------------------|--------------|
| Independence | ✅ Runs alone | ❌ Requires hnsell.py |
| CSV Processing | ✅ Built-in | ✅ Shared methods |
| UI Framework | tkinter | wxPython |
| File Size | Larger (all methods) | Smaller (shared code) |
| Updates | Independent | Synced with main app |

**When to use standalone:**
- Quick portfolio generation without full HNSell setup
- Distribution to non-technical users
- Batch processing via scripts
- CI/CD pipeline integration

**When to use HNSell Tab 3:**
- Already using HNSell for CSV processing
- Need translation/description features
- Prefer wxPython scrolling behavior
- Want unified interface for all HNS operations

## File Locations

```
hnsell[junct]/
├── pagemaker/
│   ├── pagemaker2.py          ← This application
│   └── pagemaker.README.md    ← This file
├── html/
│   ├── credits.html           ← Example credits snippet
│   └── footer.html            ← Example footer snippet
└── csv-s/                     ← Example CSV files
    ├── csv-bob/
    ├── csv-nb/
    ├── csv-ss/
    └── csv-fw/
```

## Troubleshooting

**"No domains found in selected files"**
- Check CSV format matches supported sources
- Verify `for_sale=TRUE` for Shakestation domains (unless "List all" checked)
- Bob/FW require `email` or `price` columns with values (unless "List all" checked)

**"Malformed CSV" errors**
- Try different CSV export options from your wallet
- Check for unescaped quotes in description fields
- Use Excel/LibreOffice to clean and re-export

**Unicode characters not displaying**
- Ensure browser supports Unicode
- Check HTML file encoding is UTF-8
- Verify `unicode` column has valid unicode strings

**Email button not working**
- Browser must support Clipboard API (Chrome, Firefox, Edge)
- HTTPS required for clipboard access (or localhost)
- Check browser console for JavaScript errors

## License

Part of the HNSell project - Handshake Domain Manager  
See main project README for license information

## Support

For issues specific to PageMaker standalone:
- Check main project documentation
- Review example CSV files in `csv-s/` directories
- Ensure pandas and idna are installed

For HNSell integration issues, refer to the main application documentation.
