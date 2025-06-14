import pytest
from unittest import mock
import json
import os

# Modules to test
from spotify2ytmusic import backend
from spotify2ytmusic.exceptions import (
    YTMAuthError,
    PlaylistLookupError,
    PlaylistCreationError,
    SongLookupError,
    SpotifyBackupError, # Though not directly raised in backend.py, good to have if testing interactions
)
from spotify2ytmusic.constants import (
    SEARCH_ALGO_EXACT,
    SEARCH_ALGO_EXTENDED,
    SEARCH_ALGO_APPROXIMATE,
    DEFAULT_SEARCH_ALGORITHM
)

# Named tuple from backend
SongInfo = backend.SongInfo

# Mock YTMusic class structure for type hinting if needed, and for return values
class MockYTMusic:
    def __init__(self, oauth_path=None):
        if oauth_path == "error_oauth.json": # Simulate JSONDecodeError
            raise json.decoder.JSONDecodeError("Simulated JSON error", "doc", 0)
        self.oauth_path = oauth_path

    def create_playlist(self, title, description, privacy_status):
        # This will be mocked per test for specific behaviors (success, failure, retries)
        pass

    def get_library_playlists(self, limit=None):
        pass

    def get_album(self, browseId):
        pass

    def search(self, query, filter=None, limit=None, ignore_spelling=None):
        pass

    def get_playlist(self, playlistId):
        pass

    def add_playlist_items(self, playlistId, videoIds, duplicates=False):
        pass

    def rate_song(self, videoId, rating):
        pass

    def get_search_suggestions(self, query):
        return []


@pytest.fixture
def mock_ytmusic_instance():
    return mock.MagicMock(spec=MockYTMusic)

# Test get_ytmusic()
@mock.patch('spotify2ytmusic.backend.YTMusic', MockYTMusic) # Mock the class itself
@mock.patch('spotify2ytmusic.backend.os.path.exists')
def test_get_ytmusic_no_oauth_file(mock_exists):
    mock_exists.return_value = False
    with pytest.raises(YTMAuthError, match="No file 'oauth.json' exists"):
        backend.get_ytmusic()

@mock.patch('spotify2ytmusic.backend.YTMusic', MockYTMusic)
@mock.patch('spotify2ytmusic.backend.os.path.exists')
def test_get_ytmusic_json_decode_error(mock_exists):
    mock_exists.return_value = True
    # To trigger JSONDecodeError, MockYTMusic constructor will check for "error_oauth.json"
    # but we call YTMusic("oauth.json"). So, we need to mock YTMusic directly.
    with mock.patch('spotify2ytmusic.backend.YTMusic', side_effect=json.decoder.JSONDecodeError("Simulated error", "doc", 0)):
        with pytest.raises(YTMAuthError, match="JSON Decode error"):
            backend.get_ytmusic()

@mock.patch('spotify2ytmusic.backend.YTMusic', MockYTMusic)
@mock.patch('spotify2ytmusic.backend.os.path.exists')
def test_get_ytmusic_success(mock_exists): # Removed unused fixture
    mock_exists.return_value = True
    # For this test, we want the actual MockYTMusic to be instantiated
    yt = backend.get_ytmusic()
    assert isinstance(yt, MockYTMusic)
    assert yt.oauth_path == "oauth.json"


# Test _ytmusic_create_playlist()
@mock.patch('time.sleep', return_value=None) # Mock time.sleep to speed up tests
def test_ytmusic_create_playlist_success_first_try(mock_sleep, mock_ytmusic_instance):
    mock_ytmusic_instance.create_playlist.return_value = "playlist_id_123"
    playlist_id = backend._ytmusic_create_playlist(mock_ytmusic_instance, "Test Playlist", "Desc")
    assert playlist_id == "playlist_id_123"
    mock_ytmusic_instance.create_playlist.assert_called_once()

@mock.patch('time.sleep', return_value=None)
def test_ytmusic_create_playlist_success_after_retries(mock_sleep, mock_ytmusic_instance):
    mock_ytmusic_instance.create_playlist.side_effect = [
        Exception("Attempt 1 failed"),
        Exception("Attempt 2 failed"),
        "playlist_id_456"
    ]
    playlist_id = backend._ytmusic_create_playlist(mock_ytmusic_instance, "Retry Playlist", "Desc")
    assert playlist_id == "playlist_id_456"
    assert mock_ytmusic_instance.create_playlist.call_count == 3

@mock.patch('time.sleep', return_value=None)
def test_ytmusic_create_playlist_failure_after_all_retries(mock_sleep, mock_ytmusic_instance):
    mock_ytmusic_instance.create_playlist.side_effect = Exception("Persistent failure")
    with pytest.raises(PlaylistCreationError, match='Could not create playlist "Fail Playlist" after multiple retries.'):
        backend._ytmusic_create_playlist(mock_ytmusic_instance, "Fail Playlist", "Desc")
    assert mock_ytmusic_instance.create_playlist.call_count == 10


# Test iter_spotify_playlist()
SAMPLE_SPOTIFY_DATA = {
    "playlists": [
        {
            "name": "Liked Songs",
            "id": "liked_songs_id_placeholder", # Actual liked songs usually don't have an ID this way
            "tracks": [
                {"track": {"name": "Song A", "artists": [{"name": "Artist A"}], "album": {"name": "Album X"}}},
                {"track": {"name": "Song B", "artists": [{"name": "Artist B"}], "album": {"name": "Album Y"}}},
            ]
        },
        {
            "name": "My Playlist 1",
            "id": "playlist1_id",
            "tracks": [
                {"track": {"name": "Song C", "artists": [{"name": "Artist C"}], "album": {"name": "Album Z"}}},
                {"track": None}, # Malformed track
            ]
        }
    ]
}

@mock.patch('spotify2ytmusic.backend.load_playlists_json')
def test_iter_spotify_playlist_liked_songs(mock_load_json):
    mock_load_json.return_value = SAMPLE_SPOTIFY_DATA
    songs = list(backend.iter_spotify_playlist(src_pl_id=None, reverse_playlist=False))
    assert len(songs) == 2
    assert songs[0] == SongInfo("Song A", "Artist A", "Album X")
    assert songs[1] == SongInfo("Song B", "Artist B", "Album Y")

@mock.patch('spotify2ytmusic.backend.load_playlists_json')
def test_iter_spotify_playlist_by_id(mock_load_json):
    mock_load_json.return_value = SAMPLE_SPOTIFY_DATA
    songs = list(backend.iter_spotify_playlist(src_pl_id="playlist1_id", reverse_playlist=False))
    assert len(songs) == 1 # Malformed track is skipped
    assert songs[0] == SongInfo("Song C", "Artist C", "Album Z")

@mock.patch('spotify2ytmusic.backend.load_playlists_json')
def test_iter_spotify_playlist_not_found(mock_load_json):
    mock_load_json.return_value = SAMPLE_SPOTIFY_DATA
    with pytest.raises(PlaylistLookupError, match="Could not find Spotify playlist with ID: non_existent_id"):
        list(backend.iter_spotify_playlist(src_pl_id="non_existent_id"))

@mock.patch('spotify2ytmusic.backend.load_playlists_json')
def test_iter_spotify_playlist_malformed_track_skip(mock_load_json, capsys):
    mock_load_json.return_value = SAMPLE_SPOTIFY_DATA
    list(backend.iter_spotify_playlist(src_pl_id="playlist1_id")) # Iterate through it
    captured = capsys.readouterr()
    assert "WARNING: Spotify track seems to be malformed, Skipping." in captured.out


# Test get_playlist_id_by_name()
def test_get_playlist_id_by_name_found(mock_ytmusic_instance):
    mock_ytmusic_instance.get_library_playlists.return_value = [
        {"title": "Playlist Alpha", "playlistId": "alpha_id"},
        {"title": "Playlist Beta", "playlistId": "beta_id"},
    ]
    playlist_id = backend.get_playlist_id_by_name(mock_ytmusic_instance, "Playlist Alpha")
    assert playlist_id == "alpha_id"

def test_get_playlist_id_by_name_not_found(mock_ytmusic_instance):
    mock_ytmusic_instance.get_library_playlists.return_value = [
        {"title": "Playlist Alpha", "playlistId": "alpha_id"},
    ]
    playlist_id = backend.get_playlist_id_by_name(mock_ytmusic_instance, "Non Existent Playlist")
    assert playlist_id is None

def test_get_playlist_id_by_name_key_error(mock_ytmusic_instance, capsys):
    mock_ytmusic_instance.get_library_playlists.side_effect = KeyError("Simulated API error")
    with pytest.raises(KeyError): # Current logic re-raises
        backend.get_playlist_id_by_name(mock_ytmusic_instance, "Any Playlist")
    captured = capsys.readouterr()
    assert "failed with KeyError" in captured.out


# Test lookup_song() - Simplified examples
# Full testing would require many cases for each algorithm.
def test_lookup_song_exact_algo_album_match(mock_ytmusic_instance):
    mock_ytmusic_instance.search.return_value = [{"browseId": "album_browse_id", "title": "Album X", "artists": [{"name": "Artist A"}]}] # Album search
    mock_ytmusic_instance.get_album.return_value = {
        "tracks": [{"title": "Song A", "videoId": "vidA"}]
    }
    result = backend.lookup_song(mock_ytmusic_instance, "Song A", "Artist A", "Album X", SEARCH_ALGO_EXACT)
    assert result["title"] == "Song A"

def test_lookup_song_exact_algo_song_match(mock_ytmusic_instance):
    # Fail album lookup path first
    mock_ytmusic_instance.search.side_effect = [
        [], # Empty album search result
        [{"title": "Song A", "artists": [{"name": "Artist A"}], "album": {"name": "Album X"}, "videoId": "vidA_song"}] # Song search
    ]
    mock_ytmusic_instance.get_album.return_value = {"tracks": []} # No tracks in any album found

    result = backend.lookup_song(mock_ytmusic_instance, "Song A", "Artist A", "Album X", SEARCH_ALGO_EXACT)
    assert result["title"] == "Song A"
    assert result["videoId"] == "vidA_song"
    # Check that search was called twice (once for albums, once for songs)
    assert mock_ytmusic_instance.search.call_count == 2


def test_lookup_song_extended_algo_match(mock_ytmusic_instance):
    songs_results = [
        {"title": "Wrong Song", "artists": [{"name": "Artist A"}], "album": {"name": "Album X"}, "videoId": "vidWrong"},
        {"title": "Song A", "artists": [{"name": "Artist A"}], "album": {"name": "Album X"}, "videoId": "vidA_ext"},
    ]
    mock_ytmusic_instance.search.side_effect = [
        [], # Album search returns nothing
        songs_results # Song search
    ]
    result = backend.lookup_song(mock_ytmusic_instance, "Song A", "Artist A", "Album X", SEARCH_ALGO_EXTENDED)
    assert result["videoId"] == "vidA_ext"

def test_lookup_song_extended_algo_not_found(mock_ytmusic_instance):
    songs_results = [
        {"title": "Wrong Song", "artists": [{"name": "Artist A"}], "album": {"name": "Album X"}, "videoId": "vidWrong"},
    ]
    mock_ytmusic_instance.search.side_effect = [
        [], # Album search returns nothing
        songs_results # Song search
    ]
    with pytest.raises(SongLookupError):
        backend.lookup_song(mock_ytmusic_instance, "Song A", "Artist A", "Album X", SEARCH_ALGO_EXTENDED)


def test_lookup_song_no_results_at_all(mock_ytmusic_instance):
    mock_ytmusic_instance.search.return_value = [] # Both album and song searches yield nothing
    with pytest.raises(SongLookupError, match="No songs found for query"): # Match specific error from new check
        backend.lookup_song(mock_ytmusic_instance, "NonExistent", "Artist", "Album", SEARCH_ALGO_EXACT)


# Test get_formatted_playlists()
@mock.patch('spotify2ytmusic.backend.load_playlists_json')
@mock.patch('spotify2ytmusic.backend.get_ytmusic')
def test_get_formatted_playlists_success(mock_get_yt, mock_load_spotify, mock_ytmusic_instance):
    mock_get_yt.return_value = mock_ytmusic_instance
    mock_load_spotify.return_value = SAMPLE_SPOTIFY_DATA
    mock_ytmusic_instance.get_library_playlists.return_value = [
        {"title": "YT Playlist 1", "playlistId": "yt_id_1", "count": 10}
    ]

    spotify_lines, ytmusic_lines = backend.get_formatted_playlists()

    assert "== Spotify Playlists:" in spotify_lines[0]
    assert f"{SAMPLE_SPOTIFY_DATA['playlists'][0]['id']}" in spotify_lines[1]
    assert f"{SAMPLE_SPOTIFY_DATA['playlists'][1]['id']}" in spotify_lines[2]

    assert "\n== YTMusic Playlists:" in ytmusic_lines[0]
    assert "yt_id_1 YT Playlist 1 (10 tracks)" in ytmusic_lines[1]

@mock.patch('spotify2ytmusic.backend.load_playlists_json', side_effect=FileNotFoundError("Simulated FileNotFoundError from load_playlists_json"))
def test_get_formatted_playlists_spotify_file_not_found(mock_load_spotify):
    # The function get_formatted_playlists catches FileNotFoundError and re-raises it with a more specific message
    with pytest.raises(FileNotFoundError, match="Error: 'playlists.json' not found. Please run Spotify backup first."):
        backend.get_formatted_playlists()

@mock.patch('spotify2ytmusic.backend.load_playlists_json')
@mock.patch('spotify2ytmusic.backend.get_ytmusic', side_effect=YTMAuthError("Auth failed"))
def test_get_formatted_playlists_ytm_auth_error(mock_get_yt, mock_load_spotify):
    mock_load_spotify.return_value = SAMPLE_SPOTIFY_DATA # Spotify part is fine
    with pytest.raises(YTMAuthError, match="Auth failed"):
        backend.get_formatted_playlists()

@mock.patch('spotify2ytmusic.backend.load_playlists_json')
@mock.patch('spotify2ytmusic.backend.get_ytmusic')
def test_get_formatted_playlists_ytm_key_error(mock_get_yt, mock_load_spotify, mock_ytmusic_instance):
    mock_get_yt.return_value = mock_ytmusic_instance
    mock_load_spotify.return_value = SAMPLE_SPOTIFY_DATA
    mock_ytmusic_instance.get_library_playlists.side_effect = KeyError("YTMusic API key error")

    with pytest.raises(PlaylistLookupError, match="YTMusic API key error"):
        backend.get_formatted_playlists()


# Test copier() - High-level flow and error counting
@mock.patch('spotify2ytmusic.backend.get_ytmusic') # Mocks get_ytmusic called within copier
@mock.patch('spotify2ytmusic.backend.lookup_song')
def test_copier_flow_and_errors(mock_lookup_song, mock_get_yt_global, mock_ytmusic_instance):
    # Setup get_ytmusic to return our main mock instance for copier's internal call
    mock_get_yt_global.return_value = mock_ytmusic_instance

    # Mock iter_spotify_playlist (not done here, assumed to be passed as src_tracks)
    src_tracks_data = [
        SongInfo("Song Good", "Artist G", "Album G"),
        SongInfo("Song Bad", "Artist B", "Album B"), # This one will fail lookup
        SongInfo("Song Also Good", "Artist AG", "Album AG"),
    ]

    # Mock lookup_song behavior
    def lookup_song_side_effect(yt, title, artist, album, algo):
        if title == "Song Bad":
            raise SongLookupError("Failed to find Song Bad")
        return {"title": title, "artists": [{"name": artist}], "album": {"name": album}, "videoId": f"vid_{title.replace(' ', '')}"}
    mock_lookup_song.side_effect = lookup_song_side_effect

    # Mock YTMusic methods that would be called by copier
    mock_ytmusic_instance.get_playlist.return_value = {"title": "Destination Playlist"} # For dst_pl_id not None
    mock_ytmusic_instance.add_playlist_items.return_value = None # Simulate success
    mock_ytmusic_instance.rate_song.return_value = None # Simulate success

    # Test adding to a specific playlist
    with mock.patch('builtins.print') as mock_print: # To check output easily
        backend.copier(iter(src_tracks_data), dst_pl_id="dest_playlist_id", dry_run=False, yt=mock_ytmusic_instance)

        # Assertions
        assert mock_lookup_song.call_count == 3
        mock_ytmusic_instance.add_playlist_items.assert_any_call(playlistId="dest_playlist_id", videoIds=["vid_SongGood"], duplicates=False)
        mock_ytmusic_instance.add_playlist_items.assert_any_call(playlistId="dest_playlist_id", videoIds=["vid_SongAlsoGood"], duplicates=False)
        assert mock_ytmusic_instance.add_playlist_items.call_count == 2 # Not called for "Song Bad"

        # Check print output for error count
        found_error_count_line = False
        for call_args in mock_print.call_args_list:
                # Ensure there's something to index in call_args[0]
                if call_args[0] and len(call_args[0]) > 0:
                    log_line = str(call_args[0][0]) # Make sure it's a string
                    if "Added 2 tracks" in log_line and "1 errors" in log_line:
                        found_error_count_line = True
                        break
        assert found_error_count_line, "Error count line not found or incorrect in output"

    # Test "Liking" songs (dst_pl_id is None)
    mock_lookup_song.call_count = 0 # Reset for this part
    mock_ytmusic_instance.rate_song.call_count = 0
    with mock.patch('builtins.print'):
        backend.copier(iter(src_tracks_data), dst_pl_id=None, dry_run=False, yt=mock_ytmusic_instance)
        assert mock_ytmusic_instance.rate_song.call_count == 2 # Song Bad fails lookup
        mock_ytmusic_instance.rate_song.assert_any_call("vid_SongGood", "LIKE")


def test_copier_playlist_lookup_error(mock_ytmusic_instance):
    # Test PlaylistLookupError if dst_pl_id is provided but playlist fetch fails
    mock_ytmusic_instance.get_playlist.side_effect = Exception("YT API error finding playlist")
    src_tracks_data = [SongInfo("Test Song", "Test Artist", "Test Album")]

    with pytest.raises(PlaylistLookupError, match="ERROR: Unable to find YTMusic playlist"):
        backend.copier(iter(src_tracks_data), dst_pl_id="invalid_dst_id", yt=mock_ytmusic_instance)

# More tests could be added for:
# - copy_playlist (higher level, combines many backend functions)
# - copy_all_playlists (even higher level)
# These would involve more complex mocking setups.
# The current set covers the core logic units fairly well.
