import asyncio
import json
from pathlib import Path
from typing import List, Optional

from tools.kit import tool


@tool(
    "Execute Git commands in the project repository",
    command="The Git command to execute (e.g., 'status', 'log --oneline', 'diff')",
    timeout="Optional timeout in seconds, defaults to 30",
)
async def git_command(command: str, timeout: int = 30) -> str:
    """
    Execute Git commands in the project repository.
    
    This tool executes Git commands securely within the project directory.
    Only specific Git commands are allowed for security reasons.
    
    Returns the output of the Git command or an error message.
    """
    try:
        # Change to project root directory to ensure we're in the right repo
        project_root = Path(__file__).parent.parent.resolve()
        
        # Validate command to prevent injection attacks
        allowed_commands = ['status', 'log', 'diff', 'show', 'branch', 'remote', 'config', 'pull', 'push']
        if not any(cmd in command.split()[0] for cmd in allowed_commands):
            return f"Error: Command '{command.split()[0]}' is not allowed for security reasons"
            
        # Execute the Git command
        process = await asyncio.create_subprocess_shell(
            f"git {command}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=project_root
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

        output = stdout.decode("utf-8").strip() if stdout else ""
        error = stderr.decode("utf-8").strip() if stderr else ""
        
        if process.returncode == 0:
            return output
        else:
            return f"Git command failed with return code {process.returncode}: {error}"
            
    except asyncio.TimeoutError:
        return f"Error: Git command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing Git command: {str(e)}"


@tool(
    "Get the current Git commit hash",
    short="Whether to return abbreviated commit hash (default: False)",
    timeout="Optional timeout in seconds, defaults to 30",
)
async def git_commit_hash(short: bool = False, timeout: int = 30) -> str:
    """
    Get the current Git commit hash.
    
    Returns the full or abbreviated commit hash depending on the 'short' parameter.
    """
    try:
        cmd = "git rev-parse" + (" --short" if short else "")
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        
        if process.returncode == 0:
            return stdout.decode("utf-8").strip()
        else:
            return f"Error getting commit hash: {stderr.decode('utf-8').strip()}"
            
    except asyncio.TimeoutError:
        return f"Error: Git command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error getting commit hash: {str(e)}"


@tool(
    "List Git branches",
    remote="Whether to list remote branches (default: False)",
    timeout="Optional timeout in seconds, defaults to 30",
)
async def git_branches(remote: bool = False, timeout: int = 30) -> str:
    """
    List Git branches in the repository.
    
    Returns branch information or an error message.
    If remote=True, lists both local and remote branches.
    """
    try:
        cmd = "git branch -a" if remote else "git branch"
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        
        if process.returncode == 0:
            return stdout.decode("utf-8").strip()
        else:
            return f"Error listing branches: {stderr.decode('utf-8').strip()}"
            
    except asyncio.TimeoutError:
        return f"Error: Git command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error listing branches: {str(e)}"


@tool(
    "Get Git repository information",
    timeout="Optional timeout in seconds, defaults to 30",
)
async def git_info(timeout: int = 30) -> str:
    """
    Get comprehensive Git repository information.
    
    Returns a JSON string with repository details including:
    - Current branch
    - Current commit hash
    - Origin repository URL
    - Repository status
    
    This is useful for understanding the current state of the repository.
    """
    try:
        # Get various Git information
        info = {}
        
        # Current branch
        process = await asyncio.create_subprocess_shell(
            "git rev-parse --abbrev-ref HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        if process.returncode == 0:
            info["branch"] = stdout.decode("utf-8").strip()
        
        # Current commit
        process = await asyncio.create_subprocess_shell(
            "git rev-parse HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        if process.returncode == 0:
            info["commit"] = stdout.decode("utf-8").strip()
        
        # Repository URL
        process = await asyncio.create_subprocess_shell(
            "git remote get-url origin",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        if process.returncode == 0:
            info["origin"] = stdout.decode("utf-8").strip()
        
        # Status
        process = await asyncio.create_subprocess_shell(
            "git status --porcelain",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        if process.returncode == 0:
            info["status"] = stdout.decode("utf-8").strip()
        
        return json.dumps(info, indent=2)
        
    except asyncio.TimeoutError:
        return f"Error: Git command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error getting Git info: {str(e)}"