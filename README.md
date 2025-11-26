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

Running `python main.py` with no flags launches the interactive TUI. Use `--eval` to enter evaluation mode:

### Start the TUI
```bash
python main.py
```

### Evaluate a postfix expression
```bash
python main.py --eval --expr "(1 2 add)"
```

### Evaluate a script file (default main entry)
```bash
python main.py --eval --script "./script.aex"
```

### Evaluate a script file with arguments for `main`
```bash
python main.py --eval --script "./add_script.aex" --expr "(a b main)"
```
