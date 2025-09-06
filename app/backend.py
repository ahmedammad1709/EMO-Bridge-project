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
import speech_recognition as sr
import pyttsx3
import paho.mqtt.client as mqtt


class EMOBridgeBackend:
    """
    Backend class for the EMO Bridge application
    """
    def __init__(self, config, status_callback=None, persona="EMO"):
        """
        Initialize the backend with the provided configuration
        
        Args:
            config (dict): Application configuration
            status_callback (callable, optional): Callback function for status updates
            persona (str, optional): Initial persona (EMO or EMUSINIO)
        """
        self.config = config
        self.status_callback = status_callback
        self.persona = persona
        self.running = False
        self.thread = None
        self.recognizer = sr.Recognizer()
        self.mqtt_client = None
        self.speaking = False
        self.tts_thread = None
        self.background_listener = None
        self.interrupt_event = threading.Event()
        
        # Configure Gemini API
        self._configure_gemini()
        
        # Configure MQTT if enabled
        if config.get('enable_mqtt', False):
            self._configure_mqtt()
    
    def _configure_gemini(self):
        """
        Configure the Gemini API with the API key from config
        """
        api_key = self.config.get('gemini_api_key', '')
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.model = None
            if self.status_callback:
                self.status_callback("Error")
    
    def _configure_mqtt(self):
        """
        Configure MQTT client if enabled
        """
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.connect(
                self.config.get('mqtt_broker', 'localhost'),
                self.config.get('mqtt_port', 1883),
                60
            )
            self.mqtt_client.loop_start()
        except Exception as e:
            print(f"MQTT Error: {e}")
            self.mqtt_client = None
    
    def update_config(self, config):
        """
        Update the backend configuration
        
        Args:
            config (dict): New configuration
        """
        self.config = config
        
        # Reconfigure Gemini API
        self._configure_gemini()
        
        # Reconfigure MQTT
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client = None
            
        if config.get('enable_mqtt', False):
            self._configure_mqtt()
    
    def set_persona(self, persona):
        """
        Set the current persona
        
        Args:
            persona (str): Persona name (EMO or EMUSINIO)
        """
        self.persona = persona
    
    def get_persona_instruction(self):
        """
        Get the instruction prompt for the current persona
        
        Returns:
            str: Instruction prompt
        """
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
        """
        Start the chat session in a separate thread
        """
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._voice_loop, daemon=True)
        self.thread.start()
    
    def stop_chat(self):
        """
        Stop the chat session
        """
        self.running = False
        
        # Stop background listener if active
        self._stop_background_listener()
        
        # Set interrupt flag to stop any ongoing TTS
        self.interrupt_event.set()
        
        # Wait for main thread to finish
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        
        # Wait for TTS thread to finish
        if self.tts_thread and self.tts_thread.is_alive():
            self.tts_thread.join(timeout=1.0)
        
        # Reset speaking flag
        self.speaking = False
        
        # Say goodbye
        try:
            # Initialize a fresh engine for goodbye message
            engine = pyttsx3.init()
            engine.setProperty('rate', self.config.get('voice_rate', 180))
            engine.setProperty('volume', self.config.get('voice_volume', 1.0))
            
            # Say goodbye with debug logs
            print("Starting TTS playback for goodbye...")
            engine.say("Goodbye!")
            engine.runAndWait()
            engine.stop()
            del engine
            print("Finished TTS playback for goodbye.")
        except Exception as e:
            print(f"Goodbye TTS Error: {e}")
    
    def _speak(self, text):
        """
        Speak text using pyttsx3 in a separate thread with barge-in capability
        """
        # Reset interrupt event
        self.interrupt_event.clear()
        
        # Set speaking flag
        self.speaking = True
        
        # Start TTS in a separate thread
        self.tts_thread = threading.Thread(target=self._tts_thread_func, args=(text,), daemon=True)
        self.tts_thread.start()
        
        # Start background listener for barge-in
        self._start_background_listener()
        
        # Wait for TTS to complete or be interrupted
        self.tts_thread.join()
        
        # Clean up background listener
        self._stop_background_listener()
        
        # Reset speaking flag
        self.speaking = False
    
    def _tts_thread_func(self, text):
        """
        Thread function for TTS playback
        """
        try:
            print("Starting TTS playback...")
            engine = pyttsx3.init()
            engine.setProperty('rate', self.config.get('voice_rate', 180))
            engine.setProperty('volume', self.config.get('voice_volume', 1.0))
            engine.say(text)
            
            # Check for interruption while running TTS
            engine.runAndWait()
            
            # Only if not interrupted
            if not self.interrupt_event.is_set():
                engine.stop()
                del engine
                print("Finished TTS playback.")
            else:
                print("TTS playback interrupted.")
        except Exception as e:
            print(f"TTS Error: {e}")
    
    def _start_background_listener(self):
        """
        Start background listener for barge-in detection
        """
        try:
            # Create a microphone source
            self.mic = sr.Microphone()
            
            # Start background listening
            self.background_listener = self.recognizer.listen_in_background(
                self.mic, self._on_speech_detected, phrase_time_limit=5.0
            )
            print("Background listener started")
        except Exception as e:
            print(f"Background listener error: {e}")
    
    def _stop_background_listener(self):
        """
        Stop the background listener
        """
        if self.background_listener:
            self.background_listener(wait_for_stop=False)
            self.background_listener = None
            print("Background listener stopped")
    
    def _on_speech_detected(self, recognizer, audio):
        """
        Callback for when speech is detected during TTS playback
        """
        if not self.speaking:
            return
            
        try:
            # Try to recognize the speech
            text = recognizer.recognize_google(audio).lower().strip()
            
            # If we got text, interrupt the TTS
            if text:
                print(f"Barge-in detected: {text}")
                
                # Set interrupt flag
                self.interrupt_event.set()
                
                # Stop TTS engine
                engine = pyttsx3.init()
                engine.stop()
                del engine
                
                # Update status to Interrupted
                if self.status_callback:
                    self.status_callback("Interrupted")
                
                # Process the new input in the main thread
                self._process_barge_in(text)
        except sr.UnknownValueError:
            # Ignore if we couldn't understand the audio
            pass
        except Exception as e:
            print(f"Barge-in error: {e}")
    
    def _process_barge_in(self, text):
        """
        Process text from barge-in interruption
        """
        # Wait for TTS thread to finish cleanup
        if self.tts_thread and self.tts_thread.is_alive():
            self.tts_thread.join(timeout=1.0)
        
        # Update status to Listening
        if self.status_callback:
            self.status_callback("Listening")
        
        # Process the text (similar to _voice_loop but without the listening part)
        # Check for quit/exit commands
        if text in ["quit", "exit", "stop", "end"]:
            self.running = False
            if self.status_callback:
                self.status_callback("Idle")
            return
        
        # Process persona switching in the text
        if text.startswith("emo"):
            self.persona = "EMO"
            text = text.replace("emo", "", 1).strip()
            print("Persona switched to EMO")
        
        elif text.startswith("emusinio"):
            self.persona = "EMUSINIO"
            text = text.replace("emusinio", "", 1).strip()
            print("Persona switched to EMUSINIO")
        
        # Skip processing if no text or model
        if not text or not self.model:
            return
        
        # Create prompt for Gemini
        instruction = self.get_persona_instruction()
        prompt = f"""
        You are {self.persona}. {instruction}
        If the user is asking to quit/exit/end/stop, 
        no matter how they phrase it, reply ONLY with the word QUIT.
        Otherwise, reply in your normal persona style.

        User said: "{text}"
        """
        
        # Get response from Gemini
        response = self.model.generate_content(prompt)
        reply = response.text.strip()
        print(f"{self.persona}: {reply}")
        
        # Check for QUIT response
        if reply == "QUIT":
            self.running = False
            if self.status_callback:
                self.status_callback("Idle")
            return
        
        # Update status to Speaking
        if self.status_callback:
            self.status_callback("Speaking")
        
        # Speak the response
        self._speak(reply)
        
        # Publish to MQTT if enabled
        if self.mqtt_client:
            topic = self.config.get('mqtt_topic', 'emo/bridge')
            self.mqtt_client.publish(topic, reply)
    
    def _voice_loop(self):
        """
        Main voice processing loop
        """
        while self.running:
            try:
                # Update status to Listening
                if self.status_callback:
                    self.status_callback("Listening")
                
                # Listen for audio input
                with sr.Microphone() as source:
                    print("Listening...")
                    audio = self.recognizer.listen(source)
                
                # Process audio to text
                text = self.recognizer.recognize_google(audio).lower().strip()
                print(f"User said: {text}")
                
                # Check for quit/exit commands
                if text in ["quit", "exit", "stop", "end"]:
                    self.running = False
                    if self.status_callback:
                        self.status_callback("Idle")
                    break
                
                # Process persona switching in the text
                if text.startswith("emo"):
                    self.persona = "EMO"
                    text = text.replace("emo", "", 1).strip()
                    print("Persona switched to EMO")
                
                elif text.startswith("emusinio"):
                    self.persona = "EMUSINIO"
                    text = text.replace("emusinio", "", 1).strip()
                    print("Persona switched to EMUSINIO")
                
                # Skip processing if no text or model
                if not text or not self.model:
                    continue
                
                # Create prompt for Gemini
                instruction = self.get_persona_instruction()
                prompt = f"""
                You are {self.persona}. {instruction}
                If the user is asking to quit/exit/end/stop, 
                no matter how they phrase it, reply ONLY with the word QUIT.
                Otherwise, reply in your normal persona style.

                User said: "{text}"
                """
                
                # Get response from Gemini
                response = self.model.generate_content(prompt)
                reply = response.text.strip()
                print(f"{self.persona}: {reply}")
                
                # Check for QUIT response
                if reply == "QUIT":
                    self.running = False
                    if self.status_callback:
                        self.status_callback("Idle")
                    break
                
                # Update status to Speaking
                if self.status_callback:
                    self.status_callback("Speaking")
                
                # Speak the response (now with barge-in capability)
                self._speak(reply)
                
                # Publish to MQTT if enabled
                if self.mqtt_client:
                    topic = self.config.get('mqtt_topic', 'emo/bridge')
                    self.mqtt_client.publish(topic, reply)
                
                # Short pause between interactions
                # Note: We don't need to set status back to Listening here
                # as it's handled by the _speak method after TTS completes
                # or by _process_barge_in if interrupted
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
                time.sleep(1)  # Prevent rapid error loops
        
        # Ensure status is updated when loop ends
        if self.status_callback:
            self.status_callback("Idle")
