"""
Lyrics Parser Module
Supports multiple lyric formats: Plain text, LRC, SRT, and Custom
Includes advanced syllabification using pyphen and fallback algorithms
"""

import re
from enum import Enum
from typing import List, Dict, Optional, Tuple
import pyphen

# Initialize pyphen dictionaries for multiple languages
_dic_en = pyphen.Pyphen(lang='en_US')
_dic_es = pyphen.Pyphen(lang='es')
_dic_ja = None  # Japanese handled separately

# Common English word syllable overrides for better accuracy
# These are words where algorithmic syllabification often fails
SYLLABLE_OVERRIDES = {
    # Single syllable words often incorrectly split
    'night': ['night'],
    'sky': ['sky'],
    'why': ['why'],
    'die': ['die'],
    'alive': ['a', 'live'],
    'until': ['un', 'til'],
    'find': ['find'],
    'size': ['size'],
    'right': ['right'],
    'lost': ['lost'],
    'cost': ['cost'],
    'tossed': ['tossed'],
    'aside': ['a', 'side'],
    'feel': ['feel'],
    'real': ['real'],
    'decide': ['de', 'cide'],
    'inside': ['in', 'side'],
    'holding': ['hol', 'ding'],
    'cannot': ['can', 'not'],
    'cause': ['cause'],
    'because': ['be', 'cause'],
    'moments': ['mo', 'ments'],
    'money': ['mo', 'ney'],
    'dreams': ['dreams'],
    'answer': ['an', 'swer'],
    'wonder': ['won', 'der'],
    'only': ['on', 'ly'],
    #'everything': ['ev', 'er', 'y', 'thing'],
    #'every': ['ev', 'er', 'y'],
    # Contractions
    "you're": ["you're"],
    "you've": ["you've"],
    "i'm": ["i'm"],
    "i've": ["i've"],
    "i'll": ["i'll"],
    "we're": ["we're"],
    "they're": ["they're"],
    "can't": ["can't"],
    "won't": ["won't"],
    "don't": ["don't"],
    "isn't": ["is", "n't"],
    "wasn't": ["was", "n't"],
    # Common problematic words
    'being': ['be', 'ing'],
    'seeing': ['see', 'ing'],
    'going': ['go', 'ing'],
    'doing': ['do', 'ing'],
}


class LyricsFormat(Enum):
    """Supported lyrics formats"""
    AUTO = 'auto'
    PLAIN = 'plain'           # Space/newline separated syllables
    LRC = 'lrc'               # Standard LRC format [mm:ss.xx]text
    SRT = 'srt'               # SubRip subtitle format
    SYLLABLE = 'syllable'     # One syllable per line
    TIMED_CSV = 'timed_csv'   # time,syllable CSV format
    PRE_SYLLABIFIED = 'pre_syllabified'  # Already syllabified with hyphens


class LyricUnit:
    """Represents a single lyric unit (syllable or word) with metadata"""
    def __init__(self, text: str, time: Optional[float] = None, 
                 is_word_start: bool = True, is_word_end: bool = True,
                 original_word: Optional[str] = None):
        self.text = text
        self.time = time
        self.is_word_start = is_word_start
        self.is_word_end = is_word_end
        self.original_word = original_word or text
    
    def to_dict(self) -> Dict:
        result = {'text': self.text}
        if self.time is not None:
            result['time'] = self.time
        result['is_word_start'] = self.is_word_start
        result['is_word_end'] = self.is_word_end
        result['original_word'] = self.original_word
        return result


def parse_lyrics(content: str, format: LyricsFormat) -> List[Dict]:
    """
    Parse lyrics from various formats
    
    Returns:
        List of dictionaries with 'text' and optionally 'time' keys
    """
    if format == LyricsFormat.AUTO:
        format = detect_format(content)
    
    parsers = {
        LyricsFormat.PLAIN: parse_plain,
        LyricsFormat.LRC: parse_lrc,
        LyricsFormat.SRT: parse_srt,
        LyricsFormat.SYLLABLE: parse_syllable,
        LyricsFormat.TIMED_CSV: parse_timed_csv,
        LyricsFormat.PRE_SYLLABIFIED: parse_pre_syllabified
    }
    
    parser = parsers.get(format, parse_plain)
    return parser(content)


def detect_format(content: str) -> LyricsFormat:
    """Auto-detect the lyrics format from content"""
    content = content.strip()
    
    # Check for LRC format [mm:ss.xx]
    if re.search(r'\[\d{1,2}:\d{2}[\.:]?\d{0,3}\]', content):
        return LyricsFormat.LRC
    
    # Check for SRT format (numbered entries with timestamps)
    if re.search(r'^\d+\s*\n\d{2}:\d{2}:\d{2},\d{3}\s*-->', content, re.MULTILINE):
        return LyricsFormat.SRT
    
    # Check for timed CSV (starts with time)
    if re.search(r'^\d+\.?\d*\s*,\s*\S+', content, re.MULTILINE):
        return LyricsFormat.TIMED_CSV
    
    # Check if content has hyphenated words (pre-syllabified)
    words = content.split()
    hyphenated_count = sum(1 for w in words if '-' in w and not w.startswith('-') and not w.endswith('-'))
    if hyphenated_count > len(words) * 0.3:  # More than 30% hyphenated
        return LyricsFormat.PRE_SYLLABIFIED
    
    # Check if each line is a single word/syllable
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    if lines and all(len(l.split()) == 1 for l in lines):
        return LyricsFormat.SYLLABLE
    
    # Default to plain text
    return LyricsFormat.PLAIN


def parse_plain(content: str) -> List[Dict]:
    """
    Parse plain text lyrics
    Treats words as whole units - does NOT auto-syllabify
    Use parse_plain_syllabified() if you want auto-syllabification
    """
    lyrics = []
    
    # Replace common separators
    content = content.replace('\r\n', '\n')
    content = content.replace('\r', '\n')
    
    # Split on whitespace
    words = content.split()
    
    for word in words:
        # Handle hyphenated syllables (e.g., "hel-lo" becomes "hel", "lo")
        if '-' in word and not word.startswith('-') and not word.endswith('-'):
            syllables = word.split('-')
            for i, syl in enumerate(syllables):
                if syl.strip():
                    lyrics.append({
                        'text': clean_syllable(syl),
                        'is_word_start': i == 0,
                        'is_word_end': i == len(syllables) - 1,
                        'original_word': word.replace('-', '')
                    })
        else:
            if word.strip():
                cleaned = clean_syllable(word)
                lyrics.append({
                    'text': cleaned,
                    'is_word_start': True,
                    'is_word_end': True,
                    'original_word': cleaned
                })
    
    return lyrics


def parse_pre_syllabified(content: str) -> List[Dict]:
    """
    Parse lyrics that are already syllabified with hyphens
    E.g., "hel-lo world I won-der why"
    """
    lyrics = []
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    words = content.split()
    
    for word in words:
        if '-' in word and not word.startswith('-') and not word.endswith('-'):
            # Pre-syllabified word
            syllables = word.split('-')
            original = word.replace('-', '')
            for i, syl in enumerate(syllables):
                if syl.strip():
                    lyrics.append({
                        'text': clean_syllable(syl),
                        'is_word_start': i == 0,
                        'is_word_end': i == len(syllables) - 1,
                        'original_word': original
                    })
        else:
            # Single syllable word
            cleaned = clean_syllable(word)
            if cleaned:
                lyrics.append({
                    'text': cleaned,
                    'is_word_start': True,
                    'is_word_end': True,
                    'original_word': cleaned
                })
    
    return lyrics


def parse_lrc(content: str) -> List[Dict]:
    """
    Parse LRC format lyrics
    Format: [mm:ss.xx]text or [mm:ss:xx]text
    """
    lyrics = []
    
    # Pattern for LRC timestamps - more flexible
    pattern = r'\[(\d{1,2}):(\d{2})[\.:]+(\d{1,3})\]([^\[\]]*)'
    
    for match in re.finditer(pattern, content):
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        centiseconds = int(match.group(3))
        text = match.group(4).strip()
        
        if text:
            # Convert to milliseconds
            if len(match.group(3)) == 2:  # Centiseconds
                time_ms = (minutes * 60 + seconds) * 1000 + centiseconds * 10
            else:  # Milliseconds
                time_ms = (minutes * 60 + seconds) * 1000 + centiseconds
            
            # Split text into syllables if it contains spaces
            for syllable in text.split():
                cleaned = clean_syllable(syllable)
                if cleaned:
                    lyrics.append({
                        'text': cleaned,
                        'time': time_ms,
                        'is_word_start': True,
                        'is_word_end': True,
                        'original_word': cleaned
                    })
    
    return lyrics


def parse_srt(content: str) -> List[Dict]:
    """
    Parse SRT (SubRip) subtitle format
    """
    lyrics = []
    
    # Pattern for SRT entries
    pattern = r'(\d+)\s*\n(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}\s*\n(.+?)(?=\n\n|\n\d+\s*\n|$)'
    
    for match in re.finditer(pattern, content, re.DOTALL):
        hours = int(match.group(2))
        minutes = int(match.group(3))
        seconds = int(match.group(4))
        milliseconds = int(match.group(5))
        text = match.group(6).strip()
        
        time_ms = ((hours * 3600 + minutes * 60 + seconds) * 1000) + milliseconds
        
        # Clean HTML tags from SRT
        text = re.sub(r'<[^>]+>', '', text)
        
        # Split into syllables
        for line in text.split('\n'):
            for word in line.split():
                cleaned = clean_syllable(word)
                if cleaned:
                    lyrics.append({
                        'text': cleaned,
                        'time': time_ms,
                        'is_word_start': True,
                        'is_word_end': True,
                        'original_word': cleaned
                    })
    
    return lyrics


def parse_syllable(content: str) -> List[Dict]:
    """
    Parse one-syllable-per-line format
    """
    lyrics = []
    
    for line in content.split('\n'):
        line = line.strip()
        if line:
            lyrics.append({
                'text': clean_syllable(line),
                'is_word_start': True,
                'is_word_end': True,
                'original_word': clean_syllable(line)
            })
    
    return lyrics


def parse_timed_csv(content: str) -> List[Dict]:
    """
    Parse timed CSV format: time_ms,syllable
    """
    lyrics = []
    
    for line in content.split('\n'):
        line = line.strip()
        if ',' in line:
            parts = line.split(',', 1)
            try:
                time_ms = float(parts[0].strip())
                text = parts[1].strip()
                if text:
                    lyrics.append({
                        'text': clean_syllable(text),
                        'time': time_ms,
                        'is_word_start': True,
                        'is_word_end': True,
                        'original_word': clean_syllable(text)
                    })
            except ValueError:
                continue
    
    return lyrics


def clean_syllable(text: str) -> str:
    """
    Clean and normalize a syllable
    """
    # Remove surrounding punctuation but keep internal
    text = text.strip()
    
    # Remove leading/trailing punctuation except for apostrophes
    text = re.sub(r'^[^\w\']+', '', text)
    text = re.sub(r'[^\w\']+$', '', text)
    
    return text


def syllabify(word: str, language: str = 'en') -> List[str]:
    """
    Advanced English syllabification using pyphen with overrides
    
    Args:
        word: The word to syllabify
        language: Language code ('en', 'es', 'ja')
    
    Returns:
        List of syllables
    """
    word = word.strip()
    if not word:
        return []
        
    # Check if already manual hyphenated (e.g. "ev-er-y-thing")
    # We only treat it as pre-syllabified if it has internal hyphens
    if '-' in word and not word.startswith('-') and not word.endswith('-'):
        syllables = [s.strip() for s in word.split('-') if s.strip()]
        if syllables:
            return syllables
    
    # Check for contractions and special cases first
    word_lower = word.lower()
    
    # Check override dictionary
    if word_lower in SYLLABLE_OVERRIDES:
        result = SYLLABLE_OVERRIDES[word_lower]
        # Preserve original case on first character if needed
        if word[0].isupper() and result and result[0]:
            result = [result[0].capitalize()] + result[1:]
        return result
    
    # Handle contractions specially
    if "'" in word:
        # Most contractions are single syllables
        return [word]
    
    # Use pyphen for standard syllabification
    try:
        if language == 'en':
            syllables = _dic_en.inserted(word, '-').split('-')
        elif language == 'es':
            syllables = _dic_es.inserted(word, '-').split('-')
        else:
            # Fallback to basic algorithm
            syllables = syllabify_basic(word)
        
        # Filter out empty syllables
        syllables = [s for s in syllables if s.strip()]
        
        if not syllables:
            return [word]
        
        return syllables
        
    except Exception:
        return syllabify_basic(word)


def syllabify_basic(word: str) -> List[str]:
    """
    Fallback basic syllabification when pyphen fails
    Uses improved vowel-consonant clustering
    """
    word = word.lower()
    vowels = 'aeiouy'
    
    # Single letter or short words
    if len(word) <= 2:
        return [word]
    
    syllables = []
    current = ''
    i = 0
    
    while i < len(word):
        char = word[i]
        current += char
        
        # Check if current ends with a vowel
        if char in vowels:
            # Look ahead for consonant cluster
            j = i + 1
            while j < len(word) and word[j] not in vowels:
                j += 1
            
            # How many consonants follow?
            consonant_count = j - (i + 1)
            
            if consonant_count == 0:
                # No consonants, vowel at end or followed by vowel
                if j >= len(word):
                    # End of word
                    pass
                else:
                    # Followed by vowel, split here
                    if len(current) > 0:
                        syllables.append(current)
                        current = ''
            elif consonant_count == 1:
                # One consonant - goes with next syllable
                if len(current) > 0:
                    syllables.append(current)
                    current = ''
            else:
                # Multiple consonants - split between them
                current += word[i + 1]
                syllables.append(current)
                current = ''
                i += 1
        
        i += 1
    
    if current:
        if syllables:
            # Merge short endings
            if len(current) == 1 and current not in vowels:
                syllables[-1] += current
            else:
                syllables.append(current)
        else:
            syllables.append(current)
    
    return syllables if syllables else [word]


def syllabify_text(text: str, preserve_hyphenated: bool = True) -> List[Dict]:
    """
    Syllabify a block of text, respecting word boundaries
    
    Args:
        text: The text to syllabify
        preserve_hyphenated: If True, treat hyphenated words as already syllabified
    
    Returns:
        List of syllable dicts with word boundary info
    """
    result = []
    words = text.split()
    
    for word in words:
        cleaned = clean_syllable(word)
        if not cleaned:
            continue
        
        # Check if already hyphenated (user pre-syllabified)
        if preserve_hyphenated and '-' in cleaned and not cleaned.startswith('-') and not cleaned.endswith('-'):
            syllables = cleaned.split('-')
            for i, syl in enumerate(syllables):
                if syl:
                    result.append({
                        'text': syl,
                        'is_word_start': i == 0,
                        'is_word_end': i == len(syllables) - 1,
                        'original_word': cleaned.replace('-', '')
                    })
        else:
            # Auto-syllabify
            syllables = syllabify(cleaned)
            for i, syl in enumerate(syllables):
                result.append({
                    'text': syl,
                    'is_word_start': i == 0,
                    'is_word_end': i == len(syllables) - 1,
                    'original_word': cleaned
                })
    
    return result


def expand_lyrics_to_syllables(lyrics: List[Dict], target_count: int) -> List[Dict]:
    """
    Expand lyrics into syllables to better match a target note count
    Uses intelligent syllabification, respecting word boundaries
    
    Args:
        lyrics: List of lyric dicts
        target_count: Desired number of syllables
    
    Returns:
        Expanded list of syllable dicts
    """
    if not lyrics or target_count <= len(lyrics):
        return lyrics
    
    result = []
    remaining_to_expand = target_count - len(lyrics)
    
    # First pass: identify expandable words (those with multiple syllables)
    expandable_indices = []
    for i, lyric in enumerate(lyrics):
        word = lyric.get('original_word', lyric['text'])
        syllables = syllabify(word)
        if len(syllables) > 1:
            expandable_indices.append((i, syllables))
    
    # Determine how many words to expand
    expanded_set = set()
    for idx, syllables in expandable_indices:
        if remaining_to_expand <= 0:
            break
        expansion = len(syllables) - 1  # How many extra syllables we get
        if expansion <= remaining_to_expand:
            expanded_set.add(idx)
            remaining_to_expand -= expansion
    
    # Build result
    for i, lyric in enumerate(lyrics):
        if i in expanded_set:
            word = lyric.get('original_word', lyric['text'])
            syllables = syllabify(word)
            for j, syl in enumerate(syllables):
                new_lyric = lyric.copy()
                new_lyric['text'] = syl
                new_lyric['is_word_start'] = j == 0
                new_lyric['is_word_end'] = j == len(syllables) - 1
                if 'time' in lyric:
                    new_lyric['time'] = lyric['time']
                result.append(new_lyric)
        else:
            result.append(lyric)
    
    return result
