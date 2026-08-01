"""通用 UDP 动捕适配器骨架。

预期每个 UDP 数据包为一行 UTF-8 JSON，例如：
{
  "device_timestamp": 12.345,
  "frame_id": 1001,
  "joints": {
    "right_wrist": {"x": 0.1, "y": 1.2, "z": 0.3,
                    "qx": 0.0, "qy": 0.0, "qz": 0.0, "qw": 1.0}
  }
}

具体字段需要在确认动捕服品牌、SDK 和输出格式后调整。
"""

from __future__ import annotations

import json
import socket
import time
from typing import Iterator, Optional

from .base_mocap import BaseMocapAdapter, MocapFrame


class GenericUdpMocapAdapter(BaseMocapAdapter):
    def __init__(self, host: str = "0.0.0.0", port: int = 7001, timeout_sec: float = 1.0):
        self.host = host
        self.port = int(port)
        self.timeout_sec = float(timeout_sec)
        self._socket: Optional[socket.socket] = None

    def open(self) -> None:
        if self._socket is not None:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))
        sock.settimeout(self.timeout_sec)
        self._socket = sock

    def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def frames(self) -> Iterator[MocapFrame]:
        if self._socket is None:
            raise RuntimeError("动捕适配器尚未打开，请先调用 open()。")

        while True:
            try:
                payload, _ = self._socket.recvfrom(65535)
            except socket.timeout:
                continue

            host_timestamp = time.monotonic()
            try:
                data = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("收到的 UDP 动捕数据不是有效 UTF-8 JSON。") from exc

            joints = data.get("joints")
            if not isinstance(joints, dict):
                raise ValueError("动捕数据必须包含字典类型的 joints 字段。")

            yield MocapFrame(
                host_timestamp=host_timestamp,
                device_timestamp=data.get("device_timestamp"),
                frame_id=data.get("frame_id"),
                joints=joints,
            )
