"""Pure-Python CRC-32C fallback for the Alibaba FC deployment package.

The upstream ``crc32c`` wheel contains a native extension.  Function Compute
does not load that extension reliably from this ZIP deployment, so we provide
the small compatible API required by the Tablestore SDK.
"""

from __future__ import annotations


def _make_table() -> tuple[int, ...]:
    polynomial = 0x82F63B78  # Reflected Castagnoli polynomial.
    values: list[int] = []
    for index in range(256):
        value = index
        for _ in range(8):
            value = (value >> 1) ^ polynomial if value & 1 else value >> 1
        values.append(value & 0xFFFFFFFF)
    return tuple(values)


_TABLE = _make_table()


def crc32c(data: bytes | bytearray | memoryview, crc: int = 0) -> int:
    """Return the unsigned CRC-32C checksum, matching ``crc32c.crc32c``."""
    value = crc ^ 0xFFFFFFFF
    for byte in memoryview(data).cast("B"):
        value = _TABLE[(value ^ byte) & 0xFF] ^ (value >> 8)
    return (value ^ 0xFFFFFFFF) & 0xFFFFFFFF
