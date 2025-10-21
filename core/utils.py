from pathlib import Path


META_FILES = ["README.md", "pyproject.toml"]


def _fmt_src(file: str | Path, base_dir: Path):
    if isinstance(file, str):
        relative_path = file
    else:
        relative_path = file.relative_to(base_dir)
    txt = f"--- {relative_path} ---\n```"
    with open(file, mode="r") as f:
        for line in f.readlines():
            txt += line
    txt += "```\n\n"
    return txt


def get_snapshot():
    root_dir = Path(__file__).parent.parent
    snap_txt = ""

    for file in META_FILES:
        snap_txt += _fmt_src(file, root_dir)

    for file in root_dir.rglob("*.py"):
        if ".venv" not in str(file):
            snap_txt += _fmt_src(file, root_dir)
    return snap_txt


def create_default_system_prompt():
    """Create a default system prompt file if it doesn't exist."""
    system_prompt_path = Path("system_prompt.txt")
    if not system_prompt_path.exists():
        default_prompt = """You are Strix, an AI-powered agent designed to help with development tasks.
You have access to various tools including:
- Web search capabilities
- Shell command execution
- File editing and creation
- Cryptocurrency price tracking
- Git repository operations

Your primary role is to assist with software development tasks by:
1. Understanding user requirements clearly
2. Breaking down complex tasks into manageable steps
3. Using appropriate tools to accomplish tasks
4. Providing clear explanations and code examples when needed
5. Ensuring all code modifications are accurate and follow best practices

When using tools:
- Always think through the steps before executing
- Use the most appropriate tool for the task
- Provide clear feedback about what you're doing
- Handle errors gracefully and suggest alternatives when tools fail

Remember to be helpful, precise, and maintain a professional tone while being approachable."""
        
        with open(system_prompt_path, "w") as f:
            f.write(default_prompt)
        print(f"Created default system prompt: {system_prompt_path}")
