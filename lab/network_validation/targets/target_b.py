from __future__ import annotations

import argparse
import asyncio
import json


async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    request = await reader.readuntil(b"\r\n\r\n")
    first = request.split(b"\r\n", 1)[0].decode("ascii", "replace").split()
    method, path = first[0], first[1]
    status = 403 if path.startswith(("/auth/", "/session")) else 404 if path.startswith(("/.env", "/admin")) else 200
    reason = {200: "OK", 403: "Forbidden", 404: "Not Found"}[status]
    body = json.dumps({"result": reason.lower(), "resource": path}).encode()
    writer.write(f"HTTP/1.1 {status} {reason}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode())
    if method != "HEAD":
        writer.write(body)
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def serve(port: int) -> None:
    server = await asyncio.start_server(handle, "0.0.0.0", port)
    async with server:
        await server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9080)
    args = parser.parse_args()
    asyncio.run(serve(args.port))


if __name__ == "__main__":
    main()
