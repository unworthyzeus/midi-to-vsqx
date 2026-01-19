"""
VSQX/UST/USTX/SVP Generator Module
Generates vocal synthesis project files:
- VSQ4 (Vocaloid 4) - XML format
- UST (UTAU) - Classic UTAU format
- USTX (OpenUTAU) - Modern YAML-based format
- SVP (Synthesizer V) - JSON format
"""

from enum import Enum
from typing import List, Dict, Tuple, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom
import uuid
import time
import json
import io


class VSQXVersion(Enum):
    """Supported vocal synthesis project versions"""
    VSQ4 = 'vsq4'  # Vocaloid 4 (XML)
    UST = 'ust'    # UTAU (Classic format)
    USTX = 'ustx'  # OpenUTAU (YAML-based)
    SVP = 'svp'    # Synthesizer V (JSON)


# Comprehensive singer/voicebank database
# For display purposes - actual voicebanks are software-specific
SINGERS = {
    # === VOCALOID 4 (for VSQX) ===
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
    'Cyber_Diva': {'id': 'V4_CYBERDIVA_001', 'name': 'CYBER DIVA', 'version': 'V4', 'type': 'Standard', 'language': 'English'},

    # === UTAU Voicebanks (for UST/USTX) ===
    'Teto': {'id': 'UTAU_TETO', 'name': 'Kasane Teto', 'version': 'UTAU', 'type': 'CV', 'language': 'Japanese'},
    'Defoko': {'id': 'UTAU_DEFOKO', 'name': 'Defoko (Uta Utane)', 'version': 'UTAU', 'type': 'CV', 'language': 'Japanese'},
    'Momo': {'id': 'UTAU_MOMO', 'name': 'Momone Momo', 'version': 'UTAU', 'type': 'CV', 'language': 'Japanese'},
    'Ruko': {'id': 'UTAU_RUKO', 'name': 'Yokune Ruko', 'version': 'UTAU', 'type': 'VCV', 'language': 'Japanese'},
    'Ritsu': {'id': 'UTAU_RITSU', 'name': 'Namine Ritsu', 'version': 'UTAU', 'type': 'VCV', 'language': 'Japanese'},
    'Tei': {'id': 'UTAU_TEI', 'name': 'Sukone Tei', 'version': 'UTAU', 'type': 'CV', 'language': 'Japanese'},
    
    # === SynthV Voicebanks (for SVP) ===
    'Eleanor': {'id': 'SVP_ELEANOR', 'name': 'Eleanor Forte', 'version': 'SynthV', 'type': 'AI', 'language': 'English'},
    'Solaria': {'id': 'SVP_SOLARIA', 'name': 'Solaria', 'version': 'SynthV', 'type': 'AI', 'language': 'English'},
    'Kevin': {'id': 'SVP_KEVIN', 'name': 'Kevin', 'version': 'SynthV', 'type': 'AI', 'language': 'English'},
    'Asterian': {'id': 'SVP_ASTERIAN', 'name': 'Asterian', 'version': 'SynthV', 'type': 'AI', 'language': 'English'},
    'Mai': {'id': 'SVP_MAI', 'name': 'Mai', 'version': 'SynthV', 'type': 'AI', 'language': 'Japanese'},
    'Saki': {'id': 'SVP_SAKI', 'name': 'Koharu Rikka', 'version': 'SynthV', 'type': 'AI', 'language': 'Japanese'},
    'Tsurumaki': {'id': 'SVP_TSURU', 'name': 'Tsurumaki Maki', 'version': 'SynthV', 'type': 'AI', 'language': 'Japanese'},
    
    # === OpenUTAU (for USTX) ===
    'OpenUtau_Default': {'id': 'OPENUTAU_DEFAULT', 'name': 'OpenUTAU Default', 'version': 'OpenUTAU', 'type': 'CV', 'language': 'Japanese'},
    
    # === Legacy/Generic ===
    'Default': {'id': 'AAAAAAAAAAAAAAAAA', 'name': 'Default Singer', 'version': 'Any', 'type': 'Standard', 'language': 'Any'},
}

# Backwards compatibility alias
DEFAULT_SINGERS = {k: {'id': v['id'], 'name': v['name']} for k, v in SINGERS.items()}

# Simple aliases for common names
SINGER_ALIASES = {
    'Miku': 'Miku_V4X',
    'Luka': 'Luka_V4X',
    'Rin': 'Rin_V4X',
    'Len': 'Len_V4X',
    'KAITO': 'KAITO_V4',
    'GUMI': 'GUMI_V4',
}


def get_singer(name: str) -> Dict:
    """Get singer info by name or alias"""
    if name in SINGER_ALIASES:
        name = SINGER_ALIASES[name]
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
    Generate a vocal synthesis project file from parsed MIDI data and lyrics
    
    Args:
        notes: List of note dictionaries with pitch, start, duration, lyric
        tempo: BPM
        time_signature: Tuple of (numerator, denominator)
        version: VSQ4, UST, USTX, or SVP
        singer_name: Name of the singer/voicebank
        project_name: Name for the project
        similarity_score: Match quality score (0-1)
    
    Returns:
        String containing the project file content
    """
    comment = f'Generated by MIDI to VSQX Converter (Match: {similarity_score*100:.1f}%)'
    
    if version == VSQXVersion.UST:
        return _generate_ust(notes, tempo, time_signature, singer_name, project_name, comment)
    elif version == VSQXVersion.USTX:
        return _generate_ustx(notes, tempo, time_signature, singer_name, project_name, comment)
    elif version == VSQXVersion.SVP:
        return _generate_svp(notes, tempo, time_signature, singer_name, project_name, comment)
    else:
        return _generate_vsq4(notes, tempo, time_signature, singer_name, project_name, comment)


def generate_multi_track_vsqx(
    tracks: List[Dict],
    tempo: float,
    time_signature: Tuple[int, int],
    version: VSQXVersion = VSQXVersion.VSQ4,
    singer_name: str = 'Miku'
) -> str:
    """
    Generate a vocal synthesis project file with multiple tracks
    
    Args:
        tracks: List of track dicts with 'name', 'notes', 'similarity', etc.
        tempo: BPM
        time_signature: Tuple of (numerator, denominator)
        version: VSQ4, UST, USTX, or SVP
        singer_name: Name of the singer/voicebank
    
    Returns:
        String containing the project file content with multiple tracks
    """
    if version == VSQXVersion.UST:
        return _generate_ust_multi(tracks, tempo, time_signature, singer_name)
    elif version == VSQXVersion.USTX:
        return _generate_ustx_multi(tracks, tempo, time_signature, singer_name)
    elif version == VSQXVersion.SVP:
        return _generate_svp_multi(tracks, tempo, time_signature, singer_name)
    else:
        return _generate_vsq4_multi(tracks, tempo, time_signature, singer_name)


# ============================================
# VSQ4 (Vocaloid 4) Format Generators
# ============================================

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
    
    ET.SubElement(root, 'vender').text = 'Yamaha corporation'
    ET.SubElement(root, 'version').text = '4.0.0.3'
    
    # Voice table
    voice_table = ET.SubElement(root, 'vVoiceTable')
    voice = ET.SubElement(voice_table, 'vVoice')
    ET.SubElement(voice, 'bs').text = '1'
    ET.SubElement(voice, 'pc').text = '0'
    ET.SubElement(voice, 'id').text = singer['id']
    ET.SubElement(voice, 'name').text = singer['name']
    
    v_prm = ET.SubElement(voice, 'vPrm')
    ET.SubElement(v_prm, 'bre').text = '0'
    ET.SubElement(v_prm, 'bri').text = '0'
    ET.SubElement(v_prm, 'cle').text = '0'
    ET.SubElement(v_prm, 'gen').text = '0'
    ET.SubElement(v_prm, 'ope').text = '0'
    
    # Mixer
    mixer = ET.SubElement(root, 'mixer')
    
    master_unit = ET.SubElement(mixer, 'masterUnit')
    ET.SubElement(master_unit, 'oDev').text = '0'
    ET.SubElement(master_unit, 'rLvl').text = '0'
    ET.SubElement(master_unit, 'vol').text = '0'
    
    vs_unit = ET.SubElement(mixer, 'vsUnit')
    ET.SubElement(vs_unit, 'tNo').text = '0'
    ET.SubElement(vs_unit, 'iGin').text = '0'
    ET.SubElement(vs_unit, 'sLvl').text = '-898'
    ET.SubElement(vs_unit, 'sEnable').text = '0'
    ET.SubElement(vs_unit, 'm').text = '0'
    ET.SubElement(vs_unit, 's').text = '0'
    ET.SubElement(vs_unit, 'pan').text = '64'
    ET.SubElement(vs_unit, 'vol').text = '0'
    
    mono_unit = ET.SubElement(mixer, 'monoUnit')
    ET.SubElement(mono_unit, 'iGin').text = '0'
    ET.SubElement(mono_unit, 'sLvl').text = '-898'
    ET.SubElement(mono_unit, 'sEnable').text = '0'
    ET.SubElement(mono_unit, 'm').text = '0'
    ET.SubElement(mono_unit, 's').text = '0'
    ET.SubElement(mono_unit, 'pan').text = '64'
    ET.SubElement(mono_unit, 'vol').text = '0'
    
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
    ET.SubElement(master_track, 'preMeasure').text = '4'
    
    time_sig = ET.SubElement(master_track, 'timeSig')
    ET.SubElement(time_sig, 'm').text = '0'
    ET.SubElement(time_sig, 'nu').text = str(time_signature[0])
    ET.SubElement(time_sig, 'de').text = str(time_signature[1])
    
    tempo_elem = ET.SubElement(master_track, 'tempo')
    ET.SubElement(tempo_elem, 't').text = '0'
    ET.SubElement(tempo_elem, 'v').text = str(int(tempo * 100))
    
    # VS Track
    vs_track = ET.SubElement(root, 'vsTrack')
    ET.SubElement(vs_track, 'tNo').text = '0'
    ET.SubElement(vs_track, 'name').text = project_name
    ET.SubElement(vs_track, 'comment').text = project_name
    
    # vsPart
    vs_part = ET.SubElement(vs_track, 'vsPart')
    
    ticks_per_measure = int(time_signature[0] * 480 * 4 / time_signature[1])
    pre_measure_ticks = 4 * ticks_per_measure
    ET.SubElement(vs_part, 't').text = str(pre_measure_ticks)
    ET.SubElement(vs_part, 'playTime').text = str(_get_total_ticks(notes))
    ET.SubElement(vs_part, 'name').text = project_name
    ET.SubElement(vs_part, 'comment').text = project_name
    
    s_plug = ET.SubElement(vs_part, 'sPlug')
    ET.SubElement(s_plug, 'id').text = 'ACA9C502-A04B-42b5-B2EB-5CEA36D16FCE'
    ET.SubElement(s_plug, 'name').text = 'VOCALOID2 Compatible Style'
    ET.SubElement(s_plug, 'version').text = '3.0.0.1'
    
    p_style = ET.SubElement(vs_part, 'pStyle')
    _add_style_elements(p_style)
    
    singer_elem = ET.SubElement(vs_part, 'singer')
    ET.SubElement(singer_elem, 't').text = '0'
    ET.SubElement(singer_elem, 'bs').text = '1'
    ET.SubElement(singer_elem, 'pc').text = '0'
    
    for note in notes:
        _add_note_vsq4(vs_part, note)
    
    ET.SubElement(vs_part, 'plane').text = '0'
    
    ET.SubElement(root, 'monoTrack')
    ET.SubElement(root, 'stTrack')
    
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


def _add_note_vsq4(parent: ET.Element, note: Dict) -> None:
    """Add a note element for VSQ4 format"""
    note_elem = ET.SubElement(parent, 'note')
    
    pos_tick = note.get('start_ticks', int(note['start'] * 480 / 500))
    ET.SubElement(note_elem, 't').text = str(int(pos_tick))
    
    dur_tick = note.get('duration_ticks', int(note['duration'] * 480 / 500))
    ET.SubElement(note_elem, 'dur').text = str(max(1, int(dur_tick)))
    
    ET.SubElement(note_elem, 'n').text = str(note['pitch'])
    ET.SubElement(note_elem, 'v').text = str(note.get('velocity', 64))
    
    lyric = note.get('lyric', 'a')
    ET.SubElement(note_elem, 'y').text = lyric
    
    phoneme = note.get('phoneme', lyric)
    ET.SubElement(note_elem, 'p').text = phoneme
    
    n_style = ET.SubElement(note_elem, 'nStyle')
    
    style_params = [
        ('accent', '50'), ('bendDep', '8'), ('bendLen', '0'),
        ('decay', '50'), ('fallPort', '0'), ('opening', '127'),
        ('risePort', '0'), ('vibLen', '0'), ('vibType', '0')
    ]
    for id_val, val in style_params:
        v_elem = ET.SubElement(n_style, 'v')
        v_elem.set('id', id_val)
        v_elem.text = val


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
    
    ET.SubElement(root, 'monoTrack')
    ET.SubElement(root, 'stTrack')
    ET.SubElement(root, 'seTrack')
    
    return _prettify_xml(root)


def _get_total_ticks(notes: List[Dict]) -> int:
    """Calculate total duration in ticks"""
    if not notes:
        return 1920
    
    last_note = max(notes, key=lambda n: n['start'] + n['duration'])
    end_tick = last_note.get('start_ticks', 0) + last_note.get('duration_ticks', 480)
    
    return int(end_tick + 480)


def _prettify_xml(elem: ET.Element) -> str:
    """Return a pretty-printed XML string with proper declaration"""
    rough_string = ET.tostring(elem, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    xml_str = reparsed.toprettyxml(indent='  ')
    if xml_str.startswith('<?xml'):
        newline_pos = xml_str.find('?>')
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>' + xml_str[newline_pos + 2:]
    return xml_str


# ============================================
# UST (UTAU) Format Generators
# Classic UTAU format - INI-style text file
# ============================================

def _generate_ust(
    notes: List[Dict],
    tempo: float,
    time_signature: Tuple[int, int],
    singer_name: str,
    project_name: str,
    comment: str = 'Generated by MIDI to VSQX Converter'
) -> str:
    """Generate UST (UTAU) format"""
    
    singer = get_singer(singer_name)
    lines = []
    
    # Header section
    lines.append('[#SETTING]')
    lines.append(f'Tempo={tempo:.2f}')
    lines.append('Tracks=1')
    lines.append(f'ProjectName={project_name}')
    lines.append(f'VoiceDir=%VOICE%{singer["name"]}')
    lines.append(f'OutFile={project_name}.wav')
    lines.append('CacheDir=cache')
    lines.append('Mode2=True')
    lines.append(f'Flags=')
    lines.append('')
    
    # Notes
    # UTAU uses 480 ticks per quarter note
    resolution = 480
    
    for i, note in enumerate(notes):
        pos_tick = note.get('start_ticks', int(note['start'] * resolution / 500))
        dur_tick = note.get('duration_ticks', int(note['duration'] * resolution / 500))
        
        # Ensure minimum duration
        dur_tick = max(60, int(dur_tick))
        
        lines.append(f'[#{i:04d}]')
        lines.append(f'Length={dur_tick}')
        lines.append(f'Lyric={note.get("lyric", "a")}')
        lines.append(f'NoteNum={note["pitch"]}')
        lines.append(f'Velocity={note.get("velocity", 100) * 100 // 127}')
        lines.append('Intensity=100')
        lines.append('Modulation=0')
        lines.append('Flags=')
        lines.append('PBType=5')
        lines.append('')
    
    # End marker
    lines.append('[#TRACKEND]')
    lines.append('')
    
    return '\n'.join(lines)


def _generate_ust_multi(
    tracks: List[Dict],
    tempo: float,
    time_signature: Tuple[int, int],
    singer_name: str
) -> str:
    """Generate UST format - for multi-track, we combine into one (UST doesn't support multi-track natively)"""
    # UST format doesn't support multiple tracks, so merge all notes
    all_notes = []
    for track in tracks:
        all_notes.extend(track.get('notes', []))
    
    # Sort by start time
    all_notes.sort(key=lambda n: n.get('start_ticks', n['start']))
    
    return _generate_ust(
        notes=all_notes,
        tempo=tempo,
        time_signature=time_signature,
        singer_name=singer_name,
        project_name='Multi-Track Project',
        comment='Generated by MIDI to VSQX Converter (Multi-Track merged)'
    )


# ============================================
# USTX (OpenUTAU) Format Generators
# Modern YAML-based format
# ============================================

def _generate_ustx(
    notes: List[Dict],
    tempo: float,
    time_signature: Tuple[int, int],
    singer_name: str,
    project_name: str,
    comment: str = 'Generated by MIDI to VSQX Converter'
) -> str:
    """Generate USTX (OpenUTAU) format - YAML-based"""
    
    singer = get_singer(singer_name)
    resolution = 480
    
    # Build YAML manually (to avoid yaml dependency)
    lines = []
    lines.append('name: ' + _yaml_escape(project_name))
    lines.append('comment: ' + _yaml_escape(comment))
    lines.append(f'output_dir: .')
    lines.append(f'cache_dir: UCache')
    lines.append(f'ustx_version: "0.6"')
    lines.append('')
    lines.append(f'bpm: {tempo}')
    lines.append(f'beat_per_bar: {time_signature[0]}')
    lines.append(f'beat_unit: {time_signature[1]}')
    lines.append(f'resolution: {resolution}')
    lines.append('')
    lines.append('expressions:')
    lines.append('  - name: velocity')
    lines.append('    abbr: vel')
    lines.append('    type: Numerical')
    lines.append('    min: 0')
    lines.append('    max: 200')
    lines.append('    default: 100')
    lines.append('    flag: ""')
    lines.append('')
    lines.append('voice_parts:')
    lines.append('  - name: Part 1')
    lines.append('    comment: ""')
    lines.append('    track_no: 0')
    lines.append('    position: 0')
    lines.append(f'    singer: {_yaml_escape(singer["name"])}')
    lines.append('    notes:')
    
    for note in notes:
        pos_tick = note.get('start_ticks', int(note['start'] * resolution / 500))
        dur_tick = note.get('duration_ticks', int(note['duration'] * resolution / 500))
        dur_tick = max(60, int(dur_tick))
        lyric = note.get('lyric', 'a')
        
        lines.append(f'      - position: {int(pos_tick)}')
        lines.append(f'        duration: {dur_tick}')
        lines.append(f'        tone: {note["pitch"]}')
        lines.append(f'        lyric: {_yaml_escape(lyric)}')
        lines.append(f'        phonemes: []')
    
    lines.append('')
    lines.append('wave_parts: []')
    lines.append('')
    lines.append('tracks:')
    lines.append('  - singer: ' + _yaml_escape(singer["name"]))
    lines.append('    phonemizer: ""')
    lines.append('    mute: false')
    lines.append('    solo: false')
    lines.append('    volume: 0')
    lines.append('')
    
    return '\n'.join(lines)


def _yaml_escape(s: str) -> str:
    """Escape a string for YAML"""
    if not s:
        return '""'
    # If string contains special chars, quote it
    if any(c in s for c in [':', '#', '[', ']', '{', '}', ',', '&', '*', '!', '|', '>', "'", '"', '%', '@', '`']):
        return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if s.startswith(' ') or s.endswith(' ') or s.startswith('-'):
        return '"' + s + '"'
    return s


def _generate_ustx_multi(
    tracks: List[Dict],
    tempo: float,
    time_signature: Tuple[int, int],
    singer_name: str
) -> str:
    """Generate USTX format with multiple tracks"""
    
    singer = get_singer(singer_name)
    resolution = 480
    
    lines = []
    lines.append('name: Multi-Track Project')
    lines.append('comment: Generated by MIDI to VSQX Converter (Multi-Track)')
    lines.append('output_dir: .')
    lines.append('cache_dir: UCache')
    lines.append('ustx_version: "0.6"')
    lines.append('')
    lines.append(f'bpm: {tempo}')
    lines.append(f'beat_per_bar: {time_signature[0]}')
    lines.append(f'beat_unit: {time_signature[1]}')
    lines.append(f'resolution: {resolution}')
    lines.append('')
    lines.append('expressions:')
    lines.append('  - name: velocity')
    lines.append('    abbr: vel')
    lines.append('    type: Numerical')
    lines.append('    min: 0')
    lines.append('    max: 200')
    lines.append('    default: 100')
    lines.append('    flag: ""')
    lines.append('')
    lines.append('voice_parts:')
    
    for i, track in enumerate(tracks):
        notes = track.get('notes', [])
        track_name = track.get('name', f'Track {i+1}')
        similarity = track.get('similarity', 0)
        
        lines.append(f'  - name: {_yaml_escape(f"{track_name} ({similarity*100:.0f}%)")}')
        lines.append('    comment: ""')
        lines.append(f'    track_no: {i}')
        lines.append('    position: 0')
        lines.append(f'    singer: {_yaml_escape(singer["name"])}')
        lines.append('    notes:')
        
        for note in notes:
            pos_tick = note.get('start_ticks', int(note['start'] * resolution / 500))
            dur_tick = note.get('duration_ticks', int(note['duration'] * resolution / 500))
            dur_tick = max(60, int(dur_tick))
            lyric = note.get('lyric', 'a')
            
            lines.append(f'      - position: {int(pos_tick)}')
            lines.append(f'        duration: {dur_tick}')
            lines.append(f'        tone: {note["pitch"]}')
            lines.append(f'        lyric: {_yaml_escape(lyric)}')
            lines.append(f'        phonemes: []')
    
    lines.append('')
    lines.append('wave_parts: []')
    lines.append('')
    lines.append('tracks:')
    
    for i, track in enumerate(tracks):
        lines.append(f'  - singer: {_yaml_escape(singer["name"])}')
        lines.append('    phonemizer: ""')
        lines.append(f'    mute: {str(i > 0).lower()}')
        lines.append('    solo: false')
        lines.append('    volume: 0')
    
    lines.append('')
    
    return '\n'.join(lines)


# ============================================
# SVP (Synthesizer V) Format Generators
# JSON-based format
# ============================================

def _generate_svp(
    notes: List[Dict],
    tempo: float,
    time_signature: Tuple[int, int],
    singer_name: str,
    project_name: str,
    comment: str = 'Generated by MIDI to VSQX Converter'
) -> str:
    """Generate SVP (Synthesizer V) format - JSON"""
    
    singer = get_singer(singer_name)
    resolution = 1470000  # SynthV uses 1470000 ticks per quarter (blicks)
    
    # Convert notes to SVP format
    svp_notes = []
    for note in notes:
        # Convert from 480 PPQ (MIDI) to SynthV blicks
        pos_tick = note.get('start_ticks', int(note['start'] * 480 / 500))
        dur_tick = note.get('duration_ticks', int(note['duration'] * 480 / 500))
        
        # Convert to blicks (1470000 per quarter = 5880000 per whole note at 480 PPQ)
        pos_blick = int(pos_tick * resolution / 480)
        dur_blick = int(dur_tick * resolution / 480)
        dur_blick = max(resolution // 16, dur_blick)  # Minimum 1/16 note
        
        svp_notes.append({
            "onset": pos_blick,
            "duration": dur_blick,
            "lyrics": note.get('lyric', 'a'),
            "phonemes": "",
            "pitch": note['pitch'],
            "detune": 0,
            "attributes": {}
        })
    
    # Calculate end position
    end_blick = 0
    if svp_notes:
        last_note = max(svp_notes, key=lambda n: n['onset'] + n['duration'])
        end_blick = last_note['onset'] + last_note['duration'] + resolution
    else:
        end_blick = resolution * 4
    
    project = {
        "version": 113,
        "time": {
            "meter": [
                {
                    "index": 0,
                    "numerator": time_signature[0],
                    "denominator": time_signature[1]
                }
            ],
            "tempo": [
                {
                    "position": 0,
                    "bpm": tempo
                }
            ]
        },
        "library": [],
        "tracks": [
            {
                "name": project_name,
                "dispColor": "ff7db235",
                "dispOrder": 0,
                "renderEnabled": True,
                "mixer": {
                    "gainDecibel": 0.0,
                    "pan": 0.0,
                    "mute": False,
                    "solo": False,
                    "display": True
                },
                "mainGroup": {
                    "name": "main",
                    "uuid": str(uuid.uuid4()),
                    "notes": svp_notes,
                    "parameters": {
                        "pitchDelta": {"mode": "cubic", "points": []},
                        "vibratoEnv": {"mode": "cubic", "points": []},
                        "loudness": {"mode": "cubic", "points": []},
                        "tension": {"mode": "cubic", "points": []},
                        "breathiness": {"mode": "cubic", "points": []},
                        "voicing": {"mode": "cubic", "points": []},
                        "gender": {"mode": "cubic", "points": []}
                    }
                },
                "mainRef": {
                    "groupID": "main",
                    "blickOffset": 0,
                    "pitchOffset": 0,
                    "isInstrumental": False,
                    "database": {
                        "name": singer['name'],
                        "language": singer.get('language', 'Japanese'),
                        "phoneset": "arpabet" if singer.get('language') == 'English' else "xsampa"
                    },
                    "dictionary": "",
                    "voice": {}
                },
                "groups": []
            }
        ],
        "renderConfig": {
            "destination": f"./{project_name}.wav",
            "filename": project_name,
            "numChannels": 1,
            "aspirationFormat": "noAspiration",
            "bitDepth": 16,
            "sampleRate": 44100,
            "exportMixDown": True
        }
    }
    
    return json.dumps(project, indent=2, ensure_ascii=False)


def _generate_svp_multi(
    tracks: List[Dict],
    tempo: float,
    time_signature: Tuple[int, int],
    singer_name: str
) -> str:
    """Generate SVP format with multiple tracks"""
    
    singer = get_singer(singer_name)
    resolution = 1470000
    
    svp_tracks = []
    colors = ["ff7db235", "ff35b27d", "ff357db2", "ffb2357d", "ffb27d35", "ff7d35b2"]
    
    for i, track in enumerate(tracks):
        notes = track.get('notes', [])
        track_name = track.get('name', f'Track {i+1}')
        similarity = track.get('similarity', 0)
        
        svp_notes = []
        for note in notes:
            pos_tick = note.get('start_ticks', int(note['start'] * 480 / 500))
            dur_tick = note.get('duration_ticks', int(note['duration'] * 480 / 500))
            
            pos_blick = int(pos_tick * resolution / 480)
            dur_blick = int(dur_tick * resolution / 480)
            dur_blick = max(resolution // 16, dur_blick)
            
            svp_notes.append({
                "onset": pos_blick,
                "duration": dur_blick,
                "lyrics": note.get('lyric', 'a'),
                "phonemes": "",
                "pitch": note['pitch'],
                "detune": 0,
                "attributes": {}
            })
        
        track_uuid = str(uuid.uuid4())
        svp_tracks.append({
            "name": f"{track_name} ({similarity*100:.0f}%)",
            "dispColor": colors[i % len(colors)],
            "dispOrder": i,
            "renderEnabled": True,
            "mixer": {
                "gainDecibel": 0.0,
                "pan": 0.0,
                "mute": i > 0,  # Mute all but first
                "solo": False,
                "display": True
            },
            "mainGroup": {
                "name": "main",
                "uuid": track_uuid,
                "notes": svp_notes,
                "parameters": {
                    "pitchDelta": {"mode": "cubic", "points": []},
                    "vibratoEnv": {"mode": "cubic", "points": []},
                    "loudness": {"mode": "cubic", "points": []},
                    "tension": {"mode": "cubic", "points": []},
                    "breathiness": {"mode": "cubic", "points": []},
                    "voicing": {"mode": "cubic", "points": []},
                    "gender": {"mode": "cubic", "points": []}
                }
            },
            "mainRef": {
                "groupID": "main",
                "blickOffset": 0,
                "pitchOffset": 0,
                "isInstrumental": False,
                "database": {
                    "name": singer['name'],
                    "language": singer.get('language', 'Japanese'),
                    "phoneset": "arpabet" if singer.get('language') == 'English' else "xsampa"
                },
                "dictionary": "",
                "voice": {}
            },
            "groups": []
        })
    
    project = {
        "version": 113,
        "time": {
            "meter": [
                {
                    "index": 0,
                    "numerator": time_signature[0],
                    "denominator": time_signature[1]
                }
            ],
            "tempo": [
                {
                    "position": 0,
                    "bpm": tempo
                }
            ]
        },
        "library": [],
        "tracks": svp_tracks,
        "renderConfig": {
            "destination": "./MultiTrack.wav",
            "filename": "MultiTrack",
            "numChannels": 1,
            "aspirationFormat": "noAspiration",
            "bitDepth": 16,
            "sampleRate": 44100,
            "exportMixDown": True
        }
    }
    
    return json.dumps(project, indent=2, ensure_ascii=False)
