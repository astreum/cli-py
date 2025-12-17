# cli-py

A Command-line interface for interacting with the Astreum blockchain written in Python.

```
 █████╗   █████╗  ████████╗ ██████╗  ███████╗ ██╗   ██╗ ███╗   ███╗
██╔══██╗ ██╔═══╝  ╚══██╔══╝ ██╔══██╗ ██╔════╝ ██║   ██║ ████╗ ████║
███████║ ╚█████╗     ██║    ██████╔╝ █████╗   ██║   ██║ ██╔████╔██║
██╔══██║  ╚═══██╗    ██║    ██╔══██╗ ██╔══╝   ██║   ██║ ██║╚██╔╝██║
██║  ██║ ██████╔╝    ██║    ██║  ██║ ███████╗ ╚██████╔╝ ██║ ╚═╝ ██║
╚═╝  ╚═╝ ╚═════╝     ╚═╝    ╚═╝  ╚═╝ ╚══════╝  ╚═════╝  ╚═╝     ╚═╝

 ██████╗  ██╗      ██╗
██╔════╝  ██║      ██║
██║       ██║      ██║
██║       ██║      ██║
╚██████╗  ███████╗ ██║
 ╚═════╝  ╚══════╝ ╚═╝

(c) Astreum Foundation
```

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
2. Activate the virtual environment:
   - macOS/Linux:
     ```bash
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

`cli-py` has three mutually exclusive modes (pick one):

- **TUI mode** (`--tui`): interactive terminal UI.
- **Evaluation mode** (`--eval`): evaluate Astreum language scripts / postfix expressions.
- **Headless mode** (`--headless`): run startup actions without launching the TUI (handy for automation).

Settings persist to `settings.json` in the app data directory:

- Windows: `%APPDATA%\Astreum\cli-py\settings.json`
- macOS/Linux: `$XDG_DATA_HOME/Astreum/cli-py/settings.json` (defaults to `~/.local/share/Astreum/cli-py/settings.json`)

### TUI mode
```bash
python main.py --tui
```

### Evaluation mode
Evaluate a postfix expression:
```bash
python main.py --eval --expr "(1 2 add)"
```

Evaluate a script file (default entry):
```bash
python main.py --eval --script "./script.aex"
```

Evaluate a script file with an explicit entry expression:
```bash
python main.py --eval --script "./add_script.aex" --expr "(a b main)"
```

### Headless mode
Run headless startup actions from the saved `cli.*` settings:
```bash
python main.py --headless
```

Override saved CLI and node settings for a single invocation with `--cli-*` / `--node-*` flags (works with `--tui`, `--eval`, or `--headless`; kebab-case maps to config keys; boolean flags default to `true` when no value is provided):
```bash
python main.py --headless --cli-on-startup-connect-node --cli-on-startup-validate-blockchain
```

Example overriding node settings:
```bash
python main.py --headless --node-verbose false --node-cold-storage-path "./atoms"
```
