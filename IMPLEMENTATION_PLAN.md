# Flux Studio - Project Implementation Breakdown

AI-powered markdown editor for writing blog posts, tutorials, and documentation.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Phase 1: Core Editor](#phase-1-core-editor)
3. [Phase 2: Live Preview](#phase-2-live-preview)
4. [Phase 3: Plugin System](#phase-3-plugin-system)
5. [Phase 4: AI Assistance](#phase-4-ai-assistance)
6. [Phase 5: Agent Orchestrator](#phase-5-agent-orchestrator)
7. [Phase 6: Comment System](#phase-6-comment-system)
8. [Phase 7: Main App Integration](#phase-7-main-app-integration)
9. [Dependencies](#dependencies)

---

## Project Overview

### Target Architecture

```
src/flux_studio/
├── app.py                      # Main application
├── editor/                     # Core editor
├── preview/                    # Preview pane
├── ai/                         # AI assistance
├── plugins/                    # Plugin system
├── agents/                     # Agent orchestrator
├── comments/                   # Comment system
├── widgets/                    # Shared UI widgets
└── config/                     # Configuration
```

### Key Features

| Feature | Description |
|---------|-------------|
| Markdown Editor | Syntax highlighting, line numbers, file operations |
| Live Preview | Real-time markdown rendering, split-pane view |
| AI Assistance | Writing suggestions, completions, quick actions |
| Plugin System | Extensible architecture, user plugins |
| Agent Orchestrator | Research, writing, review agents |
| Comment System | User/agent comments, threading, persistence |

---

## Phase 1: Core Editor

### Files to Create

#### `src/flux_studio/editor/__init__.py`
- Empty init file

#### `src/flux_studio/editor/markdown_editor.py`

**Classes:**
```python
class EditorStatusBar(Static):
    """Status bar showing file name, modified state, cursor position, word count"""
    # Reactive properties: file_path, modified, cursor_position, word_count

class MarkdownEditor(Vertical):
    """Main editor widget"""
    # Contains: TextArea, EditorStatusBar
    # Messages: ContentChanged, FileLoaded, FileSaved
    # Methods: new_file(), load_file(path), save_file(path)
```

**Key Implementation Details:**
- Use Textual's `TextArea` widget with `show_line_numbers=True`
- Track modified state on content changes
- Post messages for app-level event handling

#### `src/flux_studio/editor/syntax_highlighter.py`

**Functions:**
```python
def highlight_markdown(text: str) -> Text:
    """Apply Rich styling to markdown text"""
    # Patterns: headers, bold, italic, code, links, lists, blockquotes

def get_line_type(line: str) -> str:
    """Determine line type: header, code, list, blockquote, hr, text"""
```

#### `src/flux_studio/editor/file_operations.py`

**Classes:**
```python
class RecentFilesManager:
    """Track recently opened files in ~/.flux-studio/recent_files.json"""
    # Methods: add(path), get_recent(), clear()

class AutoSaveManager:
    """Auto-save backups to ~/.flux-studio/backups/"""
    # Methods: create_backup(content, path), get_backups(), cleanup_old_backups()
```

### Verification
- [ ] Editor displays with line numbers
- [ ] Content changes trigger events
- [ ] File save/load works correctly
- [ ] Status bar updates on cursor move

---

## Phase 2: Live Preview

### Files to Create

#### `src/flux_studio/preview/__init__.py`
- Empty init file

#### `src/flux_studio/preview/markdown_parser.py`

**Classes/Functions:**
```python
class MarkdownDocument:
    """Parsed markdown document using Rich's Markdown renderer"""
    # Implements __rich_console__ for rendering

def parse_markdown(source: str) -> MarkdownDocument
def extract_frontmatter(source: str) -> tuple[dict | None, str]
def get_word_count(source: str) -> int
def get_reading_time(source: str, wpm=200) -> int
```

#### `src/flux_studio/preview/preview_pane.py`

**Classes:**
```python
class PreviewHeader(Static):
    """Header with word count and reading time"""

class PreviewContent(VerticalScroll):
    """Scrollable rendered markdown"""
    # Methods: update_content(markdown_source)

class PreviewPane(Static):
    """Main preview container"""
    # Reactive: content, visible
    # Methods: update_preview(markdown_source)
```

#### `src/flux_studio/widgets/split_view.py`

**Class:**
```python
class SplitView(Horizontal):
    """Left/right split pane with toggleable modes"""
    # Reactive: mode ("split", "editor", "preview")
    # Methods: toggle_preview(), cycle_mode()
    # CSS classes for hiding panes based on mode
```

### Verification
- [ ] Preview renders markdown correctly
- [ ] Split view toggles work
- [ ] Word count updates on content change

---

## Phase 3: Plugin System

### Files to Create

#### `src/flux_studio/plugins/__init__.py`

#### `src/flux_studio/plugins/plugin_base.py`

**Enums/Dataclasses:**
```python
class PluginState(Enum):
    UNLOADED, LOADED, ACTIVE, ERROR

@dataclass
class PluginMetadata:
    id, name, version, description, author, homepage, dependencies, tags

@dataclass
class PluginCommand:
    id, name, callback, keybinding, description
```

**Base Class:**
```python
class Plugin(ABC):
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata
    
    # Lifecycle hooks
    def on_load(self)
    def on_unload(self)
    def on_activate(self)
    def on_deactivate(self)
    
    # Document hooks
    def on_document_open(self, path)
    def on_document_save(self, path)
    def on_content_change(self, content)
    
    # Command registration
    def register_command(self, id, name, callback, keybinding=None)
```

#### `src/flux_studio/plugins/plugin_registry.py`

**Class:**
```python
class PluginRegistry:
    """Manages loaded plugins"""
    # Methods: register(plugin), unregister(id), get(id), get_all()
    # Methods: get_active(), get_by_tag(tag), get_all_commands()
```

#### `src/flux_studio/plugins/plugin_loader.py`

**Class:**
```python
class PluginLoader:
    """Discovers and loads plugins"""
    # Constructor: registry, user_plugin_dir (~/.flux-studio/plugins/)
    # Methods: load_builtin_plugins(app), load_user_plugins(app)
    # Methods: activate_plugin(id), deactivate_plugin(id), unload_plugin(id)
```

**Plugin Discovery:**
- Load from `~/.flux-studio/plugins/` directory
- Support single .py files and directories with `__init__.py`
- Find Plugin subclass in module

#### `src/flux_studio/plugins/plugin_manager.py`

**Classes:**
```python
class PluginCard(Static):
    """UI card for a plugin with toggle switch"""
    
class PluginManager(Static):
    """Plugin management panel"""
    # Lists all plugins with enable/disable toggles
```

### Verification
- [ ] Plugin registry stores plugins
- [ ] Plugin loader discovers user plugins
- [ ] Plugin manager UI shows plugins
- [ ] Plugin lifecycle hooks fire correctly

---

## Phase 4: AI Assistance

### Files to Create

#### `src/flux_studio/ai/__init__.py`

#### `src/flux_studio/ai/ai_service.py`

**Dataclasses:**
```python
@dataclass
class AIMessage:
    role: str  # "user", "assistant", "system"
    content: str

@dataclass
class AIRequest:
    messages: List[AIMessage]
    system_prompt: str | None
    max_tokens: int = 1000
    temperature: float = 0.7
    context: str | None  # Current document

@dataclass
class AIResponse:
    content: str
    finish_reason: str
    tokens_used: int
    cost_estimate: float

@dataclass
class AIStreamChunk:
    content: str
    is_final: bool
```

**Abstract Class:**
```python
class AIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str
    
    @abstractmethod
    async def complete(self, request: AIRequest) -> AIResponse
    
    @abstractmethod
    async def stream(self, request: AIRequest) -> AsyncIterator[AIStreamChunk]
    
    @abstractmethod
    def is_configured(self) -> bool
```

**Service Class:**
```python
class AIService:
    """Manages AI providers and conversation"""
    DEFAULT_SYSTEM_PROMPT = "..."  # Writing assistant prompt
    
    # Methods: register_provider(provider), set_active_provider(name)
    # Methods: get_available_providers(), get_configured_providers()
    # Methods: async ask(prompt, context), async stream_ask(prompt, context)
    # Methods: clear_conversation(), add_message(role, content)
```

#### `src/flux_studio/ai/providers/base_provider.py`

**Classes:**
```python
class MockProvider(AIProvider):
    """Always configured, returns placeholder responses"""

class OpenAIProvider(AIProvider):
    """OpenAI API - reads OPENAI_API_KEY from env"""
    # Requires: openai package

class AnthropicProvider(AIProvider):
    """Anthropic API - reads ANTHROPIC_API_KEY from env"""
    # Requires: anthropic package
```

#### `src/flux_studio/ai/ai_panel.py`

**Classes:**
```python
class ChatMessage(Static):
    """Single chat message display (user or assistant)"""

class QuickActionBar(Static):
    """Improve, Expand, Summarize, Review buttons"""
    # Message: ActionPressed(action)

class AIPanel(Static):
    """Chat interface with input and history"""
    # Messages: AIRequestSubmitted(prompt)
    # Methods: add_response(response), add_error(error), clear_chat()
```

### Verification
- [ ] MockProvider returns responses
- [ ] AIService manages conversation history
- [ ] AIPanel displays chat messages
- [ ] Quick actions send appropriate prompts

---

## Phase 5: Agent Orchestrator

### Files to Create

#### `src/flux_studio/agents/__init__.py`

#### `src/flux_studio/agents/agent_protocol.py`

**Enums/Dataclasses:**
```python
class AgentCapability(Enum):
    RESEARCH, WRITING, REVIEW, EDITING, SUMMARIZATION, TRANSLATION

class TaskStatus(Enum):
    PENDING, RUNNING, COMPLETED, FAILED, CANCELLED

class MessageType(Enum):
    REQUEST, RESPONSE, STATUS, ERROR, COMMENT

@dataclass
class AgentMessage:
    id, type, sender, recipient, content, timestamp, in_reply_to

@dataclass
class AgentTask:
    id, agent_id, description, context: dict
    status, result, error
    created_at, started_at, completed_at

@dataclass
class AgentInfo:
    id, name, description, capabilities: List[AgentCapability], version, author
```

**Base Class:**
```python
class Agent(ABC):
    @property
    @abstractmethod
    def info(self) -> AgentInfo
    
    @abstractmethod
    async def execute(self, task: AgentTask) -> Any
    
    # Optional streaming
    async def stream_execute(self, task) -> AsyncIterator[str]
    
    # Lifecycle
    def on_start(self), on_stop()
    def on_task_start(task), on_task_complete(task, result), on_task_error(task, error)
```

#### `src/flux_studio/agents/agent_registry.py`

**Class:**
```python
class AgentRegistry:
    # Methods: register(agent), unregister(id), get(id), get_all()
    # Methods: get_by_capability(capability), get_agent_info()
    # Methods: async dispatch_task(task), get_task_history(agent_id, status, limit)
```

#### `src/flux_studio/agents/builtins/research_agent.py`

**Class:**
```python
class ResearchAgent(Agent):
    """Web research and information gathering"""
    # Capabilities: RESEARCH, SUMMARIZATION
    # Returns: summary, findings[], suggestions[]
```

#### `src/flux_studio/agents/builtins/writing_agent.py`

**Class:**
```python
class WritingAgent(Agent):
    """Content drafting and expansion"""
    # Capabilities: WRITING, EDITING
    # Uses AIService if available
    # Returns: content, tokens_used
```

#### `src/flux_studio/agents/builtins/review_agent.py`

**Class:**
```python
class ReviewAgent(Agent):
    """Content review with actionable comments"""
    # Capabilities: REVIEW, EDITING
    # Returns: summary, score, comments[], improvements[]
    # Comments include: line, type, message, author
```

#### `src/flux_studio/agents/agent_panel.py`

**Classes:**
```python
class AgentCard(Static):
    """Displays agent info with 'Use Agent' button"""
    # Message: AgentSelected(agent_id)

class TaskCard(Static):
    """Displays task status with color coding"""

class AgentPanel(Static):
    """Agent orchestrator UI"""
    # Shows available agents, task queue, task input
    # Message: TaskSubmitted(agent_id, description)
```

### Verification
- [ ] Agents register correctly
- [ ] Task dispatch works
- [ ] Built-in agents return results
- [ ] Agent panel shows status

---

## Phase 6: Comment System

### Files to Create

#### `src/flux_studio/comments/__init__.py`

#### `src/flux_studio/comments/comment_model.py`

**Enums/Dataclasses:**
```python
class CommentType(Enum):
    ACTION_REQUIRED, SUGGESTION, INFO, RESOLVED

class CommentAuthorType(Enum):
    USER, AGENT

@dataclass
class CommentAuthor:
    id, name, type: CommentAuthorType
    @classmethod user(name="User")
    @classmethod agent(agent_id, agent_name)

@dataclass
class Comment:
    id, author, content, type
    created_at, updated_at
    start_line, end_line  # Optional, 1-indexed
    parent_id  # For threading
    assigned_to  # Agent ID
    resolved_at, resolved_by
    
    # Methods: resolve(resolver_id), update_content(new), assign_to_agent(agent_id)
    # Properties: is_thread_root, is_resolved, is_from_agent, has_line_range
    # Serialization: to_dict(), from_dict(data)

@dataclass
class CommentThread:
    root: Comment
    replies: List[Comment]
```

#### `src/flux_studio/comments/comment_manager.py`

**Class:**
```python
class CommentManager:
    """CRUD operations for comments"""
    # Storage: dict[doc_path, List[Comment]]
    
    # Query
    def get_comments(doc_path, type_filter, author_filter, include_resolved, line)
    def get_threads(doc_path) -> List[CommentThread]
    def get_lines_with_comments(doc_path) -> List[int]
    
    # Mutate
    def add_comment(doc_path, author, content, type, start_line, end_line, parent_id)
    def update_comment(doc_path, comment_id, new_content)
    def resolve_comment(doc_path, comment_id, resolver_id)
    def delete_comment(doc_path, comment_id)
    def assign_to_agent(doc_path, comment_id, agent_id)
    
    # Persistence: save as .md.comments.json alongside doc
    def save_comments(doc_path) -> Path
    def load_comments(doc_path) -> List[Comment]
    
    # Events
    def subscribe(callback), unsubscribe(callback)
```

#### `src/flux_studio/comments/comment_panel.py`

**Classes:**
```python
class CommentCard(Static):
    """Single comment with Reply/Resolve/Assign buttons"""
    # Messages: ResolveRequested, ReplyRequested, AssignRequested

class ThreadView(Static):
    """Root comment + indented replies"""

class CommentPanel(Static):
    """Comment management panel"""
    # Filter buttons: All, Action, Suggestions
    # Add comment input with type buttons
    # Message: CommentAdded(content, type)
```

### Verification
- [ ] Comments persist to file
- [ ] Thread structure works
- [ ] Filter by type works
- [ ] Resolve/assign works

---

## Phase 7: Main App Integration

### Files to Modify/Create

#### `src/flux_studio/config/settings.py`

**Dataclasses:**
```python
@dataclass
class EditorSettings:
    show_line_numbers, word_wrap, tab_size, auto_save, auto_save_interval

@dataclass
class PreviewSettings:
    enabled, sync_scroll, default_mode

@dataclass
class AISettings:
    default_provider, openai_api_key, anthropic_api_key, max_tokens, temperature

@dataclass
class Settings:
    editor, preview, ai, plugin_dir, theme
    # Methods: load(path), save(path)
```

#### `src/flux_studio/widgets/sidebar.py`

**Class:**
```python
class Sidebar(Static):
    """Collapsible right sidebar with tabbed panels"""
    # Reactive: collapsed
    # Methods: toggle(), show(), hide()
```

#### `src/flux_studio/app.py` (Modify Existing)

**App Structure:**
```python
class FluxStudioApp(App):
    # Initialize services
    def __init__(self):
        self.settings = Settings.load()
        self.ai_service = AIService()
        self.agent_registry = AgentRegistry()
        self.plugin_registry = PluginRegistry()
        self.plugin_loader = PluginLoader(...)
        self.comment_manager = CommentManager()
    
    # Setup
    def _setup_ai_providers(self)  # Register Mock, OpenAI, Anthropic
    def _setup_agents(self)  # Register Research, Writing, Review
    
    # Layout
    def compose(self):
        # Header
        # Main: SplitView(MarkdownEditor, PreviewPane)
        # Sidebar with TabbedContent: AI, Agents, Comments, Plugins
        # Footer
    
    # Event handlers
    def on_markdown_editor_content_changed(self, event)
    def on_markdown_editor_file_loaded(self, event)
    def on_markdown_editor_file_saved(self, event)
    async def on_ai_panel_ai_request_submitted(self, event)
    async def on_agent_panel_task_submitted(self, event)
    def on_comment_panel_comment_added(self, event)
    
    # Actions / Key bindings
    def action_toggle_preview(self)
    def action_toggle_sidebar(self)
    def action_focus_ai(self)
    def action_new(self)
    def action_save(self)
    def action_open(self)
```

**Key Bindings:**
| Key | Action |
|-----|--------|
| `Ctrl+S` | Save |
| `Ctrl+O` | Open |
| `Ctrl+N` | New |
| `Ctrl+P` | Toggle preview |
| `Ctrl+B` | Toggle sidebar |
| `Ctrl+Shift+A` | Focus AI |
| `Ctrl+Q` | Quit |

### Verification
- [ ] App starts without errors
- [ ] All panels accessible
- [ ] Editor ↔ Preview sync works
- [ ] Comments tied to current file
- [ ] Settings persist

---

## Dependencies

### pyproject.toml Updates

```toml
[project]
dependencies = [
    "textual>=0.40.0",
    "aiofiles>=23.2.0",
    "httpx>=0.26.0",
]

[project.optional-dependencies]
openai = ["openai>=1.0.0"]
anthropic = ["anthropic>=0.18.0"]
all = ["openai>=1.0.0", "anthropic>=0.18.0"]
dev = ["pytest>=8.0.0", "pytest-asyncio>=0.23.0"]
```

### Installation Commands

```bash
uv sync                    # Base install
uv sync --extra openai     # With OpenAI
uv sync --extra anthropic  # With Anthropic
uv sync --extra all        # All providers
```

---

## Implementation Order

| Phase | Estimated Effort | Dependencies |
|-------|------------------|--------------|
| 1. Core Editor | Medium | None |
| 2. Live Preview | Small | Phase 1 |
| 3. Plugin System | Medium | Phase 1 |
| 4. AI Assistance | Medium | None |
| 5. Agent Orchestrator | Medium | Phase 4 |
| 6. Comment System | Medium | Phase 5 |
| 7. Integration | Large | All phases |

> [!TIP]
> Start with Phase 1 and 2 to get a working editor, then add features incrementally.
