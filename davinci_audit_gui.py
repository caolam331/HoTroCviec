import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class DavinciProjectParser:
    """Parse DaVinci project file and flatten module config for audit."""

    def parse_project(self, project_path: Path) -> Dict[str, List[Tuple[str, str]]]:
        if not project_path.exists():
            raise FileNotFoundError(f"File không tồn tại: {project_path}")

        if project_path.suffix.lower() == ".drp":
            return self._parse_drp(project_path)

        if project_path.suffix.lower() in {".xml", ".drx", ".drt"}:
            return self._parse_xml_file(project_path.read_text(encoding="utf-8", errors="ignore"))

        if project_path.suffix.lower() == ".json":
            return self._parse_json(project_path.read_text(encoding="utf-8", errors="ignore"))

        raise ValueError("Định dạng chưa hỗ trợ. Hãy dùng .drp/.xml/.drx/.drt/.json")

    def _parse_drp(self, drp_path: Path) -> Dict[str, List[Tuple[str, str]]]:
        with zipfile.ZipFile(drp_path, "r") as archive:
            xml_candidates = [n for n in archive.namelist() if n.lower().endswith((".xml", ".drx", ".drt"))]
            json_candidates = [n for n in archive.namelist() if n.lower().endswith(".json")]

            if xml_candidates:
                content = archive.read(xml_candidates[0]).decode("utf-8", errors="ignore")
                return self._parse_xml_file(content)

            if json_candidates:
                content = archive.read(json_candidates[0]).decode("utf-8", errors="ignore")
                return self._parse_json(content)

            raise ValueError("Không tìm thấy XML/JSON bên trong file .drp")

    def _parse_xml_file(self, xml_content: str) -> Dict[str, List[Tuple[str, str]]]:
        root = ET.fromstring(xml_content)
        modules: Dict[str, List[Tuple[str, str]]] = {}

        for node in root.iter():
            node_name = node.tag.lower()
            if any(k in node_name for k in ["module", "node", "plugin", "effect", "tool"]):
                module_name = node.attrib.get("name") or node.attrib.get("id") or node.tag
                entries = []
                for key, value in node.attrib.items():
                    entries.append((key, value))

                for child in node:
                    child_label = child.attrib.get("name") or child.tag
                    child_value = (child.text or "").strip()
                    if child_value:
                        entries.append((child_label, child_value))
                    for ck, cv in child.attrib.items():
                        entries.append((f"{child_label}.{ck}", cv))

                if entries:
                    modules.setdefault(module_name, []).extend(entries)

        if not modules:
            modules["project_root"] = self._flatten_xml_generic(root)

        return modules

    def _flatten_xml_generic(self, element: ET.Element, prefix: str = "") -> List[Tuple[str, str]]:
        rows: List[Tuple[str, str]] = []
        path = f"{prefix}/{element.tag}" if prefix else element.tag

        for k, v in element.attrib.items():
            rows.append((f"{path}.@{k}", str(v)))

        text = (element.text or "").strip()
        if text:
            rows.append((path, text))

        for child in element:
            rows.extend(self._flatten_xml_generic(child, path))
        return rows

    def _parse_json(self, json_content: str) -> Dict[str, List[Tuple[str, str]]]:
        data = json.loads(json_content)
        modules: Dict[str, List[Tuple[str, str]]] = {}

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    modules[key] = self._flatten_json(value, key)

        if not modules:
            modules["project"] = self._flatten_json(data, "project")

        return modules

    def _flatten_json(self, value: Any, prefix: str) -> List[Tuple[str, str]]:
        rows: List[Tuple[str, str]] = []
        if isinstance(value, dict):
            for k, v in value.items():
                rows.extend(self._flatten_json(v, f"{prefix}.{k}"))
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                rows.extend(self._flatten_json(item, f"{prefix}[{idx}]"))
        else:
            rows.append((prefix, str(value)))
        return rows


class DavinciAuditWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DaVinci Project Config Auditor")
        self.resize(1200, 760)
        self.parser = DavinciProjectParser()
        self.module_data: Dict[str, List[Tuple[str, str]]] = {}

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        self.path_label = QLabel("Chưa chọn file project")
        open_btn = QPushButton("Mở project")
        open_btn.clicked.connect(self.open_project)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Lọc parameter theo tên/giá trị...")
        self.search_input.textChanged.connect(self.filter_table)

        layout.addWidget(self.path_label)
        layout.addWidget(open_btn)
        layout.addWidget(self.search_input)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, stretch=1)

        self.module_tree = QTreeWidget()
        self.module_tree.setHeaderLabel("Modules")
        self.module_tree.itemSelectionChanged.connect(self.show_selected_module)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSortingEnabled(True)

        splitter.addWidget(self.module_tree)
        splitter.addWidget(self.table)
        splitter.setSizes([280, 900])

    def open_project(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn DaVinci project",
            "",
            "DaVinci Project (*.drp *.xml *.drx *.drt *.json);;All Files (*)",
        )
        if not file_path:
            return

        path = Path(file_path)
        self.path_label.setText(str(path))

        try:
            self.module_data = self.parser.parse_project(path)
            self.render_modules()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi parse", str(exc))

    def render_modules(self):
        self.module_tree.clear()
        for module_name, params in sorted(self.module_data.items()):
            item = QTreeWidgetItem([f"{module_name} ({len(params)})"])
            item.setData(0, Qt.UserRole, module_name)
            self.module_tree.addTopLevelItem(item)

        if self.module_tree.topLevelItemCount() > 0:
            self.module_tree.setCurrentItem(self.module_tree.topLevelItem(0))

    def show_selected_module(self):
        selected = self.module_tree.selectedItems()
        if not selected:
            return

        module_name = selected[0].data(0, Qt.UserRole)
        rows = self.module_data.get(module_name, [])

        self.table.setRowCount(len(rows))
        for row_index, (param, value) in enumerate(rows):
            self.table.setItem(row_index, 0, QTableWidgetItem(param))
            self.table.setItem(row_index, 1, QTableWidgetItem(value))

        self.filter_table(self.search_input.text())

    def filter_table(self, keyword: str):
        key = keyword.lower().strip()
        for row in range(self.table.rowCount()):
            param_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)
            hay = f"{param_item.text()} {value_item.text()}".lower() if param_item and value_item else ""
            self.table.setRowHidden(row, bool(key) and key not in hay)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DavinciAuditWindow()
    window.show()
    sys.exit(app.exec_())
