# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=2"]
# ///
"""Call the installed AgentCAD MCP server through its stdio interface."""
import asyncio
import base64
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
SERVER = r"C:\Program Files\FreeCAD-TW 1.2\Mod\Agent\mcp\server.py"


async def main():
    tool = sys.argv[1]
    if tool == "run_code" and len(sys.argv) == 3 and not sys.argv[2].startswith("{"):
        arguments = {"code": Path(sys.argv[2]).read_text(encoding="utf-8")}
    else:
        arguments = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    params = StdioServerParameters(command="uv", args=["run", "--script", SERVER])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments)
            image_index = 0
            for item in result.content:
                if item.type == "text":
                    print(item.text)
                elif item.type == "image":
                    view = arguments.get("views", ["isometric"])[image_index]
                    path = ROOT / "previews" / (view + ".png")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(base64.b64decode(item.data))
                    print(path)
                    image_index += 1
            if result.is_error:
                raise RuntimeError("AgentCAD MCP call failed")


if __name__ == "__main__":
    asyncio.run(main())
