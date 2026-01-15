# Flux Studio

A powerful, AI-integrated terminal-based markdown editor built with [Textual](https://textual.textualize.io/). Flux Studio combines the speed of Vim with modern AI capabilities to streamline technical writing, documentation, and content creation.

## Features

- **Textual-based TUI**: Beautiful, responsive terminal user interface with native mouse support.
- **AI Agent Integration**:
    - **Research Agent**: Gather context and information for your writing.
    - **Writing Agent**: Draft and expand content using AI.
    - **Review Agent**: Get actionable feedback and improvements.
- **Vim-like Command Palette**: Familiar commands for efficiency (e.g., `:w`, `:q`, `:agents`).
- **Project & Package Management**: Built on modern standards with `uv`.
- **Customizable**: Dark mode support and extensive configuration options.

## Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) package manager

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd flux-studio
```

2. Install dependencies:
```bash
uv sync
```

## Running the Application

### Using uv run (Recommended)

```bash
uv run flux-studio
```

### Key Bindings & Commands

| Key Binding | Command | Action |
|-------------|---------|--------|
| `Ctrl+N`    | `:new`  | Create a new file |
| `Ctrl+O`    | `:e <file>` | Open a file |
| `Ctrl+S`    | `:w`    | Save current file |
| `Ctrl+Shift+A` | `:agents` | Toggle AI Agent Panel |
| `Ctrl+P`    |         | Open Command Palette |
| `Ctrl+Q`    | `:q`    | Quit application |

## Development

### Project Structure

```
flux_studio/
├── app.py                      # Main application entry point
├── editor/                     # Core editor logic (MarkdownEditor)
├── agents/                     # Agent orchestration & registry
│   ├── agent_panel.py          # UI for interacting with agents
│   ├── agent_registry.py       # Agent management
│   └── ...
├── file_comm.py                # File communication utilities
└── ...
```

### Adding Dependencies

To add new dependencies:

```bash
uv add <package-name>
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
