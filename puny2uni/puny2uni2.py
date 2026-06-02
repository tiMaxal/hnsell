#!/usr/bin/env python3
"""
puny2uni2.py - Standalone Punycode ⟷ Unicode Converter with Translation
Enhanced version with language detection and translation capabilities

Features:
- Bidirectional punycode/unicode conversion
- Automatic language detection (CJK, Japanese, Arabic, Hebrew, etc.)
- Translation to English and other target languages
- Batch processing of .txt files
- Command-line interface and interactive mode

Usage:
    python puny2uni2.py input.txt              # Convert file
    python puny2uni2.py input.txt -t en        # Convert and translate to English
    python puny2uni2.py -i                     # Interactive mode
    python puny2uni2.py xn--domain --translate # Convert and translate single domain
"""

import sys
import os
import re
import codecs
import idna
import unicodedata
import argparse
import math
from pathlib import Path

# CSV processing
try:
    import pandas as pd
    CSV_AVAILABLE = True
except ImportError:
    CSV_AVAILABLE = False
    print("Warning: pandas not installed. CSV processing disabled.")
    print("Install with: pip install pandas")

# Translation library (install: pip install deep-translator)
try:
    from deep_translator import GoogleTranslator
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    print("Warning: deep-translator not installed. Translation features disabled.")
    print("Install with: pip install deep-translator")

class Puny2UniConverter:
    """Punycode/Unicode converter with language detection and translation"""
    
    def __init__(self):
        self.translator = None
        if TRANSLATION_AVAILABLE:
            self.translator = GoogleTranslator(source='auto', target='en')
    
    def detect_csv_source(self, filepath):
        """Detect CSV source format (bob-tr, bob-tld, nb-tr, nb-tld, ss-tr, ss-tld, fw, hsd-truth)"""
        if not CSV_AVAILABLE:
            return 'unknown'
        
        try:
            df = pd.read_csv(filepath, nrows=1)
            headers = df.columns.tolist()
            headers_lower = [h.lower() for h in headers]
            
            # Each format uses ONLY ONE unique identifier for efficiency
            # Canonical HSD truth file: domain + wallet_id schema
            if 'domain' in headers_lower and 'wallet_id' in headers_lower and (
                'ownership_status' in headers_lower or 'first_seen' in headers_lower
            ):
                return 'hsd-truth'
            # Namebase Transactions: extra.domain (dot notation) is UNIQUE
            if 'extra.domain' in headers:
                return 'nb-tr'
            # Shakestation TLD: for_sale column is UNIQUE
            elif 'for_sale' in headers_lower:
                return 'ss-tld'
            # Shakestation Transactions: coin column is UNIQUE
            elif 'coin' in headers_lower:
                return 'ss-tr'
            # Firewallet: expiry column is UNIQUE (date format, only FW has this)
            elif 'expiry' in headers_lower:
                return 'fw'
            # Namebase TLD: price_hns is UNIQUE to Namebase
            elif 'price_hns' in headers_lower:
                return 'nb-tld'
            # Bob Wallet Transactions: txhash column is UNIQUE
            elif 'txhash' in headers_lower:
                return 'bob-tr'
            # Bob Wallet TLD (processed): domains column (plural) - only after txhash ruled out
            elif 'domains' in headers_lower:
                return 'bob-tld'
            # Bob Wallet TLD (unprocessed): NO header, single column of domain names
            elif len(headers) == 1:
                first_val = str(headers[0]).lower()
                # Exclude if first value is a known column name from other formats
                if first_val in ['name', 'domain', 'time', 'action', 'coin', 'expiry', 'value', 'maxbid', 'price_hns', 'for_sale']:
                    return 'unknown'
                # Accept if looks like domain: xn-- prefix OR alphanumeric/hyphen/underscore <= 63 chars
                if first_val.startswith('xn--') or (len(first_val) <= 63 and all(c.isalnum() or c in '-_' for c in first_val)):
                    return 'bob-tld'
            return 'unknown'
        except:
            return 'unknown'
    
    def is_emoji(self, char):
        """Check if character is an emoji"""
        try:
            char_name = unicodedata.name(char, '')
            return any(keyword in char_name for keyword in ['EMOJI', 'FACE', 'HEART', 'STAR', 'SYMBOL'])
        except:
            return False
    
    def get_char_description(self, char):
        """Get official Unicode character name"""
        try:
            return unicodedata.name(char, char)
        except:
            return char
    
    def detect_language(self, text):
        """Detect language based on Unicode blocks"""
        if not text:
            return None
        
        # Check for Hawaiian (uses macrons/kahakō: ā ē ī ō ū)
        hawaiian_vowels = {'ā', 'ē', 'ī', 'ō', 'ū', 'Ā', 'Ē', 'Ī', 'Ō', 'Ū'}
        if any(char in hawaiian_vowels for char in text):
            # Check if it's mostly Latin letters (Hawaiian characteristic)
            latin_chars = sum(1 for c in text if c.isalpha() and ord(c) < 0x0180)
            if latin_chars > len(text) * 0.5:  # More than 50% Latin-based
                return 'Hawaiian', 'haw'
        
        # Check first character for language detection
        for char in text:
            if char.isspace():
                continue
            code_point = ord(char)
            
            # CJK Unified Ideographs
            if 0x4E00 <= code_point <= 0x9FFF:
                return 'Chinese/Japanese/Korean', 'zh-CN'
            # Hiragana
            elif 0x3040 <= code_point <= 0x309F:
                return 'Japanese', 'ja'
            # Katakana
            elif 0x30A0 <= code_point <= 0x30FF:
                return 'Japanese', 'ja'
            # Arabic (includes Urdu, Uyghur)
            elif 0x0600 <= code_point <= 0x06FF:
                return 'Arabic/Urdu/Uyghur', 'ar'
            # Hebrew
            elif 0x0590 <= code_point <= 0x05FF:
                return 'Hebrew', 'he'
            # Cyrillic (Russian, Ukrainian, etc.)
            elif 0x0400 <= code_point <= 0x04FF:
                return 'Cyrillic (Russian/Ukrainian)', 'ru'
            # Greek
            elif 0x0370 <= code_point <= 0x03FF:
                return 'Greek', 'el'
            # Thai
            elif 0x0E00 <= code_point <= 0x0E7F:
                return 'Thai', 'th'
            # Devanagari (Hindi/Sanskrit)
            elif 0x0900 <= code_point <= 0x097F:
                return 'Devanagari (Hindi)', 'hi'
            # Tamil
            elif 0x0B80 <= code_point <= 0x0BFF:
                return 'Tamil', 'ta'
            # Malayalam
            elif 0x0D00 <= code_point <= 0x0D7F:
                return 'Malayalam', 'ml'
            # Georgian
            elif 0x10A0 <= code_point <= 0x10FF:
                return 'Georgian', 'ka'
            # Armenian
            elif 0x0530 <= code_point <= 0x058F:
                return 'Armenian', 'hy'
            # Latin Extended-A (European languages with diacritics)
            elif 0x0100 <= code_point <= 0x017F:
                return 'European (Latin Extended)', 'auto'
            # Latin Extended-B
            elif 0x0180 <= code_point <= 0x024F:
                return 'European (Latin Extended)', 'auto'
        
        return None, None
    
    def punycode_to_unicode(self, punycode_str):
        """Convert punycode to unicode with validation level tagging"""
        if not punycode_str.startswith("xn--"):
            return punycode_str, None, "NOT_PUNYCODE"
        
        # Try strict IDNA decode
        try:
            decoded = punycode_str.encode('ascii').decode('idna', errors='strict')
            return decoded, self.detect_language(decoded)[0], 'PUNY_IDNA'
        except UnicodeError:
            # Try lenient decode
            try:
                unicode_str = idna.decode(punycode_str)
                return unicode_str, self.detect_language(unicode_str)[0], 'PUNY_ALT'
            except Exception as e:
                # Extract partial Unicode from error message
                error_message = str(e)
                unicode_match = re.search(r"'([^']*)'", error_message)
                if unicode_match:
                    partial = unicode_match.group(1)
                    return partial, self.detect_language(partial)[0], 'PUNY_ALT'
                else:
                    return punycode_str, None, 'PUNY_INVALID'
    
    def unicode_to_punycode(self, unicode_str):
        """Convert unicode to punycode"""
        if unicode_str.startswith("xn--"):
            return unicode_str  # Already punycode
        
        try:
            punycode_encoder = codecs.getencoder('punycode')
            punycode_string, _ = punycode_encoder(unicode_str)
            return f"xn--{punycode_string.decode('ascii')}"
        except Exception as e:
            return unicode_str  # Return original on error
    
    def translate_text(self, text, target_lang='en'):
        """Translate text to target language using Google Translate"""
        if not TRANSLATION_AVAILABLE or not self.translator:
            return None
        
        if not text or not text.strip():
            return None
        
        # Skip translation if text is purely ASCII and looks like English
        # But still allow translation of ASCII text that might be in other languages
        if text.isascii() and len(text.split()) > 1:
            # Check if it looks like English words
            try:
                # Try to detect if it's already English
                test_translator = GoogleTranslator(source='auto', target='en')
                test_result = test_translator.translate(text)
                if test_result == text:
                    return None  # Already in target language
            except:
                pass
        
        try:
            # Update target language
            self.translator.target = target_lang
            translated = self.translator.translate(text)
            
            # Return None if translation is the same as input
            if translated and translated.strip() and translated != text:
                return translated
            return None
            
        except Exception as e:
            # Better error handling with specific messages
            error_msg = str(e).lower()
            if 'rate limit' in error_msg or 'quota' in error_msg:
                print(f"⚠ Translation rate limit reached. Skipping translation.")
            elif 'network' in error_msg or 'connection' in error_msg:
                print(f"⚠ Network error during translation. Check connection.")
            else:
                print(f"⚠ Translation error: {e}")
            return None
    
    def generate_description(self, unicode_str, validation_tag):
        """Generate description based on unicode content"""
        if validation_tag != 'PUNY_IDNA' or not unicode_str:
            return ''
        
        # Check if purely emoji
        is_all_emoji = all(self.is_emoji(c) or c.isspace() for c in unicode_str if not c.isalnum())
        has_emoji = any(self.is_emoji(c) for c in unicode_str)
        
        if is_all_emoji and has_emoji:
            # Purely emoji - show character names
            names = []
            for char in unicode_str:
                if not char.isspace():
                    names.append(self.get_char_description(char))
            return ' + '.join(names)
        
        # Check for recognized language
        lang_name, lang_code = self.detect_language(unicode_str)
        if lang_name:
            return lang_name
        
        # Mixed letters + unicode chars - show as it appears
        if has_emoji or any(ord(c) > 127 for c in unicode_str):
            # Has special unicode characters
            char_names = []
            for char in unicode_str:
                if ord(char) > 127 and not char.isspace():
                    char_names.append(self.get_char_description(char))
            if char_names:
                return f"Letters + {', '.join(char_names)}"
        
        return unicode_str
    
    def add_categorization_tags(self, domain, unicode_val):
        """Add categorization tags for domain (1D, 1L, 1C, 2D, 2L, 2C, etc.)
        Returns list of tags"""
        tags = []
        
        def is_pure_alpha(s):
            return str(s).isalpha()
        
        # Determine display length - use unicode for punycode domains
        if str(domain).startswith('xn--') and unicode_val:
            display_length = len(str(unicode_val))
            is_punycode = True
        else:
            display_length = len(str(domain))
            is_punycode = False
        
        # Single character tags (1D, 1L, 1C)
        if display_length == 1:
            if str(domain).isdigit():
                tags.append('1D')
            elif is_pure_alpha(domain) and not is_punycode:
                tags.append('1L')
            else:
                tags.append('1C')  # Single char emoji/unicode
        
        # Two character tags (2D, 2L, 2C)
        elif display_length == 2:
            if str(domain).isdigit():
                tags.append('2D')
            elif is_pure_alpha(domain) and not is_punycode:
                tags.append('2L')
            else:
                tags.append('2C')  # Two char emoji/unicode
        
        # Three character tags (3D, 3L, 3C)
        elif display_length == 3:
            if str(domain).isdigit():
                tags.append('3D')
            elif is_pure_alpha(domain):
                tags.append('3L')
            else:
                tags.append('3C')
        
        # Four character tags (4D, 4L, 4C)
        elif display_length == 4:
            if str(domain).isdigit():
                tags.append('4D')
            elif is_pure_alpha(domain):
                tags.append('4L')
            else:
                tags.append('4C')
        
        # Five character tags (5D, 5L, 5C)
        elif display_length == 5:
            if str(domain).isdigit():
                tags.append('5D')
            elif is_pure_alpha(domain):
                tags.append('5L')
            else:
                tags.append('5C')
        
        # Six/Seven digit tags
        elif display_length == 6 and str(domain).isdigit():
            tags.append('6D')
        elif display_length == 7 and str(domain).isdigit():
            tags.append('7D')
        
        return tags
    
    def convert_domain(self, domain, translate=False, target_lang='en', verbose=True):
        """Convert a single domain and optionally translate"""
        domain = domain.strip()
        
        if not domain:
            return None
        
        # Determine conversion direction
        if domain.startswith('xn--'):
            # Punycode to Unicode
            unicode_str, detected_lang, validation = self.punycode_to_unicode(domain)
            
            # Add categorization tags
            tags = self.add_categorization_tags(domain, unicode_str)
            
            result = {
                'input': domain,
                'output': unicode_str,
                'direction': 'puny→uni',
                'language': detected_lang,
                'validation': validation,
                'translation': None,
                'tags': tags
            }
            
            if verbose:
                print(f"\n{'='*60}")
                print(f"Input (Punycode):  {domain}")
                print(f"Output (Unicode):  {unicode_str}")
                print(f"Validation Level:  {validation}")
                if detected_lang:
                    print(f"Detected Language: {detected_lang}")
                    description = self.generate_description(unicode_str, validation)
                    if description:
                        print(f"Description:       {description}")
            
            # Translate if requested
            if translate and detected_lang and validation == 'PUNY_IDNA':
                if verbose:
                    print(f"Translating to {target_lang}...", end=' ')
                translation = self.translate_text(unicode_str, target_lang)
                if translation:
                    result['translation'] = translation
                    if verbose:
                        print(f"✓")
                        print(f"Translation ({target_lang}): {translation}")
                else:
                    if verbose:
                        print(f"(skipped)")
            
            if verbose:
                print(f"{'='*60}\n")
            
            return result
        else:
            # Unicode to Punycode
            punycode_str = self.unicode_to_punycode(domain)
            detected_lang, _ = self.detect_language(domain)
            
            # Add categorization tags
            tags = self.add_categorization_tags(domain, domain)  # For unicode, domain is the display
            
            result = {
                'input': domain,
                'output': punycode_str,
                'direction': 'uni→puny',
                'language': detected_lang,
                'validation': 'N/A',
                'translation': None,
                'tags': tags
            }
            
            if verbose:
                print(f"\n{'='*60}")
                print(f"Input (Unicode):   {domain}")
                print(f"Output (Punycode): {punycode_str}")
                if detected_lang:
                    print(f"Detected Language: {detected_lang}")
            
            # Translate if requested
            if translate and detected_lang:
                if verbose:
                    print(f"Translating to {target_lang}...", end=' ')
                translation = self.translate_text(domain, target_lang)
                if translation:
                    result['translation'] = translation
                    if verbose:
                        print(f"✓")
                        print(f"Translation ({target_lang}): {translation}")
                else:
                    if verbose:
                        print(f"(skipped)")
            
            if verbose:
                print(f"{'='*60}\n")
            
            return result
    
    def process_file(self, input_path, translate=False, target_lang='en', output_path=None):
        """Process a text file with domains (one per line)"""
        input_path = Path(input_path)
        
        if not input_path.exists():
            print(f"Error: File not found: {input_path}")
            return False
        
        # Read input file
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"Error reading file: {e}")
            return False
        
        if not lines:
            print("Error: File is empty")
            return False
        
        # Determine conversion direction from first line
        first_domain = lines[0]
        if first_domain.startswith('xn--'):
            direction = 'puny2uni'
            suffix = '_uni'
        else:
            direction = 'uni2puny'
            suffix = '_puny'
        
        # Determine output path
        if output_path is None:
            output_path = input_path.with_name(input_path.stem + suffix + input_path.suffix)
        
        print(f"\nProcessing {len(lines)} domains from {input_path.name}")
        print(f"Direction: {direction}")
        if translate:
            print(f"Translation: enabled (target: {target_lang})")
            if not TRANSLATION_AVAILABLE:
                print(f"⚠ Translation not available (deep-translator not installed)")
                translate = False
        print(f"Output: {output_path.name}\n")
        
        # Process all domains
        results = []
        translations = []
        translation_count = 0
        
        for i, domain in enumerate(lines, 1):
            result = self.convert_domain(domain, translate=translate, target_lang=target_lang, verbose=False)
            if result:
                results.append(result['output'])
                if result['translation']:
                    translations.append(f"{result['output']} | {result['translation']}")
                    translation_count += 1
                
                # Show progress with translation count
                if i % 10 == 0 or i == len(lines):
                    status = f"Processed {i}/{len(lines)} domains"
                    if translate:
                        status += f" | Translated: {translation_count}"
                    print(f"{status}...", end='\r')
        
        print()  # New line after progress
        
        # Write output file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(results))
            print(f"\n✓ Converted domains saved to: {output_path}")
            
            # Write translations if available
            if translations:
                translation_path = input_path.with_name(input_path.stem + suffix + '_translations' + input_path.suffix)
                with open(translation_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(translations))
                print(f"✓ Translations saved to: {translation_path.name}")
            
            return True
        except Exception as e:
            print(f"Error writing output file: {e}")
            return False
    
    def process_csv(self, input_path, translate=False, target_lang='en', output_path=None, respect_existing=True):
        """Process CSV file from HNS platforms with translation
        
        Args:
            input_path: Path to CSV file
            translate: Enable translation
            target_lang: Target language for translation
            output_path: Custom output path (optional)
            respect_existing: Skip domains that already have descript-IDNA/translate-IDNA values (default: True)
        """
        if not CSV_AVAILABLE:
            print("Error: pandas not installed. Install with: pip install pandas")
            return False
        
        input_path = Path(input_path)
        
        if not input_path.exists():
            print(f"Error: File not found: {input_path}")
            return False
        
        # Detect source format
        source_type = self.detect_csv_source(input_path)
        print(f"\nDetected format: {source_type}")
        
        if source_type == 'unknown':
            print("Warning: Unknown CSV format. Attempting generic processing...")
        
        # Read CSV with appropriate error handling
        # Bob TLD (original) has no header - just a list of domain names
        if source_type == 'bob-tld':
            # Check if first row looks like a domain (no actual header)
            try:
                first_check = pd.read_csv(input_path, nrows=1)
                first_val = str(first_check.columns[0]) if len(first_check.columns) > 0 else ''
                # If first value looks like a domain name, read without header
                if first_val.startswith('xn--') or (len(first_val) <= 63 and all(c.isalnum() or c in '-_' for c in first_val)):
                    print("Note: No header detected - reading as raw domain list")
                    df = pd.read_csv(input_path, header=None, names=['domains'])
                else:
                    df = pd.read_csv(input_path)
            except:
                df = pd.read_csv(input_path, header=None, names=['domains'])
        else:
            try:
                df = pd.read_csv(input_path)
            except pd.errors.ParserError:
                # Try with different quoting settings for malformed CSVs (e.g., Shakestation)
                try:
                    df = pd.read_csv(input_path, quoting=1, escapechar='\\')
                except:
                    df = pd.read_csv(input_path, on_bad_lines='skip')
        
        print(f"Processing {len(df)} rows from {input_path.name}")
        if translate:
            print(f"Translation: enabled (target: {target_lang})")
            if not TRANSLATION_AVAILABLE:
                print(f"⚠ Translation not available (deep-translator not installed)")
                translate = False
        
        # Determine domain column based on source type
        domain_col = self._get_domain_column(df, source_type)
        
        if not domain_col:
            print("Error: Could not identify domain column")
            return False
        
        print(f"Domain column: {domain_col}")
        
        # Store original columns for Shakestation (first 6 must remain in place)
        original_cols = df.columns.tolist()
        is_shakestation = source_type in ['ss-tld', 'ss-tr']
        
        # Check if already processed (has unicode column)
        already_processed = 'unicode' in df.columns
        has_descript = 'descript-IDNA' in df.columns or 'description' in df.columns
        has_translate = 'translate-IDNA' in df.columns
        
        if already_processed:
            print("Note: CSV already has unicode column.")
        
        if respect_existing and (has_descript or has_translate):
            print(f"Note: Respecting existing entries (respect_existing=True)")
            print(f"      Only processing domains without descript-IDNA/translate-IDNA values")
        else:
            if not respect_existing:
                print(f"Note: Override mode enabled (respect_existing=False)")
                print(f"      Re-processing all domains regardless of existing values")
        
        # Process each domain
        results = []
        translation_count = 0
        skipped_count = 0
        for idx, row in df.iterrows():
            domain = row[domain_col]
            
            # Handle NaN
            if isinstance(domain, float) and math.isnan(domain):
                results.append({
                    'unicode': '',
                    'descript-IDNA': '',
                    'translate-IDNA': ''
                })
                continue
            
            domain = str(domain).strip()
            
            if not domain or not domain.startswith('xn--'):
                results.append({
                    'unicode': '',
                    'descript-IDNA': '',
                    'translate-IDNA': ''
                })
                continue
            
            # Check if should skip this entry (respect_existing mode)
            should_skip = False
            if respect_existing:
                # Check for existing descript-IDNA or description
                existing_descript = ''
                if 'descript-IDNA' in df.columns:
                    existing_descript = str(row.get('descript-IDNA', '')).strip()
                elif 'description' in df.columns:
                    existing_descript = str(row.get('description', '')).strip()
                
                # Check for existing translate-IDNA
                existing_translate = ''
                if 'translate-IDNA' in df.columns:
                    existing_translate = str(row.get('translate-IDNA', '')).strip()
                
                # Skip if either field has content (not empty, not 'nan')
                if existing_descript and existing_descript.lower() != 'nan':
                    should_skip = True
                elif translate and existing_translate and existing_translate.lower() != 'nan':
                    should_skip = True
            
            if should_skip:
                # Keep existing values
                skipped_count += 1
                existing_unicode = str(row.get('unicode', '')).strip() if 'unicode' in df.columns else ''
                existing_descript = str(row.get('descript-IDNA', row.get('description', ''))).strip()
                existing_translate = str(row.get('translate-IDNA', '')).strip()
                existing_tags = str(row.get('tags', '')).strip() if 'tags' in df.columns else ''
                
                results.append({
                    'unicode': existing_unicode if existing_unicode.lower() != 'nan' else '',
                    'descript-IDNA': existing_descript if existing_descript.lower() != 'nan' else '',
                    'translate-IDNA': existing_translate if existing_translate.lower() != 'nan' else '',
                    'tags': existing_tags if existing_tags.lower() != 'nan' else ''
                })
                
                # Show progress with skip count
                if (idx + 1) % 10 == 0 or (idx + 1) == len(df):
                    status = f"Processed {idx + 1}/{len(df)} domains | Skipped: {skipped_count}"
                    if translate:
                        status += f" | Translated: {translation_count}"
                    print(f"{status}...", end='\r')
                continue
            
            # Convert domain
            result = self.convert_domain(domain, translate=translate, target_lang=target_lang, verbose=False)
            
            if result:
                unicode_val = result['output']
                lang_name = result.get('language', '')
                translation = result.get('translation', '')
                tags = result.get('tags', [])
                
                # Clean up unicode string (remove escape sequences)
                if unicode_val:
                    unicode_val = re.sub(r'(?:\\x[\da-fA-F]{2})+|\\u(?:[\da-fA-F]{4})+', '', unicode_val)
                
                if translation:
                    translation_count += 1
                
                results.append({
                    'unicode': unicode_val if unicode_val != domain else '',
                    'descript-IDNA': lang_name if lang_name else '',
                    'translate-IDNA': translation if translation else '',
                    'tags': ','.join(tags) if tags else ''
                })
            else:
                results.append({
                    'unicode': '',
                    'descript-IDNA': '',
                    'translate-IDNA': '',
                    'tags': ''
                })
            
            # Show progress with translation count
            if (idx + 1) % 10 == 0 or (idx + 1) == len(df):
                status = f"Processed {idx + 1}/{len(df)} domains"
                if translate:
                    status += f" | Translated: {translation_count}"
                print(f"{status}...", end='\r')
        
        print()  # New line after progress
        
        # Add or update columns
        if not already_processed:
            df['unicode'] = [r['unicode'] for r in results]
        
        df['descript-IDNA'] = [r['descript-IDNA'] for r in results]
        df['translate-IDNA'] = [r['translate-IDNA'] for r in results]
        df['tags'] = [r['tags'] for r in results]
        
        # Arrange columns appropriately
        if is_shakestation:
            # Preserve first 6 columns for Shakestation
            first_six = original_cols[:6] if len(original_cols) >= 6 else original_cols
            remaining_original = [col for col in original_cols[6:] if col not in ['unicode', 'descript-IDNA', 'translate-IDNA', 'tags']]
            
            # Build final column order
            if already_processed:
                new_cols = ['unicode', 'descript-IDNA', 'translate-IDNA', 'tags']
            else:
                new_cols = ['unicode', 'descript-IDNA', 'translate-IDNA', 'tags']
            
            final_cols = first_six + remaining_original + new_cols
            # Remove duplicates while preserving order
            seen = set()
            final_cols = [col for col in final_cols if col not in seen and not seen.add(col) and col in df.columns]
            df = df[final_cols]
        else:
            # For other formats, append new columns at the end
            new_cols = ['unicode', 'descript-IDNA', 'translate-IDNA', 'tags']
            other_cols = [col for col in df.columns if col not in new_cols]
            df = df[other_cols + new_cols]
        
        # Determine output path
        if output_path is None:
            # Add timestamp
            from datetime import datetime
            date_suffix = datetime.now().strftime("%Y%m%d")
            stem = input_path.stem
            # Remove existing date suffix if present
            stem = re.sub(r'_\d{8}$', '', stem)
            output_path = input_path.with_name(f"{stem}_{date_suffix}_translated.csv")
        
        # Write output
        try:
            df.to_csv(output_path, index=False)
            print(f"\n✓ Translated CSV saved to: {output_path}")
            
            # Show summary
            unicode_count = sum(1 for r in results if r['unicode'])
            translated_count = sum(1 for r in results if r['translate-IDNA'])
            print(f"✓ Converted {unicode_count} punycode domains to unicode")
            if translate:
                print(f"✓ Successfully translated {translated_count} domains to {target_lang}")
            if skipped_count > 0:
                print(f"ℹ Skipped {skipped_count} domains (already have descript/translate values)")
            
            return True
        except Exception as e:
            print(f"Error writing output file: {e}")
            return False
    
    def _get_domain_column(self, df, source_type):
        """Get the domain column name based on source type"""
        headers_lower = {h.lower(): h for h in df.columns}
        
        if source_type == 'nb-tr':
            return 'extra.domain' if 'extra.domain' in df.columns else None
        elif source_type in ['ss-tld', 'ss-tr']:
            return headers_lower.get('domain', None)
        elif source_type == 'nb-tld':
            return headers_lower.get('name', None)
        elif source_type in ['bob-tld', 'bob-tr']:
            return headers_lower.get('domains', None)
        elif source_type == 'hsd-truth':
            return headers_lower.get('domain', None)
        elif source_type == 'fw':
            # Firewallet uses 'name' or first column
            return headers_lower.get('name', df.columns[0] if len(df.columns) > 0 else None)
        else:
            # Try common column names
            for col_name in ['domain', 'name', 'domains']:
                if col_name in headers_lower:
                    return headers_lower[col_name]
            return None
    
    def interactive_mode(self):
        """Interactive mode for converting domains"""
        print("\n" + "="*60)
        print("  Punycode ⟷ Unicode Converter - Interactive Mode")
        print("="*60)
        print("\nCommands:")
        print("  - Enter a domain to convert (punycode or unicode)")
        print("  - Type 'translate on' or 'translate off' to toggle translation")
        print("  - Type 'lang XX' to change target language (e.g., 'lang es' for Spanish)")
        print("  - Type 'quit' or 'exit' to exit")
        print("\n" + "="*60 + "\n")
        
        translate_mode = False
        target_lang = 'en'
        
        while True:
            try:
                user_input = input("Enter domain (or command): ").strip()
                
                if not user_input:
                    continue
                
                # Check for commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye!")
                    break
                elif user_input.lower() == 'translate on':
                    translate_mode = True
                    print(f"✓ Translation enabled (target: {target_lang})")
                    continue
                elif user_input.lower() == 'translate off':
                    translate_mode = False
                    print("✓ Translation disabled")
                    continue
                elif user_input.lower().startswith('lang '):
                    new_lang = user_input.split()[1].lower()
                    target_lang = new_lang
                    print(f"✓ Target language set to: {target_lang}")
                    continue
                elif user_input.lower() == 'help':
                    print("\nCommands:")
                    print("  translate on/off  - Toggle translation")
                    print("  lang XX          - Set target language (e.g., lang es)")
                    print("  quit/exit        - Exit interactive mode")
                    continue
                
                # Convert the domain
                self.convert_domain(user_input, translate=translate_mode, target_lang=target_lang)
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except EOFError:
                print("\n\nGoodbye!")
                break


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Punycode ⟷ Unicode Converter with Language Detection and Translation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s domains.txt                    # Convert text file
  %(prog)s domains.csv                    # Process CSV with translations
  %(prog)s domains.csv -t                 # CSV with English translations
  %(prog)s domains.csv -t -l es           # CSV with Spanish translations
  %(prog)s domains.txt -t                 # Convert and translate to English
  %(prog)s xn--domain                     # Convert single domain
  %(prog)s xn--domain --translate         # Convert and translate single domain
  %(prog)s -i                             # Interactive mode
        """
    )
    
    parser.add_argument('input', nargs='?', help='Input file or domain to convert')
    parser.add_argument('-i', '--interactive', action='store_true', help='Interactive mode')
    parser.add_argument('-t', '--translate', action='store_true', help='Enable translation')
    parser.add_argument('-l', '--lang', default='en', help='Target language for translation (default: en)')
    parser.add_argument('-o', '--output', help='Output file path (for file processing)')
    parser.add_argument('--override', action='store_true', help='Override existing descript/translate values (CSV only, default: respect existing)')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 2.0')
    
    args = parser.parse_args()
    
    # Create converter
    converter = Puny2UniConverter()
    
    # Interactive mode
    if args.interactive:
        converter.interactive_mode()
        return
    
    # Check if input provided
    if not args.input:
        parser.print_help()
        return
    
    # Check if input is a file
    if os.path.isfile(args.input):
        # Determine file type
        file_ext = Path(args.input).suffix.lower()
        
        if file_ext == '.csv':
            # Process CSV file
            converter.process_csv(
                args.input,
                translate=args.translate,
                target_lang=args.lang,
                output_path=args.output,
                respect_existing=not args.override
            )
        else:
            # Process text file
            converter.process_file(
                args.input,
                translate=args.translate,
                target_lang=args.lang,
                output_path=args.output
            )
    else:
        # Process single domain
        converter.convert_domain(
            args.input,
            translate=args.translate,
            target_lang=args.lang
        )


if __name__ == '__main__':
    main()
