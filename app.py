"""
MIDI to Voice Synth Converter - Flask Backend
Converts MIDI files + lyrics into vocal synthesis project formats

Supported Formats:
- VSQX (Vocaloid 4)
- VPR (Vocaloid 5/6)
- UST (UTAU)
- USTX (OpenUTAU)
- SVP (Synthesizer V)

Based on format specifications from UtaFormatix3 (Apache 2.0)
https://github.com/sdercolin/utaformatix3
"""

from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import os
import tempfile
import io
import json
from midi_parser import parse_midi
from lyrics_parser import parse_lyrics, LyricsFormat, syllabify_text, expand_lyrics_to_syllables
from vsqx_generator import (
    generate_output, generate_multi_track_output, 
    OutputFormat, SINGERS, get_file_extension, get_mime_type
)
from smart_matcher import SmartMatcher, create_matcher

# Backward compatibility
VSQXVersion = OutputFormat
generate_vsqx = generate_output
generate_multi_track_vsqx = generate_multi_track_output
from channel_analyzer import ChannelAnalyzer, analyze_midi_channels

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Ensure upload folder exists
UPLOAD_FOLDER = tempfile.mkdtemp()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max


@app.route('/')
def index():
    """Serve the main application page"""
    return app.send_static_file('index.html')


@app.route('/api/convert', methods=['POST'])
def convert():
    """
    Main conversion endpoint
    Accepts MIDI file, optional lyrics file, and configuration options
    Returns generated VSQX file (or ZIP with multiple tracks)
    
    New: Supports channel_lyrics_mapping for assigning different lyrics to different channels
    Format: { "channel_id": "lyrics_text" }
    """
    try:
        # Get uploaded files
        if 'midi' not in request.files:
            return jsonify({'error': 'No MIDI file provided'}), 400
        
        midi_file = request.files['midi']
        lyrics_file = request.files.get('lyrics')
        
        # Get configuration options
        vsqx_version = request.form.get('version', 'vsq4')
        lyrics_format = request.form.get('lyrics_format', 'auto')
        lyrics_source = request.form.get('lyrics_source', 'midi')
        tempo_override = request.form.get('tempo')
        multi_track = request.form.get('multi_track', 'false') == 'true'
        selected_channel = request.form.get('selected_channel')
        
        # New: Channel-specific lyrics mapping
        channel_lyrics_raw = request.form.get('channel_lyrics_mapping', '{}')
        try:
            channel_lyrics_mapping = json.loads(channel_lyrics_raw)
        except json.JSONDecodeError:
            channel_lyrics_mapping = {}
        
        # Smart matching options
        respect_word_boundaries = request.form.get('respect_word_boundaries', 'true') == 'true'
        auto_syllabify = request.form.get('auto_syllabify', 'true') == 'true'
        try:
            phrase_gap = float(request.form.get('phrase_gap_threshold', 400))
        except ValueError:
            phrase_gap = 400.0
        try:
            overlap_ms = float(request.form.get('overlap_ms', 10))
        except ValueError:
            overlap_ms = 10.0
        split_logic = request.form.get('split_logic', 'melody')
        
        # Save MIDI file temporarily
        midi_path = os.path.join(app.config['UPLOAD_FOLDER'], 'input.mid')
        midi_file.save(midi_path)
        
        # Parse MIDI file
        midi_data = parse_midi(midi_path)
        
        # Analyze channels and split polyphonic parts
        analyzer = ChannelAnalyzer(config={'max_overlap_ms': overlap_ms, 'split_logic': split_logic})
        tracks = analyzer.analyze_and_split(midi_data)
        
        # Get default lyrics (used when no channel-specific lyrics provided)
        default_lyrics = []
        if lyrics_source == 'midi':
            default_lyrics = midi_data.get('lyrics', [])
        elif lyrics_file:
            lyrics_path = os.path.join(app.config['UPLOAD_FOLDER'], 'lyrics.txt')
            lyrics_file.save(lyrics_path)
            with open(lyrics_path, 'r', encoding='utf-8') as f:
                lyrics_content = f.read()
            default_lyrics = parse_lyrics(lyrics_content, LyricsFormat(lyrics_format))
        
        manual_lyrics = request.form.get('manual_lyrics', '').strip()
        if manual_lyrics:
            default_lyrics = parse_lyrics(manual_lyrics, LyricsFormat.PLAIN)
        
        # Override tempo if specified
        if tempo_override:
            try:
                midi_data['tempo'] = float(tempo_override)
            except ValueError:
                pass
        
        # Parse version
        version_map = {
            'vsqx': OutputFormat.VSQX,
            'vpr': OutputFormat.VPR,
            'ust': OutputFormat.UST,
            'ustx': OutputFormat.USTX,
            'svp': OutputFormat.SVP,
        }
        version = version_map.get(vsqx_version, OutputFormat.VSQX)
        
        # Create configured matcher
        matcher = create_matcher(
            respect_word_boundaries=respect_word_boundaries,
            auto_syllabify=auto_syllabify,
            phrase_gap_threshold=phrase_gap
        )
        
        base_filename = os.path.splitext(midi_file.filename)[0]
        
        # Determine file extension and mime type from format
        file_ext = get_file_extension(version)
        mime_type = get_mime_type(version)
        is_binary = (version == OutputFormat.VPR)  # VPR is a ZIP file
        
        if multi_track and len(tracks) > 1:
            # Generate multi-track project with per-channel lyrics
            track_data = []
            
            for track in tracks:
                # Get lyrics for this channel
                channel_key = str(track.channel_id)
                if channel_key in channel_lyrics_mapping:
                    track_lyrics_text = channel_lyrics_mapping[channel_key]
                    track_lyrics = parse_lyrics(track_lyrics_text, LyricsFormat.PLAIN)
                else:
                    track_lyrics = default_lyrics
                
                if track_lyrics:
                    similarity = analyzer._calculate_similarity(track, track_lyrics)
                else:
                    similarity = 0.0
                
                matched_notes = matcher.match(track.notes, track_lyrics)
                
                track_data.append({
                    'name': track.track_name,
                    'notes': matched_notes,
                    'similarity': similarity,
                    'note_count': track.note_count,
                    'is_polyphonic': track.is_polyphonic
                })
            
            track_data.sort(key=lambda t: -t['similarity'])
            
            content = generate_multi_track_output(
                tracks=track_data,
                tempo=midi_data['tempo'],
                time_signature=midi_data['time_signature'],
                output_format=version,
                singer_name='Default'
            )
            
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], f'output{file_ext}')
            if is_binary:
                with open(output_path, 'wb') as f:
                    f.write(content)
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            return send_file(
                output_path,
                mimetype=mime_type,
                as_attachment=True,
                download_name=f'{base_filename}_multitrack{file_ext}'
            )
        else:
            # Single track mode
            if selected_channel is not None:
                try:
                    channel_idx = int(selected_channel)
                    target_track = next((t for t in tracks if t.channel_id == channel_idx), None)
                except (ValueError, StopIteration):
                    target_track = None
            else:
                target_track = None
            
            if target_track is None:
                if default_lyrics and tracks:
                    best_score = -1
                    for track in tracks:
                        score = analyzer._calculate_similarity(track, default_lyrics)
                        if score > best_score:
                            best_score = score
                            target_track = track
                elif tracks:
                    target_track = analyzer.get_best_vocal_track(tracks)
            
            if target_track:
                notes_to_use = target_track.notes
                similarity = analyzer._calculate_similarity(target_track, default_lyrics) if default_lyrics else 0.0
            else:
                notes_to_use = midi_data['notes']
                similarity = 0.0
            
            matched_notes = matcher.match(notes_to_use, default_lyrics)
            
            content = generate_vsqx(
                notes=matched_notes,
                tempo=midi_data['tempo'],
                time_signature=midi_data['time_signature'],
                version=version,
                singer_name=singer_name,
                similarity_score=similarity
            )
            
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], f'output{file_ext}')
            if is_binary:
                with open(output_path, 'wb') as f:
                    f.write(content)
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            return send_file(
                output_path,
                mimetype=mime_type,
                as_attachment=True,
                download_name=f'{base_filename}{file_ext}'
            )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/preview', methods=['POST'])
def preview():
    """
    Preview the conversion without downloading
    Returns JSON with matched notes, lyrics, and channel analysis
    
    New: Supports channel_lyrics_mapping for previewing per-channel lyrics
    """
    try:
        if 'midi' not in request.files:
            return jsonify({'error': 'No MIDI file provided'}), 400
        
        midi_file = request.files['midi']
        lyrics_file = request.files.get('lyrics')
        
        lyrics_format = request.form.get('lyrics_format', 'auto')
        lyrics_source = request.form.get('lyrics_source', 'midi')
        selected_channel = request.form.get('selected_channel')
        
        # Smart matching options
        respect_word_boundaries = request.form.get('respect_word_boundaries', 'true') == 'true'
        auto_syllabify = request.form.get('auto_syllabify', 'true') == 'true'
        try:
            phrase_gap = float(request.form.get('phrase_gap_threshold', 400))
        except ValueError:
            phrase_gap = 400.0
        try:
            overlap_ms = float(request.form.get('overlap_ms', 10))
        except ValueError:
            overlap_ms = 10.0
        split_logic = request.form.get('split_logic', 'melody')
        
        # Channel-specific lyrics mapping
        channel_lyrics_raw = request.form.get('channel_lyrics_mapping', '{}')
        try:
            channel_lyrics_mapping = json.loads(channel_lyrics_raw)
        except json.JSONDecodeError:
            channel_lyrics_mapping = {}
        
        # Save and parse MIDI
        midi_path = os.path.join(app.config['UPLOAD_FOLDER'], 'preview.mid')
        midi_file.save(midi_path)
        midi_data = parse_midi(midi_path)
        
        # Analyze channels
        analyzer = ChannelAnalyzer(config={'max_overlap_ms': overlap_ms, 'split_logic': split_logic})
        tracks = analyzer.analyze_and_split(midi_data)
        
        # Get default lyrics
        default_lyrics = []
        if lyrics_source == 'midi':
            default_lyrics = midi_data.get('lyrics', [])
        elif lyrics_file:
            lyrics_path = os.path.join(app.config['UPLOAD_FOLDER'], 'preview_lyrics.txt')
            lyrics_file.save(lyrics_path)
            with open(lyrics_path, 'r', encoding='utf-8') as f:
                lyrics_content = f.read()
            default_lyrics = parse_lyrics(lyrics_content, LyricsFormat(lyrics_format))
        
        manual_lyrics = request.form.get('manual_lyrics', '').strip()
        if manual_lyrics:
            default_lyrics = parse_lyrics(manual_lyrics, LyricsFormat.PLAIN)
        
        # Calculate similarity for each track
        track_info = []
        for track in tracks:
            # Use channel-specific lyrics if available
            channel_key = str(track.channel_id)
            if channel_key in channel_lyrics_mapping:
                track_lyrics = parse_lyrics(channel_lyrics_mapping[channel_key], LyricsFormat.PLAIN)
            else:
                track_lyrics = default_lyrics
            
            similarity = analyzer._calculate_similarity(track, track_lyrics) if track_lyrics else 0.0
            
            track_info.append({
                'channel_id': track.channel_id,
                'name': track.track_name,
                'note_count': track.note_count,
                'is_polyphonic': track.is_polyphonic,
                'similarity': round(similarity * 100, 1),
                'original_channel': track.original_channel,
                'has_custom_lyrics': channel_key in channel_lyrics_mapping
            })
        
        track_info.sort(key=lambda t: -t['similarity'])
        
        # Select track for preview
        if selected_channel is not None:
            try:
                channel_idx = int(selected_channel)
                target_track = next((t for t in tracks if t.channel_id == channel_idx), None)
            except (ValueError, StopIteration):
                target_track = tracks[0] if tracks else None
        else:
            if default_lyrics and tracks:
                best_score = -1
                target_track = None
                for track in tracks:
                    score = analyzer._calculate_similarity(track, default_lyrics)
                    if score > best_score:
                        best_score = score
                        target_track = track
            elif tracks:
                target_track = analyzer.get_best_vocal_track(tracks)
            else:
                target_track = None
        
        # Get lyrics for selected track
        if target_track:
            channel_key = str(target_track.channel_id)
            if channel_key in channel_lyrics_mapping:
                track_lyrics = parse_lyrics(channel_lyrics_mapping[channel_key], LyricsFormat.PLAIN)
            else:
                track_lyrics = default_lyrics
            
            notes_to_use = target_track.notes
            selected_similarity = analyzer._calculate_similarity(target_track, track_lyrics) if track_lyrics else 0.0
        else:
            notes_to_use = midi_data['notes']
            track_lyrics = default_lyrics
            selected_similarity = 0.0
        
        # Smart match with configured options
        matcher = create_matcher(
            respect_word_boundaries=respect_word_boundaries,
            auto_syllabify=auto_syllabify,
            phrase_gap_threshold=phrase_gap
        )
        matched_notes = matcher.match(notes_to_use, track_lyrics)
        
        # Build preview response
        preview_data = {
            'tempo': midi_data['tempo'],
            'time_signature': midi_data['time_signature'],
            'total_notes': len(midi_data['notes']),
            'total_lyrics': len(track_lyrics),
            'channels': track_info,
            'selected_channel': target_track.channel_id if target_track else None,
            'similarity_score': round(selected_similarity * 100, 1),
            'matched_notes': [
                {
                    'pitch': n['pitch'],
                    'pitch_name': note_name(n['pitch']),
                    'start': n['start'],
                    'duration': n['duration'],
                    'lyric': n.get('lyric', ''),
                    'phoneme': n.get('phoneme', ''),
                    'was_split': n.get('was_split', False),
                    'is_word_start': n.get('is_word_start', True),
                    'is_word_end': n.get('is_word_end', True),
                    'original_word': n.get('original_word', '')
                }
                for n in matched_notes[:100]
            ],
            'has_more': len(matched_notes) > 100,
            'matching_options': {
                'respect_word_boundaries': respect_word_boundaries,
                'auto_syllabify': auto_syllabify
            }
        }
        
        return jsonify(preview_data)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    Analyze MIDI file and return channel information
    Useful for selecting which channel to use before conversion
    """
    try:
        if 'midi' not in request.files:
            return jsonify({'error': 'No MIDI file provided'}), 400
        
        midi_file = request.files['midi']
        
        # Save and parse MIDI
        midi_path = os.path.join(app.config['UPLOAD_FOLDER'], 'analyze.mid')
        midi_file.save(midi_path)
        midi_data = parse_midi(midi_path)
        
        # Analyze channels
        try:
            overlap_ms = float(request.form.get('overlap_ms', 10))
        except ValueError:
            overlap_ms = 10.0
        split_logic = request.form.get('split_logic', 'melody')
        
        analyzer = ChannelAnalyzer(config={'max_overlap_ms': overlap_ms, 'split_logic': split_logic})
        tracks = analyzer.analyze_and_split(midi_data)
        best_track = analyzer.get_best_vocal_track(tracks)
        
        # Build response
        track_info = []
        for track in tracks:
            pitches = [n['pitch'] for n in track.notes]
            min_pitch = min(pitches) if pitches else 0
            max_pitch = max(pitches) if pitches else 0
            avg_pitch = sum(pitches) / len(pitches) if pitches else 0
            
            # Get duration info
            durations = [n['duration'] for n in track.notes]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            track_info.append({
                'channel_id': track.channel_id,
                'name': track.track_name,
                'note_count': track.note_count,
                'is_polyphonic': track.is_polyphonic,
                'original_channel': track.original_channel,
                'pitch_range': {
                    'min': min_pitch,
                    'min_name': note_name(min_pitch),
                    'max': max_pitch,
                    'max_name': note_name(max_pitch),
                    'avg': round(avg_pitch, 1),
                    'avg_name': note_name(int(avg_pitch))
                },
                'avg_duration_ms': round(avg_duration, 1),
                'is_recommended': track == best_track
            })
        
        return jsonify({
            'tempo': midi_data['tempo'],
            'time_signature': midi_data['time_signature'],
            'total_notes': len(midi_data['notes']),
            'embedded_lyrics_count': len(midi_data.get('lyrics', [])),
            'has_embedded_lyrics': len(midi_data.get('lyrics', [])) > 0,
            'channels': track_info,
            'recommended_channel': best_track.channel_id if best_track else None,
            'has_polyphonic': any(t.is_polyphonic for t in tracks)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/syllabify', methods=['POST'])
def syllabify_endpoint():
    """
    Syllabify text and return the syllables
    Useful for previewing how text will be split
    """
    try:
        data = request.get_json()
        text = data.get('text', '')
        preserve_hyphenated = data.get('preserve_hyphenated', True)
        
        if not text:
            return jsonify({'syllables': [], 'count': 0})
        
        syllables = syllabify_text(text, preserve_hyphenated=preserve_hyphenated)
        
        return jsonify({
            'syllables': syllables,
            'count': len(syllables),
            'original_text': text
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/singers', methods=['GET'])
def get_singers():
    """
    Return list of available singers/voicebanks
    Organized by Vocaloid version
    """
    by_version = {}
    for key, singer in SINGERS.items():
        version = singer.get('version', 'Any')
        if version not in by_version:
            by_version[version] = []
        by_version[version].append({
            'key': key,
            'id': singer['id'],
            'name': singer['name'],
            'type': singer.get('type', 'Standard'),
            'language': singer.get('language', 'Any')
        })
    
    version_order = ['V6', 'V5', 'V4', 'V3', 'Any']
    ordered = []
    for v in version_order:
        if v in by_version:
            ordered.append({
                'version': v,
                'label': f'Vocaloid {v[1]}' if v.startswith('V') else 'Other',
                'singers': by_version[v]
            })
    
    return jsonify({
        'singers': SINGERS,
        'by_version': ordered,
        'total': len(SINGERS)
    })


def note_name(midi_note: int) -> str:
    """Convert MIDI note number to note name (e.g., 60 -> C4)"""
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (midi_note // 12) - 1
    note = notes[midi_note % 12]
    return f"{note}{octave}"


if __name__ == '__main__':
    app.run(debug=True, port=5000)
