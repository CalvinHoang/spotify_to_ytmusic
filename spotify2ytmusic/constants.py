"""
Constants for the Spotify to YouTube Music application.
"""

# Search Algorithm Constants
SEARCH_ALGO_EXACT = "exact"
SEARCH_ALGO_EXTENDED = "extended"  # Corresponds to former integer value 1
SEARCH_ALGO_APPROXIMATE = "approximate"  # Corresponds to former integer value 2
DEFAULT_SEARCH_ALGORITHM = SEARCH_ALGO_EXACT

SEARCH_ALGORITHM_CHOICES = [SEARCH_ALGO_EXACT, SEARCH_ALGO_EXTENDED, SEARCH_ALGO_APPROXIMATE]

# For mapping old integer values from settings to new string constants (optional, for backward compatibility)
SEARCH_ALGO_INT_TO_STR_MAP = {
    0: SEARCH_ALGO_EXACT,
    1: SEARCH_ALGO_EXTENDED,
    2: SEARCH_ALGO_APPROXIMATE,
}

# For mapping string constants to display text in GUI
SEARCH_ALGO_DISPLAY_NAMES = {
    SEARCH_ALGO_EXACT: "Exact Match: Searches for songs with the exact same title and artist. (Fastest, Recommended)",
    SEARCH_ALGO_EXTENDED: "Fuzzy Match: Uses fuzzy string matching to find similar song titles. (Slower, might find incorrect matches)",
    SEARCH_ALGO_APPROXIMATE: "Fuzzy Match with Videos: Similar to Fuzzy Match, but also includes video results from YouTube Music. (Slowest, highest chance of incorrect matches)"
}
