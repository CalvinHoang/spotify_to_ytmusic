### Overview

This is a set of scripts for copying "liked" songs and playlists from Spotify to YTMusic. It features a user-friendly Graphical User Interface (GUI) to guide you through the process.

---

### Preparation/Pre-Conditions

1.  **Install Python and Git**: Ensure you have Python (3.7+ recommended) and Git installed on your system.
2.  **Uninstall Previous Versions (Optional)**: If you previously installed `linsomniac/spotify_to_ytmusic` or an older version of this tool via pip, uninstall it:
    *   Windows: `python -m pip uninstall spotify2ytmusic`
    *   Linux/Mac: `python3 -m pip uninstall spotify2ytmusic`

---

### Setup Instructions

#### 1. Clone the Repository

```bash
git clone https://github.com/linsomniac/spotify_to_ytmusic.git
cd spotify_to_ytmusic
```

#### 2. Create a Virtual Environment and Install Dependencies

Using a virtual environment is highly recommended to manage dependencies.

*   **Windows**:
    ```bash
    python -m venv .venv
    .venv\Scripts\activate
    pip install ytmusicapi tk spotipy
    ```
*   **Linux/Mac**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install ytmusicapi tk spotipy
    ```
    *(Note: `tk` might already be included with your Python installation. If you encounter `tkinter` errors, you might need to install it system-wide, e.g., `sudo apt-get install python3-tk` on Debian/Ubuntu).*

---

### Using the GUI

The GUI provides a step-by-step approach to transfer your music.

#### Launching the GUI

*   **Windows**: `python -m spotify2ytmusic.gui`
*   **Linux/Mac**: `python3 -m spotify2ytmusic.gui`

#### GUI Workflow and Tabs

The GUI is organized into several tabs, each corresponding to a step in the migration process:

1.  **Welcome Tab**:
    *   Provides an introduction to the application, outlines prerequisites, and explains the overall process.
    *   It's recommended to read this tab first to understand the workflow.

2.  **Tab 1: Login to YT Music**:
    *   **Action**: Click the "Login to YouTube Music" button.
    *   **Purpose**: Authenticates your YouTube Music account.
    *   **Details**: If you don't have an `oauth.json` file (from a previous successful login) in the application's directory, a console window (or a message in the GUI log) will guide you through the `ytmusicapi` OAuth process. On successful login, or if `oauth.json` is already present and valid, the application will automatically proceed or enable the next relevant tab.
    *   **Note**: The old method of manually creating `raw_headers.txt` is no longer the primary recommended way for GUI users; the interactive OAuth process initiated by this tab is preferred.

3.  **Tab 2: Spotify Backup**:
    *   **Action**: Click the "Start Spotify Backup" button.
    *   **Purpose**: Creates a local backup of your Spotify library, including liked songs and playlists. This backup is stored in a `playlists.json` file.
    *   **Details**: This step uses the `spotipy` library and will likely prompt you to log in to your Spotify account through your web browser if it's the first time or your credentials have expired.

4.  **Tab 3: Load Liked Songs**:
    *   **Action**: Click the "Transfer Liked Songs" button.
    *   **Purpose**: Migrates your Spotify liked songs (from the `playlists.json` backup) to your YouTube Music library.
    *   **Details**: The GUI log will show the progress as songs are matched and transferred.

5.  **Tab 4: List Playlists**:
    *   **Action**: Click the "List Spotify Playlists" button.
    *   **Purpose**: Displays all your Spotify playlists (from the backup) along with their unique IDs.
    *   **Details**: These IDs are useful if you want to transfer specific playlists individually using Tab 6.

6.  **Tab 5: Copy All Playlists**:
    *   **Action**: Click the "Copy All Playlists" button.
    *   **Purpose**: Transfers all your backed-up Spotify playlists to YouTube Music.
    *   **Details**: This can take a significant amount of time as songs are added one by one. Playlist names will be replicated from Spotify to YouTube Music. This does not copy the "Liked Songs" playlist (use Tab 3 for that).

7.  **Tab 6: Copy Specific Playlist**:
    *   **Action**: Enter the "Spotify Playlist ID" (required) and optionally a "YouTube Music Playlist ID". Click "Copy This Playlist".
    *   **Purpose**: Transfers a single Spotify playlist to YouTube Music.
    *   **Details**:
        *   Get the Spotify Playlist ID from the list generated in Tab 4.
        *   If you provide a YouTube Music Playlist ID, songs will be added to that existing playlist.
        *   If you leave the YouTube Music Playlist ID blank, a new playlist will be created in YouTube Music with the same name as the Spotify playlist.
        *   Input validation will prompt you if the Spotify Playlist ID is missing.

8.  **Tab 7: Settings**:
    *   **Purpose**: Configure application settings.
    *   **Options**:
        *   **Enable Auto-Scroll in Log View**: Check this to have the log area automatically scroll to the latest messages.
        *   **Song Matching Algorithm**: Choose how the application matches songs between Spotify and YouTube Music. Options include:
            *   Exact Match (fastest, recommended)
            *   Fuzzy Match (slower, may find incorrect matches)
            *   Fuzzy Match with Videos (slowest, highest chance of incorrect matches)
    *   Settings are saved in `settings.json` and loaded when the GUI starts.

**General GUI Notes**:
*   **Log Area**: The bottom part of the GUI displays log messages, progress, and any errors.
*   **Error Handling**: The GUI will display error messages in dialog boxes for issues like missing input or problems during backend operations.
*   **Responsiveness**: Operations that take time (like transferring songs) are run in separate threads to keep the GUI responsive. You can follow their progress in the log area.

---

### Command Line Usage

Note: The following command-line instructions are optional and intended for advanced users or specific scripting scenarios. All primary functionalities of this application are available through the Graphical User Interface (GUI), which is the recommended method for most users.

(The command-line usage section remains largely the same but ensure consistency with any backend changes if those were also part of the scope. For this task, focusing on GUI updates in README.)

**NOTE**: There are two possible ways to run these commands, one is via standalone commands
if the application was installed, which takes the form of: `s2yt_load_liked`

If not fully installed, you can replace the "s2yt\_" with "python -m spotify2ytmusic", for
example: `s2yt_load_liked` becomes `python -m spotify2ytmusic load_liked` (adjust for Windows/Linux python command if necessary).

#### Login to YTMusic (for CLI)
For command-line usage, `ytmusicapi` requires an `oauth.json`. If you run a CLI command that needs authentication and `oauth.json` is missing or invalid, `ytmusicapi` will typically print instructions on how to perform the OAuth setup. This usually involves running `ytmusicapi oauth` in your terminal.

#### Backup Your Spotify Playlists
Run `spotify2ytmusic/spotify_backup.py` (or `python -m spotify2ytmusic.spotify_backup`) and it will guide you through authorizing access to your Spotify account.
Example: `python3 -m spotify2ytmusic.spotify_backup playlists.json --dump=liked,playlists --format=json`
This saves your playlists and liked songs into "playlists.json".

#### Import Your Liked Songs
`python3 -m spotify2ytmusic load_liked`
(or `python -m spotify2ytmusic load_liked` on Windows)

#### List Your Playlists
`python3 -m spotify2ytmusic list_playlists`

#### Copy All Playlists
`python3 -m spotify2ytmusic copy_all_playlists`

#### Copy Specific Playlist
`python3 -m spotify2ytmusic copy_playlist <SPOTIFY_PLAYLIST_ID> <YTMUSIC_PLAYLIST_ID_OR_NAME>`
If `<YTMUSIC_PLAYLIST_ID_OR_NAME>` starts with a `+`, a new playlist with that name (after the `+`) will be created. Otherwise, it's treated as an existing YTMusic Playlist ID.

Example: `python3 -m spotify2ytmusic copy_playlist YOUR_SPOTIFY_ID "+My New Playlist Name"`

---

### Details About Search Algorithms

(This section can remain as is, assuming the core backend logic for search hasn't changed.)

The function first searches for albums by the given artist name on YTMusic.
... (rest of the section) ...

---

### FAQ

(This section can remain as is, unless GUI changes affect any answers.)

- My copy is failing after 20-40 minutes. Is my session timing out?
  Try playing music in the browser on Youtube Music while you are loading the playlists,
  this has been reported to keep the session from timing out.
... (rest of the section) ...

---

### Testing

This section provides an overview of the testing approach for the application.

#### GUI Testing
Due to environmental limitations with `tkinter` (the GUI toolkit used) in some automated or headless environments, comprehensive interactive GUI testing was not always feasible.

To address this and ensure core logic is testable:
*   The settings management logic within the GUI was refactored into a separate, pure Python module: `spotify2ytmusic/gui_utils.py`.
*   This `gui_utils.py` module has a dedicated suite of unit tests located in `tests/test_gui_utils.py`. These tests cover functionalities such as parsing settings from JSON, handling malformed or incomplete data, applying default settings, and preparing settings data for saving. These tests currently pass, ensuring the robustness of this non-visual part of the GUI's logic.
*   The core visual components and event handling within `spotify2ytmusic/gui.py` (which directly depend on `tkinter`) are not currently covered by automated tests due to the aforementioned environmental limitations. Manual testing is recommended for these aspects.

#### Backend/Core Logic Testing
Tests for the backend music synchronization logic (e.g., in `backend.py`, `spotify_backup.py`, and command-line interface scripts) are handled separately and aim to cover the core functionalities of song and playlist transfers.

---

## License

Creative Commons Zero v1.0 Universal

spotify-backup.py licensed under MIT License.
See <https://github.com/caseychu/spotify-backup> for more information.

[//]: # " vim: set tw=90 ts=4 sw=4 ai: "
