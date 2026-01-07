"""
Test script to demonstrate the new description and translation functionality
"""
import unicodedata

class DescriptionTester:
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
        
        for char in text:
            if char.isspace():
                continue
            code_point = ord(char)
            
            # CJK Unified Ideographs
            if 0x4E00 <= code_point <= 0x9FFF:
                return 'Chinese/Japanese/Korean'
            # Hiragana
            elif 0x3040 <= code_point <= 0x309F:
                return 'Japanese'
            # Katakana
            elif 0x30A0 <= code_point <= 0x30FF:
                return 'Japanese'
            # Arabic (includes Urdu, Uyghur)
            elif 0x0600 <= code_point <= 0x06FF:
                return 'Arabic/Urdu/Uyghur'
            # Hebrew
            elif 0x0590 <= code_point <= 0x05FF:
                return 'Hebrew'
            # Cyrillic (Russian, Ukrainian, etc.)
            elif 0x0400 <= code_point <= 0x04FF:
                return 'Cyrillic (Russian/Ukrainian)'
            # Greek
            elif 0x0370 <= code_point <= 0x03FF:
                return 'Greek'
            # Thai
            elif 0x0E00 <= code_point <= 0x0E7F:
                return 'Thai'
            # Devanagari (Hindi/Sanskrit)
            elif 0x0900 <= code_point <= 0x097F:
                return 'Devanagari (Hindi)'
            # Tamil
            elif 0x0B80 <= code_point <= 0x0BFF:
                return 'Tamil'
            # Malayalam
            elif 0x0D00 <= code_point <= 0x0D7F:
                return 'Malayalam'
            # Georgian
            elif 0x10A0 <= code_point <= 0x10FF:
                return 'Georgian'
            # Armenian
            elif 0x0530 <= code_point <= 0x058F:
                return 'Armenian'
            # Latin Extended-A (European languages with diacritics)
            elif 0x0100 <= code_point <= 0x017F:
                return 'European (Latin Extended)'
            # Latin Extended-B
            elif 0x0180 <= code_point <= 0x024F:
                return 'European (Latin Extended)'
        
        return None
    
    def generate_description(self, unicode_str, tag):
        """Generate description based on unicode content for PUNY_IDNA only"""
        if tag != 'PUNY_IDNA' or not unicode_str:
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
        lang = self.detect_language(unicode_str)
        if lang:
            return lang
        
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

# Test examples
if __name__ == "__main__":
    tester = DescriptionTester()
    
    print("=== DESCRIPTION GENERATION TEST ===\n")
    
    test_cases = [
        ("😀", "PUNY_IDNA", "Pure emoji"),
        ("😀🎨", "PUNY_IDNA", "Multiple emojis"),
        ("café", "PUNY_IDNA", "Letters + accented char"),
        ("漢字", "PUNY_IDNA", "Chinese/Japanese characters"),
        ("مرحبا", "PUNY_IDNA", "Arabic text"),
        ("اردو", "PUNY_IDNA", "Urdu text (Arabic script)"),
        ("Привет", "PUNY_IDNA", "Russian (Cyrillic)"),
        ("Привіт", "PUNY_IDNA", "Ukrainian (Cyrillic)"),
        ("საქართველო", "PUNY_IDNA", "Georgian text"),
        ("தமிழ்", "PUNY_IDNA", "Tamil text"),
        ("മലയാളം", "PUNY_IDNA", "Malayalam text"),
        ("हिन्दी", "PUNY_IDNA", "Hindi (Devanagari)"),
        ("Հայերեն", "PUNY_IDNA", "Armenian text"),
        ("Ελληνικά", "PUNY_IDNA", "Greek text"),
        ("résumé", "PUNY_IDNA", "European (French)"),
        ("Müller", "PUNY_IDNA", "European (German)"),
        ("hello", "PUNY_ALT", "PUNY_ALT tag (should be empty)"),
        ("test", "PUNY_IDNA", "Plain ASCII"),
    ]
    
    for unicode_str, tag, description in test_cases:
        result = tester.generate_description(unicode_str, tag)
        print(f"Input: {unicode_str:15} | Tag: {tag:12} | Result: {result}")
        print(f"       ({description})")
        print()
