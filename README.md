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
   python -m venv venv
   ```
2. Activate the virtual environment:
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

`cli-py` has three mutually exclusive modes (pick one):

- **TUI mode** (`--tui`): interactive terminal UI.
- **Evaluation mode** (`--eval`): evaluate Astreum language scripts / postfix expressions.
- **Headless mode** (`--headless`): run startup actions without launching the TUI (handy for automation). Optionally start an HTTP API server with `--api-port`.

Settings persist to `settings.json` in the app data directory when saved from the TUI:

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
Run headless startup actions from saved `cli.*` settings (if present):
```bash
python main.py --headless
```

Override saved CLI and node settings for a single invocation with `--cli-*` / `--node-*` flags (works with `--tui`, `--eval`, or `--headless`; kebab-case maps to config keys; boolean flags default to `true` when no value is provided). `--node-default-seed` accepts a value; use `none` or `null` to clear the default seed for that run:
```bash
python main.py --headless --cli-on-startup-connect-node --cli-on-startup-validate-blockchain
```

Example overriding node settings:
```bash
python main.py --headless --node-verbose false --node-cold-storage-path "./atoms"
```

Disable the default seed:
```bash
python main.py --headless --node-default-seed none
```

### Headless + API server

Start the HTTP API server alongside headless mode on port 52781:

```bash
python main.py --headless --api-port 52781
```

Custom host:

```bash
python main.py --headless --api-port 52781 --api-host 0.0.0.0
```

Open `http://127.0.0.1:52781/docs` for the auto-generated Swagger UI to test all endpoints.

Available endpoints:

```
GET /expr/{id}                     Single expression by blake3 hash
GET /list/{id}                    Expr list chain from root hash
GET /chain/{chain_id}             Latest block for a chain (or null)
GET /block/{id}                   Full block by atom hash
GET /block/{id}/account/{addr}    Account state at a specific block
GET /transaction/{id}             Transaction by atom hash
GET /search                       Transaction search via bloom filters
```

### Transaction search

Search for transactions across bloom-filtered eras using `GET /search`:

```bash
# Search by sender
curl "http://127.0.0.1:52781/search?sender=0x..."

# Search by receiver
curl "http://127.0.0.1:52781/search?receiver=0x..."

# Search by tx hash
curl "http://127.0.0.1:52781/search?tx_hash=0x..."

# Search by key
curl "http://127.0.0.1:52781/search?key=0x..."

# Combine filters (at least one required)
curl "http://127.0.0.1:52781/search?sender=0x...&receiver=0x...&era_start=0&era_end=5"
```

Parameters are hex-encoded bytes. Returns a list of matching block hashes (bloom filter — may include false positives). Optional `era_start` (default 0) and `era_end` (default current era) control the search range.
