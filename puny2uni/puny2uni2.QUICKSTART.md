# puny2uni2 - Quick Start Guide

## Installation (2 minutes)

### Step 1: Install Required Package
```bash
pip install idna
```

### Step 2: (Optional) Install Translation Support
```bash
pip install deep-translator
```

Or use the requirements file:
```bash
pip install -r requirements_puny2uni2.txt
```

## Quick Examples

### 1. Convert a Single Domain
```bash
python puny2uni2.py xn--wgv71a
```
Output:
```
Input (Punycode):  xn--wgv71a
Output (Unicode):  日本
Validation Level:  PUNY_IDNA
Detected Language: Chinese/Japanese/Korean
```

### 2. Interactive Mode (Most Beginner-Friendly!)
```bash
python puny2uni2.py -i
```
Then type any domain:
```
Enter domain (or command): xn--fiqs8s
Input (Punycode):  xn--fiqs8s
Output (Unicode):  中国
Validation Level:  PUNY_IDNA
Detected Language: Chinese/Japanese/Korean

Enter domain (or command): quit
```

### 3. Process a File
```bash
python puny2uni2.py sample_punycode_domains.txt
```
Creates: `sample_punycode_domains_uni.txt` with all conversions

### 4. With Translation (Requires deep-translator)
```bash
python puny2uni2.py xn--wgv71a --translate
```
Output includes:
```
Translation (en): Japan
```

## Common Use Cases

### Convert Your Handshake Domains
1. Export your domains to a text file (one per line)
2. Run: `python puny2uni2.py my_domains.txt`
3. Check the output file: `my_domains_uni.txt`

### Find Out What a Domain Means
```bash
python puny2uni2.py xn--mgbayh7gpa --translate
```

### Create Punycode from Unicode
```bash
python puny2uni2.py 日本
```
Output: `xn--wgv71a`

## Interactive Mode Commands

When in interactive mode (`python puny2uni2.py -i`):

- Enter any domain to convert it
- `translate on` - Enable translation
- `translate off` - Disable translation
- `lang es` - Change target language to Spanish
- `lang fr` - Change to French
- `help` - Show commands
- `quit` or `exit` - Exit

## Supported Languages

Auto-detects: Japanese, Chinese, Korean, Arabic, Hebrew, Russian, Greek, Thai, Hindi, Tamil, Malayalam, Georgian, Armenian, Hawaiian, and more!

Translates to: English, Spanish, French, German, Italian, Portuguese, and 100+ other languages!

## File Formats

### Input
- Text files (.txt) with one domain per line
- Can be punycode OR unicode
- Auto-detects conversion direction

### Output
- `filename_uni.txt` - Converted domains (if input was punycode)
- `filename_puny.txt` - Converted domains (if input was unicode)
- `filename_uni_translations.txt` - With translations (if -t flag used)

## Tips

1. **Test first**: Try a single domain before processing large files
2. **Use interactive mode**: Best for exploring and learning
3. **Translation optional**: Core conversion works without deep-translator
4. **Batch processing**: Process hundreds of domains at once
5. **Check validation**: PUNY_IDNA = safe, PUNY_ALT = caution, PUNY_INVALID = check manually

## Need Help?

Run with `-h`:
```bash
python puny2uni2.py -h
```

Or read the full documentation: `puny2uni2.README.md`

## Example Workflow

```bash
# 1. Get your Handshake domains (from Bob Wallet, Namebase, etc.)
# 2. Create domains.txt with one domain per line
# 3. Convert them:
python puny2uni2.py domains.txt -t

# 4. Check the results:
#    - domains_uni.txt (converted)
#    - domains_uni_translations.txt (with English translations)
```

That's it! 🎉
