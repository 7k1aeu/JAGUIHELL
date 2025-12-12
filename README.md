# JAGUIHELL

**JA**panese **G**lyph **U**nicode **I**mage **HELL** Protocol Transceiver

JAGUIHELL is a Windows application for transmitting and receiving images using the HELL (Hellschreiber) protocol with support for Japanese characters.

## Features

- Full Unicode support including Japanese Hiragana, Katakana, and Kanji characters
- Real-time image transmission and reception
- Configurable audio parameters (sample rate, carrier frequency)
- Built-in test pattern generation
- Waterfall display for signal visualization
- Support for both ASCII and Japanese character sets
- Persistent settings storage

## Requirements

- Windows operating system
- Audio input/output device
- .NET Framework (if required by dependencies)

## Installation

1. Download the latest release from the releases page
2. Extract the archive to your desired location
3. Run `JAGUIHELL.exe`

## Configuration

Settings are stored in `JAGUIHELL.ini` and include:

### [General] Section
- `Callsign`: Your amateur radio callsign (used in transmissions)

### [Audio] Section
- `SampleRate`: Audio sample rate (default: 48000 Hz)
- `CarrierFrequency`: Transmission carrier frequency (default: 1000 Hz)

### [Display] Section
- `WaterfallHeight`: Height of the waterfall display in pixels

## Usage

### Transmitting

1. Enter your text in the input field (supports Japanese input methods)
2. Click "Send" to begin transmission
3. The application will generate and transmit the HELL signal through your audio output

### Receiving

1. Ensure your audio input is connected to the receiver
2. The application will automatically decode incoming HELL signals
3. Received text and images will be displayed in the reception window

### Test Mode

Use the "Test" button to generate a test pattern for calibration and verification.

## Character Support

### ASCII Characters
- Standard ASCII printable characters (space through ~)
- Fixed-width font rendering

### Japanese Characters
- Hiragana (ぁ-ん)
- Katakana (ァ-ヶ)
- Common Kanji characters
- Full-width Japanese punctuation

## Technical Details

### HELL Protocol
- Character transmission using on-off keying
- Pixel-by-pixel vertical scanning
- Visual representation of characters
- No error correction (visual redundancy instead)

### Audio Processing
- Configurable sample rate (default 48 kHz)
- Carrier frequency modulation
- Real-time FFT for signal detection
- Automatic level adjustment

## Sample Files

The `sample` directory contains example text files for testing:

- `sample/sample.txt` - English text sample
- `sample/jpsample.txt` - Japanese text sample (UTF-8 encoded)

These files demonstrate the character support and can be loaded for transmission testing.

## Version History

- **Version 1.0.1** — 2025/12/03 — Initial public release
  - Basic HELL protocol implementation
  - Japanese character support
  - Configuration file support
  - Waterfall display

- **Version 1.0.2** — 2025/12/04 — Feature additions and improvements
  - Added callsign configuration in `JAGUIHELL.ini` under `[General]` section.
  - Introduced waveform generation cache to improve performance.
  - Added fallback processing for sample rate during audio stream initialization.

- **Version 1.0.3** — 2025/12/04 — ASCII Glyphs optimization
  - Reduced ASCII character spacing by changing glyph size from 14x14 to 14x11.
  - Optimized glyph processing with unified 14-column format for ASCII and Japanese characters.

- **Version 1.0.4** — 2025/12/12 — Documentation update
  - Updated installation instructions and clarified sample file description.

---

## License

This project is released under the MIT License. See LICENSE file for details.

## Author

7K1AEU

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## Acknowledgments

- Based on the Hellschreiber transmission system developed by Rudolf Hell
- Japanese character rendering inspired by various amateur radio digital mode implementations

## Support

For questions, issues, or suggestions, please open an issue on the GitHub repository.
