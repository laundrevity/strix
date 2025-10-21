# Strix

Strix is an AI-powered agent framework that enables conversational interaction with language models through a command-line interface. It provides a extensible tool system for various operations including web search, shell commands, file editing, and cryptocurrency price tracking.

## Features

- **Conversational AI Agent**: Interactive chat interface with streaming responses
- **Extensible Tool System**: Modular tools for various operations
- **Project Snapshot**: Include project context in conversations
- **Multiple Built-in Tools**:
  - Web search via DuckDuckGo
  - Shell command execution
  - File creation and editing
  - Cryptocurrency price tracking
  - Git repository operations
- **Streaming Support**: Real-time response streaming with reasoning content
- **Enhanced Error Handling**: Robust error handling and user feedback
- **Logging**: Comprehensive logging with timestamps and structured output

## Installation

### Prerequisites

- Python 3.14 or higher
- An LLM API endpoint and credentials

### Setup

1. Clone or download the project
2. Install dependencies:
   ```bash
   uv sync --group dev
   ```

3. Set up environment variables:
   ```bash
   # Create a .env file with your API configuration
   LLM_API_ENDPOINT=https://your-api-endpoint.com/v1/chat/completions
   LLM_API_MODEL=your-model-name
   ZAI_API_KEY=your-api-key
   ```

## Usage

### Basic Usage

Run the agent with a prompt:
```bash
python main.py "Your prompt here"
```

### Include Project Snapshot

Include the entire project context as a system prompt:
```bash
python main.py "Analyze this codebase" --snap
```

### Command Line Options

- `prompt`: Required argument - the initial prompt to send to the agent
- `--snap, -s`: Optional flag - include project snapshot as system prompt
- `--help`: Show help message

## Built-in Tools

### Web Search
Search the web using DuckDuckGo and extract content from various sites:

```python
# Search with default 5 results
await web_search("python asyncio tutorial")

# Search with custom result count
await web_search("machine learning", k=10)
```

Special site handlers:
- **GitHub**: Extract README files or raw file content
- **Stack Overflow**: Extract questions and accepted answers
- **Reddit**: Extract posts and top comments

### Shell Commands
Execute shell commands asynchronously:

```python
# Execute a simple command
await execute_shell_command("echo 'Hello World'")

# Execute with custom timeout
await execute_shell_command("sleep 5", timeout=10)
```

### File Editing
Create or modify files with literal string replacement:

```python
# Create a new file
replace(
    file_path="/path/to/file.txt",
    old_string="",
    new_string="Hello World"
)

# Modify existing file
replace(
    file_path="/path/to/file.txt",
    old_string="Hello World",
    new_string="Hello Modified World",
    expected_replacements=1
)
```

### Cryptocurrency Prices
Get current cryptocurrency prices from Coinbase:

```python
# Get BTC-USD price
await get_spot_pair_price("BTC-USD")

# Get ETH-USD price
await get_spot_pair_price("ETH-USD")
```

## Architecture

### Core Components

- **Agent**: Main orchestrator handling conversation flow and tool execution
- **Tools**: Modular system for extensible functionality
- **Utils**: Utility functions for project snapshots and formatting

### Tool System

Tools are implemented using a decorator system that automatically generates JSON schemas:

```python
@tool(
    "Tool description",
    param1="Parameter description",
    param2="Another parameter description"
)
async def my_tool(param1: str, param2: int = 10):
    # Tool implementation
    return result
```

### Conversation Flow

1. User sends initial prompt
2. Agent constructs payload with tools and messages
3. LLM responds with streaming content
4. If tools are called, Agent executes them and sends results back
5. LLM provides final response
6. Loop continues for ongoing conversation

## Development

### Project Structure

```
strix/
├── core/
│   ├── Agent.py          # Main agent implementation
│   └── utils.py          # Utility functions
├── tools/
│   ├── kit.py            # Tool framework and utilities
│   ├── crypto.py         # Cryptocurrency price tool
│   ├── shell.py          # Shell command execution
│   ├── edit.py           # File editing tool
│   └── search.py         # Web search functionality
├── tests/
│   └── test_kit.py       # Tool tests
├── main.py               # CLI entry point
├── pyproject.toml        # Project configuration
└── README.md             # This file
```

### Adding New Tools

1. Create a new file in the `tools/` directory
2. Use the `@tool` decorator to define the tool:
   ```python
   from tools.kit import tool

   @tool("Your tool description", param1="Parameter description")
   async def your_tool(param1: str):
       # Implementation
       return result
   ```
3. Tools are automatically discovered and included

### Testing

Run tests with pytest:
```bash
uv run pytest -v
```

Tests cover:
- Tool functionality
- Error handling
- File operations
- Web search
- Shell execution

## Configuration

### Environment Variables

- `LLM_API_ENDPOINT`: Your LLM API endpoint URL
- `LLM_API_MODEL`: The model name to use
- `ZAI_API_KEY`: Your API authentication key

### Logging

Logs are written to:
- Console (INFO level and above)
- File in `logs/` directory (DEBUG level and above)

Log files are timestamped: `logs/agent_YYYYMMDD_HHMMSS.log`

## Example Usage

Here are some practical examples of how to use the Strix agent:

1. **Get cryptocurrency prices**:
   ```bash
   uv run main.py "What's the current price of Bitcoin?" --snap
   ```

2. **Search the web for information**:
   ```bash
   uv run main.py "Explain how asyncio works in Python" --snap
   ```

3. **Execute shell commands**:
   ```bash
   uv run main.py "List all Python files in this directory" --snap
   ```

4. **Create or modify files**:
   ```bash
   uv run main.py "Create a simple Python script that prints 'Hello, World!'" --snap
   ```
