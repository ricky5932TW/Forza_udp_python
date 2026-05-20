"""Minimal Forza Data Out UDP logger.

Run from a terminal or IDE:
    python main.py

Use from another Python module:
    from main import run_listener

    session_dir = run_listener(host="127.0.0.1", port=9999, max_packets=600)
"""

from __future__ import annotations

import csv
import json
import logging
import socket
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from packet_format import PacketSizeError, expected_packet_size, field_names, parse_packet


# Edit these defaults when running from an IDE without command-line arguments.
HOST = "0.0.0.0"
PORT = 9999
OUTPUT_DIR = "data"
QUIET = False
DEBUG = False

# Keep the format name explicit so later Motorsport/Sled/Dash support can reuse
# the same listener code.
PACKET_FORMAT = "horizon"
BUFFER_SIZE = 2048
FLUSH_EVERY_N_PACKETS = 60
LOG_EVERY_N_PACKETS = 300
SOCKET_TIMEOUT_SECONDS = 1.0

LOGGER_NAME = "forza_udp"


def make_session_dir(output_dir: str | Path) -> Path:
    """Create one timestamped folder for a recording session.

    Example:
        session_dir = make_session_dir("data")
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = Path(output_dir) / timestamp
    session_dir.mkdir(parents=True, exist_ok=False)
    return session_dir


def configure_logger(session_dir: Path, quiet: bool, debug: bool) -> logging.Logger:
    """Configure console/file logging for one session."""

    logger = logging.getLogger(LOGGER_NAME)
    # The module can be imported and run repeatedly in tests; clear old handlers
    # so messages do not duplicate across runs.
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    file_handler = logging.FileHandler(session_dir / "run.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if not quiet:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def close_logger(logger: logging.Logger) -> None:
    """Close handlers so Windows releases run.log immediately after a run."""

    for handler in list(logger.handlers):
        handler.flush()
        handler.close()
        logger.removeHandler(handler)


def now_iso() -> str:
    """Return a local timezone-aware timestamp for CSV/JSONL rows."""

    return datetime.now().astimezone().isoformat(timespec="microseconds")


def make_record(payload: bytes, received_time_ns: int, packet_format: str) -> dict[str, Any]:
    """Convert one UDP payload into one output row.

    Example:
        record = make_record(payload, time.time_ns(), "horizon")
        print(record["Speed"], record["received_time_ns"])
    """

    telemetry = parse_packet(payload, packet_format=packet_format)
    return {
        "received_time_ns": received_time_ns,
        "received_time_iso": now_iso(),
        "packet_size": len(payload),
        **telemetry,
    }


def run_listener(
    host: str = HOST,
    port: int = PORT,
    output_dir: str | Path = OUTPUT_DIR,
    packet_format: str = PACKET_FORMAT,
    quiet: bool = QUIET,
    debug: bool = DEBUG,
    max_packets: int | None = None,
) -> Path:
    """Listen for Forza UDP packets and write a session folder.

    ``max_packets`` is mainly for tests and local smoke checks. Leave it as
    ``None`` for normal logging, then stop with Ctrl+C.

    Example:
        run_listener(host="0.0.0.0", port=9999, output_dir="data")
    """

    session_dir = make_session_dir(output_dir)
    logger = configure_logger(session_dir, quiet=quiet, debug=debug)

    csv_path = session_dir / "telemetry.csv"
    jsonl_path = session_dir / "telemetry.jsonl"
    csv_fields = ["received_time_ns", "received_time_iso", "packet_size", *field_names(packet_format)]

    packet_count = 0
    skipped_count = 0

    logger.info("Forza UDP logger starting")
    logger.info("Packet format: %s", packet_format)
    logger.info("Expected minimum packet size: %d bytes", expected_packet_size(packet_format))
    logger.info("Listening on %s:%d", host, port)
    logger.info("Writing session files to %s", session_dir)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.bind((host, port))
            udp_socket.settimeout(SOCKET_TIMEOUT_SECONDS)

            with csv_path.open("w", newline="", encoding="utf-8") as csv_file, jsonl_path.open(
                "w", encoding="utf-8"
            ) as jsonl_file:
                csv_writer = csv.DictWriter(csv_file, fieldnames=csv_fields, extrasaction="ignore")
                csv_writer.writeheader()

                while True:
                    if max_packets is not None and packet_count >= max_packets:
                        logger.info("Reached max_packets=%d", max_packets)
                        break

                    try:
                        payload, address = udp_socket.recvfrom(BUFFER_SIZE)
                    except socket.timeout:
                        continue

                    received_time_ns = time.time_ns()
                    try:
                        record = make_record(payload, received_time_ns, packet_format)
                    except PacketSizeError as exc:
                        # A short packet is usually a wrong format/port or a
                        # partial test packet. Log it and keep the collector up.
                        skipped_count += 1
                        logger.warning("Skipping packet from %s:%d: %s", address[0], address[1], exc)
                        continue

                    csv_writer.writerow(record)
                    jsonl_file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

                    packet_count += 1
                    if packet_count % FLUSH_EVERY_N_PACKETS == 0:
                        # Periodic flush limits data loss if the process is
                        # killed without a clean KeyboardInterrupt.
                        csv_file.flush()
                        jsonl_file.flush()

                    if packet_count % LOG_EVERY_N_PACKETS == 0:
                        logger.info("Received %d packets, skipped %d", packet_count, skipped_count)

    except KeyboardInterrupt:
        logger.info("Stop requested by user")
    except OSError as exc:
        logger.exception("UDP listener failed: %s", exc)
        raise
    finally:
        logger.info("Stopped. Received %d packets, skipped %d", packet_count, skipped_count)
        close_logger(logger)

    return session_dir


def main() -> None:
    """Entry point for IDE Run and ``python main.py``."""

    run_listener()


if __name__ == "__main__":
    main()
