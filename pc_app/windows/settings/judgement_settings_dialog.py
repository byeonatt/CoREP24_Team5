from pathlib import Path

from PySide6.QtCore import QFile, QIODevice, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMessageBox, QAbstractSpinBox


class JudgementSettingsDialog:

    MODE_WIDGETS = {
        "MODE_OD": (
            "odMinSpinBox",
            "odMaxSpinBox",
        ),
        "MODE_ID_2": (
            "id2MinSpinBox",
            "id2MaxSpinBox",
        ),
        "MODE_ID_3": (
            "id3MinSpinBox",
            "id3MaxSpinBox",
        ),
    }

    def __init__(
        self,
        config
    ):
        self.config = config

        ui_path = (
            Path(__file__).parent
            / "judgement_settings.ui"
        )

        ui_file = QFile(
            str(ui_path)
        )

        if not ui_file.open(
            QIODevice.ReadOnly
        ):
            raise FileNotFoundError(
                f"Cannot open {ui_path}"
            )

        self.dialog = (
            QUiLoader().load(
                ui_file
            )
        )

        ui_file.close()

        self.dialog.setWindowTitle(
            "판정 기준 설정"
        )

        self.dialog.setWindowFlag(
            Qt.WindowMaximizeButtonHint,
            False
        )

        self.dialog.setFixedSize(
            self.dialog.size()
        )

        self.setup_spin_boxes()
        self.load_settings()
        self.connect_signal()
        self.update_input_state()

    def connect_signal(self):
        self.dialog.enableRadioButton.toggled.connect(
            self.update_input_state
        )

        self.dialog.disableRadioButton.toggled.connect(
            self.update_input_state
        )

        self.dialog.saveButton.clicked.connect(
            self.save_settings
        )

        self.dialog.cancelButton.clicked.connect(
            self.dialog.reject
        )

    def load_settings(self):
        settings = (
            self.config
            .get_all_judgement_settings()
        )

        enabled = bool(
            settings["enabled"]
        )

        self.dialog.enableRadioButton.setChecked(
            enabled
        )

        self.dialog.disableRadioButton.setChecked(
            not enabled
        )

        for mode, (
            min_name,
            max_name
        ) in self.MODE_WIDGETS.items():

            limits = settings[mode]

            min_widget = getattr(
                self.dialog,
                min_name
            )

            max_widget = getattr(
                self.dialog,
                max_name
            )

            min_widget.setValue(
                float(
                    limits[
                        "min_force"
                    ]
                )
            )

            max_widget.setValue(
                float(
                    limits[
                        "max_force"
                    ]
                )
            )

    def update_input_state(
        self,
        *_args
    ):
        enabled = (
            self.dialog
            .enableRadioButton
            .isChecked()
        )

        self.dialog.rangeContainer.setEnabled(
            enabled
        )

        if enabled:
            self.dialog.statusHintLabel.setText(
                "설정한 범위를 벗어난 Grip Event를 "
                "NG로 판정합니다."
            )
        else:
            self.dialog.statusHintLabel.setText(
                "파지력은 기록하지만 "
                "OK/NG 판정은 수행하지 않습니다."
            )

    def collect_limits(
        self
    ) -> dict:
        result = {}

        for mode, (
            min_name,
            max_name
        ) in self.MODE_WIDGETS.items():

            min_widget = getattr(
                self.dialog,
                min_name
            )

            max_widget = getattr(
                self.dialog,
                max_name
            )

            result[mode] = {
                "min_force":
                    min_widget.value(),
                "max_force":
                    max_widget.value(),
            }

        return result

    def save_settings(self):
        enabled = (
            self.dialog
            .enableRadioButton
            .isChecked()
        )

        limits = (
            self.collect_limits()
        )

        try:
            self.config.set_judgement_settings(
                enabled=enabled,
                limits_by_mode=limits
            )

        except ValueError as error:
            QMessageBox.warning(
                self.dialog,
                "판정 기준 입력 오류",
                str(error)
            )
            return

        if enabled:
            message = (
                "판정 기준이 저장되었습니다.\n\n"
                "새로 시작하는 Measurement부터 "
                "현재 설정이 적용됩니다."
            )
        else:
            message = (
                "판정 기준 미적용으로 저장되었습니다.\n\n"
                "파지 데이터와 Grip Event는 "
                "계속 기록되지만 OK/NG 판정은 "
                "수행하지 않습니다."
            )

        QMessageBox.information(
            self.dialog,
            "판정 기준 저장 완료",
            message
        )

        self.dialog.accept()

    def setup_spin_boxes(self):

        spin_boxes = [
            self.dialog.odMinSpinBox,
            self.dialog.odMaxSpinBox,

            self.dialog.id2MinSpinBox,
            self.dialog.id2MaxSpinBox,

            self.dialog.id3MinSpinBox,
            self.dialog.id3MaxSpinBox,
        ]

        for spin_box in spin_boxes:
            spin_box.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
            spin_box.setSingleStep(0.1)
            spin_box.setAccelerated(True)
            spin_box.setRange(0.0,1000.0)
            spin_box.setDecimals(3)
            spin_box.setReadOnly(False)

