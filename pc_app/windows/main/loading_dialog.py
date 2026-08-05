from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout
from PySide6.QtCore import Qt


class LoadingDialog(QDialog):

    def __init__(self, message="처리 중입니다..."):
        super().__init__()

        self.setWindowTitle("loading ...")
        self.setFixedSize(250, 100)

        self.setModal(True)

        layout = QVBoxLayout()

        label = QLabel(message)
        label.setAlignment(Qt.AlignCenter)

        layout.addWidget(label)

        self.setLayout(layout)