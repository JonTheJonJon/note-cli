#!/usr/bin/env python3
"""
Note CLI - A Terminal User Interface for Managing Notes

A powerful command-line interface for browsing, searching, and managing notes
organized in a hierarchical folder structure. Features include:

- Tree view navigation with expandable folders
- Real-time search across folders and notes
- Create new notes in any folder
- Open notes in your preferred editor
- Manage search directories
- Support for .txt and .md files

Requirements:
    - Python 3.6+
    - prompt_toolkit: pip install prompt_toolkit

Usage:
    python main.py

Configuration:
    - Config file: ~/.notecli_config.json
    - Editor: Set via $EDITOR environment variable (defaults to vim)
    - Supported extensions: .txt, .md
"""

import os
import subprocess
import json
import time
from pathlib import Path
from typing import List, Set, Dict, Any, Optional, Tuple

# Third-party imports
from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

# --- Configuration Constants ---
CONFIG_FILE = Path(__file__).parent / "notecli_config.json"
DEFAULT_EDITOR = "vim"
NOTE_EXTENSIONS = [".txt", ".md"]

# --- Color Constants ---
class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

# --- Type Definitions ---
TreeItem = Tuple[str, Any, int]  # (type, item, indent_level)
AppState = Dict[str, Any]


def is_safe_path(base_path: Path, user_path: str) -> bool:
    """
    Validate that user path doesn't escape base directory.
    
    Args:
        base_path: The base directory that should contain the user path
        user_path: The user-provided path to validate
        
    Returns:
        True if the path is safe, False otherwise
    """
    try:
        # Resolve the full path to handle any symlinks or relative paths
        full_path = (base_path / user_path).resolve()
        # Check if the resolved path is within the base directory
        return base_path in full_path.parents or base_path == full_path
    except (ValueError, RuntimeError):
        return False


def validate_editor(editor: str) -> bool:
    """
    Validate editor command is safe.
    
    Args:
        editor: The editor command to validate
        
    Returns:
        True if the editor is allowed, False otherwise
    """
    # Whitelist of safe editors
    allowed_editors = [
        'vim', 'nvim', 'nano', 'code', 'subl', 'atom', 
        'notepad', 'notepad++', 'gedit', 'kate', 'mousepad'
    ]
    return editor.lower() in allowed_editors


def validate_filename(filename: str) -> bool:
    """
    Validate filename is safe.
    
    Args:
        filename: The filename to validate
        
    Returns:
        True if the filename is safe, False otherwise
    """
    # Dangerous extensions that could be executed
    dangerous_extensions = [
        '.exe', '.sh', '.bat', '.cmd', '.py', '.js', '.php', 
        '.rb', '.pl', '.ps1', '.vbs', '.jar', '.app'
    ]
    
    # Check for dangerous extensions
    if any(filename.lower().endswith(ext) for ext in dangerous_extensions):
        return False
    
    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    
    # Check for null bytes or other dangerous characters
    if '\x00' in filename:
        return False
    
    return True


def validate_folder_access(folder_path: Path) -> bool:
    """
    Validate folder is safe to access.
    
    Args:
        folder_path: The folder path to validate
        
    Returns:
        True if the folder is safe to access, False otherwise
    """
    try:
        resolved_path = folder_path.resolve()
        
        # List of sensitive system directories to avoid
        sensitive_dirs = [
            '/etc', '/var', '/usr', '/bin', '/sbin', '/root',
            '/boot', '/dev', '/proc', '/sys', '/tmp',
            'C:\\Windows', 'C:\\System32', 'C:\\Program Files'
        ]
        
        # Check if the path is in a sensitive directory
        for sensitive_dir in sensitive_dirs:
            if str(resolved_path).startswith(sensitive_dir):
                return False
        
        # Ensure the path is a directory and accessible
        return resolved_path.is_dir() and os.access(resolved_path, os.R_OK)
        
    except (ValueError, RuntimeError, OSError):
        return False


def clear_screen() -> None:
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def load_config() -> Dict[str, List[str]]:
    """
    Load configuration from JSON file.
    
    Returns:
        Dict containing configuration with 'folders' key listing search directories.
        Returns empty config if file doesn't exist or is invalid.
    """
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"folders": []}
    return {"folders": []}


def save_config(config: Dict[str, List[str]]) -> None:
    """
    Save configuration to JSON file.
    
    Args:
        config: Configuration dictionary to save
    """
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except IOError as e:
        print(f"Error saving config: {e}")


def get_editor() -> str:
    """
    Get the preferred text editor.
    
    Returns:
        Editor command from $EDITOR environment variable or DEFAULT_EDITOR
    """
    return os.environ.get("EDITOR", DEFAULT_EDITOR)


def find_notes(folders: List[str]) -> List[Path]:
    """
    Find all note files in the specified folders.
    
    Args:
        folders: List of folder paths to search
        
    Returns:
        List of Path objects for found note files, sorted alphabetically
    """
    notes = []
    for folder in folders:
        path = Path(folder).expanduser()
        
        # Security check: Validate folder access before scanning
        if not validate_folder_access(path):
            print(f"{Colors.YELLOW}Warning: Skipping unsafe folder '{folder}'{Colors.END}")
            continue
            
        if path.is_dir():
            try:
                for note_file in path.rglob("*"):
                    if note_file.is_file() and note_file.suffix.lower() in NOTE_EXTENSIONS:
                        notes.append(note_file)
            except (PermissionError, OSError) as e:
                print(f"{Colors.YELLOW}Warning: Cannot access folder '{folder}': {e}{Colors.END}")
                continue
    return sorted(notes, key=lambda x: x.name)


def open_note(note_path: Path) -> None:
    """
    Open a note file in the user's preferred editor.
    
    Args:
        note_path: Path to the note file to open
    """
    editor = get_editor()
    
    # Validate the editor command for security
    if not validate_editor(editor):
        print(f"{Colors.RED}Security Error: Editor '{editor}' is not in the allowed list.{Colors.END}")
        print(f"{Colors.YELLOW}Please set a safe editor in your $EDITOR environment variable.{Colors.END}")
        return
    
    try:
        subprocess.run([editor, str(note_path)], check=True)
    except FileNotFoundError:
        print(f"{Colors.RED}Error: Editor '{editor}' not found. Please check your $EDITOR environment variable.{Colors.END}")
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}Error opening note with {editor}: {e}{Colors.END}")


def create_new_note(folder_path: str, config: Dict[str, List[str]]) -> Optional[Path]:
    """
    Create a new note file in the specified folder.
    
    Args:
        folder_path: Relative path of the folder to create the note in
        config: Application configuration
        
    Returns:
        Path to the created file, or None if creation failed
    """
    # Find the absolute path of the folder
    absolute_folder_path = None
    for config_folder in config["folders"]:
        config_path = Path(config_folder).expanduser().resolve()
        try:
            # Validate that the folder_path doesn't escape the config folder
            if not is_safe_path(config_path, folder_path):
                print(f"{Colors.RED}Security Error: Invalid folder path '{folder_path}'{Colors.END}")
                return None
            
            absolute_folder_path = config_path / folder_path
            if absolute_folder_path.is_dir():
                break
        except ValueError:
            continue
    
    if not absolute_folder_path or not absolute_folder_path.is_dir():
        print(f"{Colors.RED}Error: Could not find folder '{folder_path}'{Colors.END}")
        return None
    
    # Get filename from user
    print(f'{Colors.YELLOW}Empty name will not create a file and go back to the main menu{Colors.END}')
    filename = input(f"Enter filename for new note in '{folder_path}': ").strip()
    if not filename:
        print(f"{Colors.YELLOW}No filename provided. Going back to the main menu.{Colors.END}")
        return None
    
    # Validate filename for security
    if not validate_filename(filename):
        print(f"{Colors.RED}Security Error: Invalid filename '{filename}'{Colors.END}")
        print(f"{Colors.YELLOW}Filename contains dangerous characters or extensions.{Colors.END}")
        return None
    
    # Add .md extension if no extension provided
    if not any(filename.endswith(ext) for ext in NOTE_EXTENSIONS):
        filename += ".md"
    
    # Create the full file path
    new_file_path = absolute_folder_path / filename
    
    # Check if file already exists
    if new_file_path.exists():
        print(f"{Colors.RED}Error: File '{filename}' already exists.{Colors.END}")
        return None
    
    # Create the file
    try:
        new_file_path.touch()
        print(f"{Colors.GREEN}Created new note: {filename}{Colors.END}")
        return new_file_path
    except Exception as e:
        print(f"{Colors.RED}Error creating file: {e}{Colors.END}")
        return None


def create_new_folder(parent_folder_path: str, config: Dict[str, List[str]]) -> Optional[Path]:
    """
    Create a new folder within the specified parent folder.
    
    Args:
        parent_folder_path: Relative path of the parent folder
        config: Application configuration
        
    Returns:
        Path to the created folder, or None if creation failed
    """
    # Find the absolute path of the parent folder
    absolute_parent_path = None
    for config_folder in config["folders"]:
        config_path = Path(config_folder).expanduser().resolve()
        try:
            # Validate that the parent_folder_path doesn't escape the config folder
            if not is_safe_path(config_path, parent_folder_path):
                print(f"{Colors.RED}Security Error: Invalid parent folder path '{parent_folder_path}'{Colors.END}")
                return None
            
            absolute_parent_path = config_path / parent_folder_path
            if absolute_parent_path.is_dir():
                break
        except ValueError:
            continue
    
    if not absolute_parent_path or not absolute_parent_path.is_dir():
        print(f"{Colors.RED}Error: Could not find parent folder '{parent_folder_path}'{Colors.END}")
        return None
    
    # Get folder name from user
    print(f'{Colors.YELLOW}Empty name will not create a folder and go back to the main menu{Colors.END}')
    folder_name = input(f"Enter name for new folder in '{parent_folder_path}': ").strip()
    if not folder_name:
        print(f"{Colors.YELLOW}No folder name provided. Going back to the main menu.{Colors.END}")
        return None
    
    # Validate folder name for security
    if not validate_filename(folder_name):
        print(f"{Colors.RED}Security Error: Invalid folder name '{folder_name}'{Colors.END}")
        print(f"{Colors.YELLOW}Folder name contains dangerous characters.{Colors.END}")
        return None
    
    # Create the full folder path
    new_folder_path = absolute_parent_path / folder_name
    
    # Check if folder already exists
    if new_folder_path.exists():
        print(f"{Colors.RED}Error: Folder '{folder_name}' already exists.{Colors.END}")
        return None
    
    # Create the folder
    try:
        new_folder_path.mkdir(parents=True, exist_ok=False)
        print(f"{Colors.GREEN}Created new folder: {new_folder_path}{Colors.END}")
        return new_folder_path
    except Exception as e:
        print(f"{Colors.RED}Error creating folder: {e}{Colors.END}")
        return None


def delete_file(note_path: Path, config: Dict[str, List[str]]) -> bool:
    """
    Delete a note file with confirmation.
    
    Args:
        note_path: Path to the note file to delete
        config: Application configuration
        
    Returns:
        True if file was deleted, False if cancelled or failed
    """
    # Security check: Ensure the file is within one of the configured folders
    file_is_safe = False
    for config_folder in config["folders"]:
        config_path = Path(config_folder).expanduser().resolve()
        try:
            if config_path in note_path.resolve().parents or config_path == note_path.resolve().parent:
                file_is_safe = True
                break
        except (ValueError, RuntimeError):
            continue
    
    if not file_is_safe:
        print(f"{Colors.RED}Security Error: Cannot delete file outside configured folders.{Colors.END}")
        return False
    
    print(f"{Colors.YELLOW}⚠️ You are about to delete the file:{Colors.END}")
    print(f"{Colors.RED}   {note_path}{Colors.END}")
    print(f"{Colors.YELLOW}This action cannot be undone!{Colors.END}\n")
    
    # Get confirmation from user
    confirm = input(f"{Colors.CYAN}Type 'DELETE' to confirm deletion: {Colors.END}").strip()
    
    if confirm != "DELETE":
        print(f"{Colors.YELLOW}Deletion cancelled.{Colors.END}")
        return False
    
    # Delete the file
    try:
        note_path.unlink()
        print(f"{Colors.GREEN}✓ File deleted successfully: {note_path.name}{Colors.END}")
        return True
    except Exception as e:
        print(f"{Colors.RED}✗ Error deleting file: {e}{Colors.END}")
        return False


def show_info() -> None:
    """Display comprehensive information about Note CLI."""
    info_text = f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗{Colors.END}
{Colors.CYAN}║                    {Colors.BOLD}Welcome to Note CLI{Colors.END}{Colors.CYAN}                       ║{Colors.END}
{Colors.CYAN}╚══════════════════════════════════════════════════════════════╝{Colors.END}

{Colors.GREEN}📝 A powerful command-line interface for managing your notes{Colors.END}

{Colors.YELLOW}NAVIGATION:{Colors.END}
  {Colors.CYAN}↑/↓ Arrow Keys{Colors.END}    Navigate through folders and notes
  {Colors.CYAN}→ Arrow Key{Colors.END}       Expand selected folder
  {Colors.CYAN}← Arrow Key{Colors.END}       Collapse selected folder
  {Colors.CYAN}Enter{Colors.END}             Toggle folder expansion/open note

{Colors.YELLOW}FILE OPERATIONS:{Colors.END}
  {Colors.CYAN}Ctrl-O{Colors.END}            Open selected note in editor
  {Colors.CYAN}Ctrl-N{Colors.END}            Create new note in selected folder
  {Colors.CYAN}Ctrl-F{Colors.END}            Create new folder in selected folder
  {Colors.CYAN}Ctrl-D{Colors.END}            Delete selected file

{Colors.YELLOW}FOLDER MANAGEMENT:{Colors.END}
  {Colors.CYAN}Ctrl-S{Colors.END}            Manage folders

{Colors.YELLOW}SEARCH:{Colors.END}
  Type in search bar to filter notes and folders
  Search works on both folder names and note names

{Colors.YELLOW}OTHER:{Colors.END}
  {Colors.CYAN}Ctrl-I{Colors.END}            Show this help
  {Colors.CYAN}Ctrl-C / Ctrl-Q{Colors.END}   Quit the application

{Colors.YELLOW}TIPS:{Colors.END}
  {Colors.GREEN}•{Colors.END} Empty folders are shown in the tree view
  {Colors.GREEN}•{Colors.END} Use arrow keys to navigate the folder structure
  {Colors.GREEN}•{Colors.END} Search automatically expands folders to show matches
  {Colors.GREEN}•{Colors.END} After editing a note, the CLI will restart automatically
  {Colors.GREEN}•{Colors.END} Configuration is saved in notecli_config.json in the same directory as the script

{Colors.PURPLE}Happy note-taking! 🚀{Colors.END}

{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗{Colors.END}
"""
    print(info_text)
    input(f"{Colors.CYAN}Press Enter to continue...{Colors.END}")


def manage_folders_menu(config: Dict[str, List[str]]) -> None:
    """
    Interactive menu for managing search folders.
    
    Args:
        config: Application configuration to modify
    """
    while True:
        print("\n" + "─" * 50)
        print("                    MANAGE FOLDERS")
        print("─" * 50)
        print("Current search folders:")
        
        if not config["folders"]:
            print("  (None)")
        else:
            for i, folder in enumerate(config["folders"], 1):
                print(f"  {i}: {folder}")

        print("\nOptions:")
        print("  (a) Add a folder")
        print("  (r) Remove a folder")
        print("  (b) Back to main menu")

        choice = input("\nEnter your choice: ").lower().strip()

        if choice == 'a':
            folder_path = input("Enter the absolute path of the folder to add: ").strip()
            if folder_path:
                expanded_path = Path(folder_path).expanduser()
                
                # Validate folder access for security
                if not validate_folder_access(expanded_path):
                    print(f"{Colors.RED}✗ Security Error: Folder '{folder_path}' is not safe to access.{Colors.END}")
                    print(f"{Colors.YELLOW}Please choose a folder in your home directory or a safe location.{Colors.END}")
                elif expanded_path.is_dir():
                    path_str = str(expanded_path.resolve())
                    if path_str not in config["folders"]:
                        config["folders"].append(path_str)
                        save_config(config)
                        print(f"{Colors.GREEN}✓ Folder '{path_str}' added successfully.{Colors.END}")
                    else:
                        print(f"{Colors.YELLOW}⚠ Folder already in the list.{Colors.END}")
                else:
                    print(f"{Colors.RED}✗ Error: Invalid folder path.{Colors.END}")
            else:
                print(f"{Colors.RED}✗ No path provided.{Colors.END}")
                
        elif choice == 'r':
            if not config["folders"]:
                print(f"{Colors.YELLOW}⚠ No folders to remove.{Colors.END}")
                continue
                
            try:
                folder_num = int(input("Enter the number of the folder to remove: "))
                if 1 <= folder_num <= len(config["folders"]):
                    removed_folder = config["folders"].pop(folder_num - 1)
                    save_config(config)
                    print(f"{Colors.GREEN}✓ Folder '{removed_folder}' removed successfully.{Colors.END}")
                else:
                    print(f"{Colors.RED}✗ Invalid folder number.{Colors.END}")
            except ValueError:
                print(f"{Colors.RED}✗ Invalid input. Please enter a number.{Colors.END}")
                
        elif choice == 'b':
            break
        else:
            print(f"{Colors.RED}✗ Invalid choice. Please try again.{Colors.END}")


class NoteCLI:
    """Main application class for the Note CLI."""
    
    def __init__(self):
        """Initialize the Note CLI application."""
        self.config = load_config()
        self.all_notes = find_notes(self.config["folders"])
        self.state: AppState = {
            "selected_index": 0,
            "filtered_notes": [],
            "note_to_open": None,
            "manage_folders": False,
            "create_file_in": None,
            "create_folder_in": None,
            "delete_file": None,
            "show_help": False,
            "expanded_folders": set(),
            "tree_items": []
        }
        self.kb = KeyBindings()
        self._setup_key_bindings()
        self._initialize_state()
    
    def _get_folders(self) -> List[str]:
        """
        Get all folders that contain notes or are empty.
        
        Returns:
            List of folder paths as strings
        """
        folders = set()
        
        # Add folders that contain notes
        for note in self.all_notes:
            for folder in self.config["folders"]:
                folder_path = Path(folder).expanduser().resolve()
                try:
                    relative_path = note.parent.relative_to(folder_path)
                    if relative_path:
                        folders.add(str(relative_path))
                        # Add all parent folders
                        path_parts = str(relative_path).split('/')
                        for i in range(1, len(path_parts)):
                            parent_folder = '/'.join(path_parts[:i])
                            folders.add(parent_folder)
                    break
                except ValueError:
                    continue
        
        # Add empty folders
        for folder in self.config["folders"]:
            folder_path = Path(folder).expanduser().resolve()
            if folder_path.is_dir():
                for root, dirs, files in os.walk(folder_path):
                    root_path = Path(root)
                    try:
                        relative_root = root_path.relative_to(folder_path)
                        if str(relative_root) != ".":
                            has_notes = any(Path(f).suffix.lower() in NOTE_EXTENSIONS for f in files)
                            if not has_notes:
                                folders.add(str(relative_root))
                                # Add parent folders
                                path_parts = str(relative_root).split('/')
                                for i in range(1, len(path_parts)):
                                    parent_folder = '/'.join(path_parts[:i])
                                    folders.add(parent_folder)
                    except ValueError:
                        continue
        
        return sorted(list(folders), key=lambda x: x)
    
    def _build_tree_items(self, folders: List[str], query: str = "") -> List[TreeItem]:
        """
        Build a tree structure of folders and their contents.
        
        Args:
            folders: List of folder paths
            query: Search query to filter results
            
        Returns:
            List of tree items (type, item, indent_level)
        """
        tree_items = []
        sorted_folders = sorted(folders, key=lambda x: x)
        
        for folder in sorted_folders:
            # Filter by search query
            if query and query not in folder.lower():
                continue
            
            # Check visibility based on parent expansion
            should_show = True
            if not query:
                folder_parts = folder.split('/')
                for i in range(1, len(folder_parts)):
                    parent_folder = '/'.join(folder_parts[:i])
                    if parent_folder in folders and parent_folder not in self.state["expanded_folders"]:
                        should_show = False
                        break
            
            if should_show:
                indent_level = folder.count('/') * 2
                tree_items.append(("folder", folder, indent_level))
                
                # Show folder contents if expanded or searching
                if folder in self.state["expanded_folders"] or query:
                    folder_notes = self._get_notes_in_folder(folder)
                    for note in sorted(folder_notes, key=lambda x: x.name):
                        if not query or query in note.name.lower():
                            tree_items.append(("note", note, indent_level + 2))
        
        return tree_items
    
    def _get_notes_in_folder(self, folder: str) -> List[Path]:
        """
        Get all notes in a specific folder.
        
        Args:
            folder: Folder path to search in
            
        Returns:
            List of note files in the folder
        """
        folder_notes = []
        for note in self.all_notes:
            for config_folder in self.config["folders"]:
                config_path = Path(config_folder).expanduser().resolve()
                try:
                    note_relative_path = note.parent.relative_to(config_path)
                    if str(note_relative_path) == folder:
                        folder_notes.append(note)
                        break
                except ValueError:
                    continue
        return folder_notes
    
    def _initialize_state(self) -> None:
        """Initialize the application state."""
        self.state["filtered_notes"] = self._get_folders()
        self.state["tree_items"] = self._build_tree_items(self.state["filtered_notes"])
    
    def _reset_state(self) -> None:
        """Reset the application state to initial values."""
        # Preserve expanded folders state
        expanded_folders = self.state.get("expanded_folders", set())
        
        self.state = {
            "selected_index": 0,
            "filtered_notes": [],
            "note_to_open": None,
            "manage_folders": False,
            "create_file_in": None,
            "create_folder_in": None,
            "delete_file": None,
            "show_help": False,
            "expanded_folders": expanded_folders,
            "tree_items": []
        }
        self._initialize_state()
    
    def _setup_key_bindings(self) -> None:
        """Set up all key bindings for the application."""
        
        # Quit commands
        @self.kb.add("c-c", eager=True)
        @self.kb.add("c-q", eager=True)
        def quit_app(event):
            """Quit the application."""
            event.app.exit()

        # No problematic key bindings - let the search buffer handle text editing normally

        # Navigation
        @self.kb.add("down")
        def move_down(event):
            """Move selection down."""
            if self.state["tree_items"]:
                self.state["selected_index"] = (self.state["selected_index"] + 1) % len(self.state["tree_items"])

        @self.kb.add("up")
        def move_up(event):
            """Move selection up."""
            if self.state["tree_items"]:
                self.state["selected_index"] = (self.state["selected_index"] - 1 + len(self.state["tree_items"])) % len(self.state["tree_items"])

        @self.kb.add("right")
        def expand_folder(event):
            """Expand the selected folder."""
            if self.state["tree_items"]:
                item_type, item, indent = self.state["tree_items"][self.state["selected_index"]]
                if item_type == "folder" and item not in self.state["expanded_folders"]:
                    self.state["expanded_folders"].add(item)
                    self.state["tree_items"] = self._build_tree_items(self.state["filtered_notes"])

        @self.kb.add("left")
        def collapse_folder(event):
            """Collapse the selected folder."""
            if self.state["tree_items"]:
                item_type, item, indent = self.state["tree_items"][self.state["selected_index"]]
                if item_type == "folder" and item in self.state["expanded_folders"]:
                    self.state["expanded_folders"].remove(item)
                    self.state["tree_items"] = self._build_tree_items(self.state["filtered_notes"])

        @self.kb.add("enter", eager=True)
        def toggle_or_open(event):
            """Toggle folder expansion or open note."""
            if self.state["tree_items"]:
                item_type, item, indent = self.state["tree_items"][self.state["selected_index"]]
                if item_type == "note":
                    self.state["note_to_open"] = item
                    event.app.exit()
                elif item_type == "folder":
                    if item in self.state["expanded_folders"]:
                        self.state["expanded_folders"].remove(item)
                    else:
                        self.state["expanded_folders"].add(item)
                    self.state["tree_items"] = self._build_tree_items(self.state["filtered_notes"])

        # File operations
        @self.kb.add("c-o")
        def open_note(event):
            """Open the selected note."""
            if self.state["tree_items"]:
                item_type, item, indent = self.state["tree_items"][self.state["selected_index"]]
                if item_type == "note":
                    self.state["note_to_open"] = item
                    event.app.exit()

        @self.kb.add("c-n")
        def create_note(event):
            """Create a new note in the selected folder."""
            if self.state["tree_items"]:
                item_type, item, indent = self.state["tree_items"][self.state["selected_index"]]
                if item_type == "folder":
                    self.state["create_file_in"] = item
                    event.app.exit()

        @self.kb.add("c-f")
        def create_folder(event):
            """Create a new folder within the selected folder."""
            if self.state["tree_items"]:
                item_type, item, indent = self.state["tree_items"][self.state["selected_index"]]
                if item_type == "folder":
                    self.state["create_folder_in"] = item
                    event.app.exit()

        @self.kb.add("c-d")
        def delete_file(event):
            """Delete the selected file."""
            if self.state["tree_items"]:
                item_type, item, indent = self.state["tree_items"][self.state["selected_index"]]
                if item_type == "note":
                    self.state["delete_file"] = item
                    event.app.exit()

        # Management and help
        @self.kb.add("c-s")
        def manage_folders(event):
            """Open folder management menu."""
            self.state["manage_folders"] = True
            event.app.exit()

        @self.kb.add("c-i")
        def show_help(event):
            """Show help information."""
            self.state["show_help"] = True
            event.app.exit()


    
    def _update_filtered_notes(self, buff: Buffer) -> None:
        """
        Update filtered notes when search text changes.
        
        Args:
            buff: Search buffer containing the query
        """
        query = buff.text.lower()
        self.state["filtered_notes"] = self._get_folders()
        self.state["tree_items"] = self._build_tree_items(self.state["filtered_notes"], query)
        self.state["selected_index"] = 0
    
    def _get_notes_text(self) -> List[Tuple[str, str]]:
        """
        Create formatted text for the notes list display.
        
        Returns:
            List of (style, text) tuples for display
        """
        result = []
        for i, (item_type, item, indent) in enumerate(self.state["tree_items"]):
            is_selected = i == self.state["selected_index"]
            indent_str = "  " * indent
            
            if item_type == "folder":
                style = "class:selected-folder" if is_selected else "class:folder"
                expand_indicator = "▼" if item in self.state["expanded_folders"] else "▶"
                # Show only the folder name (last part of the path)
                folder_name = item.split('/')[-1] if '/' in item else item
                result.append((style, f"{indent_str}{expand_indicator} 📁 {folder_name}"))
                result.append(("", "\n"))
            else:  # note
                style = "class:selected" if is_selected else ""
                result.append((style, f"{indent_str}  📄 {item.name}"))
                result.append(("", "\n"))
        
        if not self.state["tree_items"]:
            result.append(("", "No folders or notes found."))
        return result
    
    def _create_layout(self) -> Layout:
        """Create the application layout."""
        # Search buffer and window
        search_buffer = Buffer(on_text_changed=self._update_filtered_notes)
        search_window = Window(
            content=BufferControl(buffer=search_buffer),
            height=1,
            style="class:search-bar"
        )
        
        # Notes display window
        notes_window = Window(content=FormattedTextControl(self._get_notes_text))
        
        # Layout sections
        top_section = HSplit([
            Window(FormattedTextControl("Search Notes (Ctrl-C: quit, Ctrl-I: help):"), wrap_lines=True),
            search_window,
            Window(height=1, char='─'),
        ], height=Dimension(weight=7))
        
        bottom_section = HSplit([
            notes_window
        ], height=Dimension(weight=93))
        
        root_container = HSplit([top_section, bottom_section])
        return Layout(root_container, focused_element=search_window)
    
    def _create_style(self) -> Style:
        """Create the application styling."""
        return Style.from_dict({
            'search-bar': 'bg:#000000 #ffffff',
            'selected': 'bg:#0055aa #ffffff bold',
            'folder': 'fg:#00aa00 bold',
            'selected-folder': 'bg:#0055aa #ffffff bold',
        })
    
    def run(self) -> None:
        """Run the main application loop."""
        while True:
            layout = self._create_layout()
            style = self._create_style()
            
            app = Application(
                layout=layout,
                key_bindings=self.kb,
                full_screen=True,
                style=style
            )
            
            app.run()
            
            # Handle post-TUI actions
            if self.state["note_to_open"]:
                open_note(self.state["note_to_open"])
                self._reset_state()
            elif self.state["create_file_in"]:
                clear_screen()
                new_file = create_new_note(self.state["create_file_in"], self.config)
                if new_file:
                    print(f"{Colors.GREEN}{Colors.BOLD}✓ File created successfully!{Colors.END}")
                    print(f"{Colors.CYAN}Opening file in editor...{Colors.END}")
                    # Update the all_notes list to include the new file
                    self.all_notes = find_notes(self.config["folders"])
                    time.sleep(1)   
                    open_note(new_file)
                else:
                    print(f"{Colors.RED}{Colors.BOLD}✗ Failed to create file.{Colors.END}")
                    time.sleep(1)
                    input("Press Enter to return..")
                self._reset_state()
            elif self.state["create_folder_in"]:
                clear_screen()
                new_folder = create_new_folder(self.state["create_folder_in"], self.config)
                if new_folder:
                    print(f"{Colors.GREEN}{Colors.BOLD}✓ Folder created successfully!{Colors.END}")
                else:
                    print(f"{Colors.RED}{Colors.BOLD}✗ Failed to create folder.{Colors.END}")
                    time.sleep(1)
                    input("Press Enter to return..")
                self._reset_state()
            elif self.state["delete_file"]:
                clear_screen()
                file_deleted = delete_file(self.state["delete_file"], self.config)
                if file_deleted:
                    # Update the all_notes list to remove the deleted file
                    self.all_notes = find_notes(self.config["folders"])
                time.sleep(1)
                input("Press Enter to return..")
                self._reset_state()
            elif self.state["show_help"]:
                clear_screen()
                show_info()
                self._reset_state()
            elif self.state["manage_folders"]:
                clear_screen()
                manage_folders_menu(self.config)
                print(f"{Colors.GREEN}{Colors.BOLD}✓ Configuration updated.{Colors.END}")
                time.sleep(1)
                input("Press Enter to return..")
                self._reset_state()
            else:
                # No action to perform, exit the loop
                break

def main():
    """Main entry point for the Note CLI application."""
    try:
        # Show welcome screen
        clear_screen()
        show_info()
        
        cli = NoteCLI()
        cli.run()
    except KeyboardInterrupt:
        clear_screen()
        print("\n\nGoodbye! 👋")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please check your configuration and try again.")


if __name__ == "__main__":
    main()