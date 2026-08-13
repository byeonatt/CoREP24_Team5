import ctypes
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter


WM_DEVICECHANGE = 0x0219

DBT_DEVNODES_CHANGED = 0x0007
DBT_DEVICEARRIVAL = 0x8000
DBT_DEVICEREMOVECOMPLETE = 0x8004


class DeviceChangeFilter(QAbstractNativeEventFilter):

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, event_type, message):

        # Windows의 일반 Window 메시지만 확인
        if bytes(event_type) != b"windows_generic_MSG":
            return False

        try:
            msg = wintypes.MSG.from_address(int(message))
        except (TypeError, ValueError):
            return False

        if msg.message != WM_DEVICECHANGE:
            return False

        event = int(msg.wParam)

        if event == DBT_DEVICEARRIVAL:
            self.callback("arrival")

        elif event == DBT_DEVICEREMOVECOMPLETE:
            self.callback("remove")

        elif event == DBT_DEVNODES_CHANGED:
            self.callback("changed")

        # Windows 메시지를 우리가 먹지 않고
        # Qt에도 계속 전달
        return False