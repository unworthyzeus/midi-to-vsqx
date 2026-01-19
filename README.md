# MIDI to Voice Synth Converter

A free, web-based tool for converting MIDI files and lyrics into singing voice synthesis project formats.

**Now with proper VPR (Vocaloid 5/6) support!** 🎉

## Supported Output Formats

| Format | Software | Description |
|--------|----------|-------------|
| **VSQX** | Vocaloid 4 | XML-based format |
| **VPR** | Vocaloid 5/6 | JSON in ZIP format |
| **UST** | UTAU | Classic INI-style format |
| **USTX** | OpenUTAU | Modern YAML format |
| **SVP** | Synthesizer V | JSON format |

![App Screenshot](static/favicon.png)

## Features

- **Lyrics Integration**: Our unique feature - input lyrics and have them automatically matched to MIDI notes
- **Multi-Format Export**: Export to any major vocal synthesis software
- **Hybrid AI Matching**: Intelligently aligns lyrics to MIDI notes using syllabification
- **Polyphonic Splitting**: Automatically splits MIDI chords into monophonic tracks
- **Phrase-Aware Matching**: Respects word boundaries based on gaps in MIDI data
- **Smart Note Healing**: Resolves minor MIDI overlaps to preserve track monophony
- **Live Preview**: See how your lyrics will match notes before exporting
- **Multi-Track Export**: Generate project files with multiple singers

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/unworthyzeus/midi-to-vsqx.git
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

### Vocaloid (VSQX/VPR)
Hatsune Miku V4X, Megurine Luka V4X, Kagamine Rin/Len V4X, KAITO V4, GUMI V4, v flower, Fukase, and more.

### UTAU (UST/USTX)
Kasane Teto, Defoko, Momone Momo, Yokune Ruko, Namine Ritsu, Sukone Tei, and any custom voicebanks.

### Synthesizer V (SVP)
Solaria, Eleanor Forte, Kevin, Asterian, Mai, Koharu Rikka, Tsurumaki Maki, and more.

## Attribution

Format specifications are based on [UtaFormatix3](https://github.com/sdercolin/utaformatix3) by sdercolin and contributors, licensed under Apache 2.0.

## ⚠️ Legal Disclaimer

**This is NOT an official product of Yamaha, UTAU, or Dreamtonics.**

This tool is an independent, community-driven project designed for interoperability between MIDI data and vocal synthesis formats. 

- "VOCALOID", "VSQX", and "VPR" are trademarks of **Yamaha Corporation**
- "UTAU" was created by Ameya/Ayame
- "Synthesizer V" and "SVP" are products of **Dreamtonics**
- This software has no affiliation with any of these companies
- Users must own legal copies of any voicebanks used

## License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.
