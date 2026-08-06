from PySide6.QtWidgets import QMainWindow
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice
from pathlib import Path


class CalibrationWindow(QMainWindow):

    def __init__(self,serial_manager=None):
        super().__init__()

        self.serial_manager = serial_manager
        ui_path = Path(__file__).parent/"calibration.ui"
        ui_file = QFile(str(ui_path))
        ui_file.open(QIODevice.ReadOnly)
        self.ui = QUiLoader().load(ui_file)
        ui_file.close()
        
        self.setCentralWidget(self.ui)
        self.connect_signal()