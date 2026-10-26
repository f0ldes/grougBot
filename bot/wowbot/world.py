"""World server (mangosd) connection: auth session, header encryption, packet framing."""
import asyncio
import hashlib
import hmac
import os
import struct
import zlib

from . import opcodes as op
from .srp6 import to_le

BUILD = 8606
AUTH_OK = 0x0C

# AuthCrypt.cpp: header key = HMAC-SHA1(seed, K)
HEADER_KEY_SEED = bytes([0x38, 0xA7, 0x83, 0x15, 0xF8, 0x92, 0x25, 0x30,
                         0x71, 0x98, 0x67, 0xB1, 0x8C, 0x04, 0xE2, 0xAA])

# What a stock 2.4.3 client reports: one Blizzard addon with the standard key CRC
ADDON_INFO = b"Blizzard_AuctionUI\0" + struct.pack("<BII", 1, 0x4C1C776D, 0)


class HeaderCrypt:
    """Client-side mirror of AuthCrypt: we encrypt 6-byte sends, decrypt 4-byte receives."""

    def __init__(self, session_key: int):
        self.key = hmac.new(HEADER_KEY_SEED, to_le(session_key), hashlib.sha1).digest()
        self.send_i = self.send_j = self.recv_i = self.recv_j = 0

    def encrypt(self, header: bytes) -> bytes:
        out = bytearray()
        for b in header:
            x = ((b ^ self.key[self.send_i % len(self.key)]) + self.send_j) & 0xFF
            self.send_i += 1
            self.send_j = x
            out.append(x)
        return bytes(out)

    def decrypt(self, header: bytes) -> bytes:
        out = bytearray()
        for b in header:
            x = ((b - self.recv_j) & 0xFF) ^ self.key[self.recv_i % len(self.key)]
            self.recv_i += 1
            self.recv_j = b
            out.append(x)
        return bytes(out)


class WorldError(Exception):
    pass


class WorldConnection:
    def __init__(self, reader, writer, crypt=None):
        self.reader, self.writer, self.crypt = reader, writer, crypt

    @classmethod
    async def connect(cls, host: str, port: int, account: str, session_key: int):
        reader, writer = await asyncio.open_connection(host, port)
        conn = cls(reader, writer)

        opcode, data = await conn.recv()
        if opcode != op.SMSG_AUTH_CHALLENGE:
            raise WorldError(f"expected auth challenge, got 0x{opcode:03X}")
        server_seed = data[:4]

        client_seed = os.urandom(4)
        digest = hashlib.sha1(account.encode() + bytes(4) + client_seed + server_seed
                              + to_le(session_key)).digest()
        payload = (struct.pack("<II", BUILD, 0) + account.encode() + b"\0" + client_seed + digest
                   + struct.pack("<I", len(ADDON_INFO)) + zlib.compress(ADDON_INFO))
        await conn.send(op.CMSG_AUTH_SESSION, payload)

        conn.crypt = HeaderCrypt(session_key)        # everything after AUTH_SESSION is encrypted
        while True:
            opcode, data = await conn.recv()
            if opcode == op.SMSG_AUTH_RESPONSE:
                if data[0] != AUTH_OK:
                    raise WorldError(f"world auth rejected, code 0x{data[0]:02X}")
                return conn

    async def send(self, opcode: int, payload: bytes = b""):
        header = struct.pack(">H", len(payload) + 4) + struct.pack("<I", opcode)
        if self.crypt:
            header = self.crypt.encrypt(header)
        self.writer.write(header + payload)
        await self.writer.drain()

    async def recv(self) -> tuple[int, bytes]:
        header = await self.reader.readexactly(4)
        if self.crypt:
            header = self.crypt.decrypt(header)
        size, = struct.unpack(">H", header[:2])
        opcode, = struct.unpack("<H", header[2:])
        return opcode, await self.reader.readexactly(size - 2)

    def close(self):
        self.writer.close()
