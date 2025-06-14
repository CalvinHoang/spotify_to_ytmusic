import json
from typing import Dict, Any

# Default settings dictionary
DEFAULT_SETTINGS_VALUES = {"auto_scroll": True, "algo_number": 0}

def parse_settings_data(settings_json_content: str, default_settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses JSON settings content.

    Args:
        settings_json_content: Raw string content from the settings JSON file.
        default_settings: A dictionary containing the default settings.

    Returns:
        A dictionary of processed settings. Returns defaults if content is empty,
        malformed, or keys are missing.
    """
    if not settings_json_content:
        return default_settings.copy()

    try:
        loaded_settings = json.loads(settings_json_content)
        # Ensure all default keys are present
        final_settings = default_settings.copy()
        final_settings.update(loaded_settings) # Overwrite defaults with loaded if present
        return final_settings
    except json.JSONDecodeError:
        # Log this? For now, just return defaults as per original logic implicit behavior
        print("Warning: JSONDecodeError while parsing settings. Using defaults.")
        return default_settings.copy()


def prepare_settings_for_save(auto_scroll_val: bool, algo_number_val: int) -> Dict[str, Any]:
    """
    Prepares a dictionary of settings data ready for JSON serialization.

    Args:
        auto_scroll_val: Boolean value for auto_scroll setting.
        algo_number_val: Integer value for algo_number setting.

    Returns:
        A dictionary structured for saving to settings.json.
    """
    return {
        "auto_scroll": auto_scroll_val,
        "algo_number": algo_number_val,
    }
