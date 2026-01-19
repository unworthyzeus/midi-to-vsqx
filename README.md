# MIDI to Vocal Synth Converter

A premium, web-based tool for converting MIDI files and lyrics into vocal synthesis project formats.

## Supported Output Formats

- **VSQX** - Vocaloid 4 (XML format)
- **UST** - UTAU (Classic format)
- **USTX** - OpenUTAU (Modern YAML-based format)
- **SVP** - Synthesizer V (JSON format)

![App Screenshot](static/favicon.png)

## Features

- **Hybrid AI Matching**: Intelligently aligns lyrics to MIDI notes using a combination of manual hyphenation and AI syllabification (Pyphen).
- **Polyphonic Splitting**: Automatically detects and splits MIDI chords into multiple monophonic tracks (e.g., separating melody from harmony).
- **Phrase-Aware Matching**: Detects gaps in MIDI data to ensure word boundaries are respected.
- **Advanced Logic**: Choose between "Melody First" or chronological splitting for complex MIDI files.
- **Smart Note Healing**: Automatically resolves minor MIDI overlaps (up to 50ms) to preserve track monophony.
- **Live Preview**: Instantly see how your lyrics will sit on the notes before exporting.
- **Multi-Track Export**: Generate project files with multiple singers for different MIDI voices.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/midi-to-vsqx.git
   cd midi-to-vsqx
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python app.py
   ```

4. Open your browser to `http://127.0.0.1:5000`.

## Voicebank Support

### Vocaloid 4 (VSQX)
Hatsune Miku V4X, Megurine Luka V4X, Kagamine Rin/Len V4X, KAITO V4, GUMI V4, v flower, Fukase, and more.

### UTAU (UST/USTX)
Kasane Teto, Defoko, Momone Momo, Yokune Ruko, Namine Ritsu, Sukone Tei, and any custom voicebanks.

### Synthesizer V (SVP)
Solaria, Eleanor Forte, Kevin, Asterian, Mai, Koharu Rikka, Tsurumaki Maki, and more.

## ⚠️ Legal Disclaimer

**This is NOT an official product of Yamaha, UTAU, or Dreamtonics.**

This tool is an independent, community-driven project designed solely for interoperability between standard MIDI data and various vocal synthesis project file formats. 

- "VOCALOID" and "VSQX" are trademarks of **Yamaha Corporation**.
- "UTAU" was created by Ameya/Ayame.
- "Synthesizer V" and "SVP" are products of **Dreamtonics**.
- This software has no affiliation with, authorization from, or endorsement by any of these companies.
- Users are responsible for ensuring they own legal copies of any voicebanks referenced in the generated project files.

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
