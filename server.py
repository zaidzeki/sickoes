#!/usr/bin/env python3
import asyncio
import logging
import os
import socket
import ssl
os.system('pip install websockets')
import websockets


class CustomWriter:
    def __init__(self, socket) -> None:
        self.socket = socket

    async def write(self, data):
        """
        Overrides the default write method to print the data before writing it.
        """
        await self.socket.send(data)

    async def drain(self):
        """
        Overrides the default drain method to ensure all data is printed before flushing.
        """
        pass


class CustomReader:
    def __init__(self, socket) -> None:
        self.socket = socket

    async def read(self, size):
        return await self.socket.recv()


async def handle_stream_pair(reader, writer):
    while True:
        data = await reader.read(4096 * 10)
        if not data:
            break
        written = writer.write(data)
        if written is not None:
            await written
        await writer.drain()


async def backend_handler(
    host: str,
    port: int,
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
) -> None:
    try:
        # Connect to the target server

        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        try:
            remote_reader, remote_writer = await asyncio.open_connection(host, port, ssl=context)
        except ssl.SSLError:
            remote_reader, remote_writer = await asyncio.open_connection(host, port)

        tasks = [
            asyncio.ensure_future(handle_stream_pair(client_reader, remote_writer)),
            asyncio.ensure_future(handle_stream_pair(remote_reader, client_writer)),
        ]

        await asyncio.gather(*tasks)
    except Exception as e:
        logging.exception(e)
    finally:
        # Always close connections even on errors
        remote_writer.close()
        await remote_writer.wait_closed()


async def handle_connection(websocket, path):
    # Extract relevant part of the URI (assuming path starts with '/')
    uri_data = path.lstrip("/")

    try:
        # Split based on a single colon (':') to handle potential colons in domain names
        host, port = uri_data.split(":")
        print(f"Received connection for: {host} on port {port}")
        await backend_handler(
            host, port, CustomReader(websocket), CustomWriter(websocket)
        )
    except ValueError as e:
        logging.exception(e)
        return


async def main():
    async with websockets.serve(handle_connection, os.environ.get('IP', '0.0.0.0'), os.environ.get('PORT', 10000)):
        await asyncio.Future()  # serve forever


if __name__ == "__main__":
    asyncio.run(main())
