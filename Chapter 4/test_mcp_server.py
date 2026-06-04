# chapter-04/test_mcp_server.py
# Tests the MCP server by simulating agent messages

import asyncio
import json
from mcp.client.stdio import stdio_client, get_default_parameters

async def test_server():
    """Send test messages to the MCP server and print responses."""
    
    # Connect to the server
    params = get_default_parameters("python", ["first_mcp_server.py"])
    async with stdio_client(params) as (read_stream, write_stream):
        # Send a "list tools" request
        list_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        write_stream.write(json.dumps(list_request).encode() + b"\n")
        
        # Read the response
        response = await read_stream.read()
        print("Tools available:")
        print(json.loads(response))
        
        # Send a "call tool" request for weather
        call_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_weather",
                "arguments": {"city": "Chicago"}
            }
        }
        write_stream.write(json.dumps(call_request).encode() + b"\n")
        
        response = await read_stream.read()
        print("\nWeather result:")
        print(json.loads(response))

if __name__ == "__main__":
    asyncio.run(test_server())
