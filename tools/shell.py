import asyncio

from tools.kit import tool


@tool(
    "Execute a shell command asynchronously and return the result",
    command="The shell command to execute",
    timeout="Optional timeout in seconds",
)
async def execute_shell_command(command: str, timeout: int = 30):
    """Execute a shell command asynchronously and return the result."""
    try:
        process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

        return {
            "returncode": process.returncode,
            "stdout": stdout.decode("utf-8").strip() if stdout else "",
            "stderr": stderr.decode("utf-8").strip() if stderr else "",
        }
    except TimeoutError:
        return {"stderr": f"Exceeded timeout[{timeout}s]"}
