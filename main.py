import asyncio

import click

from core.Agent import Agent


async def main(prompt: str, snap: bool):
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
