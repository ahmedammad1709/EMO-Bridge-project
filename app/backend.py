#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EMO Bridge Application - Backend Module
Implements the backend functionality for the EMO Bridge application,
including Gemini API integration, speech recognition, and text-to-speech.
"""

import threading
import time
import google.generativeai as genai
import google.api_core.exceptions
import speech_recognition as sr
import pyttsx3
import paho.mqtt.client as mqtt
import requests
import platform
import subprocess


def speak(text, rate=180, volume=1.0):
    """
    Cross-platform TTS function.
    - On macOS: uses the 'say' command.
    - On Linux: uses 'espeak'.
    - On Windows: uses pyttsx3.
    
    Automatically strips emojis from text before sending to TTS.
    """
    try:
        # Strip emojis from text using regex
        import re
        # Pattern to match emoji characters
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F700-\U0001F77F"  # alchemical symbols
            "\U0001F780-\U0001F7FF"  # Geometric Shapes
            "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            "\U0001FA00-\U0001FA6F"  # Chess Symbols
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "\U00002702-\U000027B0"  # Dingbats
            "\U000024C2-\U0001F251" 
            "]", flags=re.UNICODE)
        
        # Remove emojis from text
        clean_text = emoji_pattern.sub(r'', text)
        
        system = platform.system()
        if system == "Darwin":  # macOS
            subprocess.run(["say", clean_text])
        elif system == "Linux":  # Linux
            subprocess.run(["espeak", clean_text])
        else:  # Windows
            engine = pyttsx3.init()
            engine.setProperty("rate", rate)
            engine.setProperty("volume", volume)
            engine.say(clean_text)
            engine.runAndWait()
            engine.stop()
            del engine
    except Exception as e:
        print(f"TTS Error in speak(): {e}")


class EMOBridgeBackend:
    """
    Backend class for the EMO Bridge application
    """
    def __init__(self, config, status_callback=None, persona="EMO"):
        self.config = config
        self.status_callback = status_callback
        self.persona = persona
        # Hardcoded to Portuguese - no longer using config language setting
        self.running = False
        self.thread = None
        self.recognizer = sr.Recognizer()
        self.mqtt_client = None
        self.speaking = False
        self.tts_thread = None
        self.background_listener = None
        self.interrupt_event = threading.Event()
        self.connection_error = False  # Track network connection status

        # Configure Gemini API
        self._configure_gemini()

        # Configure MQTT if enabled
        if config.get('enable_mqtt', False):
            self._configure_mqtt()

    def _configure_gemini(self):
        api_key = self.config.get('gemini_api_key', '')
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.model = None
            if self.status_callback:
                self.status_callback("Error")

    def _configure_mqtt(self):
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.connect(
                self.config.get('mqtt_broker', 'localhost'),
                self.config.get('mqtt_port', 1883),
                60
            )
            self.mqtt_client.loop_start()
            print("MQTT connected successfully")
        except Exception as e:
            print(f"MQTT Error: {e}")
            print("MQTT connection failed - continuing without MQTT support")
            self.mqtt_client = None

    def update_config(self, config):
        self.config = config
        # Language is now hardcoded to Portuguese - no longer using config language setting
        self._configure_gemini()

        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client = None

        if config.get('enable_mqtt', False):
            self._configure_mqtt()

    def set_persona(self, persona):
        self.persona = persona

    def get_persona_instruction(self):
        if self.persona == "EMO":
            return (
                "Speak in a playful, casual tone. "
                "Keep replies short, friendly, sometimes with emojis or fun expressions."
            )
        elif self.persona == "EMUSINIO":
            return (
                "Speak in a wise, formal, and calm tone. "
                "Use full sentences, no emojis, and sound like a mentor."
            )
        else:
            return "Respond in a helpful, concise manner."

    def start_chat(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._voice_loop, daemon=True)
        self.thread.start()

    def stop_chat(self):
        self.running = False
        self._stop_background_listener()
        self.interrupt_event.set()

        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None

        if self.tts_thread and self.tts_thread.is_alive():
            self.tts_thread.join(timeout=1.0)

        self.speaking = False

        # Goodbye message
        try:
            print("Starting TTS playback for goodbye...")
            speak("Goodbye!", self.config.get('voice_rate', 180), self.config.get('voice_volume', 1.0))
            print("Finished TTS playback for goodbye.")
        except Exception as e:
            print(f"Goodbye TTS Error: {e}")

    def _speak(self, text):
        """
        Speak text asynchronously with interruption support.
        """
        self.interrupt_event.clear()
        self.speaking = True
        self.tts_thread = threading.Thread(
            target=self._tts_thread_func,
            args=(text,),
            daemon=True
        )
        self.tts_thread.start()
        self._start_background_listener()
        self.tts_thread.join()
        self._stop_background_listener()
        self.speaking = False
        
    def _start_background_listener(self):
        """
        Start a background listener for interruptions while speaking
        """
        if self.background_listener is None:
            self.background_listener = threading.Thread(
                target=self._background_listen_func,
                daemon=True
            )
            self.background_listener.start()
            
    def _stop_background_listener(self):
        """
        Stop the background listener
        """
        self.background_listener = None
        
    def _background_listen_func(self):
        """
        Background function to listen for interruptions while speaking
        """
        try:
            with sr.Microphone() as source:
                while self.speaking and self.background_listener is not None:
                    try:
                        audio = self.recognizer.listen(source, timeout=0.5, phrase_time_limit=1.0)
                        text = self.recognizer.recognize_google(audio).lower().strip()
                        
                        # Check for interrupt commands
                        if text in ["stop", "quiet", "shut up", "be quiet", "enough"]:
                            print("Speech interrupted by user command")
                            self.interrupt_event.set()
                            break
                    except sr.WaitTimeoutError:
                        # Timeout is expected, just continue
                        pass
                    except Exception as e:
                        # Ignore other errors in background listener
                        pass
        except Exception as e:
            print(f"Error in background listener: {e}")
            pass

    def _tts_thread_func(self, text):
        try:
            print("Starting TTS playback...")
            
            # Select voice based on persona
            system = platform.system()
            if system == "Darwin":  # macOS
                # Use specific voices for each persona
                if self.persona == "EMO":
                    voice = "Catarina"
                elif self.persona == "EMUSINIO":
                    voice = "Joana"
                else:
                    voice = "Catarina"  # Default to Catarina
                
                # Strip emojis from text using regex
                import re
                emoji_pattern = re.compile(
                    "["
                    "\U0001F600-\U0001F64F"  # emoticons
                    "\U0001F300-\U0001F5FF"  # symbols & pictographs
                    "\U0001F680-\U0001F6FF"  # transport & map symbols
                    "\U0001F700-\U0001F77F"  # alchemical symbols
                    "\U0001F780-\U0001F7FF"  # Geometric Shapes
                    "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
                    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
                    "\U0001FA00-\U0001FA6F"  # Chess Symbols
                    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
                    "\U00002702-\U000027B0"  # Dingbats
                    "\U000024C2-\U0001F251" 
                    "]", flags=re.UNICODE)
                
                # Remove emojis from text
                clean_text = emoji_pattern.sub(r'', text)
                
                # Use subprocess with voice selection
                # Start the process but don't wait for it to complete
                process = subprocess.Popen(["say", "-v", voice, clean_text])
                
                # Wait for the process to complete or for an interrupt
                while process.poll() is None:
                    if self.interrupt_event.is_set():
                        # Kill the process if interrupted
                        process.terminate()
                        break
                    time.sleep(0.1)
            else:  # Windows or Linux
                # Fall back to the existing speak function for non-macOS platforms
                speak(text, self.config.get('voice_rate', 180), self.config.get('voice_volume', 1.0))
                
            if not self.interrupt_event.is_set():
                print("Finished TTS playback.")
            else:
                print("TTS playback interrupted.")
        except Exception as e:
            print(f"TTS Error: {e}")

    def _voice_loop(self):
        """
        Main voice processing loop
        """
        # Track consecutive network errors for backoff strategy
        network_error_count = 0
        
        while self.running:
            try:
                if self.status_callback:
                    self.status_callback("Listening")

                with sr.Microphone() as source:
                    print("Listening...")
                    audio = self.recognizer.listen(source)
                
                # Use the language mode from config
                language_mode = self.config.get('language_mode', 'en-US')
                text = self.recognizer.recognize_google(audio, language=language_mode).lower().strip()
                print(f"User said: {text}")

                # Handle quit commands
                if text in ["quit", "exit", "stop", "end"]:
                    self.running = False
                    if self.status_callback:
                        self.status_callback("Idle")
                    break

                # Persona switching
                if text.startswith("emo"):
                    self.persona = "EMO"
                    text = text.replace("emo", "", 1).strip()
                    print("Persona switched to EMO")

                elif text.startswith("emusinio"):
                    self.persona = "EMUSINIO"
                    text = text.replace("emusinio", "", 1).strip()
                    print("Persona switched to EMUSINIO")

                if not text or not self.model:
                    continue

                instruction = self.get_persona_instruction()
                language_mode = "pt-PT"  # Hardcoded to Portuguese
                
                # Add emoji instruction for EMO persona
                emoji_instruction = "Include emojis in your responses." if self.persona == "EMO" else ""
                
                # Hardcoded to Portuguese - no language selection
                language_instruction = "Always reply in Portuguese (Portugal), natural conversational style. Ignore the language the user speaks in and ALWAYS respond in Portuguese (Portugal)."
                
                prompt = f""" 
                You are {self.persona}. {instruction} 
                
                IMPORTANT: {language_instruction}
                {emoji_instruction}
                
                If the user asks to quit/exit/end/stop (in any language), reply ONLY with the word QUIT. 
                
                User said: "{text}" 
                """

                try:
                    response = self.model.generate_content(prompt)
                    reply = response.text.strip()
                    print(f"{self.persona}: {reply}")
                    self.connection_error = False
                    network_error_count = 0
                except Exception as e:
                    print(f"Network error when calling Gemini API: {e}")
                    self.connection_error = True
                    network_error_count += 1
                    if self.status_callback:
                        self.status_callback("Error: Network Connection lost")
                    continue

                if reply == "QUIT":
                    self.running = False
                    if self.status_callback:
                        self.status_callback("Idle")
                    break

                if self.status_callback:
                    self.status_callback("Speaking")

                self._speak(reply)

                if self.mqtt_client:
                    topic = self.config.get('mqtt_topic', 'emo/bridge')
                    self.mqtt_client.publish(topic, reply)

                time.sleep(0.5)

            except sr.UnknownValueError:
                print("Could not understand audio")
                continue
            except sr.RequestError as e:
                print(f"Could not request results; {e}")
                if self.status_callback:
                    self.status_callback("Error")
            except Exception as e:
                print(f"Error in voice loop: {e}")
                if self.status_callback:
                    self.status_callback("Error")
                time.sleep(1)

        if self.status_callback:
            self.status_callback("Idle")
