# ai-flags

> [!WARNING]
> This project is no longer maintained. I'm now using [Raycast Snippets](https://manual.raycast.com/snippets) for storing prompt templates.

Parse and process Claude Code prompt flags to inject contextual instructions into AI conversations.

## Motivation

When working with Claude Code, you often want to give specific instructions that apply to certain tasks:

- "Remember to create a git commit when done" (`-c`)
- "Write comprehensive tests" (`-t`)
- "Delegate work to subagents" (`-s`)
- "Enable debugging mode" (`-d`)
- "Skip linting/type checking" (`-n`)

Instead of typing these instructions repeatedly, `ai-flags` lets you append short flags to your prompts. The tool runs
as a Claude Code hook, detecting flags and injecting the appropriate context automatically.

## Installation

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- [just](https://github.com/casey/just) command runner

### Install from source

```bash
# Clone the repository
git clone https://github.com/PaulRBerg/ai-flags.git
cd ai-flags

# Install globally with just
just install-cli

# Verify installation
ai-flags --version
```

**Note**: Claude Code hooks require global installation to make the `ai-flags` command available system-wide.

### Updating an existing installation

If you already have `ai-flags` installed and need to update to a newer version:

```bash
# Pull latest changes
git pull

# Reinstall with rebuild
just install-cli
```

The `install-cli` command automatically rebuilds the package from source.

## Usage

### CLI Mode

Process prompts directly from the command line:

```bash
# Single flag
ai-flags handle "implement feature -c"

# Multiple flags
ai-flags handle "implement feature -s -c -t"

# View what context would be added
ai-flags handle "debug issue -d"
```

Output shows detected flags, cleaned prompt, and the XML context that would be injected:

```
Detected flags: -c
Cleaned prompt: implement feature

Context to be added:
<commit_instructions>
IMPORTANT: After completing your task, use the SlashCommand tool to execute the '/commit' slash command to create a git commit.
</commit_instructions>
```

### Hook Mode

The primary use case is as a Claude Code `UserPromptSubmit` hook. When installed as a hook, it automatically processes
flags in your prompts.

**Hook installation** (in `~/.claude/hooks/UserPromptSubmit/detect_flags.py`):

```python
#!/usr/bin/env python3
import subprocess
import sys
import json

# Read hook input
hook_input = json.load(sys.stdin)

# Pass to ai-flags
result = subprocess.run(
    ["ai-flags", "handle"],
    input=json.dumps(hook_input),
    capture_output=True,
    text=True
)

# Output result
print(result.stdout)
```

When you submit a prompt like `"implement auth -s -c"`, the hook:

1. Detects flags `-s` and `-c`
2. Removes them from the visible prompt
3. Injects corresponding XML context into `additionalContext`
4. Claude receives both the clean prompt and the context

## Available Flags

| Flag | Name     | Description                                    | Permission Mode |
| ---- | -------- | ---------------------------------------------- | --------------- |
| `-s` | subagent | Delegate work to parallel/sequential subagents | `plan` only     |
| `-c` | commit   | Create git commit when done                    | Always          |
| `-t` | test     | Write comprehensive tests                      | Always          |
| `-d` | debug    | Enable systematic debugging                    | Always          |
| `-n` | no_lint  | Skip linting and type checking                 | Always          |

**Note:** The `-s` flag only activates in `plan` permission mode (when Claude is planning, not executing directly).

## Configuration

Configuration is stored in `~/.config/ai-flags/config.yaml`.

### View Configuration

```bash
ai-flags config show
```

Output:

```
AI Flags Configuration
==================================================
Config file: /Users/username/.config/ai-flags/config.yaml

-s (subagent  ): ✓ enabled
-c (commit    ): ✓ enabled
-t (test      ): ✓ enabled
-d (debug     ): ✓ enabled
-n (no_lint   ): ✓ enabled
```

### Enable/Disable Flags

```bash
# Disable a flag
ai-flags config set commit disabled

# Enable a flag
ai-flags config set test enabled

# Use short or long names
ai-flags config set s disabled
ai-flags config set subagent enabled
```

### Reset to Defaults

```bash
ai-flags config reset
```

### Edit Configuration File

```bash
ai-flags config edit
```

Opens `config.yaml` in your `$EDITOR`. Example configuration:

```yaml
subagent:
  enabled: true
  content: "Custom subagent instructions here"

commit:
  enabled: true
  content: "" # Empty = use default

test:
  enabled: false
  content: ""

debug:
  enabled: true
  content: "Custom debugging instructions"

no_lint:
  enabled: true
  content: ""
```

**Custom Content:** You can override the default instructions for any flag by setting `content` to a non-empty string.
Leave empty to use built-in defaults.

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/yourusername/ai-flags.git
cd ai-flags

# Install dependencies
uv sync

# Install development tools
uv tool install ruff
```

### Running Checks

The project uses `just` for task running:

```bash
# Run all checks (prettier, ruff, pyright, tests)
just full-check

# Individual checks
just prettier-check
just ruff-check
just pyright-check
just test

# Auto-fix formatting
just prettier-fix
just ruff-fix
```

### Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_cli.py -v

# Run with coverage
uv run pytest tests/ --cov=ai_flags --cov-report=term-missing
```

Test suite includes:

- 196 total tests
- Unit tests for each flag handler
- Integration tests for CLI and hook modes
- Config persistence and validation tests
- Parser and validator tests

### Architecture

```
src/ai_flags/
├── cli.py              # Click CLI commands and mode detection
├── parser.py           # Regex-based flag parsing
├── validator.py        # Flag validation against enabled flags
├── executor.py         # Flag handler execution and XML generation
├── output.py           # JSON/text output formatting
├── config.py           # Pydantic config models
├── config_loader.py    # Config file I/O
└── handlers/           # Flag-specific handlers
    ├── base.py         # Abstract FlagHandler base class
    ├── subagent.py     # -s handler
    ├── commit.py       # -c handler
    ├── test.py         # -t handler
    ├── debug.py        # -d handler
    └── no_lint.py      # -n handler
```

### Adding a New Flag

1. Create handler in `src/ai_flags/handlers/your_flag.py`:

```python
from ai_flags.handlers.base import FlagHandler

class YourFlagHandler(FlagHandler):
    def __init__(self, content: str = ""):
        self._content = content

    def get_flag_letter(self) -> str:
        return "x"  # Your flag letter

    def get_xml_tag(self) -> str:
        return "your_instructions"

    def get_content(self, permission_mode: str | None = None) -> str:
        if self._content:
            return self._content
        return "Default instructions here"
```

2. Add to `config.py` models
3. Add to `validator.py` RECOGNIZED_FLAGS
4. Add to `cli.py` `_build_handlers()`
5. Write tests in `tests/handlers/test_your_flag.py`

## License

MIT
