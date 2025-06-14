"""
Custom exceptions for the Spotify to YouTube Music application.
"""

class YTMAuthError(Exception):
    """Custom exception for YouTube Music authentication errors."""
    pass

class PlaylistLookupError(Exception):
    """Custom exception for errors encountered while looking up playlists."""
    pass

class PlaylistCreationError(Exception):
    """Custom exception for errors encountered during playlist creation."""
    pass

class SongLookupError(Exception):
    """Custom exception for errors encountered while looking up songs."""
    pass

class SpotifyBackupError(Exception):
    """Custom exception for errors during Spotify backup operations."""
    pass

class OperationFailedError(Exception):
    """Generic error for operations that fail and should be reported to UI."""
    pass
