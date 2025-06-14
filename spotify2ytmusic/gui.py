#!/usr/bin/env python3

import os
import subprocess
import sys
import threading
import json
import tkinter as tk
from tkinter import ttk, messagebox # Import messagebox

from . import cli
from . import backend
from . import spotify_backup
from .exceptions import (YTMAuthError, PlaylistLookupError, PlaylistCreationError,
                       SongLookupError, SpotifyBackupError, OperationFailedError)
from typing import Callable # Dict, Any are no longer used directly here for the moved functions

# Import the refactored settings logic
from .gui_utils import DEFAULT_SETTINGS_VALUES, parse_settings_data, prepare_settings_for_save
# Import constants for search algorithms
from .constants import (SEARCH_ALGO_EXACT, SEARCH_ALGO_EXTENDED, SEARCH_ALGO_APPROXIMATE,
                        DEFAULT_SEARCH_ALGORITHM, SEARCH_ALGO_DISPLAY_NAMES)


def create_label(parent: tk.Frame, text: str, **kwargs) -> tk.Label:
    """Simply creates a label with the given text and the given parent.

    Args:
        parent (tk.Frame): The parent of the label.
        text (str): The text of the label.

    Returns:
        tk.Label: The label created.
    """
    return tk.Label(
        parent,
        text=text,
        font=("Helvetica", 14),
        background="#26242f",
        foreground="white",
        **kwargs,
    )


def create_button(parent: tk.Frame, text: str, **kwargs) -> tk.Button:
    """Simply creates a button with the given text and the given parent.

    Args:
        parent (tk.Frame): The parent of the button.
        text (str): The text of the button.

    Returns:
        tk.Button: The button created.
    """
    return tk.Button(
        parent,
        text=text,
        font=("Helvetica", 14),
        background="#696969",
        foreground="white",
        border=1,
        **kwargs,
    )


class Window:
    """
    The main graphical user interface for the Spotify to YT Music application.

    This class encapsulates all UI elements, including tabs for different actions
    (login, backup, copy playlists, settings) and a log display area.
    It handles user interactions and calls backend functions in separate threads
    to keep the GUI responsive.
    """

    def __init__(self) -> None:
        """
        Initializes the main window of the application.
        Sets up the window title, size, background, styles, and layout,
        including the tabbed interface and log display.
        """
        self.root = tk.Tk()
        self.root.title("Spotify to YT Music")
        self.root.geometry("1280x720")
        self.root.config(background="#26242f")

        # To store thread call status
        self._thread_call_status = {"success": False, "error": None, "error_title": "Operation Failed"}


        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "TNotebook.Tab", background="#121212", foreground="white"
        )  # Set the background color to #121212 when not selected
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#26242f")],
            foreground=[("selected", "#ffffff")],
        )  # Set the background color to #26242f and text color to white when selected
        style.configure("TFrame", background="#26242f")
        style.configure("TNotebook", background="#121212")

        # Redirect stdout to GUI
        sys.stdout.write = self.redirector

        self._configure_styles()
        self._setup_paned_window()
        self._setup_tabs() # This now includes tab0
        self._setup_log_frame()

        self._create_tab0_welcome_ui() # New tab UI
        self._create_tab1_login_ui()
        self._create_tab2_spotify_backup_ui()
        self._create_tab3_load_liked_ui()
        self._create_tab4_list_playlists_ui()
        self._create_tab5_copy_all_ui()
        self._create_tab6_copy_specific_ui()
        self._create_tab7_settings_ui()

        self.root.after(1, lambda: self.yt_login(auto=True))
        self.root.after(1, lambda: self.load_write_settings(0))

    def _configure_styles(self) -> None:
        """Configures the styles for ttk widgets.

        This method sets up the visual appearance of the TNotebook tabs and TFrame
        to match the application's dark theme.
        """
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "TNotebook.Tab", background="#121212", foreground="white"
        )  # Set the background color to #121212 when not selected
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#26242f")],
            foreground=[("selected", "#ffffff")],
        )  # Set the background color to #26242f and text color to white when selected
        style.configure("TFrame", background="#26242f")
        style.configure("TNotebook", background="#121212")

    def _setup_paned_window(self) -> None:
        """Sets up the main PanedWindow.

        The PanedWindow allows the user to resize the tabs area and the logs area.
        """
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        self.paned_window.pack(fill=tk.BOTH, expand=1)

    def _setup_tabs(self) -> None:
        """Sets up the TabControl (notebook) and creates the individual tabs.

        This method initializes the main tab control and adds all the necessary
        tabs for different functionalities of the application.
        """
        self.tab_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.tab_frame, weight=2)

        self.tabControl = ttk.Notebook(self.tab_frame)
        self.tabControl.pack(fill=tk.BOTH, expand=1)

        self.tab0 = ttk.Frame(self.tabControl) # Welcome Tab
        self.tab1 = ttk.Frame(self.tabControl) # Login Tab
        self.tab2 = ttk.Frame(self.tabControl) # Spotify Backup Tab
        self.tab3 = ttk.Frame(self.tabControl) # Load Liked Songs Tab
        self.tab4 = ttk.Frame(self.tabControl) # List Playlists Tab
        self.tab5 = ttk.Frame(self.tabControl) # Copy All Playlists Tab
        self.tab6 = ttk.Frame(self.tabControl) # Copy Specific Playlist Tab
        self.tab7 = ttk.Frame(self.tabControl) # Settings Tab

        self.tabControl.add(self.tab0, text="Welcome")
        self.tabControl.add(self.tab1, text="1. Login to YT Music")
        self.tabControl.add(self.tab2, text="2. Spotify Backup")
        self.tabControl.add(self.tab3, text="3. Load Liked Songs")
        self.tabControl.add(self.tab4, text="4. List Playlists")
        self.tabControl.add(self.tab5, text="5. Copy All Playlists")
        self.tabControl.add(self.tab6, text="6. Copy Specific Playlist")
        self.tabControl.add(self.tab7, text="7. Settings")

    def _setup_log_frame(self) -> None:
        """Sets up the frame and Text widget for displaying logs.

        The logs area displays messages, errors, and progress information to the user.
        """
        self.log_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.log_frame, weight=1)

        self.logs = tk.Text(self.log_frame, font=("Helvetica", 14))
        self.logs.pack(fill=tk.BOTH, expand=1)
        self.logs.config(background="#26242f", foreground="white")

    def _create_tab0_welcome_ui(self) -> None:
        """Creates the UI elements for Tab 0 (Welcome).

        This tab provides an introduction to the application and outlines the steps.
        """
        welcome_text = """
        Welcome to Spotify to YT Music Transfer!

        This tool helps you transfer your Spotify playlists and liked songs to YouTube Music.

        Prerequisites:
        1. Python installed on your system.
        2. `ytmusicapi` installed (`pip install ytmusicapi`). If not, the tool will
           attempt to guide you through the OAuth process for YouTube Music.
        3. Spotify data: You'll need to use the Spotify Backup tool first.

        Process Overview:
        1. Login to YT Music: Authenticate with your YouTube Music account.
        2. Spotify Backup: Create a backup of your Spotify library (playlists and liked songs).
           This step requires your Spotify username and access to Spotify API (usually handled
           by the spotipy library, which will prompt for login if needed).
        3. Load Liked Songs: Transfer your Spotify liked songs to YouTube Music.
        4. List Playlists: View your Spotify playlists and their IDs.
        5. Copy All Playlists: Transfer all your backed-up Spotify playlists to YouTube Music.
        6. Copy Specific Playlist: Transfer a single Spotify playlist using its ID.
        7. Settings: Configure application settings like log auto-scroll and matching algorithm.

        Please proceed to the '1. Login to YT Music' tab to begin.
        If you haven't backed up your Spotify data, go to '2. Spotify Backup' after logging in.
        """
        create_label(self.tab0, text=welcome_text, justify=tk.LEFT, anchor="nw").pack(
            padx=10, pady=10, fill=tk.BOTH, expand=True
        )
        create_button(
            self.tab0, text="Go to Login ->", command=lambda: self.tabControl.select(self.tab1)
        ).pack(pady=10)


    def _create_tab1_login_ui(self) -> None:
        """Creates the UI elements for Tab 1 (Login to YT Music).

        This tab provides a button for the user to initiate the YouTube Music login process.
        """
        create_label(
            self.tab1,
            text="Step 1: Login to YouTube Music\n\n"
                 "You need to authenticate with your YouTube Music account.\n"
                 "If you don't have 'oauth.json' in the application's directory,\n"
                 "a console window will open for you to complete the authentication.",
            justify=tk.CENTER,
        ).pack(anchor=tk.CENTER, expand=True, padx=10, pady=10)
        create_button(self.tab1, text="Login to YouTube Music", command=self.yt_login).pack(
            anchor=tk.CENTER, expand=True, pady=10
        )

    def _create_tab2_spotify_backup_ui(self) -> None:
        """Creates the UI elements for Tab 2 (Spotify backup).

        This tab allows the user to back up their Spotify playlists.
        """
        create_label(
            self.tab2,
            text="Step 2: Backup Spotify Library\n\n"
                 "This step will guide you through creating a local backup of your Spotify\n"
                 "playlists and liked songs. You might be prompted to log in to Spotify.",
            justify=tk.CENTER,
        ).pack(anchor=tk.CENTER, expand=True, padx=10, pady=10)
        create_button(
            self.tab2,
            text="Start Spotify Backup",
            command=lambda: self.call_func(
                func=spotify_backup.main,
                args=(),
                next_tab=self.tab3,
                error_title="Spotify Backup Failed"
            ),
        ).pack(anchor=tk.CENTER, expand=True)

    def _create_tab3_load_liked_ui(self) -> None:
        """Creates the UI elements for Tab 3 (Load liked songs).

        This tab enables the user to load their liked songs from Spotify.
        """
        create_label( # Corrected this line
            self.tab3,
            text="Step 3: Transfer Liked Songs from Spotify to YouTube Music\n\n"
                 "This will take your backed-up liked songs from Spotify and add them\n"
                 "to your YouTube Music library.",
            justify=tk.CENTER,
        ).pack(anchor=tk.CENTER, expand=True, padx=10, pady=10)
        create_button(
            self.tab3,
            text="Transfer Liked Songs",
            command=lambda: self.call_func(
                func=backend.copier,
                args=(
                    backend.iter_spotify_playlist(),
                    None,
                    False,
                    0.1,
                    self.var_algo.get(),
                ),
                next_tab=self.tab4,
                error_title="Failed to Transfer Liked Songs"
            ),
        ).pack(anchor=tk.CENTER, expand=True)

    def _create_tab4_list_playlists_ui(self) -> None:
        """Creates the UI elements for Tab 4 (List playlists).

        This tab provides a way to list all Spotify playlists with their IDs.
        """
        create_label(
            self.tab4,
            text="Step 4: List Your Spotify Playlists\n\n"
                 "This will display a list of your Spotify playlists along with their unique IDs.\n"
                 "You can use these IDs in the 'Copy Specific Playlist' step.",
            justify=tk.CENTER,
        ).pack(anchor=tk.CENTER, expand=True, padx=10, pady=10)
        create_button(
            self.tab4,
            text="List Spotify Playlists",
            command=self.display_playlists # Updated command
            # Old: command=lambda: self.call_func(
            #    func=cli.list_playlists, args=(), next_tab=self.tab5, error_title="Failed to list playlists"
            # ),
        ).pack(anchor=tk.CENTER, expand=True)

    def display_playlists(self) -> None:
        """Handles fetching and displaying playlists in the log."""
        def do_list_playlists():
            # This function will run in the thread via call_func
            # It needs to return the data or store it for display_playlists to use
            # For now, let's make it print directly, fitting the refactor of call_func
            # to primarily manage execution and tab switching.
            # If it were to return data, call_func's wrapper would need to store it.

            # New backend function get_formatted_playlists raises exceptions on failure
            spotify_list, ytmusic_list = backend.get_formatted_playlists()

            # If successful, print to log (which is self.redirector)
            # Ensure this is called from the main thread if it directly updates GUI state
            # other than self.logs.insert, but print() is fine as it goes to redirector.
            print("\n".join(spotify_list))
            print("\n".join(ytmusic_list))

        self.call_func(
            func=do_list_playlists,
            args=(),
            next_tab=self.tab5, # Or current tab if preferred: self.tab4
            error_title="Failed to List Playlists"
        )


    def _create_tab5_copy_all_ui(self) -> None:
        """Creates the UI elements for Tab 5 (Copy all playlists).

        This tab allows the user to copy all their Spotify playlists to YouTube Music.
        """
        create_label(
            self.tab5,
            text="Step 5: Copy All Spotify Playlists to YouTube Music\n\n"
                 "This will attempt to transfer all your backed-up Spotify playlists to YouTube Music.\n"
                 "Please note: This can take a significant amount of time, as songs are added individually.",
            justify=tk.CENTER,
        ).pack(anchor=tk.CENTER, expand=True, padx=10, pady=10)
        create_button(
            self.tab5,
            text="Copy All Playlists",
            command=lambda: self.call_func(
                func=backend.copy_all_playlists,
                args=(0.1, False, "utf-8", self.var_algo.get()),
                next_tab=self.tab6,
                error_title="Failed to Copy All Playlists"
            ),
        ).pack(anchor=tk.CENTER, expand=True)

    def _create_tab6_copy_specific_ui(self) -> None:
        """Creates the UI elements for Tab 6 (Copy a specific playlist).

        This tab allows the user to copy a specific Spotify playlist to YouTube Music
        by providing the Spotify playlist ID and optionally a YouTube Music playlist ID.
        """
        create_label(
            self.tab6,
            text="Step 6: Copy a Specific Spotify Playlist to YouTube Music\n\n"
                 "Use this to copy a single playlist. You'll need the Spotify Playlist ID (from Step 4).\n"
                 "You can optionally provide an existing YouTube Music Playlist ID to add to it,\n"
                 "or leave it blank to create a new playlist in YouTube Music.",
            justify=tk.CENTER,
        ).pack(anchor=tk.CENTER, expand=True, padx=10, pady=10)

        create_label(self.tab6, text="Spotify Playlist ID (Required):").pack(
            anchor=tk.W, padx=10, pady=(10,0)
        )
        self.spotify_playlist_id_entry = tk.Entry(self.tab6, width=40)
        self.spotify_playlist_id_entry.pack(anchor=tk.W, padx=10, pady=(0,10))

        create_label(self.tab6, text="YouTube Music Playlist ID (Optional - leave blank to create new):").pack(
            anchor=tk.W, padx=10, pady=(10,0)
        )
        self.yt_playlist_id_entry = tk.Entry(self.tab6, width=40)
        self.yt_playlist_id_entry.pack(anchor=tk.W, padx=10, pady=(0,10))

        create_button(
            self.tab6,
            text="Copy This Playlist",
            command=self._validate_and_copy_specific_playlist, # New validation method
        ).pack(pady=20) # Centered with some padding

    def _validate_and_copy_specific_playlist(self) -> None:
        """
        Validates the input fields for copying a specific playlist and then
        calls the backend function if valid.
        Displays an error message if validation fails.
        """
        spotify_id = self.spotify_playlist_id_entry.get().strip()
        yt_id = self.yt_playlist_id_entry.get().strip()

        if not spotify_id:
            messagebox.showerror(
                "Input Error",
                "Spotify Playlist ID is required. Please enter a valid ID.",
                parent=self.tab6 # Ensure dialog is on top of the current tab/window
            )
            return

        # Optional: Add more specific validation for playlist ID format if known
        # e.g., length, character set

        self.call_func(
            func=backend.copy_playlist,
            args=(
                spotify_id,
                yt_id,
                "utf-8",
                False,
                0.1,
                self.var_algo.get(),
            ),
            next_tab=self.tab6,  # Stay on this tab
            error_title="Failed to Copy Specific Playlist"
        )

    def _create_tab7_settings_ui(self) -> None:
        """Creates the UI elements for Tab 7 (Settings).

        This tab provides options to configure the application, such as auto-scrolling logs
        and selecting the matching algorithm.
        """
        settings_frame = ttk.Frame(self.tab7) # Use a frame for better layout
        settings_frame.pack(expand=True, padx=20, pady=20)


        self.var_scroll = tk.BooleanVar()
        auto_scroll_check = tk.Checkbutton(
            settings_frame, # Add to frame
            text="Enable Auto-Scroll in Log View",
            variable=self.var_scroll,
            command=lambda: self.load_write_settings(1), # Action 1 = save
            background="#696969", # Consider using style for consistency
            foreground="#ffffff",
            selectcolor="#26242f",
            border=1,
            anchor="w", # Align left
        )
        auto_scroll_check.pack(pady=5, fill=tk.X) # Fill horizontally
        # auto_scroll_check.select() # Default selection handled by _load_settings

        # Initialize tk.StringVar for algorithm selection, set default from constants
        # This is already done correctly based on previous diffs.
        self.var_algo = tk.StringVar(value=DEFAULT_SEARCH_ALGORITHM)

        algo_label_text = "Song Matching Algorithm:" # This label is static.
        self.algo_label = create_label(settings_frame, text=algo_label_text, anchor="w")
        self.algo_label.pack(pady=(10,0), fill=tk.X)

        # Create Radiobuttons for algorithm selection using constants
        for algo_key_const, display_name in SEARCH_ALGO_DISPLAY_NAMES.items():
            rb = ttk.Radiobutton(
                settings_frame,
                text=display_name,
                variable=self.var_algo,
                value=algo_key_const, # Use the constant itself (e.g., "exact") as the value
                command=lambda: self.load_write_settings(1) # Action 1 = save
            )
            rb.pack(anchor="w", pady=2, fill=tk.X)

        # Initial load of settings will set these correctly via self.root.after in __init__

    def redirector(self, input_str: str = "") -> None:
        """
        Redirects stdout to the Tkinter Text widget used for logging.

        This method is assigned to `sys.stdout.write` to capture print statements
        and display them in the GUI's log area. It ensures the Text widget is
        temporarily made normal (editable) to insert text and then disabled again
        to prevent user edits. It also auto-scrolls to the end if enabled in settings.

        Args:
            self: The instance of the class.
            input_str (str): The string to be inserted into the logs' widget.
        """
        self.logs.config(state=tk.NORMAL)
        self.logs.insert(tk.END, input_str)
        self.logs.config(state=tk.DISABLED)
        if self.var_scroll.get():
            self.logs.see(tk.END)

    def _execute_function_in_thread(self, func: Callable, args: tuple, error_title: str) -> None:
        """
        Wrapper to execute a function in a thread and handle exceptions.
        Updates self._thread_call_status with success/failure.
        """
        # Reset status for this call
        self._thread_call_status = {"success": False, "error": None, "error_title": error_title}
        try:
            func(*args)
            self._thread_call_status["success"] = True
        except (YTMAuthError, PlaylistLookupError, PlaylistCreationError,
                SongLookupError, SpotifyBackupError, OperationFailedError,
                FileNotFoundError, ValueError, IOError) as e: # Catch specific and common errors
            self._thread_call_status["error"] = e
            print(f"Error during '{error_title}': {e}") # Log to GUI console
        except Exception as e: # Catch any other unexpected errors
            self._thread_call_status["error"] = e
            print(f"An unexpected error occurred during '{error_title}': {e}")


    def _check_thread_status(self, thread: threading.Thread, next_tab: ttk.Frame) -> None:
        """
        Checks if the given thread is still running.
        If completed, it handles UI updates based on self._thread_call_status.
        Shows error messagebox if an error occurred, otherwise switches tab.
        """
        if thread.is_alive():
            self.root.after(100, lambda: self._check_thread_status(thread, next_tab))
        else:
            if self.root.winfo_exists(): # Check if GUI is still around
                if self._thread_call_status.get("success"):
                    self.tabControl.select(next_tab)
                    print()  # Add a newline for better log readability
                elif self._thread_call_status.get("error"):
                    error_title = self._thread_call_status.get("error_title", "Operation Failed")
                    error_message = str(self._thread_call_status["error"])
                    self.root.after(0, lambda: messagebox.showerror(error_title, error_message))
                # else: some unknown state or thread was cancelled before status set - do nothing.


    def call_func(self, func: Callable, args: tuple, next_tab: ttk.Frame, error_title: str = "Error") -> None:
        """
        Calls the given function in a separate thread.
        Manages tab switching and error display via _check_thread_status
        and self._thread_call_status.
        """
        # Pass error_title to the wrapper to be stored in self._thread_call_status
        thread = threading.Thread(target=self._execute_function_in_thread, args=(func, args, error_title))
        thread.start()
        self._check_thread_status(thread, next_tab)


    def _execute_yt_login_thread(self, auto: bool) -> None:
        """
        Executes the YouTube Music login process in a separate thread.

        Checks for an existing 'oauth.json' file. If not found and not in auto mode,
        it attempts to run the ytmusicapi oauth command in a new console window.
        Switches to the next tab upon completion or if manual login isn't required.

        Args:
            auto (bool): If True, attempts to log in automatically using existing
                         credentials. If False and no credentials found, prompts
                         for manual login.
        """
        if os.path.exists("oauth.json"):
            print("File detected, auto login")
        elif auto:
            print("No file detected. Manual login required")
            return
        else:
            print("File not detected, login required")

            # Open a new console window to run the command
            if os.name == "nt":  # If the OS is Windows
                try:
                    process = subprocess.Popen(
                        ["ytmusicapi", "oauth"],
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                    )
                    process.communicate() # Wait for the process to complete
                except FileNotFoundError:
                    messagebox.showerror(
                        "Error",
                        "Failed to run 'ytmusicapi oauth'. Is ytmusicapi installed and in your PATH?\n"
                        "You might need to run 'pip install ytmusicapi' or ensure the Python scripts directory is in your PATH.",
                        parent=self.root
                    )
                    return
                except Exception as e:
                    messagebox.showerror(
                        "Login Error",
                        f"An unexpected error occurred during 'ytmusicapi oauth': {e}",
                        parent=self.root
                    )
                    return
            else:  # For Unix and Linux
                try:
                    result = subprocess.run(
                        "python3 -m ytmusicapi oauth", # Consider using sys.executable for python interpreter
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        error_message = result.stderr or result.stdout # Sometimes errors go to stdout
                        messagebox.showerror(
                            "Login Error",
                            f"Error during 'ytmusicapi oauth':\n{error_message}\n"
                            "Ensure ytmusicapi is installed for Python 3 and accessible.",
                            parent=self.root
                        )
                        return
                    # print(result.stdout) # Optionally log success to GUI log, or remove if too verbose
                except Exception as e:
                    messagebox.showerror(
                        "Login Error",
                        f"An unexpected error occurred while trying to run 'ytmusicapi oauth': {e}",
                        parent=self.root
                    )
                    return

        self.tabControl.select(self.tab2)
        print()

    def yt_login(self, auto: bool = False) -> None:
        """
        Logs in to YT Music.

        If the oauth.json file is not found, it may open a new console window
        to run the 'ytmusicapi oauth' command, depending on the 'auto' flag.
        This operation is performed in a separate thread to keep the GUI responsive.

        Args:
            auto (bool, optional): Weather to automatically login using the
                                   oauth.json file. Defaults to False. If True,
                                   it will not attempt to open the oauth command
                                   if the file is missing.
        """
        # Run the function in a separate thread using the main call_func for consistency
        # However, yt_login has specific logic about not opening console if auto=true and no file.
        # For now, keep its original threading model but adapt error messages.
        # This function is called by root.after, not directly by a button with call_func.
        # A full refactor might integrate this into call_func as well.

        # Simplified: If _execute_yt_login_thread raises YTMAuthError, it will be caught by its caller
        # if it were using call_func. Since it's called directly, we handle its specific errors.
        try:
            if os.path.exists("oauth.json"):
                print("File detected, auto login")
            elif auto:
                print("No file detected. Manual login required during non-auto run.")
                return # Do not proceed with oauth popup if auto and no file
            else:
                print("File not detected, login required")
                if os.name == "nt":
                    try:
                        process = subprocess.Popen(["ytmusicapi", "oauth"], creationflags=subprocess.CREATE_NEW_CONSOLE)
                        process.communicate()
                    except FileNotFoundError:
                        raise YTMAuthError("Failed to run 'ytmusicapi oauth'. Is ytmusicapi installed and in PATH?")
                    except Exception as e:
                        raise YTMAuthError(f"Unexpected error during 'ytmusicapi oauth': {e}")
                else: # Unix/Linux
                    try:
                        result = subprocess.run("python3 -m ytmusicapi oauth", shell=True, capture_output=True, text=True)
                        if result.returncode != 0:
                            raise YTMAuthError(f"Error during 'ytmusicapi oauth': {result.stderr or result.stdout}")
                    except Exception as e:
                        raise YTMAuthError(f"Error running 'ytmusicapi oauth': {e}")

            # If successful or file existed
            if self.root.winfo_exists():
                 self.root.after(0, lambda: self.tabControl.select(self.tab2))
                 self.root.after(0, print) # Newline
        except YTMAuthError as e:
            if self.root.winfo_exists():
                self.root.after(0, lambda: messagebox.showerror("YT Music Login Failed", str(e)))
        except Exception as e: # Catch any other unexpected error from this logic
             if self.root.winfo_exists():
                self.root.after(0, lambda: messagebox.showerror("YT Music Login Error", f"An unexpected error occurred: {e}"))


    def yt_login(self, auto: bool = False) -> None:
        """
        Logs in to YT Music.
        Uses its own threading for now, but calls _execute_yt_login_thread which raises errors.
        The try-except is now inside _execute_yt_login_thread for errors it can handle directly.
        The call from __init__ with root.after needs to be mindful of this.

        Refined approach: The `self.root.after(1, lambda: self.yt_login(auto=True))`
        in `__init__` will run `yt_login`. `yt_login` starts a thread for `_execute_yt_login_thread`.
        `_execute_yt_login_thread` now has its own try-except for YTMAuthError and shows messagebox.
        """
        thread = threading.Thread(target=self._execute_yt_login_thread, args=(auto,))
        thread.start()
        # No call to _check_thread_status here as _execute_yt_login_thread handles its own UI outcome.

    def _load_settings(self) -> None:
        """Loads settings from the 'settings.json' file.

        If the file doesn't exist or is empty, default settings are applied.
        Updates the UI elements related to settings.
        """
        settings_file = "settings.json"
        # No need for the 'texts' dictionary here for algo_label anymore,
        # as the display names are directly on radio buttons.
        # The algo_label is now just a static "Song Matching Algorithm:"
        # However, if you wanted to display the *currently selected* algorithm's name
        # separately, you could update self.algo_label.config here.
        # The self.algo_label is static ("Song Matching Algorithm:").
        # The selected value is visually indicated by the selected radio button.

        processed_settings = DEFAULT_SETTINGS_VALUES.copy() # This now uses algo_name (string)

        try:
            with open(settings_file, "r") as f:
                file_content = f.read()
            # parse_settings_data handles backward compatibility for 'algo_number'
            processed_settings = parse_settings_data(file_content, DEFAULT_SETTINGS_VALUES.copy())
        except FileNotFoundError:
            print(f"Settings file '{settings_file}' not found. Attempting to create with default settings.")
            try:
                with open(settings_file, "w") as f:
                    json.dump(DEFAULT_SETTINGS_VALUES, f) # Save defaults (with string algo_name)
                print(f"Settings file '{settings_file}' created with default settings.")
            except IOError as e:
                messagebox.showwarning(
                    "Settings Warning",
                    f"Could not create settings file '{settings_file}': {e}\nDefault settings will be used.",
                    parent=self.root
                )

        self.var_scroll.set(processed_settings.get("auto_scroll", True))
        self.var_algo.set(processed_settings.get("algo_name", DEFAULT_SEARCH_ALGORITHM)) # Ensure var_algo gets a string

        self.root.update()

    def _save_settings(self) -> None:
        """Saves the current settings to the 'settings.json' file.

        Reads the current values from the UI elements and writes them to the file.
        """
        settings_file = "settings.json"

        settings_to_save = prepare_settings_for_save(
            self.var_scroll.get(),
            self.var_algo.get() # This is now a string
        )

        try:
            with open(settings_file, "w") as f:
                json.dump(settings_to_save, f)
        except IOError as e:
            messagebox.showerror(
                "Settings Error",
                f"Error saving settings to '{settings_file}': {e}",
                parent=self.root
            )

        # self.algo_label is static. No update needed here based on selection.
        self.root.update()

    def load_write_settings(self, action: int) -> None:
        """Loads or writes the settings to the settings.json file.

        Args:
            action (int): 0 to load the settings, 1 to write (save) the settings.
        """
        if action == 0:
            self._load_settings()
        else:
            self._save_settings()


def main() -> None:
    """
    The main entry point for the GUI application.
    Creates an instance of the Window class and starts the Tkinter main event loop.
    """
    ui = Window()
    ui.root.mainloop()


if __name__ == "__main__":
    main()
