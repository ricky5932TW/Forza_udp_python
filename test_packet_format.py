"""Tests and sample packet builder for the Horizon parser.

The fake packet helper is also useful for manual UDP checks:
    sender.sendto(fake_horizon_packet(), ("127.0.0.1", 9999))
"""

import struct
import unittest

from packet_format import (
    HORIZON_FIELDS,
    HORIZON_PACKET_SIZE,
    HORIZON_STRUCT_FORMAT,
    PacketSizeError,
    parse_horizon_packet,
)


def fake_horizon_packet() -> bytes:
    """Build one deterministic Horizon packet with a few recognizable values."""

    values = []
    for field in HORIZON_FIELDS:
        # Set the fields most likely to be checked by humans; fill the rest with
        # valid zero values for their struct type.
        if field.name == "IsRaceOn":
            values.append(1)
        elif field.name == "TimestampMS":
            values.append(123456)
        elif field.name == "CurrentEngineRpm":
            values.append(3456.5)
        elif field.name == "Speed":
            values.append(42.25)
        elif field.name == "Gear":
            values.append(4)
        elif field.name == "Accel":
            values.append(200)
        elif field.name == "Brake":
            values.append(12)
        elif field.name == "Steer":
            values.append(-8)
        elif field.data_type == "bytes12":
            values.append(bytes(range(12)))
        elif field.data_type in {"s32", "u32", "u16", "u8"}:
            values.append(0)
        elif field.data_type == "s8":
            values.append(0)
        else:
            values.append(0.0)

    return struct.pack(HORIZON_STRUCT_FORMAT, *values)


class HorizonPacketFormatTests(unittest.TestCase):
    def test_parse_fake_packet(self) -> None:
        packet = fake_horizon_packet()

        self.assertEqual(len(packet), HORIZON_PACKET_SIZE)
        telemetry = parse_horizon_packet(packet)

        self.assertEqual(telemetry["IsRaceOn"], 1)
        self.assertEqual(telemetry["TimestampMS"], 123456)
        self.assertAlmostEqual(telemetry["CurrentEngineRpm"], 3456.5)
        self.assertAlmostEqual(telemetry["Speed"], 42.25)
        self.assertEqual(telemetry["Gear"], 4)
        self.assertEqual(telemetry["Accel"], 200)
        self.assertEqual(telemetry["Brake"], 12)
        self.assertEqual(telemetry["Steer"], -8)
        self.assertEqual(telemetry["HorizonUnknownBytes"], "000102030405060708090a0b")

    def test_parse_packet_with_trailing_bytes(self) -> None:
        packet = fake_horizon_packet() + b"newer-version-extra-bytes"
        telemetry = parse_horizon_packet(packet)

        self.assertEqual(telemetry["IsRaceOn"], 1)
        self.assertAlmostEqual(telemetry["Speed"], 42.25)

    def test_short_packet_raises(self) -> None:
        with self.assertRaises(PacketSizeError):
            parse_horizon_packet(b"too short")


if __name__ == "__main__":
    unittest.main()
