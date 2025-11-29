import json
import os

class SettingsManager:
    DEFAULT_SETTINGS = {
        "goal": "97",
        "resolution": "FHD",
        "penalty_allowed": False,
        "overlay_x": 100,
        "overlay_y": 100
    }
    
    def __init__(self, filepath="settings.json"):
        self.filepath = filepath
        self.settings = self.load_settings()

    def load_settings(self):
        if not os.path.exists(self.filepath):
            return self.DEFAULT_SETTINGS.copy()
        
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)
                # Merge with defaults to ensure all keys exist
                settings = self.DEFAULT_SETTINGS.copy()
                settings.update(data)
                return settings
        except Exception as e:
            print(f"Error loading settings: {e}")
            return self.DEFAULT_SETTINGS.copy()

    def save_settings(self):
        try:
            with open(self.filepath, 'w') as f:
                json.dump(self.settings, f, indent=4)
            print("Settings saved.")
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key):
        return self.settings.get(key, self.DEFAULT_SETTINGS.get(key))

    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()
