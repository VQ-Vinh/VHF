from pathlib import Path

from PySide6.QtWidgets import QDialog, QHBoxLayout, QHeaderView, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout

from prana_elex.core.models.result import ProcessingResult

_MAX_ROWS = 1000


class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Translation History")
        self.setMinimumSize(700, 500)
        self.setObjectName("HistoryDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        top_layout = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setObjectName("HistorySearch")
        self._search.setPlaceholderText("Search transcripts...")
        self._search.textChanged.connect(self._filter)
        top_layout.addWidget(self._search)

        self._export_btn = QPushButton("Export")
        self._export_btn.clicked.connect(self._export)
        top_layout.addWidget(self._export_btn)

        self._clear_btn = QPushButton("Clear All")
        self._clear_btn.clicked.connect(self._clear_all)
        top_layout.addWidget(self._clear_btn)

        layout.addLayout(top_layout)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Time", "Language", "Transcript", "Translation"])
        self._table.setAlternatingRowColors(True)
        self._table.setWordWrap(True)
        self._table.verticalHeader().setDefaultSectionSize(60)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

        self._results: list[ProcessingResult] = []

    def add_result(self, result: ProcessingResult) -> None:
        if len(self._results) >= _MAX_ROWS:
            self._results.pop(0)
            self._table.removeRow(0)
        self._results.append(result)
        self._add_row(result)

    def _add_row(self, result: ProcessingResult) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        t = result.timestamp.strftime("%H:%M:%S") if result.timestamp else ""
        self._table.setItem(row, 0, QTableWidgetItem(t))
        self._table.setItem(row, 1, QTableWidgetItem(result.detected_language.upper()))
        self._table.setItem(row, 2, QTableWidgetItem(result.transcript_restored))
        self._table.setItem(row, 3, QTableWidgetItem(result.translation))

    def _filter(self, text: str) -> None:
        for row in range(self._table.rowCount()):
            match = False
            for col in range(self._table.columnCount()):
                item = self._table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self._table.setRowHidden(row, not match)

    def _export(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Export History", "history.txt", "Text (*.txt);;CSV (*.csv)")
        if not path:
            return
        lines = []
        for r in self._results:
            lines.append(f"[{r.timestamp.strftime('%H:%M:%S')}] [{r.detected_language.upper()}]")
            lines.append(f"  TXT: {r.transcript_restored}")
            lines.append(f"  TRN: {r.translation}")
            lines.append("")
        Path(path).write_text("\n".join(lines), encoding="utf-8")

    def _clear_all(self) -> None:
        self._results.clear()
        self._table.setRowCount(0)
