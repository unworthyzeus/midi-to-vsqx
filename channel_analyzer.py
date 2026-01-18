"""
Channel Analyzer Module
Handles polyphonic instrument splitting and channel-to-lyrics matching
"""

from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
import copy


@dataclass
class ChannelInfo:
    """Information about a MIDI channel or split track"""
    channel_id: int
    track_name: str
    notes: List[Dict]
    note_count: int
    is_polyphonic: bool
    original_channel: int  # Original channel before splitting


class ChannelAnalyzer:
    """Analyzes MIDI channels and prepares them for vocal synthesis"""
    
    def __init__(self, config: Dict = None):
        self.config = {
            'max_overlap_ms': 10,  # Notes within this range are considered simultaneous
            'min_notes_per_track': 8,  # Minimum notes to consider a track valid (increased to reduce noise)
            'prefer_melody_range': (36, 96),  # Expanded MIDI note range typical for vocals (C2-C7)
            'split_logic': 'melody',  # 'melody' (top notes first) or 'chrono' (first start time)
            'filter_low_priority': True, # Whether to hide channels that are likely not vocals
            'auto_heal_limit_ms': 50, # Max overlap duration that we 'heal' (shorten note) instead of split
        }
        if config:
            self.config.update(config)
    
    def analyze_and_split(self, midi_data: Dict) -> List[ChannelInfo]:
        """
        Analyze MIDI data, split polyphonic channels, and return monophonic tracks
        
        Returns list of ChannelInfo objects, each representing a monophonic track
        """
        notes = midi_data.get('notes', [])
        
        # Group notes by channel
        channels = self._group_by_channel(notes)
        
        # Split polyphonic channels into monophonic tracks
        monophonic_tracks = []
        track_id = 0
        
        for channel_num, channel_notes in channels.items():
            # Standard MIDI Channel 10 is usually percussion - skip it for vocals
            if channel_num == 9: # 0-indexed channel 10
                continue
                
            # 1. Try to "heal" minor overlaps first to avoid splitting
            healed_notes = self._heal_overlaps(channel_notes)
            
            if self._is_polyphonic(healed_notes):
                # Split into multiple monophonic tracks
                split_tracks = self._split_polyphonic(healed_notes)
                for i, track_notes in enumerate(split_tracks):
                    # Stricter for split voices (harmonies) to avoid UI clutter
                    min_notes = self.config['min_notes_per_track']
                    if i > 0:
                        min_notes *= 2 # Harmonies need more substance to be shown
                        
                    if len(track_notes) >= min_notes:
                        monophonic_tracks.append(ChannelInfo(
                            channel_id=track_id,
                            track_name=f"Ch {channel_num} (Voice {i+1})",
                            notes=track_notes,
                            note_count=len(track_notes),
                            is_polyphonic=True,
                            original_channel=channel_num
                        ))
                        track_id += 1
            else:
                if len(healed_notes) >= self.config['min_notes_per_track']:
                    monophonic_tracks.append(ChannelInfo(
                        channel_id=track_id,
                        track_name=f"Channel {channel_num}",
                        notes=healed_notes,
                        note_count=len(healed_notes),
                        is_polyphonic=False,
                        original_channel=channel_num
                    ))
                    track_id += 1
        
        return monophonic_tracks
    
    def _group_by_channel(self, notes: List[Dict]) -> Dict[int, List[Dict]]:
        """Group notes by MIDI channel"""
        channels = {}
        for note in notes:
            ch = note.get('channel', 0)
            if ch not in channels:
                channels[ch] = []
            channels[ch].append(note)
        
        # Sort each channel by start time
        for ch in channels:
            channels[ch].sort(key=lambda n: n['start'])
        
        return channels
    
    def _heal_overlaps(self, notes: List[Dict]) -> List[Dict]:
        """
        Attempts to fix minor overlaps by shortening previous notes.
        This preserves monophonic tracks that just have sloppy MIDI timing.
        """
        if not notes:
            return []
            
        healed = [copy.deepcopy(notes[0])]
        limit = self.config['auto_heal_limit_ms']
        
        for i in range(1, len(notes)):
            current = copy.deepcopy(notes[i])
            previous = healed[-1]
            
            prev_end = previous['start'] + previous['duration']
            overlap = prev_end - current['start']
            
            if 0 < overlap <= limit:
                # Minor overlap - shorten previous note
                previous['duration'] = max(1, previous['duration'] - overlap)
            
            healed.append(current)
            
        return healed
        
    def _is_polyphonic(self, notes: List[Dict]) -> bool:
        """Check if a set of notes contains polyphonic sections"""
        max_overlap = self.config['max_overlap_ms']
        
        for i in range(len(notes) - 1):
            note_end = notes[i]['start'] + notes[i]['duration']
            next_start = notes[i + 1]['start']
            
            # If next note starts before current ends (with tolerance)
            if next_start < note_end - max_overlap:
                return True
        
        return False
    
    def _split_polyphonic(self, notes: List[Dict]) -> List[List[Dict]]:
        """
        Split polyphonic notes into multiple monophonic voice lines.
        Prioritizes higher pitches for earlier voices (usually where the melody is).
        """
        max_overlap = self.config['max_overlap_ms']
        voices = []  # List of voice tracks, each is a list of notes
        
        # Sort logic based on config
        if self.config.get('split_logic') == 'melody':
            # Sort notes by start time, then by pitch (highest first) to keep melody in top voice
            sorted_notes = sorted(notes, key=lambda n: (n['start'], -n['pitch']))
        else:
            # Strictly chronological
            sorted_notes = sorted(notes, key=lambda n: n['start'])
        
        for note in sorted_notes:
            note_copy = copy.deepcopy(note)
            assigned = False
            
            # Try to assign to the first available voice where it doesn't overlap
            for voice in voices:
                if not voice:
                    voice.append(note_copy)
                    assigned = True
                    break
                
                # Check if note fits after the last note in this voice
                last_note = voice[-1]
                last_end = last_note['start'] + last_note['duration']
                
                # VSQX is strict: next note's start MUST be >= previous note's end
                if note_copy['start'] >= last_end - 1: # 1ms overlap tolerance for rounding
                    voice.append(note_copy)
                    assigned = True
                    break
            
            # Create new voice if no existing voice can take this note
            if not assigned:
                voices.append([note_copy])
        
        return voices
    
    def match_channels_to_lyrics(
        self, 
        tracks: List[ChannelInfo], 
        lyrics_groups: List[List[Dict]]
    ) -> List[Tuple[ChannelInfo, List[Dict], float]]:
        """
        Match MIDI tracks to lyrics groups based on similarity
        
        Args:
            tracks: List of monophonic track info
            lyrics_groups: List of lyrics groups (e.g., multiple verses or parts)
        
        Returns:
            List of (track, lyrics, similarity_score) tuples
        """
        if not tracks:
            return []
        
        if not lyrics_groups:
            # No lyrics - return tracks with empty lyrics
            return [(track, [], 0.0) for track in tracks]
        
        results = []
        used_lyrics = set()
        
        # Sort tracks by note count (prefer tracks with more notes)
        sorted_tracks = sorted(tracks, key=lambda t: -t.note_count)
        
        for track in sorted_tracks:
            best_match = None
            best_score = -1.0
            best_idx = -1
            
            for i, lyrics in enumerate(lyrics_groups):
                if i in used_lyrics:
                    continue
                
                score = self._calculate_similarity(track, lyrics)
                if score > best_score:
                    best_score = score
                    best_match = lyrics
                    best_idx = i
            
            if best_match is not None and best_score > 0.3:  # Threshold for matching
                results.append((track, best_match, best_score))
                used_lyrics.add(best_idx)
            else:
                # No good match - use empty lyrics
                results.append((track, [], 0.0))
        
        return results
    
    def _calculate_similarity(self, track: ChannelInfo, lyrics: List[Dict]) -> float:
        """
        Calculate similarity score between a track and lyrics
        Based on:
        - Note count vs syllable count (primary)
        - Pitch range (vocal range preference)
        - Note duration patterns
        """
        if not lyrics:
            return 0.0
        
        note_count = track.note_count
        syllable_count = len(lyrics)
        
        # Count similarity (most important)
        if note_count == 0 or syllable_count == 0:
            count_score = 0.0
        else:
            ratio = min(note_count, syllable_count) / max(note_count, syllable_count)
            count_score = ratio
        
        # Pitch range score (prefer vocal range)
        pitches = [n['pitch'] for n in track.notes]
        if pitches:
            avg_pitch = sum(pitches) / len(pitches)
            min_vocal, max_vocal = self.config['prefer_melody_range']
            mid_vocal = (min_vocal + max_vocal) / 2
            
            if min_vocal <= avg_pitch <= max_vocal:
                # Within vocal range
                range_score = 1.0 - abs(avg_pitch - mid_vocal) / ((max_vocal - min_vocal) / 2) * 0.3
            else:
                # Outside vocal range - penalize
                if avg_pitch < min_vocal:
                    range_score = max(0, 0.5 - (min_vocal - avg_pitch) / 24)
                else:
                    range_score = max(0, 0.5 - (avg_pitch - max_vocal) / 24)
        else:
            range_score = 0.5
        
        # Weighted combination
        similarity = count_score * 0.7 + range_score * 0.3
        
        return similarity
    
    def get_best_vocal_track(self, tracks: List[ChannelInfo]) -> ChannelInfo:
        """
        Identify the most likely vocal/melody track based on heuristics
        """
        if not tracks:
            return None
        
        def track_score(track: ChannelInfo) -> float:
            # Factors: note count, pitch range, monophonic preference
            notes = track.notes
            if not notes:
                return 0
            
            pitches = [n['pitch'] for n in notes]
            avg_pitch = sum(pitches) / len(pitches)
            min_vocal, max_vocal = self.config['prefer_melody_range']
            
            # Pitch range score
            if min_vocal <= avg_pitch <= max_vocal:
                pitch_score = 1.0
            else:
                pitch_score = 0.5
            
            # Note count score (normalized)
            max_notes = max(t.note_count for t in tracks)
            count_score = track.note_count / max_notes if max_notes > 0 else 0
            
            # Prefer non-polyphonic (already split)
            poly_penalty = 0.9 if track.is_polyphonic else 1.0
            
            return (pitch_score * 0.4 + count_score * 0.6) * poly_penalty
        
        return max(tracks, key=track_score)


def analyze_midi_channels(midi_data: Dict) -> Dict[str, Any]:
    """
    Convenience function to analyze MIDI and return channel information
    """
    analyzer = ChannelAnalyzer()
    tracks = analyzer.analyze_and_split(midi_data)
    
    return {
        'tracks': tracks,
        'total_tracks': len(tracks),
        'best_vocal_track': analyzer.get_best_vocal_track(tracks),
        'has_polyphonic': any(t.is_polyphonic for t in tracks)
    }
