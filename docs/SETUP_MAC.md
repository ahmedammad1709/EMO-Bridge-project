# EMO Bridge - macOS Setup Guide

## Prerequisites

1. **Python 3.8+**: EMO Bridge requires Python 3.8 or newer.
   ```bash
   # Check your Python version
   python3 --version
   ```
   If needed, download the latest version from [python.org](https://www.python.org/downloads/macos/) or install via Homebrew:
   ```bash
   brew install python
   ```

2. **Gemini API Key**: You'll need a Google Gemini API key to use the application.
   - Visit [Google AI Studio](https://ai.google.dev/) to get your API key
   - You'll enter this key in the application settings

## Installation

### Option 1: Run from Source

1. **Clone or download the repository**

2. **Create a virtual environment** (recommended)
   ```bash
   cd bridge
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python app/main.py
   ```

### Option 2: Build a macOS App with PyInstaller

1. **Install PyInstaller**
   ```bash
   pip install pyinstaller
   ```

2. **Build the application**
   ```bash
   cd bridge
   pyinstaller --windowed --name "EMO Bridge" --icon=resources/icon.icns --add-data "config:config" app/main.py
   ```

3. **Find the built application**
   - The app will be in the `dist` folder as `EMO Bridge.app`
   - You can move this to your Applications folder

## Configuration

1. **First Launch Setup**
   - On first launch, enter your Gemini API key in the settings panel
   - Click "Save Settings" to store your configuration

2. **Manual Configuration**
   - You can manually edit the config file at `config/config.yaml`
   - If running the built app, the config will be in the app bundle

## Troubleshooting

### Microphone Access

On macOS, you'll need to grant microphone permissions:

1. Go to System Preferences > Security & Privacy > Privacy > Microphone
2. Ensure EMO Bridge is checked in the list of allowed applications

### Audio Output Issues

If you're using EMO as your audio output device:

1. Connect EMO to your Mac via Bluetooth
2. In System Preferences > Sound > Output, select EMO as your output device
3. The application will automatically use the system's default audio device

### PyInstaller Issues

If you encounter issues with the PyInstaller build:

1. Try cleaning the build directories:
   ```bash
   rm -rf build dist
   ```

2. Ensure you have the latest PyInstaller:
   ```bash
   pip install --upgrade pyinstaller
   ```

3. For more detailed debugging, run PyInstaller with the `--debug` flag

## Dependencies

The application requires the following Python packages:

- `google-generativeai`: Google Gemini API client
- `speech_recognition`: For microphone input
- `pyttsx3`: For text-to-speech output
- `ttkbootstrap`: For the modern UI
- `pyyaml`: For configuration management
- `paho-mqtt`: For MQTT integration (optional)

## Support

If you encounter any issues, please check the following:

1. Ensure your Gemini API key is valid and correctly entered
2. Check that your microphone and speakers are working properly
3. Verify that all dependencies are correctly installed

---

© 2023 EMO Bridge - Connect your EMO to the power of Gemini AI