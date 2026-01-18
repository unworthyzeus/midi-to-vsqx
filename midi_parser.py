"""
MIDI Parser Module
Extracts notes, tempo, time signature, and embedded lyrics from MIDI files
"""

import mido
from typing import Dict, List, Any


def parse_midi(filepath: str) -> Dict[str, Any]:
    """
    Parse a MIDI file and extract relevant musical data
    
    Returns:
        Dictionary containing:
        - notes: List of note events with pitch, start time, duration
        - tempo: BPM (default 120 if not specified)
        - time_signature: Tuple of (numerator, denominator)
        - lyrics: List of lyric events extracted from MIDI
    """
    midi = mido.MidiFile(filepath)
    
    notes = []
    lyrics = []
    tempo = 500000  # Default tempo (120 BPM in microseconds per beat)
    time_signature = (4, 4)
    
    ticks_per_beat = midi.ticks_per_beat
    
    # Track active notes for calculating duration
    active_notes = {}  # key: (channel, pitch), value: (start_tick, velocity)
    
    for track in midi.tracks:
        current_tick = 0
        
        for msg in track:
            current_tick += msg.time
            
            if msg.type == 'set_tempo':
                tempo = msg.tempo
                
            elif msg.type == 'time_signature':
                time_signature = (msg.numerator, msg.denominator)
                
            elif msg.type == 'note_on' and msg.velocity > 0:
                # Note starts
                key = (msg.channel, msg.note)
                active_notes[key] = (current_tick, msg.velocity)
                
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                # Note ends
                key = (msg.channel, msg.note)
                if key in active_notes:
                    start_tick, velocity = active_notes.pop(key)
                    duration_ticks = current_tick - start_tick
                    
                    # Convert ticks to milliseconds
                    start_ms = ticks_to_ms(start_tick, tempo, ticks_per_beat)
                    duration_ms = ticks_to_ms(duration_ticks, tempo, ticks_per_beat)
                    
                    notes.append({
                        'pitch': msg.note,
                        'start': start_ms,
                        'start_ticks': start_tick,
                        'duration': duration_ms,
                        'duration_ticks': duration_ticks,
                        'velocity': velocity,
                        'channel': msg.channel
                    })
                    
            elif msg.type == 'lyrics':
                # Extract embedded lyrics
                lyrics.append({
                    'text': msg.text,
                    'time': current_tick,
                    'time_ms': ticks_to_ms(current_tick, tempo, ticks_per_beat)
                })
                
            elif msg.type == 'text' and is_lyric_text(msg.text):
                # Some MIDI files use text events for lyrics
                lyrics.append({
                    'text': msg.text,
                    'time': current_tick,
                    'time_ms': ticks_to_ms(current_tick, tempo, ticks_per_beat)
                })
    
    # Sort notes by start time
    notes.sort(key=lambda n: n['start'])
    lyrics.sort(key=lambda l: l['time'])
    
    # Convert tempo to BPM
    bpm = 60000000 / tempo
    
    return {
        'notes': notes,
        'tempo': bpm,
        'time_signature': time_signature,
        'lyrics': lyrics,
        'ticks_per_beat': ticks_per_beat,
        'raw_tempo': tempo
    }


def ticks_to_ms(ticks: int, tempo_us: int, ticks_per_beat: int) -> float:
    """Convert MIDI ticks to milliseconds"""
    if ticks_per_beat == 0:
        return 0
    return (ticks * tempo_us) / (ticks_per_beat * 1000)


def is_lyric_text(text: str) -> bool:
    """
    Heuristic to determine if a text event is likely a lyric
    (as opposed to track name, copyright, etc.)
    """
    # Skip common non-lyric text patterns
    skip_patterns = [
        'created by', 'copyright', 'track', 'channel',
        'instrument', 'tempo', 'http', 'www.', '.com',
        'midi', 'sequence'
    ]
    
    text_lower = text.lower().strip()
    
    # Skip if it matches non-lyric patterns
    for pattern in skip_patterns:
        if pattern in text_lower:
            return False
    
    # Skip very long texts (likely descriptions)
    if len(text) > 50:
        return False
    
    # Skip empty or whitespace-only
    if not text.strip():
        return False
    
    return True


def get_note_name(midi_note: int) -> str:
    """Convert MIDI note number to note name"""
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (midi_note // 12) - 1
    return f"{notes[midi_note % 12]}{octave}"
