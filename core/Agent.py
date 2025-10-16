from logging import getLogger as get_logger
from inspect import isawaitable
from datetime import datetime
from pathlib import Path
from typing import Any
import asyncio
import logging
import json
import sys
import os

from aiohttp import ClientSession
from dotenv import load_dotenv

from core.utils import get_snapshot
from tools.kit import gather_tools


load_dotenv()
_ENDPOINT = os.getenv("LLM_API_ENDPOINT")
_MODEL = os.getenv("LLM_API_MODEL")
_HEADERS = {"Authorization": f"Bearer {os.getenv('ZAI_API_KEY')}"}
_THINKING = "🧠"
_CONTENT = "🤖"
_TOOL_CALLS = "🛠️"


class Agent:
    def __init__(self, prompt: str, snap: bool):
        if snap:
            self.messages = [{"role": "system", "content": get_snapshot()}]
        else:
            self.messages = []
        self.messages.append({"role": "user", "content": prompt})
        self.log = get_logger(__name__)

        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"agent_{timestamp}.log"
        formatter = logging.Formatter(
            "%(asctime)s.%(msecs)03d T[%(threadName)10s] [%(levelname)8s] %(name)s: %(message)s (%(filename)s:%(lineno)s)"
        )
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(file_handler)
        self.log.addHandler(console_handler)

        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self._reader_transport: asyncio.ReadTransport | None = None
        self._writer_transport: asyncio.WriteTransport | None = None
        self.tools_schema, self.tools = gather_tools(self)

    @property
    def payload(self):
        return {
            "messages": self.messages,
            "stream": True,
            "tools": self.tools_schema,
            "tool_stream": True,
            "model": _MODEL,
        }

    async def __aenter__(self):
        self.reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(self.reader)
        loop = asyncio.get_running_loop()
        self._reader_transport, _ = await loop.connect_read_pipe(
            lambda: protocol, sys.stdin
        )
        self._writer_transport, _ = await loop.connect_write_pipe(
            lambda: asyncio.Protocol(), sys.stdout
        )
        self.writer = asyncio.StreamWriter(
            self._writer_transport, protocol, self.reader, loop
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.log.info(
            "__aexit__ exc_type[%s] exc_val[%s] exc_tb[%s]", exc_type, exc_val, exc_tb
        )
        self.reader.feed_eof()
        self._reader_transport.close()
        self._writer_transport.close()

    async def __call__(self):
        while True:
            response, n_tokens = await self.get_response()
            self.messages.append(response)
            while tool_calls := response.get("tool_calls"):
                for tc in tool_calls:
                    fn_name = tc["function"]["name"]
                    if fn := self.tools.get(fn_name):
                        kwargs = json.loads(tc["function"]["arguments"])
                        res = fn(**kwargs)
                        if isawaitable(res):
                            res = await res
                    else:
                        res = f"{fn_name} not in tools[{list(self.tools.keys())}]"
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "name": fn_name,
                            "content": str(res),
                        }
                    )
                response, n_tokens = await self.get_response()
                self.messages.append(response)

            prompt = await self.read(prefix=f"[{n_tokens}] > ")
            self.messages.append({"role": "user", "content": prompt})

    async def read(self, prefix=""):
        if prefix:
            await self.write(prefix)
        data: bytes = await self.reader.readline()
        return data.decode(encoding="utf-8")

    async def write(self, data: str | bytes):
        if isinstance(data, str):
            data = data.encode(encoding="utf-8")
        self.writer.write(data)
        await self.writer.drain()

    async def get_response(self) -> tuple[dict[str, Any], int]:
        self.log.debug("send payload[%s]", json.dumps(self.payload, indent=4))
        async with ClientSession() as session:
            async with session.post(
                _ENDPOINT, headers=_HEADERS, json=self.payload
            ) as resp:
                started_reasoning = False
                started_content = False
                started_tool_calls = False
                n_tokens = 0
                tool_call_index = -1
                message = {"role": "assistant"}

                async for chunk_bytes in resp.content:
                    self.log.debug("rcvd chunk_bytes[%s]", chunk_bytes)
                    chunk = chunk_bytes.decode("utf-8").rstrip()
                    if chunk.startswith("data: "):
                        chunk = chunk[6:]
                        if chunk == "[DONE]":
                            await self.write("\n\n")
                            self.log.debug(
                                "rcvd n_tokens[%s] resp[%s]",
                                n_tokens,
                                json.dumps(message, indent=4),
                            )
                            return message, n_tokens

                        chunk_json = json.loads(chunk)
                        choice = chunk_json["choices"][0]
                        if delta := choice.get("delta"):
                            if reasoning_content := delta.get("reasoning_content"):
                                if not started_reasoning:
                                    await self.write(f"{_THINKING} ")
                                    started_reasoning = True
                                    message["reasoning_content"] = reasoning_content
                                else:
                                    message["reasoning_content"] += reasoning_content
                                await self.write(reasoning_content)

                            elif (
                                content := delta.get("content", "\n")
                            ) != "\n" and content:
                                self.log.debug("delta content[%s]", content)
                                if not started_content:
                                    await self.write(f"\n\n{_CONTENT} ")
                                    started_content = True
                                    message["content"] = content
                                else:
                                    message["content"] += content
                                await self.write(content)

                            elif tool_calls := delta.get("tool_calls"):
                                tc = tool_calls[0]
                                args_data = tc["function"]["arguments"]
                                if not started_tool_calls:
                                    await self.write(f"\n\n{_TOOL_CALLS}  ")
                                    started_tool_calls = True
                                    message["tool_calls"] = []
                                if tc.get("id"):
                                    tool_call_index += 1
                                    if tool_call_index:
                                        await self.write(") ")

                                    message["tool_calls"].append(
                                        {
                                            "type": "function",
                                            "id": tc["id"],
                                            "function": {
                                                "name": tc["function"]["name"],
                                                "arguments": args_data,
                                            },
                                        }
                                    )
                                    await self.write(
                                        f"{tc['function']['name']}({args_data}"
                                    )
                                else:
                                    message["tool_calls"][tool_call_index]["function"][
                                        "arguments"
                                    ] += args_data
                                    await self.write(args_data)

                        if finish_reason := choice.get("finish_reason"):
                            if finish_reason == "tool_calls":
                                await self.write(")")
                            if timings := chunk_json.get("timings"):
                                n_tokens = (
                                    timings["cache_n"]
                                    + timings["prompt_n"]
                                    + timings["predicted_n"]
                                )
                            elif usage := chunk_json.get("usage"):
                                n_tokens = usage["total_tokens"]
