import json
from typing import Dict, Any
from .constants import DEFAULT_SEARCH_ALGORITHM, SEARCH_ALGO_INT_TO_STR_MAP, SEARCH_ALGORITHM_CHOICES

# Default settings dictionary using new string constant for algorithm
DEFAULT_SETTINGS_VALUES = {"auto_scroll": True, "algo_name": DEFAULT_SEARCH_ALGORITHM}

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
        final_settings = default_settings.copy() # Start with current defaults (e.g., with algo_name)

        # Handle auto_scroll
        if "auto_scroll" in loaded_settings and isinstance(loaded_settings["auto_scroll"], bool):
            final_settings["auto_scroll"] = loaded_settings["auto_scroll"]

        # Handle algorithm:
        # Priority 1: New 'algo_name' string
        if "algo_name" in loaded_settings and loaded_settings["algo_name"] in SEARCH_ALGORITHM_CHOICES:
            final_settings["algo_name"] = loaded_settings["algo_name"]
        # Priority 2: Old 'algo_number' integer (for backward compatibility)
        elif "algo_number" in loaded_settings and isinstance(loaded_settings["algo_number"], int):
            final_settings["algo_name"] = SEARCH_ALGO_INT_TO_STR_MAP.get(
                loaded_settings["algo_number"], default_settings["algo_name"]
            )
        # If neither is present or valid, it will keep the default 'algo_name' from final_settings initialization.

        # Remove old algo_number if it exists from loaded_settings to keep settings clean
        if "algo_number" in final_settings and "algo_name" in final_settings:
             final_settings.pop("algo_number", None)


        # Ensure all default keys are present if not handled above explicitly
        # This part might be redundant if all keys are handled explicitly like auto_scroll and algo_name
        # For other potential settings, this generic update is fine.
        # final_settings.update(loaded_settings) # This could re-introduce algo_number if not careful
        # Let's be more specific:
        for key in default_settings:
            if key not in final_settings and key in loaded_settings: # For any other future settings
                 final_settings[key] = loaded_settings[key]

        return final_settings
    except json.JSONDecodeError:
        print("Warning: JSONDecodeError while parsing settings. Using defaults.")
        return default_settings.copy()


def prepare_settings_for_save(auto_scroll_val: bool, algo_name_val: str) -> Dict[str, Any]:
    """
    Prepares a dictionary of settings data ready for JSON serialization.

    Args:
        auto_scroll_val: Boolean value for auto_scroll setting.
        algo_name_val: String value for algo_name setting.

    Returns:
        A dictionary structured for saving to settings.json.
    """
    if algo_name_val not in SEARCH_ALGORITHM_CHOICES:
        print(f"Warning: Invalid algo_name_val '{algo_name_val}' being saved. Defaulting to {DEFAULT_SEARCH_ALGORITHM}.")
        algo_name_val = DEFAULT_SEARCH_ALGORITHM
    return {
        "auto_scroll": auto_scroll_val,
        "algo_name": algo_name_val,
    }
