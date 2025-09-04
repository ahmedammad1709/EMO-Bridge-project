# EMO Bridge

A modern desktop application that connects EMO to Google's Gemini AI, enabling voice conversations with different personas.

## Features

- **Voice Interaction**: Speak to EMO and get AI-powered responses
- **Multiple Personas**: Choose between playful "EMO" or wise "EMUSINIO" personas
- **Modern UI**: Clean, user-friendly interface with ttkbootstrap styling
- **Smart Home Integration**: Optional MQTT support for home automation
- **Easy Configuration**: Simple settings panel for API key and preferences

## Requirements

- Python 3.8 or higher
- Google Gemini API key
- macOS (primary target platform)

## Quick Start

1. Install dependencies: `pip install -r requirements.txt`
2. Run the application: `python app/main.py`
3. Enter your Gemini API key in the settings panel
4. Click "Start Chat" to begin voice interaction

## Project Structure

```
bridge/
  ├── app/
  │   ├── main.py       # Application entry point
  │   ├── gui.py        # User interface implementation
  │   └── backend.py    # Gemini API, speech, and TTS integration
  ├── config/
  │   └── config.yaml   # Application configuration
  ├── docs/
  │   └── SETUP_MAC.md  # macOS setup instructions
  └── requirements.txt  # Python dependencies
```

## Building for macOS

See [SETUP_MAC.md](docs/SETUP_MAC.md) for detailed instructions on building a standalone macOS application.

## License

MIT License

---

Built with ❤️ for EMO