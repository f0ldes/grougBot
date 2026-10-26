"""Milestone 1: log the bot in, create its character if needed, enter the world, print position.

    py hello.py                 # uses BOT_ACCOUNT / BOT_PASSWORD from server/.env
    py hello.py --name Grukk    # character name to use or create
"""
import argparse
import asyncio
import struct
from pathlib import Path

from wowbot import opcodes as op
from wowbot.realm import login
from wowbot.world import WorldConnection

ENV_FILE = Path(__file__).resolve().parent.parent / "server" / ".env"

RACE_ORC, CLASS_WARRIOR = 2, 1
CHAR_CREATE_SUCCESS = 0x2F


def load_env() -> dict[str, str]:
    env = {}
    for line in ENV_FILE.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and not key.startswith("#"):
            env[key.strip()] = value.strip()
    return env


def parse_char_enum(data: bytes) -> list[dict]:
    chars, pos = [], 1
    for _ in range(data[0]):
        guid, = struct.unpack_from("<Q", data, pos)
        end = data.index(b"\0", pos + 8)
        name = data[pos + 8:end].decode()
        pos = end + 1
        race, cls, _gender = data[pos:pos + 3]
        level = data[pos + 8]
        zone, map_id, x, y, z = struct.unpack_from("<IIfff", data, pos + 9)
        pos += 9 + 20                     # appearance+level, zone/map/xyz
        pos += 4 + 4 + 1 + 12             # guild, flags, first login, pet
        pos += 20 * 9                     # equipment slots
        chars.append(dict(guid=guid, name=name, race=race, cls=cls, level=level,
                          zone=zone, map=map_id, pos=(x, y, z)))
    return chars


async def wait_for(conn, *opcodes):
    while True:
        opcode, data = await conn.recv()
        if opcode in opcodes:
            return opcode, data


async def main(char_name: str):
    env = load_env()
    result = await login("127.0.0.1", 3724, env["BOT_ACCOUNT"], env["BOT_PASSWORD"])
    realm = result.realms[0]
    print(f"Logged in as {result.account}; realm '{realm.name}' at {realm.host}:{realm.port}")

    conn = await WorldConnection.connect(realm.host, realm.port, result.account, result.session_key)
    print("World server accepted the session")

    await conn.send(op.CMSG_CHAR_ENUM)
    _, data = await wait_for(conn, op.SMSG_CHAR_ENUM)
    chars = parse_char_enum(data)

    if not any(c["name"].lower() == char_name.lower() for c in chars):
        print(f"Creating orc warrior '{char_name}'...")
        payload = char_name.encode() + b"\0" + bytes([RACE_ORC, CLASS_WARRIOR, 0, 0, 0, 0, 0, 0, 0])
        await conn.send(op.CMSG_CHAR_CREATE, payload)
        _, data = await wait_for(conn, op.SMSG_CHAR_CREATE)
        if data[0] != CHAR_CREATE_SUCCESS:
            raise SystemExit(f"Character creation failed, code 0x{data[0]:02X} (name taken or invalid?)")
        await conn.send(op.CMSG_CHAR_ENUM)
        _, data = await wait_for(conn, op.SMSG_CHAR_ENUM)
        chars = parse_char_enum(data)

    char = next(c for c in chars if c["name"].lower() == char_name.lower())
    print(f"Entering world as {char['name']} (level {char['level']})...")
    await conn.send(op.CMSG_PLAYER_LOGIN, struct.pack("<Q", char["guid"]))

    opcode, data = await wait_for(conn, op.SMSG_LOGIN_VERIFY_WORLD, op.SMSG_CHARACTER_LOGIN_FAILED)
    if opcode == op.SMSG_CHARACTER_LOGIN_FAILED:
        raise SystemExit(f"Login failed, code 0x{data[0]:02X}")
    map_id, x, y, z, o = struct.unpack("<Iffff", data[:20])
    print(f"In the world! map={map_id} x={x:.2f} y={y:.2f} z={z:.2f} facing={o:.2f}")

    # Stay a few seconds so you can spot the bot in-game, showing what the server sends
    seen = {}
    try:
        async with asyncio.timeout(15):
            while True:
                opcode, _ = await conn.recv()
                seen[opcode] = seen.get(opcode, 0) + 1
    except TimeoutError:
        pass
    print("Packets received in 15s:", ", ".join(f"{op.NAMES.get(k, hex(k))}x{v}" for k, v in seen.items()))

    await conn.send(op.CMSG_LOGOUT_REQUEST)
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="Botgar")
    asyncio.run(main(parser.parse_args().name))
