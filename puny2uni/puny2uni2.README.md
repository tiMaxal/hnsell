# puny2uni2.py - Enhanced Punycode ⟷ Unicode Converter

A standalone Python application for converting between Punycode and Unicode with automatic language detection and translation capabilities.

## Features

✅ **Bidirectional Conversion**
- Punycode → Unicode (decoding)
- Unicode → Punycode (encoding)

✅ **CSV Processing** (NEW!)
- Auto-detects HNS platform formats (Bob, Namebase, Shakestation, Firewallet)
- Adds `descript-IDNA` column with detected language
- Adds `translate-IDNA` column with translations
- Preserves Shakestation's first 6 columns (upload compatibility)
- Processes 1,800+ domain files efficiently

✅ **Language Detection**
- Automatic detection of 15+ languages and scripts
- CJK (Chinese/Japanese/Korean)
- Arabic, Hebrew, Cyrillic
- Greek, Thai, Hindi, Tamil, Malayalam
- Georgian, Armenian, Hawaiian
- European languages with diacritics

✅ **Translation Support**
- Translate decoded Unicode to English or 100+ languages
- Uses Google Translate API (free)
- Batch translation for multiple domains

✅ **Validation Levels**
- `PUNY_IDNA`: Strict IDNA compliance (highest level)
- `PUNY_ALT`: Alternative punycode (may have rendering issues)
- `PUNY_INVALID`: Contains invalid/non-rendering characters

✅ **Multiple Usage Modes**
- Command-line processing
- Batch file processing
- Interactive mode
- Single domain conversion

## Installation

### Basic Installation
```bash
pip install -r requirements_puny2uni2.txt
```

Or install dependencies manually:
```bash
pip install idna>=3.6
pip install pandas>=2.2.0          # Required for CSV processing
pip install deep-translator>=1.11.4 # Required for translation
```

## Usage

### 1. CSV Processing (NEW! - Process HNS Platform Exports)

**Supported Platforms:**
- Bob Wallet (bob-tld, bob-tr)
- Namebase (nb-tld, nb-tr)
- Shakestation (ss-tld, ss-tr) - First 6 columns preserved!
- Firewallet (fw)

```bash
# Auto-detect format and add translations
python puny2uni2.py domains.csv -t

# Translate to Spanish
python puny2uni2.py domains.csv -t -l es

# Translate to French
python puny2uni2.py domains.csv -t -l fr

# Custom output path
python puny2uni2.py input.csv -t -o output.csv
```

**What it does:**
- Detects CSV format automatically
- Adds `descript-IDNA` column (detected language)
- Adds `translate-IDNA` column (translation)
- Preserves original column order (especially Shakestation first 6)
- Creates timestamped output file

**Example Output:**
```
Original: domains.csv
Output:   domains_20260107_translated.csv

New columns added:
- descript-IDNA: "Chinese/Japanese/Korean", "Hebrew", etc.
- translate-IDNA: English translation (or target language)
```

### 2. Interactive Mode (Recommended for Beginners)
```bash
python puny2uni2.py -i
```

Example session:
```
Enter domain (or command): xn--n3h
Input (Punycode):  xn--n3h
Output (Unicode):  ☃
Validation Level:  PUNY_IDNA
Detected Language: Emoji

Enter domain (or command): translate on
✓ Translation enabled (target: en)

Enter domain (or command): xn--wgv71a
Input (Punycode):  xn--wgv71a
Output (Unicode):  日本
Validation Level:  PUNY_IDNA
Detected Language: Japanese
Translation (en): Japan

Enter domain (or command): quit
```

### 2. Single Domain Conversion
```bash
# Punycode to Unicode
python puny2uni2.py xn--wgv71a

# Unicode to Punycode
python puny2uni2.py 日本

# With translation
python puny2uni2.py xn--wgv71a --translate

# Translate to specific language
python puny2uni2.py xn--wgv71a --translate --lang es
```

### 3. Batch File Processing

**Input file format** (one domain per line):
```
xn--wgv71a
xn--fiqs8s
xn--n3h
xn--80akhbyknj4f
```

**Convert file:**
```bash
# Basic conversion
python puny2uni2.py domains.txt

# With translation to English
python puny2uni2.py domains.txt -t

# Translate to Spanish
python puny2uni2.py domains.txt -t -l es

# Specify output file
python puny2uni2.py domains.txt -o converted.txt
```

**Output:**
- Main output: `domains_uni.txt` (converted domains)
- Translations: `domains_uni_translations.txt` (with translations)

### 4. Command-Line Options

```
usage: puny2uni2.py [-h] [-i] [-t] [-l LANG] [-o OUTPUT] [-v] [input]

positional arguments:
  input                 Input file or domain to convert

optional arguments:
  -h, --help            Show help message
  -i, --interactive     Interactive mode
  -t, --translate       Enable translation
  -l LANG, --lang LANG  Target language for translation (default: en)
  -o OUTPUT, --output   Output file path (for file processing)
  -v, --version         Show version
```

## Examples

### Example 1: Convert Handshake Domains
```bash
# Input: hns_domains.txt
xn--80akhbyknj4f
xn--wgv71a
xn--fiqs8s
xn--mgbayh7gpa

# Command
python puny2uni2.py hns_domains.txt -t

# Output: hns_domains_uni.txt
Россия
日本
中国
الاردن

# Output: hns_domains_uni_translations.txt
Россия | Russia
日本 | Japan
中国 | China
الاردن | Jordan
```

### Example 2: Unicode to Punycode
```bash
# Input: unicode_names.txt
日本
中国
Россия
العربية

# Command
python puny2uni2.py unicode_names.txt

# Output: unicode_names_puny.txt
xn--wgv71a
xn--fiqs8s
xn--80akhbyknj4f
xn--mgbah7gpa
```

### Example 3: Interactive Translation
```bash
python puny2uni2.py -i

Enter domain (or command): translate on
Enter domain (or command): lang es
✓ Target language set to: es

Enter domain (or command): xn--wgv71a
Input (Punycode):  xn--wgv71a
Output (Unicode):  日本
Validation Level:  PUNY_IDNA
Detected Language: Japanese
Translation (es): Japón
```

## Supported Languages

The app automatically detects and can translate these language families:

| Language Family | Script | ISO Code | Example |
|----------------|--------|----------|---------|
| Chinese/Japanese/Korean | CJK | zh-CN, ja, ko | 日本, 中国 |
| Japanese | Hiragana/Katakana | ja | ひらがな |
| Arabic/Urdu | Arabic | ar | العربية |
| Hebrew | Hebrew | he | עברית |
| Russian/Ukrainian | Cyrillic | ru | Россия |
| Greek | Greek | el | Ελληνικά |
| Thai | Thai | th | ไทย |
| Hindi | Devanagari | hi | हिन्दी |
| Tamil | Tamil | ta | தமிழ் |
| Malayalam | Malayalam | ml | മലയാളം |
| Georgian | Georgian | ka | ქართული |
| Armenian | Armenian | hy | Հայերեն |
| Hawaiian | Latin+Macrons | haw | Hawaiʻi |

Translation target languages support 100+ languages via Google Translate.

## Technical Details

### Validation Levels

1. **PUNY_IDNA** (Strict)
   - Fully IDNA-compliant
   - Guaranteed to render correctly
   - Safe for DNS usage

2. **PUNY_ALT** (Alternative)
   - Decoded via lenient parsing
   - May have rendering inconsistencies
   - Use with caution

3. **PUNY_INVALID**
   - Contains invalid characters
   - May not display properly
   - Not recommended for use

### Character Description

For PUNY_IDNA level domains, the app provides:
- Emoji character names (e.g., "SNOWMAN")
- Language family identification
- Script classification

## Troubleshooting

### Translation Not Working

If you see:
```
Warning: deep-translator not installed. Translation features disabled.
```

Install the translation library:
```bash
pip install deep-translator
```

### File Encoding Issues

If you encounter encoding errors:
```bash
# Save your input file with UTF-8 encoding
# In most text editors: File → Save As → Encoding: UTF-8
```

### Invalid Punycode

If a domain shows `PUNY_INVALID`:
- The punycode may be malformed
- Contains characters that don't render properly
- May need manual verification

## Integration with HNSell

This standalone app extracts the core conversion logic from HNSell's Tab 1 (Punytag Processor) and enhances it with:
- Standalone execution (no GUI required)
- Command-line interface
- Translation capabilities
- Batch processing optimization

You can use this alongside HNSell for:
1. Quick domain lookups (use puny2uni2.py)
2. CSV processing (use HNSell)
3. Portfolio generation (use HNSell)

## License

This tool is part of the HNSell project.
Forked from original punytag tools by [@i1li](https://github.com/i1li)

## Contributing

Contributions welcome! Areas for improvement:
- Additional translation providers (DeepL, Microsoft Translator)
- OCR integration for image-based domains
- Web interface
- Pronunciation guides for detected languages

## Version History

**v2.0** (Current)
- ✅ Standalone execution
- ✅ Translation support (15+ languages)
- ✅ Interactive mode
- ✅ Batch processing
- ✅ Validation levels
- ✅ Language detection

**v1.0** (HNSell Tab 2)
- Basic punycode/unicode conversion
- File processing (.txt only)
