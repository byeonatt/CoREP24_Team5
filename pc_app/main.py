import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from windows.main.measurement import MeasurementWindow
from PySide6.QtGui import QIcon

from utils.config import Config
from data_manager.csv_manager import CSVManager
from communication.serial_manager import SerialManager

# 테스트 디버그 파일
from communication.simulated_serial_manager import SimulatedSerialManager
SIMULATION_MODE = 1    # <<< 여기만 1/0으로 바꾸면 됨



def main():

    config = Config()
    config.create_new_session()
    
    csv_manager = CSVManager( config.get_save_directory() )
    if SIMULATION_MODE : serial_manager = SimulatedSerialManager(config)
    else : serial_manager = SerialManager(config)
    
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