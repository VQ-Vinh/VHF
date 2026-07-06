from __future__ import annotations

import threading
import numpy as np


class RingBuffer:
    def __init__(self, max_size: int, dtype: np.dtype = np.int16):
        self._buffer = np.zeros(max_size, dtype=dtype)
        self._max_size = max_size
        self._head = 0
        self._count = 0
        self._lock = threading.Lock()

    @property
    def count(self) -> int:
        return self._count

    @property
    def max_size(self) -> int:
        return self._max_size

    def push(self, data: np.ndarray) -> None:
        n = len(data)
        if n > self._max_size:
            data = data[-self._max_size:]
            n = self._max_size
        with self._lock:
            if self._head + n <= self._max_size:
                self._buffer[self._head : self._head + n] = data
            else:
                first = self._max_size - self._head
                self._buffer[self._head:] = data[:first]
                self._buffer[: n - first] = data[first:]
            self._head = (self._head + n) % self._max_size
            self._count = min(self._count + n, self._max_size)

    def get_last(self, n: int) -> np.ndarray:
        n = min(n, self._count)
        with self._lock:
            if self._count == 0:
                return np.array([], dtype=self._buffer.dtype)
            if n <= self._head:
                return self._buffer[self._head - n : self._head].copy()
            result = np.empty(n, dtype=self._buffer.dtype)
            tail = self._buffer[: self._head]
            head = self._buffer[self._head - (n - len(tail)) : self._head]
            result[: len(head)] = head
            result[len(head) :] = tail
            return result

    def get_all(self) -> np.ndarray:
        return self.get_last(self._count)

    def clear(self) -> None:
        with self._lock:
            self._buffer.fill(0)
            self._head = 0
            self._count = 0
