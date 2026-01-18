"""
VSQX/VPR Generator Module
Generates Vocaloid project files:
- VSQ3 (Vocaloid 3)
- VSQ4 (Vocaloid 4)
- VPR (Vocaloid 5/6) - JSON-based ZIP format
"""

from enum import Enum
from typing import List, Dict, Tuple, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom
import uuid
import time
import json
import zipfile
import io


class VSQXVersion(Enum):
    """Supported Vocaloid project versions"""
    VSQ3 = 'vsq3'  # Vocaloid 3
    VSQ4 = 'vsq4'  # Vocaloid 4
    VPR = 'vpr'    # Vocaloid 5/6


# Comprehensive singer/voicebank database
# Organized by Vocaloid version with unique IDs
SINGERS = {
    # === VOCALOID 6 AI ===
    'Haruka_V6AI': {'id': 'V6AI_HARUKA_001', 'name': 'HARUKA (V6 AI)', 'version': 'V6', 'type': 'AI', 'language': 'Japanese'},
    'Akito_V6AI': {'id': 'V6AI_AKITO_001', 'name': 'AKITO (V6 AI)', 'version': 'V6', 'type': 'AI', 'language': 'Japanese'},
    'Sarah_V6AI': {'id': 'V6AI_SARAH_001', 'name': 'SARAH (V6 AI)', 'version': 'V6', 'type': 'AI', 'language': 'English'},
    'Allen_V6AI': {'id': 'V6AI_ALLEN_001', 'name': 'ALLEN (V6 AI)', 'version': 'V6', 'type': 'AI', 'language': 'English'},
    'Megpoid_V6AI': {'id': 'V6AI_GUMI_001', 'name': 'AI Megpoid (GUMI V6)', 'version': 'V6', 'type': 'AI', 'language': 'Japanese'},
    'Una_V6AI': {'id': 'V6AI_UNA_001', 'name': 'AI Otomachi Una Spicy', 'version': 'V6', 'type': 'AI', 'language': 'Japanese'},
    'Una_Sugar_V6AI': {'id': 'V6AI_UNA_SUGAR_001', 'name': 'AI Otomachi Una Sugar', 'version': 'V6', 'type': 'AI', 'language': 'Japanese'},
    'Fuiro_V6': {'id': 'V6AI_FUIRO_001', 'name': 'Fuiro (V6)', 'version': 'V6', 'type': 'AI', 'language': 'Japanese'},
    'Galaco_V6': {'id': 'V6AI_GALACO_001', 'name': 'Galaco Black & White', 'version': 'V6', 'type': 'AI', 'language': 'Japanese'},
    'Tsuina_V6AI': {'id': 'V6AI_TSUINA_001', 'name': 'AI Tsuina-chan', 'version': 'V6', 'type': 'AI', 'language': 'Japanese'},
    'Akari_V6AI': {'id': 'V6AI_AKARI_001', 'name': 'AI Kizuna Akari', 'version': 'V6', 'type': 'AI', 'language': 'Japanese'},
    'PoUta_V6': {'id': 'V6AI_POUTA_001', 'name': 'Po-uta (V6)', 'version': 'V6', 'type': 'AI', 'language': 'Japanese'},
    
    # === VOCALOID 5 (Non-AI, included with V6) ===
    'Amy_V5': {'id': 'V5_AMY_001', 'name': 'Amy (V5)', 'version': 'V5', 'type': 'Standard', 'language': 'English'},
    'Chris_V5': {'id': 'V5_CHRIS_001', 'name': 'Chris (V5)', 'version': 'V5', 'type': 'Standard', 'language': 'English'},
    'Kaori_V5': {'id': 'V5_KAORI_001', 'name': 'Kaori (V5)', 'version': 'V5', 'type': 'Standard', 'language': 'Japanese'},
    'Ken_V5': {'id': 'V5_KEN_001', 'name': 'Ken (V5)', 'version': 'V5', 'type': 'Standard', 'language': 'Japanese'},
    
    # === VOCALOID 4 (Popular, Non-AI) ===
    'Miku_V4X': {'id': 'BHHP9W79F6TFRCD5', 'name': 'Hatsune Miku V4X', 'version': 'V4', 'type': 'Standard', 'language': 'Japanese'},
    'Miku_V4X_Eng': {'id': 'BHHP9W79F6TFRCD6', 'name': 'Hatsune Miku V4X English', 'version': 'V4', 'type': 'Standard', 'language': 'English'},
    'Luka_V4X': {'id': 'BCEY7S56V3TSW7FC', 'name': 'Megurine Luka V4X', 'version': 'V4', 'type': 'Standard', 'language': 'Japanese'},
    'Rin_V4X': {'id': 'BHEY7S79F6TFRCD5', 'name': 'Kagamine Rin V4X', 'version': 'V4', 'type': 'Standard', 'language': 'Japanese'},
    'Len_V4X': {'id': 'BHFY7S79F6TFRCD5', 'name': 'Kagamine Len V4X', 'version': 'V4', 'type': 'Standard', 'language': 'Japanese'},
    'KAITO_V4': {'id': 'BHKA9W79F6TFRCD5', 'name': 'KAITO V4', 'version': 'V4', 'type': 'Standard', 'language': 'Japanese'},
    'GUMI_V4': {'id': 'BHGP9W79F6TFRCD5', 'name': 'Megpoid (GUMI) V4', 'version': 'V4', 'type': 'Standard', 'language': 'Japanese'},
    'Flower_V4': {'id': 'V4_FLOWER_001', 'name': 'v flower (V4)', 'version': 'V4', 'type': 'Standard', 'language': 'Japanese'},
    'Fukase_V4': {'id': 'V4_FUKASE_001', 'name': 'Fukase (V4)', 'version': 'V4', 'type': 'Standard', 'language': 'Japanese'},
    'Yukari_V4': {'id': 'V4_YUKARI_001', 'name': 'Yuzuki Yukari V4', 'version': 'V4', 'type': 'Standard', 'language': 'Japanese'},
    'Una_V4': {'id': 'V4_UNA_001', 'name': 'Otomachi Una (V4)', 'version': 'V4', 'type': 'Standard', 'language': 'Japanese'},
    'Una_Sugar_V4': {'id': 'V4_UNA_SUGAR_001', 'name': 'Otomachi Una Sugar (V4)', 'version': 'V4', 'type': 'Standard', 'language': 'Japanese'},
    'Cyber_Diva': {'id': 'V4_CYBERDIVA_001', 'name': 'CYBER DIVA', 'version': 'V4', 'type': 'Standard', 'language': 'English'},
    'Cyber_Songman': {'id': 'V4_CYBERSONGMAN_001', 'name': 'CYBER SONGMAN', 'version': 'V4', 'type': 'Standard', 'language': 'English'},
    
    # === VOCALOID 3 (Classic, Non-AI) ===
    'KAITO_V3': {'id': 'V3_KAITO_001', 'name': 'KAITO V3', 'version': 'V3', 'type': 'Standard', 'language': 'Japanese'},
    'IA_V3': {'id': 'BHIP9W79F6TFRCD5', 'name': 'IA (V3)', 'version': 'V3', 'type': 'Standard', 'language': 'Japanese'},
    'IA_Rocks': {'id': 'V3_IAROCKS_001', 'name': 'IA ROCKS', 'version': 'V3', 'type': 'Standard', 'language': 'Japanese'},
    'Mayu_V3': {'id': 'V3_MAYU_001', 'name': 'MAYU (V3)', 'version': 'V3', 'type': 'Standard', 'language': 'Japanese'},
    'Lily_V3': {'id': 'V3_LILY_001', 'name': 'Lily (V3)', 'version': 'V3', 'type': 'Standard', 'language': 'Japanese'},
    'VY1_V3': {'id': 'V3_VY1_001', 'name': 'VY1 (V3)', 'version': 'V3', 'type': 'Standard', 'language': 'Japanese'},
    'VY2_V3': {'id': 'V3_VY2_001', 'name': 'VY2 (V3)', 'version': 'V3', 'type': 'Standard', 'language': 'Japanese'},
    'Miku_V3': {'id': 'V3_MIKU_001', 'name': 'Hatsune Miku V3', 'version': 'V3', 'type': 'Standard', 'language': 'Japanese'},
    'SeeU_V3': {'id': 'V3_SEEU_001', 'name': 'SeeU (V3)', 'version': 'V3', 'type': 'Standard', 'language': 'Korean'},
    'Oliver_V3': {'id': 'V3_OLIVER_001', 'name': 'Oliver (V3)', 'version': 'V3', 'type': 'Standard', 'language': 'English'},
    'Avanna_V3': {'id': 'V3_AVANNA_001', 'name': 'Avanna (V3)', 'version': 'V3', 'type': 'Standard', 'language': 'English'},
    
    # === Legacy/Generic ===
    'Default': {'id': 'AAAAAAAAAAAAAAAAA', 'name': 'Default Singer', 'version': 'Any', 'type': 'Standard', 'language': 'Any'},
}

# Backwards compatibility alias
DEFAULT_SINGERS = {k: {'id': v['id'], 'name': v['name']} for k, v in SINGERS.items()}

# Also keep simple aliases for common names
SINGER_ALIASES = {
    'Miku': 'Miku_V4X',
    'Luka': 'Luka_V4X',
    'Rin': 'Rin_V4X',
    'Len': 'Len_V4X',
    'KAITO': 'KAITO_V4',
    'GUMI': 'GUMI_V4',
    'IA': 'IA_V3',
    'Haruka': 'Haruka_V6AI',
    'Akito': 'Akito_V6AI',
    'Sarah': 'Sarah_V6AI',
    'Allen': 'Allen_V6AI',
}

def get_singer(name: str) -> Dict:
    """Get singer info by name or alias"""
    # Check alias first
    if name in SINGER_ALIASES:
        name = SINGER_ALIASES[name]
    # Return singer or default
    return SINGERS.get(name, SINGERS['Default'])


def generate_vsqx(
    notes: List[Dict],
    tempo: float,
    time_signature: Tuple[int, int],
    version: VSQXVersion = VSQXVersion.VSQ4,
    singer_name: str = 'Miku',
    project_name: str = 'Converted Project',
    similarity_score: float = 0.0
) -> str:
    """
    Generate a Vocaloid project file from parsed MIDI data and lyrics
    
    Args:
        notes: List of note dictionaries with pitch, start, duration, lyric
        tempo: BPM
        time_signature: Tuple of (numerator, denominator)
        version: VSQ4 or VPR (Vocaloid 5/6). VSQ3 redirects to VSQ4.
        singer_name: Name of the singer/voicebank
        project_name: Name for the project
        similarity_score: Match quality score (0-1)
    
    Returns:
        String containing the project file content (XML for VSQX, binary for VPR)
    """
    # Include similarity in comment
    comment = f'Generated by MIDI to VSQX Converter (Match: {similarity_score*100:.1f}%)'
    
    if version == VSQXVersion.VPR:
        return _generate_vpr(notes, tempo, time_signature, singer_name, project_name, comment)
    else:
        # VSQ3 and VSQ4 both use VSQ4 format (V3 is deprecated)
        return _generate_vsq4(notes, tempo, time_signature, singer_name, project_name, comment)


def generate_multi_track_vsqx(
    tracks: List[Dict],
    tempo: float,
    time_signature: Tuple[int, int],
    version: VSQXVersion = VSQXVersion.VSQ4,
    singer_name: str = 'Miku'
) -> str:
    """
    Generate a Vocaloid project file with multiple vocal tracks
    
    Args:
        tracks: List of track dicts with 'name', 'notes', 'similarity', etc.
        tempo: BPM
        time_signature: Tuple of (numerator, denominator)
        version: VSQ4 or VPR
        singer_name: Name of the singer/voicebank
    
    Returns:
        String containing the project file content with multiple tracks
    """
    if version == VSQXVersion.VPR:
        return _generate_vpr_multi(tracks, tempo, time_signature, singer_name)
    else:
        # VSQ3 and VSQ4 both use VSQ4 format
        return _generate_vsq4_multi(tracks, tempo, time_signature, singer_name)


def _generate_vsq3(
    notes: List[Dict],
    tempo: float,
    time_signature: Tuple[int, int],
    singer_name: str,
    project_name: str,
    comment: str = 'Generated by MIDI to VSQX Converter'
) -> str:
    """Generate VSQ3 (Vocaloid 3) format"""
    
    # Get singer info
    singer = DEFAULT_SINGERS.get(singer_name, DEFAULT_SINGERS['Default'])
    
    # Create root element
    root = ET.Element('vsq3')
    root.set('xmlns', 'http://www.yamaha.co.jp/vocaloid/schema/vsq3/')
    root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    root.set('xsi:schemaLocation', 'http://www.yamaha.co.jp/vocaloid/schema/vsq3/ vsq3.xsd')
    
    # Vender and version
    ET.SubElement(root, 'vender').text = 'Yamaha corporation'
    ET.SubElement(root, 'version').text = '3.0.0.1'
    
    # Voice table
    voice_table = ET.SubElement(root, 'vVoiceTable')
    voice = ET.SubElement(voice_table, 'vVoice')
    ET.SubElement(voice, 'bs').text = '0'
    ET.SubElement(voice, 'pc').text = '0'
    ET.SubElement(voice, 'id').text = singer['id']
    ET.SubElement(voice, 'name').text = singer['name']
    ET.SubElement(voice, 'vPrm')
    
    # Mixer
    mixer = ET.SubElement(root, 'mixer')
    master_unit = ET.SubElement(mixer, 'masterUnit')
    ET.SubElement(master_unit, 'outDev').text = '0'
    ET.SubElement(master_unit, 'vol').text = '0'
    
    vs_unit = ET.SubElement(mixer, 'vsUnit')
    ET.SubElement(vs_unit, 'tNo').text = '0'
    ET.SubElement(vs_unit, 'iGin').text = '0'
    ET.SubElement(vs_unit, 'sLvl').text = '-898'
    ET.SubElement(vs_unit, 'sEnable').text = '0'
    ET.SubElement(vs_unit, 'mute').text = '0'
    ET.SubElement(vs_unit, 'solo').text = '0'
    ET.SubElement(vs_unit, 'pan').text = '64'
    ET.SubElement(vs_unit, 'vol').text = '0'
    
    # Master track
    master_track = ET.SubElement(root, 'masterTrack')
    ET.SubElement(master_track, 'seqName').text = project_name
    ET.SubElement(master_track, 'comment').text = comment
    ET.SubElement(master_track, 'resolution').text = '480'
    ET.SubElement(master_track, 'preMeasure').text = '1'
    
    # Time signature
    time_sig = ET.SubElement(master_track, 'timeSig')
    ET.SubElement(time_sig, 'posMes').text = '0'
    ET.SubElement(time_sig, 'nume').text = str(time_signature[0])
    ET.SubElement(time_sig, 'denomi').text = str(time_signature[1])
    
    # Tempo
    tempo_elem = ET.SubElement(master_track, 'tempo')
    ET.SubElement(tempo_elem, 'posTick').text = '0'
    ET.SubElement(tempo_elem, 'bpm').text = str(int(tempo * 100))  # BPM * 100
    
    # VS Track (vocal track)
    vs_track = ET.SubElement(root, 'vsTrack')
    ET.SubElement(vs_track, 'tNo').text = '0'
    ET.SubElement(vs_track, 'name').text = 'Track 1'
    ET.SubElement(vs_track, 'comment').text = ''
    
    # Musical part
    musical_part = ET.SubElement(vs_track, 'musicalPart')
    ET.SubElement(musical_part, 'posTick').text = '0'
    ET.SubElement(musical_part, 'playTime').text = str(_get_total_ticks(notes))
    ET.SubElement(musical_part, 'partName').text = 'Part 1'
    ET.SubElement(musical_part, 'comment').text = ''
    
    # Singer
    singer_elem = ET.SubElement(musical_part, 'singer')
    ET.SubElement(singer_elem, 'posTick').text = '0'
    ET.SubElement(singer_elem, 'bs').text = '0'
    ET.SubElement(singer_elem, 'pc').text = '0'
    
    # Add notes
    for note in notes:
        _add_note_vsq3(musical_part, note)
    
    # Pretty print
    return _prettify_xml(root)


def _generate_vsq4(
    notes: List[Dict],
    tempo: float,
    time_signature: Tuple[int, int],
    singer_name: str,
    project_name: str,
    comment: str = 'Generated by MIDI to VSQX Converter'
) -> str:
    """Generate VSQ4 (Vocaloid 4) format matching the exact working structure"""
    
    singer = DEFAULT_SINGERS.get(singer_name, DEFAULT_SINGERS['Default'])
    
    root = ET.Element('vsq4')
    root.set('xmlns', 'http://www.yamaha.co.jp/vocaloid/schema/vsq4/')
    root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    root.set('xsi:schemaLocation', 'http://www.yamaha.co.jp/vocaloid/schema/vsq4/ vsq4.xsd')
    
    # Vender and version (plain text, not CDATA - ElementTree doesn't do CDATA easily)
    ET.SubElement(root, 'vender').text = 'Yamaha corporation'
    ET.SubElement(root, 'version').text = '4.0.0.3'
    
    # Voice table
    voice_table = ET.SubElement(root, 'vVoiceTable')
    voice = ET.SubElement(voice_table, 'vVoice')
    ET.SubElement(voice, 'bs').text = '1'  # Changed from 4 to 1
    ET.SubElement(voice, 'pc').text = '0'
    ET.SubElement(voice, 'id').text = singer['id']
    ET.SubElement(voice, 'name').text = singer['name']
    
    v_prm = ET.SubElement(voice, 'vPrm')
    ET.SubElement(v_prm, 'bre').text = '0'
    ET.SubElement(v_prm, 'bri').text = '0'
    ET.SubElement(v_prm, 'cle').text = '0'
    ET.SubElement(v_prm, 'gen').text = '0'
    ET.SubElement(v_prm, 'ope').text = '0'
    
    # Mixer - using correct structure matching working file
    mixer = ET.SubElement(root, 'mixer')
    
    # masterUnit
    master_unit = ET.SubElement(mixer, 'masterUnit')
    ET.SubElement(master_unit, 'oDev').text = '0'
    ET.SubElement(master_unit, 'rLvl').text = '0'
    ET.SubElement(master_unit, 'vol').text = '0'
    
    # vsUnit
    vs_unit = ET.SubElement(mixer, 'vsUnit')
    ET.SubElement(vs_unit, 'tNo').text = '0'
    ET.SubElement(vs_unit, 'iGin').text = '0'
    ET.SubElement(vs_unit, 'sLvl').text = '-898'
    ET.SubElement(vs_unit, 'sEnable').text = '0'
    ET.SubElement(vs_unit, 'm').text = '0'
    ET.SubElement(vs_unit, 's').text = '0'
    ET.SubElement(vs_unit, 'pan').text = '64'
    ET.SubElement(vs_unit, 'vol').text = '0'
    
    # monoUnit (not seUnit)
    mono_unit = ET.SubElement(mixer, 'monoUnit')
    ET.SubElement(mono_unit, 'iGin').text = '0'
    ET.SubElement(mono_unit, 'sLvl').text = '-898'
    ET.SubElement(mono_unit, 'sEnable').text = '0'
    ET.SubElement(mono_unit, 'm').text = '0'
    ET.SubElement(mono_unit, 's').text = '0'
    ET.SubElement(mono_unit, 'pan').text = '64'
    ET.SubElement(mono_unit, 'vol').text = '0'
    
    # stUnit (not karaokeUnit)
    st_unit = ET.SubElement(mixer, 'stUnit')
    ET.SubElement(st_unit, 'iGin').text = '0'
    ET.SubElement(st_unit, 'm').text = '0'
    ET.SubElement(st_unit, 's').text = '0'
    ET.SubElement(st_unit, 'vol').text = '-129'
    
    # Master track
    master_track = ET.SubElement(root, 'masterTrack')
    ET.SubElement(master_track, 'seqName').text = project_name
    ET.SubElement(master_track, 'comment').text = comment
    ET.SubElement(master_track, 'resolution').text = '480'
    ET.SubElement(master_track, 'preMeasure').text = '4'  # Changed from 1 to 4
    
    # Time signature
    time_sig = ET.SubElement(master_track, 'timeSig')
    ET.SubElement(time_sig, 'm').text = '0'
    ET.SubElement(time_sig, 'nu').text = str(time_signature[0])
    ET.SubElement(time_sig, 'de').text = str(time_signature[1])
    
    # Tempo
    tempo_elem = ET.SubElement(master_track, 'tempo')
    ET.SubElement(tempo_elem, 't').text = '0'
    ET.SubElement(tempo_elem, 'v').text = str(int(tempo * 100))
    
    # VS Track
    vs_track = ET.SubElement(root, 'vsTrack')
    ET.SubElement(vs_track, 'tNo').text = '0'
    ET.SubElement(vs_track, 'name').text = project_name
    ET.SubElement(vs_track, 'comment').text = project_name
    
    # vsPart (Musical part)
    vs_part = ET.SubElement(vs_track, 'vsPart')
    
    # Calculate start position - after pre-measure
    # Ticks per measure = (numerator / (denominator / 4)) * 480
    # For 4/4: 4 beats * 480 = 1920 ticks per measure, 4 measures = 7680
    # For 12/8: (12 / (8/4)) * 480 = 6 * 480 = 2880 ticks per measure
    ticks_per_measure = int(time_signature[0] * 480 * 4 / time_signature[1])
    pre_measure_ticks = 4 * ticks_per_measure  # 4 pre-measures
    ET.SubElement(vs_part, 't').text = str(pre_measure_ticks)
    ET.SubElement(vs_part, 'playTime').text = str(_get_total_ticks(notes))
    ET.SubElement(vs_part, 'name').text = project_name
    ET.SubElement(vs_part, 'comment').text = project_name
    
    # sPlug (singing style plugin) - required
    s_plug = ET.SubElement(vs_part, 'sPlug')
    ET.SubElement(s_plug, 'id').text = 'ACA9C502-A04B-42b5-B2EB-5CEA36D16FCE'
    ET.SubElement(s_plug, 'name').text = 'VOCALOID2 Compatible Style'
    ET.SubElement(s_plug, 'version').text = '3.0.0.1'
    
    # pStyle (part style) - required
    p_style = ET.SubElement(vs_part, 'pStyle')
    _add_style_elements(p_style)
    
    # Singer
    singer_elem = ET.SubElement(vs_part, 'singer')
    ET.SubElement(singer_elem, 't').text = '0'
    ET.SubElement(singer_elem, 'bs').text = '1'  # Changed from 4 to 1
    ET.SubElement(singer_elem, 'pc').text = '0'
    
    # Add notes
    for note in notes:
        _add_note_vsq4(vs_part, note)
    
    # plane element at end of vsPart - required
    ET.SubElement(vs_part, 'plane').text = '0'
    
    # monoTrack (empty but required)
    ET.SubElement(root, 'monoTrack')
    
    # stTrack (empty but required)
    ET.SubElement(root, 'stTrack')
    
    # aux element - required
    aux = ET.SubElement(root, 'aux')
    ET.SubElement(aux, 'id').text = 'AUX_VST_HOST_CHUNK_INFO'
    ET.SubElement(aux, 'content').text = 'VlNDSwAAAAADAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
    
    return _prettify_xml(root)


def _add_style_elements(parent: ET.Element) -> None:
    """Add common style elements for pStyle and nStyle"""
    styles = [
        ('accent', '50'),
        ('bendDep', '8'),
        ('bendLen', '0'),
        ('decay', '50'),
        ('fallPort', '0'),
        ('opening', '127'),
        ('risePort', '0'),
    ]
    for id_val, val in styles:
        v_elem = ET.SubElement(parent, 'v')
        v_elem.set('id', id_val)
        v_elem.text = val


def _add_note_vsq3(parent: ET.Element, note: Dict) -> None:
    """Add a note element for VSQ3 format"""
    note_elem = ET.SubElement(parent, 'note')
    
    # Position in ticks
    pos_tick = note.get('start_ticks', int(note['start'] * 480 / 500))
    ET.SubElement(note_elem, 'posTick').text = str(int(pos_tick))
    
    # Duration in ticks
    dur_tick = note.get('duration_ticks', int(note['duration'] * 480 / 500))
    ET.SubElement(note_elem, 'durTick').text = str(max(1, int(dur_tick)))
    
    # Note number (MIDI pitch)
    ET.SubElement(note_elem, 'noteNum').text = str(note['pitch'])
    
    # Velocity
    ET.SubElement(note_elem, 'velocity').text = str(note.get('velocity', 64))
    
    # Lyric
    lyric = note.get('lyric', 'a')
    ET.SubElement(note_elem, 'lyric').text = lyric
    
    # Phoneme
    phoneme = note.get('phoneme', lyric)
    ET.SubElement(note_elem, 'phnms').text = phoneme
    
    # Note style
    n_style = ET.SubElement(note_elem, 'nStyle')
    ET.SubElement(n_style, 'v').text = '0'  # Standard style
    
    # Expression elements
    ET.SubElement(note_elem, 'bendDepth').text = '0'
    ET.SubElement(note_elem, 'bendLength').text = '0'
    ET.SubElement(note_elem, 'risePort').text = '0'
    ET.SubElement(note_elem, 'fallPort').text = '0'
    ET.SubElement(note_elem, 'decay').text = '50'
    ET.SubElement(note_elem, 'accent').text = '50'
    ET.SubElement(note_elem, 'opening').text = '127'
    
    # Vibrato
    vibrato = ET.SubElement(note_elem, 'vibrato')
    ET.SubElement(vibrato, 'vibLen').text = '0'
    ET.SubElement(vibrato, 'vibType').text = '0'


def _add_note_vsq4(parent: ET.Element, note: Dict) -> None:
    """Add a note element for VSQ4 format"""
    note_elem = ET.SubElement(parent, 'note')
    
    # Position in ticks
    pos_tick = note.get('start_ticks', int(note['start'] * 480 / 500))
    ET.SubElement(note_elem, 't').text = str(int(pos_tick))
    
    # Duration in ticks
    dur_tick = note.get('duration_ticks', int(note['duration'] * 480 / 500))
    ET.SubElement(note_elem, 'dur').text = str(max(1, int(dur_tick)))
    
    # Note number
    ET.SubElement(note_elem, 'n').text = str(note['pitch'])
    
    # Velocity
    ET.SubElement(note_elem, 'v').text = str(note.get('velocity', 64))
    
    # Lyric
    lyric = note.get('lyric', 'a')
    ET.SubElement(note_elem, 'y').text = lyric
    
    # Phoneme/Pronunciation
    phoneme = note.get('phoneme', lyric)
    ET.SubElement(note_elem, 'p').text = phoneme
    
    # Note properties
    n_style = ET.SubElement(note_elem, 'nStyle')
    
    # Singing style elements
    v_elem = ET.SubElement(n_style, 'v')
    v_elem.set('id', 'accent')
    v_elem.text = '50'
    
    v_elem = ET.SubElement(n_style, 'v')
    v_elem.set('id', 'bendDep')
    v_elem.text = '8'
    
    v_elem = ET.SubElement(n_style, 'v')
    v_elem.set('id', 'bendLen')
    v_elem.text = '0'
    
    v_elem = ET.SubElement(n_style, 'v')
    v_elem.set('id', 'decay')
    v_elem.text = '50'
    
    v_elem = ET.SubElement(n_style, 'v')
    v_elem.set('id', 'fallPort')
    v_elem.text = '0'
    
    v_elem = ET.SubElement(n_style, 'v')
    v_elem.set('id', 'opening')
    v_elem.text = '127'
    
    v_elem = ET.SubElement(n_style, 'v')
    v_elem.set('id', 'risePort')
    v_elem.text = '0'
    
    v_elem = ET.SubElement(n_style, 'v')
    v_elem.set('id', 'vibLen')
    v_elem.text = '0'
    
    v_elem = ET.SubElement(n_style, 'v')
    v_elem.set('id', 'vibType')
    v_elem.text = '0'


def _get_total_ticks(notes: List[Dict]) -> int:
    """Calculate total duration in ticks"""
    if not notes:
        return 1920  # Default 1 measure
    
    last_note = max(notes, key=lambda n: n['start'] + n['duration'])
    end_tick = last_note.get('start_ticks', 0) + last_note.get('duration_ticks', 480)
    
    # Add some padding
    return int(end_tick + 480)


def _prettify_xml(elem: ET.Element) -> str:
    """Return a pretty-printed XML string with proper declaration"""
    rough_string = ET.tostring(elem, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    # Get XML with declaration, remove the first line (declaration) and add proper one
    xml_str = reparsed.toprettyxml(indent='  ')
    # Replace default declaration with UTF-8 declaration
    if xml_str.startswith('<?xml'):
        newline_pos = xml_str.find('?>')
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>' + xml_str[newline_pos + 2:]
    return xml_str


def _generate_vsq3_multi(
    tracks: List[Dict],
    tempo: float,
    time_signature: Tuple[int, int],
    singer_name: str
) -> str:
    """Generate VSQ3 format with multiple tracks"""
    singer = DEFAULT_SINGERS.get(singer_name, DEFAULT_SINGERS['Default'])
    
    root = ET.Element('vsq3')
    root.set('xmlns', 'http://www.yamaha.co.jp/vocaloid/schema/vsq3/')
    root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    root.set('xsi:schemaLocation', 'http://www.yamaha.co.jp/vocaloid/schema/vsq3/ vsq3.xsd')
    
    ET.SubElement(root, 'vender').text = 'Yamaha corporation'
    ET.SubElement(root, 'version').text = '3.0.0.1'
    
    # Voice table
    voice_table = ET.SubElement(root, 'vVoiceTable')
    voice = ET.SubElement(voice_table, 'vVoice')
    ET.SubElement(voice, 'bs').text = '0'
    ET.SubElement(voice, 'pc').text = '0'
    ET.SubElement(voice, 'id').text = singer['id']
    ET.SubElement(voice, 'name').text = singer['name']
    ET.SubElement(voice, 'vPrm')
    
    # Mixer with multiple track units
    mixer = ET.SubElement(root, 'mixer')
    master_unit = ET.SubElement(mixer, 'masterUnit')
    ET.SubElement(master_unit, 'outDev').text = '0'
    ET.SubElement(master_unit, 'vol').text = '0'
    
    for i, track in enumerate(tracks):
        vs_unit = ET.SubElement(mixer, 'vsUnit')
        ET.SubElement(vs_unit, 'tNo').text = str(i)
        ET.SubElement(vs_unit, 'iGin').text = '0'
        ET.SubElement(vs_unit, 'sLvl').text = '-898'
        ET.SubElement(vs_unit, 'sEnable').text = '0'
        ET.SubElement(vs_unit, 'mute').text = '0'
        ET.SubElement(vs_unit, 'solo').text = '0'
        ET.SubElement(vs_unit, 'pan').text = '64'
        ET.SubElement(vs_unit, 'vol').text = '0'
    
    # Master track
    master_track = ET.SubElement(root, 'masterTrack')
    ET.SubElement(master_track, 'seqName').text = 'Multi-Track Project'
    ET.SubElement(master_track, 'comment').text = 'Generated by MIDI to VSQX Converter (Multi-Track)'
    ET.SubElement(master_track, 'resolution').text = '480'
    ET.SubElement(master_track, 'preMeasure').text = '1'
    
    time_sig = ET.SubElement(master_track, 'timeSig')
    ET.SubElement(time_sig, 'posMes').text = '0'
    ET.SubElement(time_sig, 'nume').text = str(time_signature[0])
    ET.SubElement(time_sig, 'denomi').text = str(time_signature[1])
    
    tempo_elem = ET.SubElement(master_track, 'tempo')
    ET.SubElement(tempo_elem, 'posTick').text = '0'
    ET.SubElement(tempo_elem, 'bpm').text = str(int(tempo * 100))
    
    # Add each track
    for i, track in enumerate(tracks):
        vs_track = ET.SubElement(root, 'vsTrack')
        ET.SubElement(vs_track, 'tNo').text = str(i)
        ET.SubElement(vs_track, 'name').text = f"{track['name']} ({track['similarity']*100:.0f}%)"
        ET.SubElement(vs_track, 'comment').text = f"Similarity: {track['similarity']*100:.1f}%"
        
        notes = track.get('notes', [])
        musical_part = ET.SubElement(vs_track, 'musicalPart')
        ET.SubElement(musical_part, 'posTick').text = '0'
        ET.SubElement(musical_part, 'playTime').text = str(_get_total_ticks(notes))
        ET.SubElement(musical_part, 'partName').text = f'Part {i+1}'
        ET.SubElement(musical_part, 'comment').text = ''
        
        singer_elem = ET.SubElement(musical_part, 'singer')
        ET.SubElement(singer_elem, 'posTick').text = '0'
        ET.SubElement(singer_elem, 'bs').text = '0'
        ET.SubElement(singer_elem, 'pc').text = '0'
        
        for note in notes:
            _add_note_vsq3(musical_part, note)
    
    return _prettify_xml(root)


def _generate_vsq4_multi(
    tracks: List[Dict],
    tempo: float,
    time_signature: Tuple[int, int],
    singer_name: str
) -> str:
    """Generate VSQ4 format with multiple tracks"""
    singer = DEFAULT_SINGERS.get(singer_name, DEFAULT_SINGERS['Default'])
    
    root = ET.Element('vsq4')
    root.set('xmlns', 'http://www.yamaha.co.jp/vocaloid/schema/vsq4/')
    root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    root.set('xsi:schemaLocation', 'http://www.yamaha.co.jp/vocaloid/schema/vsq4/ vsq4.xsd')
    
    ET.SubElement(root, 'vender').text = 'Yamaha Corporation'
    ET.SubElement(root, 'version').text = '4.0.0.0'
    
    # Voice table
    voice_table = ET.SubElement(root, 'vVoiceTable')
    voice = ET.SubElement(voice_table, 'vVoice')
    ET.SubElement(voice, 'bs').text = '4'
    ET.SubElement(voice, 'pc').text = '0'
    ET.SubElement(voice, 'id').text = singer['id']
    ET.SubElement(voice, 'name').text = singer['name']
    
    v_prm = ET.SubElement(voice, 'vPrm')
    ET.SubElement(v_prm, 'bre').text = '0'
    ET.SubElement(v_prm, 'bri').text = '0'
    ET.SubElement(v_prm, 'cle').text = '0'
    ET.SubElement(v_prm, 'gen').text = '0'
    ET.SubElement(v_prm, 'ope').text = '0'
    
    # Mixer with multiple track units
    mixer = ET.SubElement(root, 'mixer')
    master_unit = ET.SubElement(mixer, 'masterUnit')
    ET.SubElement(master_unit, 'oDev').text = '0'
    ET.SubElement(master_unit, 'rLvl').text = '0'
    ET.SubElement(master_unit, 'vol').text = '0'
    
    for i, track in enumerate(tracks):
        vs_unit = ET.SubElement(mixer, 'vsUnit')
        ET.SubElement(vs_unit, 'tNo').text = str(i)
        ET.SubElement(vs_unit, 'iGin').text = '0'
        ET.SubElement(vs_unit, 'sLvl').text = '-898'
        ET.SubElement(vs_unit, 'sEnable').text = '0'
        ET.SubElement(vs_unit, 'm').text = '0'
        ET.SubElement(vs_unit, 's').text = '0'
        ET.SubElement(vs_unit, 'pan').text = '64'
        ET.SubElement(vs_unit, 'vol').text = '0'
    
    se_unit = ET.SubElement(mixer, 'seUnit')
    ET.SubElement(se_unit, 'iGin').text = '0'
    ET.SubElement(se_unit, 'm').text = '0'
    ET.SubElement(se_unit, 's').text = '0'
    ET.SubElement(se_unit, 'pan').text = '64'
    ET.SubElement(se_unit, 'vol').text = '0'
    
    karaoke_unit = ET.SubElement(mixer, 'karaokeUnit')
    ET.SubElement(karaoke_unit, 'iGin').text = '0'
    ET.SubElement(karaoke_unit, 'm').text = '0'
    ET.SubElement(karaoke_unit, 's').text = '0'
    ET.SubElement(karaoke_unit, 'vol').text = '0'
    
    # Master track
    master_track = ET.SubElement(root, 'masterTrack')
    ET.SubElement(master_track, 'seqName').text = 'Multi-Track Project'
    ET.SubElement(master_track, 'comment').text = 'Generated by MIDI to VSQX Converter (Multi-Track)'
    ET.SubElement(master_track, 'resolution').text = '480'
    ET.SubElement(master_track, 'preMeasure').text = '1'
    
    time_sig = ET.SubElement(master_track, 'timeSig')
    ET.SubElement(time_sig, 'm').text = '0'
    ET.SubElement(time_sig, 'nu').text = str(time_signature[0])
    ET.SubElement(time_sig, 'de').text = str(time_signature[1])
    
    tempo_elem = ET.SubElement(master_track, 'tempo')
    ET.SubElement(tempo_elem, 't').text = '0'
    ET.SubElement(tempo_elem, 'v').text = str(int(tempo * 100))
    
    # Add each track
    for i, track in enumerate(tracks):
        vs_track = ET.SubElement(root, 'vsTrack')
        ET.SubElement(vs_track, 'tNo').text = str(i)
        ET.SubElement(vs_track, 'name').text = f"{track['name']} ({track['similarity']*100:.0f}%)"
        ET.SubElement(vs_track, 'comment').text = f"Similarity: {track['similarity']*100:.1f}%"
        
        notes = track.get('notes', [])
        musical_part = ET.SubElement(vs_track, 'vsPart')
        ET.SubElement(musical_part, 't').text = '0'
        ET.SubElement(musical_part, 'playTime').text = str(_get_total_ticks(notes))
        ET.SubElement(musical_part, 'name').text = f'Part {i+1}'
        ET.SubElement(musical_part, 'comment').text = ''
        
        singer_elem = ET.SubElement(musical_part, 'singer')
        ET.SubElement(singer_elem, 't').text = '0'
        ET.SubElement(singer_elem, 'bs').text = '4'
        ET.SubElement(singer_elem, 'pc').text = '0'
        
        for note in notes:
            _add_note_vsq4(musical_part, note)
    
    # Required empty tracks
    ET.SubElement(root, 'monoTrack')
    ET.SubElement(root, 'stTrack')
    ET.SubElement(root, 'seTrack')
    
    return _prettify_xml(root)


# ============================================
# VPR (Vocaloid 5/6) Format Generators
# VPR is a ZIP file containing sequence.json
# ============================================

def _generate_vpr(
    notes: List[Dict],
    tempo: float,
    time_signature: Tuple[int, int],
    singer_name: str,
    project_name: str,
    comment: str = 'Generated by MIDI to VSQX Converter'
) -> bytes:
    """Generate VPR (Vocaloid 5/6) format - returns bytes (ZIP content)"""
    singer = get_singer(singer_name)
    
    # Build the sequence JSON structure
    sequence = _build_vpr_sequence(
        notes=notes,
        tempo=tempo,
        time_signature=time_signature,
        singer=singer,
        project_name=project_name,
        comment=comment
    )
    
    # Create ZIP file in memory
    return _create_vpr_zip(sequence)


def _generate_vpr_multi(
    tracks: List[Dict],
    tempo: float,
    time_signature: Tuple[int, int],
    singer_name: str
) -> bytes:
    """Generate VPR format with multiple tracks"""
    singer = get_singer(singer_name)
    
    # Build multi-track sequence
    sequence = _build_vpr_sequence_multi(
        tracks=tracks,
        tempo=tempo,
        time_signature=time_signature,
        singer=singer
    )
    
    return _create_vpr_zip(sequence)


def _build_vpr_sequence(
    notes: List[Dict],
    tempo: float,
    time_signature: Tuple[int, int],
    singer: Dict,
    project_name: str = 'Converted Project',
    comment: str = ''
) -> Dict:
    """Build the VPR sequence.json structure"""
    
    # VPR uses ticks at 480 PPQ
    resolution = 480
    
    # Build notes array
    vpr_notes = []
    for i, note in enumerate(notes):
        pos_tick = note.get('start_ticks', int(note['start'] * resolution / 500))
        dur_tick = note.get('duration_ticks', int(note['duration'] * resolution / 500))
        
        vpr_notes.append({
            "pos": int(pos_tick),
            "duration": max(1, int(dur_tick)),
            "number": note['pitch'],
            "velocity": note.get('velocity', 64),
            "lyric": note.get('lyric', 'a'),
            "phoneme": note.get('phoneme', note.get('lyric', 'a')),
            "exp": {
                "accent": 50,
                "decay": 50,
                "bendDepth": 8,
                "bendLength": 0
            },
            "singingSkill": {
                "duration": int(dur_tick),
                "weight": {
                    "pre": 64,
                    "post": 64
                }
            },
            "vibrato": {
                "type": 0,
                "duration": 0
            }
        })
    
    # Calculate total duration
    total_ticks = _get_total_ticks(notes) if notes else 1920
    
    sequence = {
        "version": {
            "major": 5,
            "minor": 0,
            "revision": 0
        },
        "vender": "Yamaha Corporation",
        "title": project_name,
        "comment": comment,
        "masterTrack": {
            "samplingRate": 44100,
            "tempo": {
                "global": {
                    "isEnabled": True,
                    "value": int(tempo * 100)
                },
                "events": [
                    {
                        "pos": 0,
                        "value": int(tempo * 100)
                    }
                ]
            },
            "timeSig": {
                "events": [
                    {
                        "pos": 0,
                        "numer": time_signature[0],
                        "denom": time_signature[1]
                    }
                ]
            },
            "volume": {
                "events": [
                    {"pos": 0, "value": 0}
                ]
            }
        },
        "voices": [
            {
                "compID": singer['id'],
                "name": singer['name']
            }
        ],
        "tracks": [
            {
                "type": 0,  # Vocal track
                "name": "Track 1",
                "color": 0,
                "busNo": 0,
                "isFolded": False,
                "height": 64.0,
                "volume": {
                    "events": [{"pos": 0, "value": 0}]
                },
                "panpot": {
                    "events": [{"pos": 0, "value": 64}]
                },
                "isMuted": False,
                "isSoloMode": False,
                "parts": [
                    {
                        "pos": 0,
                        "duration": total_ticks,
                        "styleName": "No Effect",
                        "voice": {
                            "compID": singer['id'],
                            "langID": 0
                        },
                        "midiEffects": [],
                        "notes": vpr_notes,
                        "controllers": []
                    }
                ]
            }
        ]
    }
    
    return sequence


def _build_vpr_sequence_multi(
    tracks: List[Dict],
    tempo: float,
    time_signature: Tuple[int, int],
    singer: Dict
) -> Dict:
    """Build VPR sequence with multiple tracks"""
    resolution = 480
    
    vpr_tracks = []
    for i, track in enumerate(tracks):
        notes = track.get('notes', [])
        
        vpr_notes = []
        for note in notes:
            pos_tick = note.get('start_ticks', int(note['start'] * resolution / 500))
            dur_tick = note.get('duration_ticks', int(note['duration'] * resolution / 500))
            
            vpr_notes.append({
                "pos": int(pos_tick),
                "duration": max(1, int(dur_tick)),
                "number": note['pitch'],
                "velocity": note.get('velocity', 64),
                "lyric": note.get('lyric', 'a'),
                "phoneme": note.get('phoneme', note.get('lyric', 'a')),
                "exp": {"accent": 50, "decay": 50, "bendDepth": 8, "bendLength": 0},
                "singingSkill": {"duration": int(dur_tick), "weight": {"pre": 64, "post": 64}},
                "vibrato": {"type": 0, "duration": 0}
            })
        
        total_ticks = _get_total_ticks(notes) if notes else 1920
        
        vpr_tracks.append({
            "type": 0,
            "name": f"{track['name']} ({track['similarity']*100:.0f}%)",
            "color": i % 8,
            "busNo": 0,
            "isFolded": False,
            "height": 64.0,
            "volume": {"events": [{"pos": 0, "value": 0}]},
            "panpot": {"events": [{"pos": 0, "value": 64}]},
            "isMuted": i > 0,  # Mute all but first track
            "isSoloMode": False,
            "parts": [
                {
                    "pos": 0,
                    "duration": total_ticks,
                    "styleName": "No Effect",
                    "voice": {"compID": singer['id'], "langID": 0},
                    "midiEffects": [],
                    "notes": vpr_notes,
                    "controllers": []
                }
            ]
        })
    
    sequence = {
        "version": {"major": 5, "minor": 0, "revision": 0},
        "vender": "Yamaha Corporation",
        "title": "Multi-Track Project",
        "comment": "Generated by MIDI to VSQX Converter (Multi-Track)",
        "masterTrack": {
            "samplingRate": 44100,
            "tempo": {
                "global": {"isEnabled": True, "value": int(tempo * 100)},
                "events": [{"pos": 0, "value": int(tempo * 100)}]
            },
            "timeSig": {
                "events": [{"pos": 0, "numer": time_signature[0], "denom": time_signature[1]}]
            },
            "volume": {"events": [{"pos": 0, "value": 0}]}
        },
        "voices": [{"compID": singer['id'], "name": singer['name']}],
        "tracks": vpr_tracks
    }
    
    return sequence


def _create_vpr_zip(sequence: Dict) -> bytes:
    """Create VPR ZIP file containing sequence.json"""
    buffer = io.BytesIO()
    
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # VPR files contain sequence.json at root
        sequence_json = json.dumps(sequence, indent=2, ensure_ascii=False)
        zf.writestr('sequence.json', sequence_json.encode('utf-8'))
    
    buffer.seek(0)
    return buffer.getvalue()

