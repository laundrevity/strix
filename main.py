import asyncio

import click

from core.Agent import Agent
from core.utils import create_default_system_prompt


async def main(prompt: str, snap: bool):
    # Create default system prompt if it doesn't exist
    create_default_system_prompt()
    
    async with Agent(prompt, snap) as agent:
        await agent()


@click.command()
@click.argument("prompt")
@click.option(
    "--snap", "-s", is_flag=True, help="Include project snapshot as system prompt"
)
def cli(prompt, snap):
    asyncio.run(main(prompt, snap))


if __name__ == "__main__":
    cli()
