"""
Smart Matcher Module - V2
Intelligently matches lyrics to MIDI notes with various strategies:
- 1:1 mapping when counts match
- Note splitting when more lyrics than notes
- Lyric merging when more notes than lyrics
- Timed alignment when timestamps available
- Phrase-aware matching that respects word boundaries
"""

from typing import List, Dict, Any, Optional, Tuple
from lyrics_parser import syllabify, expand_lyrics_to_syllables, syllabify_text
import copy


class SmartMatcher:
    """Intelligently matches lyrics to MIDI notes with phrase awareness"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {
            'min_note_duration': 50,      # Minimum note duration in ms
            'split_threshold': 0.3,        # Split notes longer than avg * threshold
            'timing_tolerance': 200,       # ms tolerance for timed lyrics
            'prefer_longer_notes': True,   # Prefer assigning lyrics to longer notes
            'respect_word_boundaries': True,  # Try to keep words together
            'auto_syllabify': True,        # Auto-syllabify when needed
            'phrase_gap_threshold': 500,   # Gap between notes that suggests phrase boundary (ms)
        }
    
    def match(self, notes: List[Dict], lyrics: List[Dict]) -> List[Dict]:
        """
        Main matching function
        Returns notes with lyrics assigned
        """
        if not notes:
            return []
        
        if not lyrics:
            # No lyrics - return notes with empty lyrics
            return [dict(n, lyric='a', phoneme='a') for n in notes]
        
        # Check if lyrics have timing information
        has_timing = any('time' in l for l in lyrics)
        
        if has_timing:
            return self._match_timed(notes, lyrics)
        else:
            return self._match_sequential_smart(notes, lyrics)
    
    def _match_timed(self, notes: List[Dict], lyrics: List[Dict]) -> List[Dict]:
        """Match lyrics to notes using timing information"""
        result = []
        lyrics_used = set()
        tolerance = self.config['timing_tolerance']
        
        for note in notes:
            note_copy = copy.deepcopy(note)
            note_start = note['start']
            
            # Find best matching lyric by timing
            best_lyric = None
            best_distance = float('inf')
            best_idx = -1
            
            for i, lyric in enumerate(lyrics):
                if i in lyrics_used:
                    continue
                    
                if 'time' in lyric:
                    distance = abs(lyric['time'] - note_start)
                    if distance < best_distance and distance <= tolerance:
                        best_distance = distance
                        best_lyric = lyric
                        best_idx = i
            
            if best_lyric:
                note_copy['lyric'] = best_lyric['text']
                note_copy['phoneme'] = self._text_to_phoneme(best_lyric['text'])
                lyrics_used.add(best_idx)
            else:
                note_copy['lyric'] = 'a'
                note_copy['phoneme'] = 'a'
            
            result.append(note_copy)
        
        return result
    
    def _match_sequential_smart(self, notes: List[Dict], lyrics: List[Dict]) -> List[Dict]:
        """
        Smart sequential matching with phrase awareness
        
        This improved algorithm:
        1. Identifies phrase boundaries in both notes and lyrics
        2. Matches phrases first, then individual syllables within phrases
        3. Respects word boundaries when possible
        4. Intelligently splits/merges only when necessary
        """
        num_notes = len(notes)
        num_lyrics = len(lyrics)
        
        # Extract text from lyrics
        lyric_texts = [l.get('text', '') for l in lyrics]
        
        # Perfect match case
        if num_notes == num_lyrics:
            return self._assign_one_to_one(notes, lyrics)
        
        # More lyrics than notes - might need to merge lyrics or split notes
        if num_lyrics > num_notes:
            return self._handle_more_lyrics_smart(notes, lyrics)
        
        # More notes than lyrics - need to expand lyrics or leave some empty
        return self._handle_more_notes_smart(notes, lyrics)
    
    def _assign_one_to_one(self, notes: List[Dict], lyrics: List[Dict]) -> List[Dict]:
        """Simple 1:1 assignment preserving metadata"""
        result = []
        for note, lyric in zip(notes, lyrics):
            note_copy = copy.deepcopy(note)
            text = lyric.get('text', lyric) if isinstance(lyric, dict) else lyric
            note_copy['lyric'] = text
            note_copy['phoneme'] = self._text_to_phoneme(text)
            
            # Preserve word boundary info
            if isinstance(lyric, dict):
                note_copy['is_word_start'] = lyric.get('is_word_start', True)
                note_copy['is_word_end'] = lyric.get('is_word_end', True)
                note_copy['original_word'] = lyric.get('original_word', text)
            
            result.append(note_copy)
        return result
    
    def _handle_more_lyrics_smart(self, notes: List[Dict], lyrics: List[Dict]) -> List[Dict]:
        """
        Handle case where there are more lyrics than notes
        Strategy: Try to merge lyrics while respecting word boundaries
        """
        result = []
        num_notes = len(notes)
        num_lyrics = len(lyrics)
        
        # Calculate how many lyrics per note on average
        lyrics_per_note = num_lyrics / num_notes
        
        # Try to find word boundaries to group lyrics
        lyric_idx = 0
        
        for i, note in enumerate(notes):
            note_copy = copy.deepcopy(note)
            
            # Calculate how many lyrics this note should get
            remaining_notes = num_notes - i
            remaining_lyrics = num_lyrics - lyric_idx
            
            if remaining_notes == 1:
                # Last note - take all remaining lyrics
                lyrics_to_take = remaining_lyrics
            else:
                # Try to take lyrics up to next word boundary
                lyrics_to_take = max(1, int(remaining_lyrics / remaining_notes))
                
                # Adjust to word boundary if respecting boundaries
                if self.config['respect_word_boundaries'] and lyric_idx + lyrics_to_take < num_lyrics:
                    for j in range(lyrics_to_take, min(lyrics_to_take + 3, remaining_lyrics)):
                        if lyric_idx + j >= num_lyrics:
                            break
                        if lyrics[lyric_idx + j - 1].get('is_word_end', True):
                            lyrics_to_take = j
                            break
            
            # Merge the lyrics
            merged_texts = []
            for j in range(lyrics_to_take):
                if lyric_idx + j < num_lyrics:
                    text = lyrics[lyric_idx + j].get('text', '')
                    # Add hyphen if mid-word continuation
                    if j > 0 and not lyrics[lyric_idx + j].get('is_word_start', True):
                        merged_texts.append(text)
                    else:
                        merged_texts.append(text)
            
            merged_text = ''.join(merged_texts) if len(merged_texts) <= 2 else ' '.join(merged_texts)
            note_copy['lyric'] = merged_text
            note_copy['phoneme'] = self._text_to_phoneme(merged_text)
            note_copy['merged_count'] = lyrics_to_take
            
            result.append(note_copy)
            lyric_idx += lyrics_to_take
        
        return result
    
    def _handle_more_notes_smart(self, notes: List[Dict], lyrics: List[Dict]) -> List[Dict]:
        """
        Handle case where there are more notes than lyrics
        Strategy: Expand multi-syllable words, then distribute with phrase awareness
        """
        num_notes = len(notes)
        num_lyrics = len(lyrics)
        
        # Step 1: Try to expand lyrics by syllabifying multi-syllable words
        if self.config['auto_syllabify']:
            expanded_lyrics = expand_lyrics_to_syllables(lyrics, num_notes)
        else:
            expanded_lyrics = lyrics
        
        num_expanded = len(expanded_lyrics)
        
        # If expansion gave us enough syllables
        if num_expanded >= num_notes:
            return self._assign_one_to_one(notes, expanded_lyrics[:num_notes])
        
        # Step 2: Find phrase boundaries in notes (gaps between notes)
        note_phrases = self._find_note_phrases(notes)
        
        # Step 3: Find word boundaries in lyrics
        lyric_words = self._group_lyrics_by_word(expanded_lyrics)
        
        # Step 4: Match using phrase-aware distribution
        return self._distribute_with_phrases(notes, expanded_lyrics, note_phrases, lyric_words)
    
    def _find_note_phrases(self, notes: List[Dict]) -> List[List[int]]:
        """
        Identify phrase boundaries in notes based on gaps between them
        Returns list of lists, each containing indices of notes in a phrase
        """
        if not notes:
            return []
        
        gap_threshold = self.config['phrase_gap_threshold']
        phrases = [[0]]
        
        for i in range(1, len(notes)):
            prev_end = notes[i-1]['start'] + notes[i-1]['duration']
            curr_start = notes[i]['start']
            gap = curr_start - prev_end
            
            if gap >= gap_threshold:
                # New phrase
                phrases.append([i])
            else:
                phrases[-1].append(i)
        
        return phrases
    
    def _group_lyrics_by_word(self, lyrics: List[Dict]) -> List[List[int]]:
        """
        Group lyrics by word boundaries
        Returns list of lists, each containing indices of syllables in a word
        """
        if not lyrics:
            return []
        
        words = [[0]]
        
        for i in range(1, len(lyrics)):
            if lyrics[i].get('is_word_start', True):
                words.append([i])
            else:
                words[-1].append(i)
        
        return words
    
    def _distribute_with_phrases(
        self, 
        notes: List[Dict], 
        lyrics: List[Dict],
        note_phrases: List[List[int]],
        lyric_words: List[List[int]]
    ) -> List[Dict]:
        """
        Distribute lyrics among notes respecting phrase and word boundaries
        """
        result = [copy.deepcopy(n) for n in notes]
        num_notes = len(notes)
        num_lyrics = len(lyrics)
        
        if num_lyrics == 0:
            for note in result:
                note['lyric'] = 'a'
                note['phoneme'] = 'a'
            return result
        
        # Calculate optimal distribution
        notes_per_lyric = num_notes / num_lyrics
        
        # Assign lyrics with even distribution
        lyric_assign = {}  # note_idx -> lyric_idx
        
        for lyric_idx in range(num_lyrics):
            # Calculate which note this lyric should go to
            note_idx = int(lyric_idx * notes_per_lyric)
            note_idx = min(note_idx, num_notes - 1)
            
            # If this note already has a lyric, find next available
            while note_idx in lyric_assign and note_idx < num_notes - 1:
                note_idx += 1
            
            lyric_assign[note_idx] = lyric_idx
        
        # Apply assignments
        for note_idx, note in enumerate(result):
            if note_idx in lyric_assign:
                lyric_idx = lyric_assign[note_idx]
                lyric = lyrics[lyric_idx]
                text = lyric.get('text', lyric) if isinstance(lyric, dict) else lyric
                note['lyric'] = text
                note['phoneme'] = self._text_to_phoneme(text)
                note['is_word_start'] = lyric.get('is_word_start', True) if isinstance(lyric, dict) else True
                note['is_word_end'] = lyric.get('is_word_end', True) if isinstance(lyric, dict) else True
            else:
                # No lyric assigned - continuation
                note['lyric'] = '-'
                note['phoneme'] = ''
        
        return result
    
    def _match_sequential(self, notes: List[Dict], lyrics: List[Dict]) -> List[Dict]:
        """Original sequential matching (kept for backwards compatibility)"""
        num_notes = len(notes)
        num_lyrics = len(lyrics)
        
        lyric_texts = [l.get('text', l) if isinstance(l, dict) else l for l in lyrics]
        
        if num_notes == num_lyrics:
            return self._assign_one_to_one(notes, lyrics)
        elif num_lyrics > num_notes:
            return self._handle_more_lyrics(notes, lyric_texts)
        else:
            return self._handle_more_notes(notes, lyric_texts)
    
    def _handle_more_lyrics(self, notes: List[Dict], lyrics: List[str]) -> List[Dict]:
        """Handle case where there are more lyrics than notes (legacy)"""
        result = []
        min_duration = self.config['min_note_duration']
        
        num_notes = len(notes)
        num_lyrics = len(lyrics)
        
        avg_duration = sum(n['duration'] for n in notes) / num_notes
        
        splittable = []
        for i, note in enumerate(notes):
            if note['duration'] >= min_duration * 2:
                splittable.append(i)
        
        extra_needed = num_lyrics - num_notes
        
        splits = {}
        if splittable and extra_needed > 0:
            remaining = extra_needed
            while remaining > 0 and splittable:
                for idx in splittable[:]:
                    if remaining <= 0:
                        break
                    current_parts = splits.get(idx, 1)
                    note_duration = notes[idx]['duration']
                    if note_duration / (current_parts + 1) >= min_duration:
                        splits[idx] = current_parts + 1
                        remaining -= 1
                    else:
                        splittable.remove(idx)
                
                if not splittable:
                    break
        
        lyric_idx = 0
        for i, note in enumerate(notes):
            if i in splits:
                num_parts = splits[i]
                part_duration = note['duration'] / num_parts
                part_duration_ticks = note.get('duration_ticks', note['duration']) / num_parts
                
                for p in range(num_parts):
                    note_copy = copy.deepcopy(note)
                    note_copy['start'] = note['start'] + (p * part_duration)
                    note_copy['duration'] = part_duration
                    
                    if 'start_ticks' in note:
                        note_copy['start_ticks'] = note['start_ticks'] + (p * part_duration_ticks)
                        note_copy['duration_ticks'] = part_duration_ticks
                    
                    note_copy['was_split'] = True
                    
                    if lyric_idx < num_lyrics:
                        note_copy['lyric'] = lyrics[lyric_idx]
                        note_copy['phoneme'] = self._text_to_phoneme(lyrics[lyric_idx])
                        lyric_idx += 1
                    else:
                        note_copy['lyric'] = 'a'
                        note_copy['phoneme'] = 'a'
                    
                    result.append(note_copy)
            else:
                note_copy = copy.deepcopy(note)
                if lyric_idx < num_lyrics:
                    note_copy['lyric'] = lyrics[lyric_idx]
                    note_copy['phoneme'] = self._text_to_phoneme(lyrics[lyric_idx])
                    lyric_idx += 1
                else:
                    note_copy['lyric'] = 'a'
                    note_copy['phoneme'] = 'a'
                result.append(note_copy)
        
        if lyric_idx < num_lyrics:
            remaining_lyrics = lyrics[lyric_idx:]
            for i, lyric in enumerate(remaining_lyrics):
                if result:
                    target_idx = min(i, len(result) - 1)
                    result[target_idx]['lyric'] += ' ' + lyric
        
        return result
    
    def _handle_more_notes(self, notes: List[Dict], lyrics: List[str]) -> List[Dict]:
        """Handle case where there are more notes than lyrics (legacy)"""
        result = []
        num_notes = len(notes)
        num_lyrics = len(lyrics)
        
        expanded_lyrics = []
        for lyric in lyrics:
            syllables = syllabify(lyric)
            if len(syllables) > 1 and len(expanded_lyrics) + len(syllables) <= num_notes:
                expanded_lyrics.extend(syllables)
            else:
                expanded_lyrics.append(lyric)
        
        if len(expanded_lyrics) >= num_notes:
            return self._assign_one_to_one(notes, [{'text': l} for l in expanded_lyrics[:num_notes]])
        
        spacing = num_notes / len(expanded_lyrics)
        
        lyric_positions = []
        for i in range(len(expanded_lyrics)):
            pos = int(i * spacing)
            lyric_positions.append(pos)
        
        pos_to_lyric = {pos: lyric for pos, lyric in zip(lyric_positions, expanded_lyrics)}
        
        for i, note in enumerate(notes):
            note_copy = copy.deepcopy(note)
            if i in pos_to_lyric:
                note_copy['lyric'] = pos_to_lyric[i]
                note_copy['phoneme'] = self._text_to_phoneme(pos_to_lyric[i])
            else:
                note_copy['lyric'] = '-'
                note_copy['phoneme'] = ''
            result.append(note_copy)
        
        return result
    
    def _text_to_phoneme(self, text: str) -> str:
        """
        Convert text to basic phoneme representation
        """
        if not text or text == '-':
            return ''
        
        text = text.lower().strip()
        return text


def create_matcher(
    respect_word_boundaries: bool = True,
    auto_syllabify: bool = True,
    timing_tolerance: int = 200,
    phrase_gap_threshold: int = 500
) -> SmartMatcher:
    """Factory function to create a configured SmartMatcher"""
    return SmartMatcher({
        'min_note_duration': 50,
        'split_threshold': 0.3,
        'timing_tolerance': timing_tolerance,
        'prefer_longer_notes': True,
        'respect_word_boundaries': respect_word_boundaries,
        'auto_syllabify': auto_syllabify,
        'phrase_gap_threshold': phrase_gap_threshold,
    })
