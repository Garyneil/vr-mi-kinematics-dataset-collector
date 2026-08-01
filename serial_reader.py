"""Serial reader for synchronized 8-channel EEG and 4-channel ECG frames."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterator, List, Optional

try:
    import serial
except ImportError:  # pragma: no cover
    serial = None


@dataclass(frozen=True)
class SignalSample:
    host_timestamp: float
    packet_id: Optional[int]
    dropped_before: int
    eeg: List[float]
    ecg: List[float]


class SerialSignalReader:
    """Read either legacy26 or counter30 framed serial samples.

    legacy26:
        uint8 header + 12 x int16 big-endian + uint8 tail

    counter30:
        uint8 header + uint32 packet_id big-endian +
        12 x int16 big-endian + uint8 tail
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout_sec: float = 1.0,
        frame_mode: str = "legacy26",
        header: int = 255,
        tail: int = 254,
        sampling_rate_hz: float = 250.0,
        eeg_channels: int = 8,
        ecg_channels: int = 4,
        eeg_scale: float = 1.0,
        ecg_scale: float = 1.0,
    ) -> None:
        if serial is None:
            raise ImportError("pyserial is required: pip install pyserial")
        if frame_mode not in {"legacy26", "counter30"}:
            raise ValueError("frame_mode must be 'legacy26' or 'counter30'")
        self.port = port
        self.baudrate = int(baudrate)
        self.timeout_sec = float(timeout_sec)
        self.frame_mode = frame_mode
        self.header = int(header)
        self.tail = int(tail)
        self.fs = float(sampling_rate_hz)
        self.eeg_channels = int(eeg_channels)
        self.ecg_channels = int(ecg_channels)
        self.total_channels = self.eeg_channels + self.ecg_channels
        self.eeg_scale = float(eeg_scale)
        self.ecg_scale = float(ecg_scale)
        self.packet_bytes = 4 if frame_mode == "counter30" else 0
        self.payload_bytes = self.total_channels * 2
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout_sec,
        )
        self._previous_packet_id: Optional[int] = None
        self._start_monotonic = time.monotonic()

    def close(self) -> None:
        if self.ser and self.ser.is_open:
            self.ser.close()

    def __enter__(self) -> "SerialSignalReader":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def _read_exact(self, size: int) -> bytes:
        data = self.ser.read(size)
        if len(data) != size:
            raise TimeoutError(f"Expected {size} serial bytes, received {len(data)}")
        return data

    def _read_frame(self) -> tuple[Optional[int], bytes]:
        while True:
            first = self.ser.read(1)
            if not first:
                continue
            if first[0] != self.header:
                continue

            packet_id: Optional[int] = None
            if self.frame_mode == "counter30":
                packet_id = int.from_bytes(self._read_exact(4), "big", signed=False)

            payload = self._read_exact(self.payload_bytes)
            frame_tail = self._read_exact(1)
            if frame_tail[0] == self.tail:
                return packet_id, payload

    def _decode_channels(self, payload: bytes) -> tuple[List[float], List[float]]:
        values: List[float] = []
        for index in range(self.total_channels):
            start = index * 2
            raw = int.from_bytes(payload[start:start + 2], "big", signed=True)
            scale = self.eeg_scale if index < self.eeg_channels else self.ecg_scale
            values.append(raw * scale)
        return values[: self.eeg_channels], values[self.eeg_channels :]

    def _count_dropped(self, packet_id: Optional[int]) -> int:
        if packet_id is None:
            return 0
        dropped = 0
        if self._previous_packet_id is not None:
            expected = (self._previous_packet_id + 1) % (2**32)
            if packet_id != expected:
                dropped = (packet_id - expected) % (2**32)
        self._previous_packet_id = packet_id
        return dropped

    def read_sample(self) -> SignalSample:
        packet_id, payload = self._read_frame()
        eeg, ecg = self._decode_channels(payload)
        return SignalSample(
            host_timestamp=time.monotonic() - self._start_monotonic,
            packet_id=packet_id,
            dropped_before=self._count_dropped(packet_id),
            eeg=eeg,
            ecg=ecg,
        )

    def samples(self) -> Iterator[SignalSample]:
        while True:
            yield self.read_sample()
