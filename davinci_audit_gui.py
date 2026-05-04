import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Tuple

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
    """Parse DaVinci/Fusion-related files and flatten module config for audit."""

    DAVINCI_EXTENSIONS = {".drp", ".drt", ".drx", ".setting", ".comp"}

    def parse_project(self, project_path: Path) -> Dict[str, List[Tuple[str, str]]]:
        if not project_path.exists():
            raise FileNotFoundError(f"File không tồn tại: {project_path}")

        suffix = project_path.suffix.lower()
        if suffix not in self.DAVINCI_EXTENSIONS:
            raise ValueError("Định dạng chưa hỗ trợ. Chỉ hỗ trợ .drp/.drt/.drx/.setting/.comp")

        if suffix == ".drp":
            return self._parse_drp(project_path)

        if suffix in {".drt", ".drx"}:
            return self._parse_drt_or_drx(project_path)

        return self._parse_fusion_setting(project_path.read_text(encoding="utf-8", errors="ignore"))

    def _parse_drp(self, drp_path: Path) -> Dict[str, List[Tuple[str, str]]]:
        with zipfile.ZipFile(drp_path, "r") as archive:
            xml_candidates = [
                name
                for name in archive.namelist()
                if name.lower().endswith(".xml") and "project" in name.lower()
            ]
            if not xml_candidates:
                xml_candidates = [name for name in archive.namelist() if name.lower().endswith(".xml")]

            if not xml_candidates:
                raise ValueError(".drp không chứa XML project hợp lệ")

            xml_content = archive.read(xml_candidates[0]).decode("utf-8", errors="ignore")
            return self._parse_xml_modules(xml_content)

    def _parse_drt_or_drx(self, file_path: Path) -> Dict[str, List[Tuple[str, str]]]:
        raw = file_path.read_bytes()

        if raw.startswith(b"PK"):
            with zipfile.ZipFile(file_path, "r") as archive:
                xml_candidates = [name for name in archive.namelist() if name.lower().endswith(".xml")]
                if not xml_candidates:
                    raise ValueError(f"{file_path.suffix} không chứa XML hợp lệ")
                xml_content = archive.read(xml_candidates[0]).decode("utf-8", errors="ignore")
                return self._parse_xml_modules(xml_content)

        text = raw.decode("utf-8", errors="ignore")
        if "<" in text and ">" in text:
            return self._parse_xml_modules(text)

        raise ValueError(f"Không đọc được dữ liệu {file_path.suffix} (không phải XML/ZIP XML)")

    def _parse_xml_modules(self, xml_content: str) -> Dict[str, List[Tuple[str, str]]]:
        root = ET.fromstring(xml_content)
        modules: Dict[str, List[Tuple[str, str]]] = {}

        for node in root.iter():
            node_name = node.tag.lower()
            if any(k in node_name for k in ["node", "plugin", "effect", "tool", "grade"]):
                module_name = node.attrib.get("name") or node.attrib.get("id") or node.tag
                entries: List[Tuple[str, str]] = []

                for key, value in node.attrib.items():
                    entries.append((key, str(value)))

                for child in node:
                    child_label = child.attrib.get("name") or child.tag
                    child_value = (child.text or "").strip()
                    if child_value:
                        entries.append((child_label, child_value))
                    for ck, cv in child.attrib.items():
                        entries.append((f"{child_label}.{ck}", str(cv)))

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

    def _parse_fusion_setting(self, content: str) -> Dict[str, List[Tuple[str, str]]]:
        modules: Dict[str, List[Tuple[str, str]]] = {}
        active_module = "fusion_config"

        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("--"):
                continue

            tool_match = re.match(r"([A-Za-z0-9_]+)\s*=\s*([A-Za-z0-9_]+)\s*\{", stripped)
            if tool_match:
                active_module = tool_match.group(1)
                modules.setdefault(active_module, [])
                modules[active_module].append(("tool_type", tool_match.group(2)))
                continue

            kv_match = re.match(r'([A-Za-z0-9_\.\[\]"\']+)\s*=\s*(.+)', stripped)
            if kv_match:
                key = kv_match.group(1)
                value = kv_match.group(2).rstrip(",")
                modules.setdefault(active_module, []).append((key, value))

        if not modules:
            modules["fusion_config"] = [("raw", content[:10000])]

        return modules


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
            "Chọn file DaVinci/Fusion",
            "",
            "DaVinci/Fusion Files (*.drp *.drt *.drx *.setting *.comp);;All Files (*)",
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
