import json
import os

SETTINGS_FILE = os.getenv("SETTINGS_FILE", "/data/settings.json")

def load_settings():
    default_rules = [
        "__pycache__", "*.pyc", ".git", "node_modules", "target", 
        ".vscode", ".idea", "dist", "build", "*.log", ".DS_Store"
    ]
    defaults = {
        "recommended_patterns": json.dumps(default_rules)
    }
    
    if not os.path.exists(SETTINGS_FILE):
        return defaults
        
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # --- Auto-Merge Missing Defaults ---
            # 1. Ensure recommended_patterns key exists
            if "recommended_patterns" not in data:
                data["recommended_patterns"] = defaults["recommended_patterns"]
            else:
                # 2. Merge missing individual patterns into existing list
                try:
                    current_list = json.loads(data["recommended_patterns"])
                    if isinstance(current_list, list):
                        updated = False
                        for rule in default_rules:
                            if rule not in current_list:
                                current_list.append(rule)
                                updated = True
                        if updated:
                            data["recommended_patterns"] = json.dumps(current_list)
                            # Save back immediately to persist merged defaults
                            save_settings(data)
                except:
                    pass # Fallback if JSON is malformed
            
            # Ensure other top-level defaults exist
            for k, v in defaults.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        print(f"Error loading settings from {SETTINGS_FILE}: {e}")
        return defaults

def save_settings(settings_data):
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, indent=2, ensure_ascii=False)
        print(f"Settings saved to {SETTINGS_FILE}")
    except Exception as e:
        print(f"Error saving settings to {SETTINGS_FILE}: {e}")

def get_setting_value(key: str, default=None):
    """
    Helper to get a single setting value directly.
    """
    data = load_settings()
    return data.get(key, default)
