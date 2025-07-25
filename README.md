# Note CLI 📝

A powerful, secure, and user-friendly command-line interface for managing your notes with a beautiful tree view and real-time search capabilities.

## 🎉 **Complete Feature Set**

### **Core Functionality:**
- ✅ **Tree view navigation** with expandable/collapsible folders
- ✅ **Real-time search** across folders and notes
- ✅ **File operations** - Create, open, delete notes
- ✅ **Folder management** - Create folders, manage search directories
- ✅ **Auto-refresh** - Tree updates after file operations

### **User Experience:**
- ✅ **Beautiful welcome screen** with comprehensive help
- ✅ **Colored interface** throughout the application
- ✅ **Intuitive key bindings** (Ctrl-O, Ctrl-N, Ctrl-F, Ctrl-D, Ctrl-S, Ctrl-I)
- ✅ **Clear feedback** with success/error messages
- ✅ **Seamless workflow** from creation to editing

### **Security Features:**
- ✅ **Path traversal protection** - Prevents directory escape attacks
- ✅ **Editor validation** - Whitelist of safe editors
- ✅ **Filename validation** - Blocks dangerous extensions
- ✅ **Folder access control** - Protects sensitive system directories
- ✅ **Input sanitization** - All user inputs validated

### **Technical Excellence:**
- ✅ **Clean architecture** with OOP design
- ✅ **State management** with proper reset mechanisms
- ✅ **Error handling** throughout the application
- ✅ **Cross-platform compatibility**
- ✅ **Configuration persistence** in project directory

## 🚀 **Quick Start**

### Installation
1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install prompt_toolkit
   ```
3. Run the application:
   ```bash
   python main.py
   ```

### First Run
On first run, the application will prompt you to configure your note folders. These are the directories where your notes are stored.

## 🎮 **Usage**

### Navigation
- **↑/↓ Arrow Keys** - Navigate through folders and notes
- **→ Arrow Key** - Expand selected folder
- **← Arrow Key** - Collapse selected folder
- **Enter** - Toggle folder expansion/open note

### File Operations
- **Ctrl-O** - Open selected note in editor
- **Ctrl-N** - Create new note in selected folder
- **Ctrl-F** - Create new folder in selected folder
- **Ctrl-D** - Delete selected file (with confirmation)

### Folder Management
- **Ctrl-S** - Manage search folders

### Search
- Type in the search bar to filter notes and folders
- Search works on both folder names and note names
- Search automatically expands folders to show matches

### Other Commands
- **Ctrl-I** - Show comprehensive help
- **Ctrl-C / Ctrl-Q** - Quit the application

## 💡 **Tips**

- Empty folders are shown in the tree view
- Use arrow keys to navigate the folder structure
- Search automatically expands folders to show matches
- After editing a note, the CLI will restart automatically
- Configuration is saved in `notecli_config.json` in the same directory as the script

## 🔧 **Configuration**

The application stores its configuration in `notecli_config.json` in the project root. This file contains:
- List of folders to search for notes
- Your preferred text editor

### Example Configuration
```json
{
  "folders": [
    "~/Documents/notes",
    "~/Desktop/quick-notes"
  ],
  "editor": "code"
}
```

## 🛡️ **Security**

This application includes comprehensive security measures:

### Path Validation
- Prevents directory traversal attacks
- Validates all file and folder paths
- Ensures operations stay within configured directories

### Editor Security
- Whitelist of safe editor commands
- Prevents command injection attacks
- Validates editor before execution

### Input Sanitization
- Validates filenames for dangerous extensions
- Checks for null bytes and path separators
- Ensures safe folder access

## 🏗️ **Architecture**

The application is built using:
- **prompt_toolkit** - Terminal User Interface (TUI) framework
- **pathlib** - Object-oriented filesystem paths
- **OOP Design** - Clean, maintainable code structure
- **State Management** - Proper application state handling

### Key Components
- `NoteCLI` class - Main application logic
- Tree view system - Hierarchical folder/note display
- Search functionality - Real-time filtering
- File operations - Create, open, delete with validation
- Configuration management - Persistent settings

## 🐛 **Troubleshooting**

### Common Issues
1. **Editor not found** - Ensure your preferred editor is installed and in PATH
2. **Permission errors** - Check folder permissions for your note directories
3. **Configuration issues** - Delete `notecli_config.json` to reset configuration

### Getting Help
- Press `Ctrl-I` anytime for comprehensive help
- Check the welcome screen for quick start information

## 📝 **Development**

This project was developed iteratively with a focus on:
- User experience and intuitive design
- Security and input validation
- Clean, maintainable code
- Cross-platform compatibility

## 🎯 **Future Enhancements**

Potential features for future development:
- Note tagging and categorization
- Advanced search with regex support
- Note templates
- Export/import functionality
- Plugin system
- Cloud sync integration

---

**Happy note-taking! 🚀**

*Built with ❤️ using Python and prompt_toolkit* 