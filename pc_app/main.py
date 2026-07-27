### 건드리지 말 것! ###
# 작성자 : 안수민

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from windows.main_window import MainWindow
from PySide6.QtGui import QIcon

def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()