"""Minimal allowlisted UDP DNS responder for observable laboratory traffic."""
from __future__ import annotations

import socket
import struct


ALLOWED = {"target-web", "target-api", "control-api", "target-ssh-sim"}


def question_name(packet: bytes) -> tuple[str, int]:
    labels = []
    offset = 12
    while offset < len(packet):
        length = packet[offset]
        offset += 1
        if length == 0:
            break
        if length > 63 or offset + length > len(packet):
            raise ValueError("invalid DNS question")
        labels.append(packet[offset:offset + length].decode("ascii"))
        offset += length
    return ".".join(labels), offset + 4


def response(packet: bytes) -> bytes:
    if len(packet) < 16:
        raise ValueError("short DNS packet")
    name, question_end = question_name(packet)
    question = packet[12:question_end]
    if name in ALLOWED:
        address = socket.gethostbyname(name)
        header = packet[:2] + struct.pack("!HHHHH", 0x8180, 1, 1, 0, 0)
        answer = b"\xc0\x0c" + struct.pack("!HHIH", 1, 1, 30, 4) + socket.inet_aton(address)
        return header + question + answer
    header = packet[:2] + struct.pack("!HHHHH", 0x8183, 1, 0, 0, 0)
    return header + question


def main() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("0.0.0.0", 53))
    while True:
        packet, peer = server.recvfrom(512)
        try:
            server.sendto(response(packet), peer)
        except (OSError, ValueError, UnicodeError):
            continue


if __name__ == "__main__":
    main()
