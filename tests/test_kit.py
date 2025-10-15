import pytest

from tools.kit import gather_tools


@pytest.mark.asyncio
async def test_crypto_tool():
    _, tools = gather_tools()
    assert "get_spot_pair_price" in tools
    tool = tools["get_spot_pair_price"]
    px = await tool("BTC-USD")
    assert px > 0


@pytest.mark.asyncio
async def test_shell_tool():
    _, tools = gather_tools()
    assert "execute_shell_command" in tools
    tool = tools["execute_shell_command"]
    res = await tool("echo 4")
    assert res["returncode"] == 0
    assert res["stdout"] == "4"
    assert res["stderr"] == ""
