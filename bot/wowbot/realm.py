"""Login server (realmd) client: SRP6 authentication and realm list for build 2.4.3.8606."""
import asyncio
import struct
from dataclasses import dataclass

from .srp6 import SRP6Client

CMD_AUTH_LOGON_CHALLENGE = 0x00
CMD_AUTH_LOGON_PROOF = 0x01
CMD_REALM_LIST = 0x10

BUILD = 8606
VERSION = (2, 4, 3)


class AuthError(Exception):
    pass


@dataclass
class Realm:
    name: str
    host: str
    port: int
    flags: int
    characters: int


@dataclass
class LoginResult:
    account: str
    session_key: int
    realms: list[Realm]


def _cstr(data: bytes, pos: int) -> tuple[str, int]:
    end = data.index(b"\0", pos)
    return data[pos:end].decode(errors="replace"), end + 1


async def login(host: str, port: int, account: str, password: str) -> LoginResult:
    reader, writer = await asyncio.open_connection(host, port)
    try:
        srp = SRP6Client(account, password)
        name = srp.username.encode()

        # Logon challenge (sAuthLogonChallengeBody, reversed 4-char tags as the client sends them)
        body = (b"WoW\0" + bytes(VERSION) + struct.pack("<H", BUILD)
                + b"68x\0" + b"niW\0" + b"BGne"
                + struct.pack("<II", 0, 0x0100007F)
                + bytes([len(name)]) + name)
        writer.write(struct.pack("<BBH", CMD_AUTH_LOGON_CHALLENGE, 8, len(body)) + body)
        await writer.drain()

        cmd, _, error = await reader.readexactly(3)
        if error != 0:
            raise AuthError(f"logon challenge rejected, code 0x{error:02X}")
        B = await reader.readexactly(32)
        g_len = (await reader.readexactly(1))[0]
        await reader.readexactly(g_len)
        n_len = (await reader.readexactly(1))[0]
        await reader.readexactly(n_len)
        salt = await reader.readexactly(32)
        await reader.readexactly(16)                    # version challenge
        security_flags = (await reader.readexactly(1))[0]
        if security_flags:
            raise AuthError(f"account requires extra security (flags 0x{security_flags:02X})")

        # Logon proof: A, M1, crc (unchecked unless StrictVersionCheck), no keys, no security
        A, M1 = srp.process_challenge(B, salt)
        writer.write(bytes([CMD_AUTH_LOGON_PROOF]) + A + M1 + bytes(20) + b"\0\0")
        await writer.drain()

        cmd, error = await reader.readexactly(2)
        if error != 0:
            raise AuthError(f"wrong account or password (code 0x{error:02X})")
        M2 = await reader.readexactly(20)
        await reader.readexactly(4 + 4 + 2)             # account flags, survey id, unk flags
        if M2 != srp.expected_server_proof():
            raise AuthError("server proof mismatch")

        # Realm list
        writer.write(bytes([CMD_REALM_LIST]) + bytes(4))
        await writer.drain()
        cmd, size = struct.unpack("<BH", await reader.readexactly(3))
        data = await reader.readexactly(size)

        count, = struct.unpack_from("<H", data, 4)
        pos, realms = 6, []
        for _ in range(count):
            _icon, _lock, flags = data[pos:pos + 3]
            pos += 3
            rname, pos = _cstr(data, pos)
            address, pos = _cstr(data, pos)
            pos += 4                                    # population
            chars = data[pos]
            pos += 3                                    # chars, category, id
            if flags & 0x04:                            # REALM_FLAG_SPECIFYBUILD
                pos += 5
            rhost, _, rport = address.rpartition(":")
            realms.append(Realm(rname, rhost, int(rport), flags, chars))

        return LoginResult(srp.username, srp.K, realms)
    finally:
        writer.close()
