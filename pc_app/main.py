# 작성자 : 안수민

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from windows.main.measurement import MeasurementWindow
from PySide6.QtGui import QIcon

from utils.config import Config
from data_manager.csv_manager import CSVManager
from communication.serial_manager import SerialManager



def main():

    config = Config()
    config.create_new_session()
    
    csv_manager = CSVManager( config.get_save_directory() )
    serial_manager = SerialManager(config)
    
    # window 생성/실행
    app = QApplication(sys.argv)
    window = MeasurementWindow(
        config=config,
        csv_manager=csv_manager,
        serial_manager=serial_manager
    )

    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()