"""Client side of WoW's SRP6 login (matches CMaNGOS src/shared/Auth/SRP6.cpp).

All big numbers travel little-endian. The server hashes them at their natural
length (no trailing zero bytes), so we do the same to stay in sync.
"""
import hashlib
import os

N = int("894B645E89E1535BBDAD5B8B290650530801B18EBFBF5E8FAB3C82872A3E9BB7", 16)
G = 7


def sha1(*parts: bytes) -> bytes:
    h = hashlib.sha1()
    for p in parts:
        h.update(p)
    return h.digest()


def to_le(n: int, length: int | None = None) -> bytes:
    """Little-endian bytes; natural length (as BigNumber::AsByteArray()) unless given."""
    if length is None:
        length = max(1, (n.bit_length() + 7) // 8)
    return n.to_bytes(length, "little")


def from_le(b: bytes) -> int:
    return int.from_bytes(b, "little")


def interleave_session_key(S: int) -> bytes:
    """SRP6::HashSessionKey: SHA1 the even and odd bytes of S separately, interleave."""
    t = to_le(S, 32)
    even = sha1(t[0::2])
    odd = sha1(t[1::2])
    return bytes(b for pair in zip(even, odd) for b in pair)


class SRP6Client:
    def __init__(self, username: str, password: str):
        self.username = username.upper()
        self.password = password.upper()

    def process_challenge(self, B_bytes: bytes, salt_bytes: bytes):
        """Returns (A, M1) to send; keeps K for the world server handshake."""
        B = from_le(B_bytes)
        s = from_le(salt_bytes)
        if B % N == 0:
            raise ValueError("server sent invalid B")

        x = from_le(sha1(to_le(s), sha1(f"{self.username}:{self.password}".encode())))

        while True:
            a = from_le(os.urandom(19))
            A = pow(G, a, N)
            if A % N:
                break

        u = from_le(sha1(to_le(A), to_le(B)))
        S = pow((B - 3 * pow(G, x, N)) % N, a + u * x, N)
        K = interleave_session_key(S)

        ng = bytes(x ^ y for x, y in zip(sha1(to_le(N)), sha1(to_le(G))))
        M1 = sha1(ng, sha1(self.username.encode()), to_le(s), to_le(A), to_le(B), to_le(from_le(K)))

        self.A, self.M1, self.K = A, M1, from_le(K)
        return to_le(A, 32), M1

    def expected_server_proof(self) -> bytes:
        return sha1(to_le(self.A), to_le(from_le(self.M1)), to_le(self.K))
