#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EMO Bridge Application - GUI Module
Implements the graphical user interface for the EMO Bridge application.
"""

import os
import yaml
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from pathlib import Path

from app.backend import EMOBridgeBackend


class EMOBridgeApp:
    """
    Main application class for the EMO Bridge GUI
    """
    def __init__(self, config):
        """
        Initialize the application with the provided configuration
        
        Args:
            config (dict): Application configuration
        """
        self.config = config
        self.backend = None
        self.root = None
        self.status_var = None
        self.persona_var = None
        self.api_key_var = None
        self.mqtt_var = None
        
    def run(self):
        """
        Start the GUI application
        """
        # Create the main window with ttkbootstrap theme
        self.root = ttk.Window(
            title="EMO Bridge",
            themename="cosmo",  # Modern, clean theme
            size=(500, 600),
            resizable=(True, True),
            minsize=(400, 500)
        )
        
        # Center the window on screen
        self.center_window()
        
        # Create the UI components
        self.create_ui()
        
        # Initialize the backend
        self.initialize_backend()
        
        # Start the main event loop
        self.root.mainloop()
    
    def center_window(self):
        """
        Center the window on the screen
        """
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_ui(self):
        """
        Create the user interface components
        """
        # Create main frame with padding
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Enhanced App title and logo
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Logo with gradient effect
        logo_frame = ttk.Frame(title_frame)
        logo_frame.pack(pady=(0, 10))
        
        logo_label = ttk.Label(
            logo_frame, 
            text="EMO", 
            font=("Helvetica", 42, "bold"),
            bootstyle="primary"
        )
        logo_label.pack(side=tk.LEFT)
        
        # App title with modern styling
        app_title = ttk.Label(
            logo_frame, 
            text="Bridge", 
            font=("Helvetica", 24),
            bootstyle="secondary"
        )
        app_title.pack(side=tk.LEFT, padx=(5, 0), pady=(15, 0))
        
        # Tagline
        tagline = ttk.Label(
            title_frame,
            text="Voice Assistant Integration Platform",
            font=("Helvetica", 10),
            bootstyle="secondary"
        )
        tagline.pack()
        
        # Control frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        # Persona selector
        persona_frame = ttk.LabelFrame(control_frame, text="Persona", padding=10)
        persona_frame.pack(fill=tk.X, pady=10)
        
        self.persona_var = tk.StringVar(value="EMO")
        persona_combo = ttk.Combobox(
            persona_frame, 
            textvariable=self.persona_var,
            values=["EMO", "EMUSINIO"],
            state="readonly",
            bootstyle="primary"
        )
        persona_combo.pack(fill=tk.X)
        persona_combo.bind("<<ComboboxSelected>>", self.on_persona_change)
        
        # Description labels for personas
        emo_desc = ttk.Label(
            persona_frame, 
            text="EMO: Playful, casual tone with emojis",
            font=("Helvetica", 9),
            bootstyle="secondary"
        )
        emo_desc.pack(anchor=tk.W, pady=(5, 0))
        
        emusinio_desc = ttk.Label(
            persona_frame, 
            text="EMUSINIO: Wise, mentor-like formal tone",
            font=("Helvetica", 9),
            bootstyle="secondary"
        )
        emusinio_desc.pack(anchor=tk.W)
        
        # Enhanced Button frame with card-like appearance
        button_card = ttk.LabelFrame(main_frame, text="Voice Controls", padding=15)
        button_card.pack(fill=tk.X, pady=15)
        
        button_frame = ttk.Frame(button_card)
        button_frame.pack(fill=tk.X)
        
        # Start button with enhanced styling
        start_btn = ttk.Button(
            button_frame, 
            text="Start Listening", 
            command=self.start_chat,
            bootstyle="success-outline",
            width=15
        )
        start_btn.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        
        # Stop button with enhanced styling
        stop_btn = ttk.Button(
            button_frame, 
            text="Stop Listening", 
            command=self.stop_chat,
            bootstyle="danger-outline",
            width=15
        )
        stop_btn.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # Enhanced Status display
        self.status_var = tk.StringVar(value="Idle")
        status_card = ttk.LabelFrame(main_frame, text="Assistant Status", padding=10)
        status_card.pack(fill=tk.X, pady=10)
        
        status_frame = ttk.Frame(status_card)
        status_frame.pack(fill=tk.X)
        
        # Status indicator (colored circle)
        self.status_indicator = ttk.Label(
            status_frame,
            text="●",
            font=("Helvetica", 16),
            bootstyle="secondary"
        )
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 5))
        
        # Status text
        status_value = ttk.Label(
            status_frame, 
            textvariable=self.status_var,
            font=("Helvetica", 11),
            bootstyle="secondary"
        )
        status_value.pack(side=tk.LEFT)
        
        # Settings panel
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding=10)
        settings_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # API Key is now loaded from config.yaml only
        self.api_key_var = tk.StringVar(value=self.config.get('gemini_api_key', ''))
        
        # Enhanced MQTT integration section
        mqtt_frame = ttk.LabelFrame(settings_frame, text="Smart Home Integration", padding=10)
        mqtt_frame.pack(fill=tk.X, pady=10)
        
        self.mqtt_var = tk.BooleanVar(value=self.config.get('enable_mqtt', False))
        mqtt_cb = ttk.Checkbutton(
            mqtt_frame, 
            text="Enable MQTT Integration", 
            variable=self.mqtt_var,
            bootstyle="success-round-toggle"
        )
        mqtt_cb.pack(anchor=tk.W, pady=(0, 5))
        
        mqtt_info = ttk.Label(
            mqtt_frame,
            text="Connect EMO to your smart home devices via MQTT",
            font=("Helvetica", 9),
            bootstyle="secondary"
        )
        mqtt_info.pack(anchor=tk.W, pady=(0, 5))
        
        # Save settings button
        save_btn = ttk.Button(
            settings_frame, 
            text="Save Settings", 
            command=self.save_settings,
            bootstyle="primary-outline"
        )
        save_btn.pack(pady=10)
        
        # Enhanced Footer with version info and credits
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Credits
        credits_label = ttk.Label(
            footer_frame, 
            text="By Codeveil Studio",
            font=("Helvetica", 8),
            bootstyle="secondary"
        )
        credits_label.pack(side=tk.LEFT)
        
        # Version info
        version_label = ttk.Label(
            footer_frame, 
            text="EMO Bridge v1.0",
            font=("Helvetica", 8),
            bootstyle="secondary"
        )
        version_label.pack(side=tk.RIGHT)
    
    def initialize_backend(self):
        """
        Initialize the backend with the current configuration
        """
        try:
            self.backend = EMOBridgeBackend(
                config=self.config,
                status_callback=self.update_status,
                persona=self.persona_var.get()
            )
        except Exception as e:
            messagebox.showerror("Backend Error", f"Failed to initialize backend: {str(e)}")
            self.update_status("Error")
    
    def start_chat(self):
        """
        Start the chat session
        """
        if not self.backend:
            self.initialize_backend()
            
        if not self.backend:
            return
            
        try:
            self.backend.start_chat()
            self.update_status("Listening")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start chat: {str(e)}")
            self.update_status("Error")
    
    def stop_chat(self):
        """
        Stop the chat session
        """
        if self.backend:
            try:
                self.backend.stop_chat()
                self.update_status("Idle")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to stop chat: {str(e)}")
                self.update_status("Error")
    
    def on_persona_change(self, event=None):
        """
        Handle persona change event
        """
        if self.backend:
            self.backend.set_persona(self.persona_var.get())
    
    def update_status(self, status):
        """
        Update the status display
        
        Args:
            status (str): New status text
        """
        self.status_var.set(status)
        
        # Update status indicator color based on status
        if status == "Idle":
            self.status_indicator.configure(bootstyle="secondary")
        elif status == "Listening":
            self.status_indicator.configure(bootstyle="success")
        elif status == "Speaking":
            self.status_indicator.configure(bootstyle="info")
        elif status == "Interrupted":
            self.status_indicator.configure(bootstyle="warning")
        elif status == "Error":
            self.status_indicator.configure(bootstyle="danger")
    
    # Method removed as API key entry is no longer in the UI
    
    def save_settings(self):
        """
        Save the current settings to the config file
        """
        # Update config with current values
        self.config['enable_mqtt'] = self.mqtt_var.get()
        
        # Save to file
        config_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / 'config' / 'config.yaml'
        
        try:
            with open(config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            
            # Update backend with new settings
            if self.backend:
                self.backend.update_config(self.config)
                
            messagebox.showinfo("Settings Saved", "Settings have been saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")