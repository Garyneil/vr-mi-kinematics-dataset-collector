"""动捕服统一接口。

当前未知具体动捕服品牌和 SDK，因此这里只定义稳定的抽象接口。
后续厂商适配器应继承 BaseMocapAdapter。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Iterator, Optional


@dataclass(frozen=True)
class MocapFrame:
    """单帧动捕数据。"""

    host_timestamp: float
    device_timestamp: Optional[float]
    frame_id: Optional[int]
    joints: Dict[str, Dict[str, float]]


class BaseMocapAdapter(ABC):
    """所有动捕服适配器必须实现的最小接口。"""

    @abstractmethod
    def open(self) -> None:
        """建立与动捕系统的连接。"""

    @abstractmethod
    def close(self) -> None:
        """关闭连接并释放资源。"""

    @abstractmethod
    def frames(self) -> Iterator[MocapFrame]:
        """连续产生标准化动捕帧。"""

    def __enter__(self) -> "BaseMocapAdapter":
        self.open()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
