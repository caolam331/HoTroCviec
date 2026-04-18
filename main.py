import copy
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QDialog, QLabel, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QTextEdit, QFileDialog, QMessageBox,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QSizePolicy,
    QScrollArea, QColorDialog, QMenu,
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QEvent
from PyQt5.QtGui import QFont, QColor, QTextCharFormat, QTextCursor, QCursor

CONFIG_FILE = Path(__file__).parent / "config.json"

# ─── Defaults ─────────────────────────────────────────────────────────────────

DEFAULT_BUTTONS = [
    {
        "id": "hello", "label": "Hello World", "icon": "★", "color": "#2196F3",
        "script": "tasks/hello.py", "description": "In ra lời chào",
        "params": [
            {"name": "name", "label": "Tên của bạn", "type": "text", "default": "World", "required": True},
            {"name": "greet", "label": "Kiểu chào", "type": "choice",
             "options": ["Hello", "Hi", "Hey", "Xin chào"], "default": "Hello"},
        ],
    },
    {
        "id": "backup", "label": "Backup Files", "icon": "⬆", "color": "#4CAF50",
        "script": "tasks/backup.py", "description": "Sao lưu thư mục",
        "params": [
            {"name": "source", "label": "Thư mục nguồn", "type": "folder", "default": "", "required": True},
            {"name": "destination", "label": "Thư mục đích", "type": "folder", "default": "", "required": True},
            {"name": "compress", "label": "Nén file", "type": "boolean", "default": True},
        ],
    },
    {
        "id": "ping", "label": "Ping Host", "icon": "◉", "color": "#FF9800",
        "script": "tasks/ping_host.py", "description": "Kiểm tra kết nối mạng",
        "params": [
            {"name": "host", "label": "Host / IP", "type": "text", "default": "google.com", "required": True},
            {"name": "count", "label": "Số lần ping", "type": "number", "default": 4},
        ],
    },
    {
        "id": "rename", "label": "Rename Files", "icon": "✎", "color": "#9C27B0",
        "script": "tasks/rename_files.py", "description": "Đổi tên hàng loạt file",
        "params": [
            {"name": "folder", "label": "Thư mục", "type": "folder", "default": "", "required": True},
            {"name": "pattern", "label": "Pattern (regex)", "type": "text", "default": ".*"},
            {"name": "prefix", "label": "Tiền tố", "type": "text", "default": ""},
            {"name": "dry_run", "label": "Chạy thử (không thay đổi)", "type": "boolean", "default": True},
        ],
    },
    {
        "id": "sysinfo", "label": "System Info", "icon": "☰", "color": "#607D8B",
        "script": "tasks/sysinfo.py", "description": "Thông tin hệ thống", "params": [],
    },
    {
        "id": "countdown", "label": "Countdown Timer", "icon": "⏱", "color": "#F44336",
        "script": "tasks/countdown.py", "description": "Hẹn giờ đếm ngược",
        "params": [
            {"name": "seconds", "label": "Số giây", "type": "number", "default": 10, "required": True},
            {"name": "message", "label": "Thông báo khi xong", "type": "text", "default": "Done!"},
        ],
    },
]

ICON_GROUPS = {
    "Phổ biến":      ["★", "☆", "◉", "▶", "⬆", "⬇", "✎", "☰", "⚙", "💡", "🚀", "🎯"],
    "Tệp & Dữ liệu": ["📁", "📂", "💾", "📄", "📝", "📋", "📊", "📈", "🗂", "🗃", "📀"],
    "Hệ thống":      ["🖥", "💻", "🖨", "🔌", "🔋", "📡", "🌐", "🔗", "📶"],
    "Công cụ":       ["🔧", "🔨", "⚒", "🛠", "🔩", "⛏", "🪛", "🪚", "🔬"],
    "Thời gian":     ["⏱", "⏲", "⏰", "📅", "📆", "🕐", "⌚"],
    "Trạng thái":    ["✓", "✗", "✕", "⚠", "ℹ", "❓", "❗", "🔔", "♻", "🔄"],
    "Khác":          ["🏠", "🎨", "🎵", "🎬", "📧", "🔐", "🔑", "💰", "📦", "🌟"],
}


# ─── Config helpers ────────────────────────────────────────────────────────────

def _make_default_config():
    return {
        "active_profile": "Mặc định",
        "profiles": [
            {"name": "Mặc định", "title": "Task Dashboard", "columns": 3,
             "buttons": copy.deepcopy(DEFAULT_BUTTONS)},
        ],
    }


def load_config():
    if not CONFIG_FILE.exists():
        data = _make_default_config()
        save_config(data)
        return data
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "profiles" not in data:
        profile = {"name": "Mặc định", "title": data.get("title", "Task Dashboard"),
                   "columns": data.get("columns", 3), "buttons": data.get("buttons", [])}
        data = {"active_profile": "Mặc định", "profiles": [profile]}
        save_config(data)
    return data


def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _lighten(hex_color, amount=30):
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f"#{min(255, r+amount):02x}{min(255, g+amount):02x}{min(255, b+amount):02x}"


# ─── Worker Signals ────────────────────────────────────────────────────────────

class WorkerSignals(QObject):
    text_ready = pyqtSignal(str, str)
    finished = pyqtSignal(str)


# ─── Shared styles ─────────────────────────────────────────────────────────────

ENTRY_STYLE = "background-color: #2a2a3e; color: white; border: none; padding: 5px 10px; border-radius: 3px;"
LBL_STYLE   = "color: #ccc; background: transparent; font: 9pt 'Segoe UI';"
BTN_DARK    = ("QPushButton { background-color: #333; color: white; border: none;"
               " padding: 6px 16px; border-radius: 4px; }"
               " QPushButton:hover { background-color: #444; }")
BTN_BLUE    = ("QPushButton { background-color: #2196F3; color: white; border: none;"
               " padding: 6px 16px; border-radius: 4px; }"
               " QPushButton:hover { background-color: #42a6f5; }")
COMBO_STYLE = ("QComboBox { background-color: #2a2a3e; color: white; border: none;"
               " padding: 5px 10px; border-radius: 3px; }"
               " QComboBox::drop-down { border: none; }"
               " QComboBox QAbstractItemView { background-color: #2a2a3e; color: white;"
               " selection-background-color: #3a3a5e; }")
MENU_STYLE  = ("QMenu { background-color: #2a2a3e; color: white; border: 1px solid #444; padding: 4px 0; }"
               " QMenu::item { padding: 7px 20px; }"
               " QMenu::item:selected { background-color: #3a3a5e; }"
               " QMenu::separator { height: 1px; background: #444; margin: 4px 0; }")


# ─── Parameter Dialog (run-time) ───────────────────────────────────────────────

class ParamDialog(QDialog):
    def __init__(self, parent, button_cfg):
        super().__init__(parent)
        self.result = None
        self.button_cfg = button_cfg
        self.widgets = {}
        self.setWindowTitle(button_cfg["label"])
        self.setFixedWidth(460)
        self.setStyleSheet("background-color: #1e1e2e; color: white;")
        self._build_ui()

    def _build_ui(self):
        cfg = self.button_cfg
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(52)
        header.setStyleSheet(f"background-color: {cfg.get('color', '#444')};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 16, 0)
        t = QLabel(f"{cfg.get('icon', '')}  {cfg['label']}")
        t.setFont(QFont("Segoe UI", 13, QFont.Bold))
        t.setStyleSheet("color: white; background: transparent;")
        hl.addWidget(t)
        layout.addWidget(header)

        content = QWidget()
        content.setStyleSheet("background-color: #1e1e2e;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(16, 8, 16, 16)
        cl.setSpacing(4)

        if cfg.get("description"):
            d = QLabel(cfg["description"])
            d.setFont(QFont("Segoe UI", 9))
            d.setStyleSheet("color: #888; background: transparent;")
            cl.addWidget(d)

        for p in cfg.get("params", []):
            self._add_row(cl, p)

        bl = QHBoxLayout()
        bl.addStretch()
        color = cfg.get("color", "#2196F3")
        run = QPushButton("▶  Chạy")
        run.setFont(QFont("Segoe UI", 10, QFont.Bold))
        run.setStyleSheet(f"QPushButton {{ background-color: {color}; color: white; border: none; padding: 6px 16px; border-radius: 4px; }} QPushButton:hover {{ background-color: {_lighten(color)}; }}")
        run.clicked.connect(self._submit)
        cancel = QPushButton("Hủy")
        cancel.setStyleSheet(BTN_DARK)
        cancel.clicked.connect(self.reject)
        bl.addWidget(run)
        bl.addWidget(cancel)
        cl.addSpacing(8)
        cl.addLayout(bl)
        layout.addWidget(content)

    def _add_row(self, parent, p):
        row = QHBoxLayout()
        row.setSpacing(8)
        lbl = QLabel(p["label"] + (" *" if p.get("required") else ""))
        lbl.setFont(QFont("Segoe UI", 9))
        lbl.setStyleSheet("color: #ccc; background: transparent;")
        lbl.setFixedWidth(160)
        row.addWidget(lbl)

        ptype = p.get("type", "text")
        name = p["name"]

        if ptype == "text":
            w = QLineEdit(str(p.get("default", "")))
            w.setStyleSheet(ENTRY_STYLE)
            row.addWidget(w, 1)
            self.widgets[name] = w
        elif ptype == "number":
            w = QLineEdit(str(p.get("default", 0)))
            w.setStyleSheet(ENTRY_STYLE)
            w.setFixedWidth(100)
            row.addWidget(w)
            self.widgets[name] = w
        elif ptype == "choice":
            w = QComboBox()
            w.addItems(p.get("options", []))
            idx = w.findText(str(p.get("default", "")))
            if idx >= 0:
                w.setCurrentIndex(idx)
            w.setStyleSheet(COMBO_STYLE)
            row.addWidget(w, 1)
            self.widgets[name] = w
        elif ptype == "boolean":
            w = QCheckBox()
            w.setChecked(bool(p.get("default", False)))
            w.setStyleSheet("QCheckBox { color: white; background: transparent; }")
            row.addWidget(w)
            self.widgets[name] = w
        elif ptype in ("file", "folder"):
            c = QWidget()
            c.setStyleSheet("background: transparent;")
            h = QHBoxLayout(c)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(4)
            line = QLineEdit(str(p.get("default", "")))
            line.setStyleSheet(ENTRY_STYLE)
            h.addWidget(line, 1)
            bb = QPushButton("…")
            bb.setFixedWidth(28)
            bb.setStyleSheet("QPushButton { background-color: #444; color: white; border: none; padding: 4px; border-radius: 3px; } QPushButton:hover { background-color: #555; }")
            def browse(_=False, le=line, t=ptype):
                path = (QFileDialog.getExistingDirectory(self, "Chọn thư mục") if t == "folder"
                        else QFileDialog.getOpenFileName(self, "Chọn file")[0])
                if path:
                    le.setText(path)
            bb.clicked.connect(browse)
            h.addWidget(bb)
            row.addWidget(c, 1)
            self.widgets[name] = line

        row.addStretch()
        parent.addLayout(row)

    def _submit(self):
        args = {}
        for p in self.button_cfg.get("params", []):
            name = p["name"]
            w = self.widgets.get(name)
            if w is None:
                continue
            ptype = p.get("type", "text")
            val = w.isChecked() if ptype == "boolean" else (w.currentText() if ptype == "choice" else w.text())
            if p.get("required") and not str(val).strip():
                QMessageBox.warning(self, "Thiếu thông tin", f"Vui lòng nhập: {p['label']}")
                return
            args[name] = val
        self.result = args
        self.accept()


# ─── Output Panel ─────────────────────────────────────────────────────────────

class OutputPanel(QDialog):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.setWindowTitle(f"Output — {title}")
        self.resize(700, 420)
        self.setStyleSheet("background-color: #1e1e2e;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        lbl = QLabel(title)
        lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        lbl.setStyleSheet("color: #aaa; background: transparent;")
        layout.addWidget(lbl)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Consolas", 10))
        self.text.setStyleSheet("background-color: #12121f; color: #e0e0e0; border: none;")
        layout.addWidget(self.text, 1)

        bb = QWidget()
        bb.setStyleSheet("background: transparent;")
        bl = QHBoxLayout(bb)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.addStretch()
        for text, slot in [("Xóa", self.clear), ("Đóng", self.close)]:
            btn = QPushButton(text)
            btn.setStyleSheet(BTN_DARK)
            btn.clicked.connect(slot)
            bl.addWidget(btn)
        layout.addWidget(bb)

    def append(self, text, tag=None):
        cursor = self.text.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#ff6b6b" if tag == "error" else "#6bff8e" if tag == "success" else "#e0e0e0"))
        cursor.setCharFormat(fmt)
        cursor.insertText(text)
        self.text.setTextCursor(cursor)
        self.text.ensureCursorVisible()

    def clear(self):
        self.text.clear()


# ─── Icon Picker Dialog ────────────────────────────────────────────────────────

class IconPickerDialog(QDialog):
    def __init__(self, parent, current=""):
        super().__init__(parent)
        self.result = current
        self.setWindowTitle("Chọn icon")
        self.setFixedSize(440, 500)
        self.setStyleSheet("background-color: #1e1e2e; color: white;")
        self._build_ui(current)

    def _build_ui(self, current):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Preview + custom input row
        pr = QHBoxLayout()
        self._preview = QLabel(current or "?")
        self._preview.setFont(QFont("Segoe UI", 26))
        self._preview.setFixedSize(52, 52)
        self._preview.setAlignment(Qt.AlignCenter)
        self._preview.setStyleSheet("background-color: #2a2a3e; border-radius: 6px; color: white;")
        pr.addWidget(self._preview)

        self._custom = QLineEdit(current)
        self._custom.setStyleSheet(ENTRY_STYLE)
        self._custom.setPlaceholderText("Nhập emoji bất kỳ hoặc click chọn bên dưới…")
        self._custom.setFont(QFont("Segoe UI", 14))
        self._custom.textChanged.connect(self._on_custom)
        pr.addWidget(self._custom, 1)
        layout.addLayout(pr)

        # Scrollable grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #1e1e2e; }")
        content = QWidget()
        content.setStyleSheet("background-color: #1e1e2e;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 4, 0, 4)
        cl.setSpacing(8)

        COLS = 9
        btn_s = ("QPushButton { background-color: #2a2a3e; color: white; border: none;"
                 " border-radius: 4px; font: 15pt 'Segoe UI'; }"
                 " QPushButton:hover { background-color: #3d6aaa; }")

        for grp, icons in ICON_GROUPS.items():
            gl = QLabel(grp)
            gl.setFont(QFont("Segoe UI", 8, QFont.Bold))
            gl.setStyleSheet("color: #666; background: transparent;")
            cl.addWidget(gl)

            grid_w = QWidget()
            grid_w.setStyleSheet("background: transparent;")
            grid = QGridLayout(grid_w)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(4)
            for i, icon in enumerate(icons):
                b = QPushButton(icon)
                b.setFixedSize(40, 38)
                b.setStyleSheet(btn_s)
                b.clicked.connect(lambda _, ic=icon: self._select(ic))
                grid.addWidget(b, i // COLS, i % COLS)
            cl.addWidget(grid_w)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        bl = QHBoxLayout()
        bl.addStretch()
        ok = QPushButton("Chọn")
        ok.setStyleSheet(BTN_BLUE)
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Hủy")
        cancel.setStyleSheet(BTN_DARK)
        cancel.clicked.connect(self.reject)
        bl.addWidget(ok)
        bl.addWidget(cancel)
        layout.addLayout(bl)

    def _on_custom(self, text):
        self.result = text
        self._preview.setText(text or "?")

    def _select(self, icon):
        self.result = icon
        self._preview.setText(icon)
        self._custom.blockSignals(True)
        self._custom.setText(icon)
        self._custom.blockSignals(False)


# ─── Param Editor Dialog (design-time) ────────────────────────────────────────

class ParamEditorDialog(QDialog):
    PARAM_TYPES = ["text", "number", "boolean", "choice", "file", "folder"]

    def __init__(self, parent, param=None):
        super().__init__(parent)
        self.result = None
        self._init = param or {}
        self.setWindowTitle("Sửa tham số" if param else "Thêm tham số")
        self.setFixedWidth(440)
        self.setStyleSheet("background-color: #1e1e2e; color: white;")
        self._build_ui()

    def _build_ui(self):
        p = self._init
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        def row(label, widget, stretch=True):
            r = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(130)
            lbl.setStyleSheet(LBL_STYLE)
            r.addWidget(lbl)
            r.addWidget(widget, 1 if stretch else 0)
            layout.addLayout(r)

        self.name_edit = QLineEdit(p.get("name", ""))
        self.name_edit.setStyleSheet(ENTRY_STYLE)
        self.name_edit.setPlaceholderText("snake_case, không dấu cách")
        row("Tên biến *", self.name_edit)

        self.label_edit = QLineEdit(p.get("label", ""))
        self.label_edit.setStyleSheet(ENTRY_STYLE)
        row("Nhãn hiển thị *", self.label_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(self.PARAM_TYPES)
        idx = self.type_combo.findText(p.get("type", "text"))
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        self.type_combo.setStyleSheet(COMBO_STYLE)
        row("Kiểu dữ liệu", self.type_combo)

        self.default_edit = QLineEdit(str(p.get("default", "")))
        self.default_edit.setStyleSheet(ENTRY_STYLE)
        row("Giá trị mặc định", self.default_edit)

        self._opt_row = QWidget()
        self._opt_row.setStyleSheet("background: transparent;")
        or_ = QHBoxLayout(self._opt_row)
        or_.setContentsMargins(0, 0, 0, 0)
        ol = QLabel("Tùy chọn")
        ol.setFixedWidth(130)
        ol.setStyleSheet(LBL_STYLE)
        or_.addWidget(ol)
        self.options_edit = QLineEdit(", ".join(p.get("options", [])))
        self.options_edit.setStyleSheet(ENTRY_STYLE)
        self.options_edit.setPlaceholderText("val1, val2, val3")
        or_.addWidget(self.options_edit, 1)
        layout.addWidget(self._opt_row)

        self.req_chk = QCheckBox("Bắt buộc nhập")
        self.req_chk.setChecked(bool(p.get("required", False)))
        self.req_chk.setStyleSheet("QCheckBox { color: #ccc; background: transparent; }")
        layout.addWidget(self.req_chk)

        self.type_combo.currentTextChanged.connect(lambda t: self._opt_row.setVisible(t == "choice"))
        self._opt_row.setVisible(self.type_combo.currentText() == "choice")

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #333; max-height: 1px;")
        layout.addWidget(sep)

        bl = QHBoxLayout()
        bl.addStretch()
        ok = QPushButton("Lưu")
        ok.setStyleSheet(BTN_BLUE)
        ok.clicked.connect(self._submit)
        cancel = QPushButton("Hủy")
        cancel.setStyleSheet(BTN_DARK)
        cancel.clicked.connect(self.reject)
        bl.addWidget(ok)
        bl.addWidget(cancel)
        layout.addLayout(bl)

    def _submit(self):
        name = self.name_edit.text().strip()
        label = self.label_edit.text().strip()
        if not name or not label:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập Tên biến và Nhãn hiển thị.")
            return
        ptype = self.type_combo.currentText()
        param = {"name": name, "label": label, "type": ptype,
                 "default": self.default_edit.text().strip(),
                 "required": self.req_chk.isChecked()}
        if ptype == "choice":
            param["options"] = [o.strip() for o in self.options_edit.text().split(",") if o.strip()]
        self.result = param
        self.accept()


# ─── Task Editor Dialog ────────────────────────────────────────────────────────

class TaskEditorDialog(QDialog):
    def __init__(self, parent, task=None):
        super().__init__(parent)
        self.result = None
        self._init_task = task or {}
        self._params = list(task.get("params", [])) if task else []
        self._color = task.get("color", "#2196F3") if task else "#2196F3"
        self.setWindowTitle("Sửa tác vụ" if task else "Thêm tác vụ mới")
        self.resize(540, 640)
        self.setStyleSheet("background-color: #1e1e2e; color: white;")
        self._build_ui()

    def _build_ui(self):
        t = self._init_task
        ml = QVBoxLayout(self)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)

        # Header
        self._header = QWidget()
        self._header.setFixedHeight(52)
        self._header.setStyleSheet(f"background-color: {self._color};")
        hl = QHBoxLayout(self._header)
        hl.setContentsMargins(16, 0, 16, 0)
        tl = QLabel(self.windowTitle())
        tl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        tl.setStyleSheet("color: white; background: transparent;")
        hl.addWidget(tl)
        ml.addWidget(self._header)

        # Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #1e1e2e; }")
        content = QWidget()
        content.setStyleSheet("background-color: #1e1e2e;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(10)

        LW = 100

        def frow(lbl_text, widget, extra=None):
            r = QHBoxLayout()
            lb = QLabel(lbl_text)
            lb.setFixedWidth(LW)
            lb.setStyleSheet(LBL_STYLE)
            r.addWidget(lb)
            r.addWidget(widget, 1)
            if extra:
                r.addWidget(extra)
            cl.addLayout(r)

        self.label_edit = QLineEdit(t.get("label", ""))
        self.label_edit.setStyleSheet(ENTRY_STYLE)
        self.label_edit.setPlaceholderText("Tên hiển thị trên card *")
        self.label_edit.textChanged.connect(self._on_label_change)
        frow("Nhãn *", self.label_edit)

        self.id_edit = QLineEdit(t.get("id", ""))
        self.id_edit.setStyleSheet(ENTRY_STYLE)
        self.id_edit.setPlaceholderText("tự động điền")
        frow("ID", self.id_edit)

        # Icon with picker button
        icon_r = QHBoxLayout()
        ib = QLabel("Icon")
        ib.setFixedWidth(LW)
        ib.setStyleSheet(LBL_STYLE)
        icon_r.addWidget(ib)
        self.icon_edit = QLineEdit(t.get("icon", ""))
        self.icon_edit.setStyleSheet(ENTRY_STYLE)
        self.icon_edit.setPlaceholderText("emoji hoặc ký tự")
        icon_r.addWidget(self.icon_edit, 1)
        pick_btn = QPushButton("☰")
        pick_btn.setFixedSize(34, 34)
        pick_btn.setToolTip("Chọn icon từ danh sách")
        pick_btn.setStyleSheet("QPushButton { background-color: #444; color: white; border: none; border-radius: 3px; font: 13pt 'Segoe UI'; } QPushButton:hover { background-color: #555; }")
        pick_btn.clicked.connect(self._pick_icon)
        icon_r.addWidget(pick_btn)
        cl.addLayout(icon_r)

        # Color
        cr = QHBoxLayout()
        clb = QLabel("Màu sắc")
        clb.setFixedWidth(LW)
        clb.setStyleSheet(LBL_STYLE)
        cr.addWidget(clb)
        self.color_btn = QPushButton(self._color)
        self.color_btn.setFixedHeight(34)
        self.color_btn.setCursor(Qt.PointingHandCursor)
        self._refresh_color_btn()
        self.color_btn.clicked.connect(self._pick_color)
        cr.addWidget(self.color_btn, 1)
        cl.addLayout(cr)

        # Script
        self.script_edit = QLineEdit(t.get("script", ""))
        self.script_edit.setStyleSheet(ENTRY_STYLE)
        self.script_edit.setPlaceholderText("tasks/my_script.py *")
        sb = QPushButton("…")
        sb.setFixedSize(28, 34)
        sb.setStyleSheet("QPushButton { background-color: #444; color: white; border: none; border-radius: 3px; } QPushButton:hover { background-color: #555; }")
        sb.clicked.connect(self._browse_script)
        frow("Script *", self.script_edit, sb)

        self.desc_edit = QLineEdit(t.get("description", ""))
        self.desc_edit.setStyleSheet(ENTRY_STYLE)
        frow("Mô tả", self.desc_edit)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #333; max-height: 1px; margin: 4px 0;")
        cl.addWidget(sep)

        # Params header
        ph = QHBoxLayout()
        ptl = QLabel("Tham số")
        ptl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        ptl.setStyleSheet("color: white; background: transparent;")
        ph.addWidget(ptl)
        ph.addStretch()
        ap = QPushButton("+ Thêm tham số")
        ap.setStyleSheet("QPushButton { background-color: #2a2a3e; color: #7eb8f7; border: none; padding: 4px 10px; border-radius: 3px; } QPushButton:hover { background-color: #3a3a5e; }")
        ap.clicked.connect(self._add_param)
        ph.addWidget(ap)
        cl.addLayout(ph)

        self._pc = QWidget()
        self._pc.setStyleSheet("background: transparent;")
        self._pl = QVBoxLayout(self._pc)
        self._pl.setContentsMargins(0, 0, 0, 0)
        self._pl.setSpacing(4)
        cl.addWidget(self._pc)
        cl.addStretch()

        self._rebuild_params()
        scroll.setWidget(content)
        ml.addWidget(scroll, 1)

        # Button bar
        bb = QWidget()
        bb.setFixedHeight(56)
        bb.setStyleSheet("background-color: #13131f; border-top: 1px solid #2a2a2a;")
        bbl = QHBoxLayout(bb)
        bbl.setContentsMargins(16, 0, 16, 0)
        bbl.addStretch()
        self._save_btn = QPushButton("Lưu tác vụ")
        self._save_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self._refresh_save_btn()
        self._save_btn.clicked.connect(self._submit)
        cancel = QPushButton("Hủy")
        cancel.setStyleSheet(BTN_DARK)
        cancel.clicked.connect(self.reject)
        bbl.addWidget(self._save_btn)
        bbl.addWidget(cancel)
        ml.addWidget(bb)

    def _on_label_change(self, text):
        if not self._init_task.get("id"):
            auto = "".join(c if (c.isascii() and (c.isalnum() or c == "_")) else "_"
                           for c in text.lower().replace(" ", "_"))
            self.id_edit.setText(auto)

    def _refresh_color_btn(self):
        self.color_btn.setText(self._color)
        self.color_btn.setStyleSheet(
            f"QPushButton {{ background-color: {self._color}; color: white; border: none;"
            f" border-radius: 3px; text-align: left; padding-left: 10px; }}"
            f" QPushButton:hover {{ background-color: {_lighten(self._color)}; }}"
        )

    def _refresh_save_btn(self):
        self._save_btn.setStyleSheet(
            f"QPushButton {{ background-color: {self._color}; color: white; border: none;"
            f" padding: 7px 20px; border-radius: 4px; }}"
            f" QPushButton:hover {{ background-color: {_lighten(self._color)}; }}"
        )

    def _pick_icon(self):
        dlg = IconPickerDialog(self, self.icon_edit.text())
        if dlg.exec_() == QDialog.Accepted:
            self.icon_edit.setText(dlg.result)

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self, "Chọn màu")
        if c.isValid():
            self._color = c.name()
            self._refresh_color_btn()
            self._refresh_save_btn()
            self._header.setStyleSheet(f"background-color: {self._color};")

    def _browse_script(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn script Python",
                                              str(Path(__file__).parent), "Python (*.py)")
        if path:
            try:
                rel = Path(path).relative_to(Path(__file__).parent)
                self.script_edit.setText(str(rel).replace("\\", "/"))
            except ValueError:
                self.script_edit.setText(path)

    def _rebuild_params(self):
        while self._pl.count():
            item = self._pl.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._params:
            e = QLabel("Chưa có tham số nào")
            e.setStyleSheet("color: #555; background: transparent; font: italic 9pt 'Segoe UI';")
            e.setAlignment(Qt.AlignCenter)
            e.setFixedHeight(34)
            self._pl.addWidget(e)
            return

        bs = ("QPushButton {{ background: {bg}; color: white; border: none; border-radius: 3px;"
              " padding: 0 8px; font: 8pt 'Segoe UI'; }} QPushButton:hover {{ background: {hov}; }}")

        for i, p in enumerate(self._params):
            rw = QWidget()
            rw.setStyleSheet("background-color: #2a2a3e; border-radius: 4px;")
            rw.setFixedHeight(36)
            rl = QHBoxLayout(rw)
            rl.setContentsMargins(10, 0, 6, 0)
            rl.setSpacing(6)

            tb = QLabel(p.get("type", "text"))
            tb.setFixedWidth(52)
            tb.setAlignment(Qt.AlignCenter)
            tb.setStyleSheet("color: #7eb8f7; background: #1e1e2e; border-radius: 3px; padding: 2px 4px; font: 8pt 'Segoe UI';")
            req = QLabel("*" if p.get("required") else "")
            req.setFixedWidth(10)
            req.setStyleSheet("color: #ff6b6b; background: transparent; font: bold 11pt 'Segoe UI';")
            nl = QLabel(p["name"])
            nl.setStyleSheet("color: white; background: transparent; font: bold 9pt 'Segoe UI';")
            ll = QLabel(p.get("label", ""))
            ll.setStyleSheet("color: #aaa; background: transparent; font: 9pt 'Segoe UI';")

            rl.addWidget(tb)
            rl.addWidget(req)
            rl.addWidget(nl)
            rl.addWidget(ll)
            rl.addStretch()

            for txt, bg, hov, slot in [
                ("↑", "#333", "#555", lambda _, idx=i: self._move_param(idx, -1)),
                ("↓", "#333", "#555", lambda _, idx=i: self._move_param(idx, 1)),
                ("Sửa", "#2a4a7a", "#3a5a9a", lambda _, idx=i: self._edit_param(idx)),
                ("Xóa", "#6b2020", "#8b3030", lambda _, idx=i: self._del_param(idx)),
            ]:
                b = QPushButton(txt)
                b.setFixedHeight(24)
                if txt in ("↑", "↓"):
                    b.setFixedWidth(24)
                b.setStyleSheet(bs.format(bg=bg, hov=hov))
                b.clicked.connect(slot)
                rl.addWidget(b)

            self._pl.addWidget(rw)

    def _add_param(self):
        dlg = ParamEditorDialog(self)
        if dlg.exec_() == QDialog.Accepted and dlg.result:
            self._params.append(dlg.result)
            self._rebuild_params()

    def _edit_param(self, idx):
        dlg = ParamEditorDialog(self, self._params[idx])
        if dlg.exec_() == QDialog.Accepted and dlg.result:
            self._params[idx] = dlg.result
            self._rebuild_params()

    def _del_param(self, idx):
        self._params.pop(idx)
        self._rebuild_params()

    def _move_param(self, idx, d):
        ni = idx + d
        if 0 <= ni < len(self._params):
            self._params[idx], self._params[ni] = self._params[ni], self._params[idx]
            self._rebuild_params()

    def _submit(self):
        label = self.label_edit.text().strip()
        script = self.script_edit.text().strip()
        if not label or not script:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập Nhãn và đường dẫn Script.")
            return
        task_id = self.id_edit.text().strip() or label.lower().replace(" ", "_")
        self.result = {
            "id": task_id, "label": label,
            "icon": self.icon_edit.text().strip(),
            "color": self._color, "script": script,
            "description": self.desc_edit.text().strip(),
            "params": self._params,
        }
        self.accept()


# ─── Profile Dialog ────────────────────────────────────────────────────────────

class ProfileDialog(QDialog):
    def __init__(self, parent, existing_names, initial_name=""):
        super().__init__(parent)
        self.result = None
        self._existing = existing_names
        self.setWindowTitle("Đổi tên hồ sơ" if initial_name else "Tạo hồ sơ mới")
        self.setFixedWidth(380)
        self.setStyleSheet("background-color: #1e1e2e; color: white;")
        self._build_ui(initial_name)

    def _build_ui(self, initial_name):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        lbl = QLabel("Tên hồ sơ:")
        lbl.setStyleSheet(LBL_STYLE)
        layout.addWidget(lbl)

        self.name_edit = QLineEdit(initial_name)
        self.name_edit.setStyleSheet(ENTRY_STYLE)
        self.name_edit.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self.name_edit)

        self.copy_combo = None
        if self._existing and not initial_name:
            cr = QHBoxLayout()
            cl = QLabel("Copy từ hồ sơ:")
            cl.setStyleSheet(LBL_STYLE)
            cl.setFixedWidth(110)
            cr.addWidget(cl)
            self.copy_combo = QComboBox()
            self.copy_combo.addItem("(Để trống)")
            self.copy_combo.addItems(self._existing)
            self.copy_combo.setStyleSheet(COMBO_STYLE)
            cr.addWidget(self.copy_combo, 1)
            layout.addLayout(cr)

        bl = QHBoxLayout()
        bl.addStretch()
        ok = QPushButton("Tạo" if not initial_name else "Lưu")
        ok.setStyleSheet(BTN_BLUE)
        ok.clicked.connect(self._submit)
        cancel = QPushButton("Hủy")
        cancel.setStyleSheet(BTN_DARK)
        cancel.clicked.connect(self.reject)
        bl.addWidget(ok)
        bl.addWidget(cancel)
        layout.addLayout(bl)

    def _submit(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Thiếu tên", "Vui lòng nhập tên hồ sơ.")
            return
        copy_from = None
        if self.copy_combo and self.copy_combo.currentIndex() > 0:
            copy_from = self.copy_combo.currentText()
        self.result = {"name": name, "copy_from": copy_from}
        self.accept()


# ─── Card Button Widget ────────────────────────────────────────────────────────

class CardButton(QWidget):
    clicked = pyqtSignal()
    edit_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    clone_requested = pyqtSignal()

    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.base_color = cfg.get("color", "#444")
        self.hover_color = _lighten(self.base_color)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAttribute(Qt.WA_Hover)
        self._build_ui(cfg)
        self._set_color(self.base_color)

    def _build_ui(self, cfg):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 14)
        layout.setSpacing(2)

        # Toolbar — hidden until hover
        self._toolbar = QWidget()
        self._toolbar.setStyleSheet("background: transparent;")
        self._toolbar.setVisible(False)
        tbl = QHBoxLayout(self._toolbar)
        tbl.setContentsMargins(0, 0, 0, 0)
        tbl.setSpacing(3)
        tbl.addStretch()

        abs_ = ("QPushButton {{ background-color: rgba(0,0,0,55); color: rgba(255,255,255,200);"
                " border: none; border-radius: 3px; font: bold 10pt 'Segoe UI'; }}"
                " QPushButton:hover {{ background-color: {hov}; color: white; }}")

        for icon, tip, hov, sig in [
            ("✎", "Sửa tác vụ",     "rgba(255,255,255,80)",  self.edit_requested),
            ("⧉", "Nhân bản",        "rgba(255,255,255,80)",  self.clone_requested),
            ("✕", "Xóa tác vụ",     "rgba(200,40,40,200)",   self.delete_requested),
        ]:
            b = QPushButton(icon)
            b.setFixedSize(24, 22)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(abs_.format(hov=hov))
            b.clicked.connect(sig)
            tbl.addWidget(b)

        layout.addWidget(self._toolbar)

        # Content
        center = QWidget()
        center.setStyleSheet("background: transparent;")
        cl = QVBoxLayout(center)
        cl.setContentsMargins(8, 2, 8, 4)
        cl.setAlignment(Qt.AlignCenter)
        cl.setSpacing(4)

        if cfg.get("icon"):
            il = QLabel(cfg["icon"])
            il.setFont(QFont("Segoe UI", 20))
            il.setStyleSheet("color: white; background: transparent;")
            il.setAlignment(Qt.AlignCenter)
            cl.addWidget(il)

        nl = QLabel(cfg["label"])
        nl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        nl.setStyleSheet("color: white; background: transparent;")
        nl.setAlignment(Qt.AlignCenter)
        nl.setWordWrap(True)
        cl.addWidget(nl)

        if cfg.get("description"):
            dl = QLabel(cfg["description"])
            dl.setFont(QFont("Segoe UI", 8))
            dl.setStyleSheet("color: rgba(255,255,255,170); background: transparent;")
            dl.setAlignment(Qt.AlignCenter)
            dl.setWordWrap(True)
            cl.addWidget(dl)

        if cfg.get("params"):
            pl = QLabel(f"{len(cfg['params'])} tham số")
            pl.setFont(QFont("Segoe UI", 8))
            pl.setStyleSheet("color: rgba(255,255,255,170); background: transparent;")
            pl.setAlignment(Qt.AlignCenter)
            cl.addWidget(pl)

        layout.addWidget(center, 1)

    def _set_color(self, color):
        self.setStyleSheet(f"CardButton {{ background-color: {color}; border-radius: 6px; }}")

    def event(self, e):
        if e.type() == QEvent.HoverEnter:
            self._set_color(self.hover_color)
            self._toolbar.setVisible(True)
        elif e.type() == QEvent.HoverLeave:
            self._set_color(self.base_color)
            self._toolbar.setVisible(False)
        return super().event(e)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


# ─── Dashboard ────────────────────────────────────────────────────────────────

class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_data = load_config()
        self.setWindowTitle(self.config_data.get("title", "Dashboard"))
        self.setStyleSheet("QMainWindow { background-color: #1e1e2e; }")
        self._build_ui()
        self._center()

    @property
    def current_profile(self):
        name = self.config_data.get("active_profile", "")
        for p in self.config_data["profiles"]:
            if p["name"] == name:
                return p
        return self.config_data["profiles"][0]

    def _center(self):
        screen = QApplication.primaryScreen().geometry()
        size = self.sizeHint()
        self.move((screen.width() - size.width()) // 2,
                  (screen.height() - size.height()) // 2)

    def _build_ui(self):
        central = QWidget()
        central.setStyleSheet("background-color: #1e1e2e;")
        self.setCentralWidget(central)
        ml = QVBoxLayout(central)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)

        # Title bar
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet("background-color: #13131f;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(16, 0, 12, 0)
        bl.setSpacing(8)

        title_lbl = QLabel("Dashboard")
        title_lbl.setFont(QFont("Segoe UI", 15, QFont.Bold))
        title_lbl.setStyleSheet("color: white; background: transparent;")
        bl.addWidget(title_lbl)

        bl.addSpacing(12)

        # Profile combo
        self.profile_combo = QComboBox()
        self.profile_combo.setFixedHeight(30)
        self.profile_combo.setMinimumWidth(140)
        self.profile_combo.setStyleSheet(
            "QComboBox { background-color: #2a2a3e; color: white; border: none; padding: 2px 10px; border-radius: 4px; }"
            " QComboBox::drop-down { border: none; }"
            " QComboBox QAbstractItemView { background-color: #2a2a3e; color: white; selection-background-color: #3a3a5e; }"
        )
        self.profile_combo.currentTextChanged.connect(self._switch_profile)
        bl.addWidget(self.profile_combo)

        # Profile menu button
        menu_btn = QPushButton("⋮")
        menu_btn.setFont(QFont("Segoe UI", 14))
        menu_btn.setFixedSize(30, 30)
        menu_btn.setToolTip("Quản lý hồ sơ")
        menu_btn.setStyleSheet(
            "QPushButton { background-color: transparent; color: #888; border: none; border-radius: 4px; }"
            " QPushButton:hover { background-color: #2a2a3e; color: white; }"
        )
        menu_btn.clicked.connect(self._show_profile_menu)
        bl.addWidget(menu_btn)

        bl.addStretch()

        self.count_lbl = QLabel()
        self.count_lbl.setFont(QFont("Segoe UI", 9))
        self.count_lbl.setStyleSheet("color: #555; background: transparent;")
        bl.addWidget(self.count_lbl)

        bl.addSpacing(8)

        add_btn = QPushButton("＋  Thêm tác vụ")
        add_btn.setFont(QFont("Segoe UI", 9))
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(
            "QPushButton { background-color: #2a2a3e; color: #7eb8f7; border: none;"
            " padding: 6px 14px; border-radius: 4px; }"
            " QPushButton:hover { background-color: #3a3a5e; }"
        )
        add_btn.clicked.connect(self._add_task)
        bl.addWidget(add_btn)

        ml.addWidget(bar)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #2a2a2a; max-height: 1px;")
        ml.addWidget(sep)

        # Grid
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background-color: #1e1e2e;")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)
        self.grid_layout.setSpacing(12)
        ml.addWidget(self.grid_widget, 1)

        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet(
            "QStatusBar { background-color: #13131f; color: #555; font: 9pt 'Segoe UI'; }")

        self._refresh_profile_combo()
        self._rebuild_grid()

    # ── Profile helpers ────────────────────────────────────────────────────────

    def _refresh_profile_combo(self):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems([p["name"] for p in self.config_data["profiles"]])
        self.profile_combo.setCurrentText(self.config_data.get("active_profile", ""))
        self.profile_combo.blockSignals(False)

    def _switch_profile(self, name):
        if name == self.config_data.get("active_profile") or not name:
            return
        self.config_data["active_profile"] = name
        save_config(self.config_data)
        self._rebuild_grid()

    def _show_profile_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        menu.addAction("＋  Tạo hồ sơ mới", self._new_profile)
        menu.addAction("✎  Đổi tên hồ sơ hiện tại", self._rename_profile)
        menu.addAction("✕  Xóa hồ sơ hiện tại", self._delete_profile)
        menu.addSeparator()
        menu.addAction("↺  Khôi phục tác vụ mặc định", self._restore_defaults)
        menu.exec_(QCursor.pos())

    def _new_profile(self):
        existing = [p["name"] for p in self.config_data["profiles"]]
        dlg = ProfileDialog(self, existing)
        if dlg.exec_() != QDialog.Accepted or not dlg.result:
            return
        name = dlg.result["name"]
        if any(p["name"] == name for p in self.config_data["profiles"]):
            QMessageBox.warning(self, "Trùng tên", f"Hồ sơ '{name}' đã tồn tại.")
            return
        copy_from = dlg.result["copy_from"]
        if copy_from:
            src = next((p for p in self.config_data["profiles"] if p["name"] == copy_from), None)
            new_p = copy.deepcopy(src)
            new_p["name"] = name
        else:
            new_p = {"name": name, "title": name, "columns": 3, "buttons": []}
        self.config_data["profiles"].append(new_p)
        self.config_data["active_profile"] = name
        save_config(self.config_data)
        self._refresh_profile_combo()
        self._rebuild_grid()
        self.status_bar.showMessage(f"Đã tạo hồ sơ: {name}")

    def _rename_profile(self):
        current_name = self.current_profile["name"]
        dlg = ProfileDialog(self, [], initial_name=current_name)
        if dlg.exec_() != QDialog.Accepted or not dlg.result:
            return
        new_name = dlg.result["name"]
        if new_name != current_name and any(p["name"] == new_name for p in self.config_data["profiles"]):
            QMessageBox.warning(self, "Trùng tên", f"Hồ sơ '{new_name}' đã tồn tại.")
            return
        self.current_profile["name"] = new_name
        self.config_data["active_profile"] = new_name
        save_config(self.config_data)
        self._refresh_profile_combo()
        self.status_bar.showMessage(f"Đã đổi tên thành: {new_name}")

    def _delete_profile(self):
        if len(self.config_data["profiles"]) <= 1:
            QMessageBox.warning(self, "Không thể xóa", "Phải giữ lại ít nhất một hồ sơ.")
            return
        name = self.current_profile["name"]
        reply = QMessageBox.question(
            self, "Xóa hồ sơ",
            f"Bạn có chắc muốn xóa hồ sơ '{name}'?\nTất cả tác vụ trong hồ sơ này sẽ bị mất.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self.config_data["profiles"] = [p for p in self.config_data["profiles"] if p["name"] != name]
        self.config_data["active_profile"] = self.config_data["profiles"][0]["name"]
        save_config(self.config_data)
        self._refresh_profile_combo()
        self._rebuild_grid()
        self.status_bar.showMessage(f"Đã xóa hồ sơ: {name}")

    def _restore_defaults(self):
        name = self.current_profile["name"]
        reply = QMessageBox.question(
            self, "Khôi phục mặc định",
            f"Thay thế toàn bộ tác vụ của hồ sơ '{name}' bằng danh sách mặc định?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.current_profile["buttons"] = copy.deepcopy(DEFAULT_BUTTONS)
            save_config(self.config_data)
            self._rebuild_grid()
            self.status_bar.showMessage("Đã khôi phục danh sách tác vụ mặc định.")

    # ── Grid ──────────────────────────────────────────────────────────────────

    def _rebuild_grid(self):
        prof = self.current_profile
        cols = prof.get("columns", 3)

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, btn_cfg in enumerate(prof["buttons"]):
            row, col = divmod(i, cols)
            card = CardButton(self.grid_widget, btn_cfg)
            card.clicked.connect(lambda c=btn_cfg: self._handle_button(c))
            card.edit_requested.connect(lambda c=btn_cfg: self._edit_task(c))
            card.clone_requested.connect(lambda c=btn_cfg: self._clone_task(c))
            card.delete_requested.connect(lambda c=btn_cfg: self._delete_task(c))
            self.grid_layout.addWidget(card, row, col)

        for c in range(cols):
            self.grid_layout.setColumnStretch(c, 1)

        self.count_lbl.setText(f"{len(prof['buttons'])} tác vụ")
        self.status_bar.showMessage("Sẵn sàng")

    # ── Task CRUD ──────────────────────────────────────────────────────────────

    def _add_task(self):
        dlg = TaskEditorDialog(self)
        if dlg.exec_() == QDialog.Accepted and dlg.result:
            self.current_profile["buttons"].append(dlg.result)
            save_config(self.config_data)
            self._rebuild_grid()
            self.status_bar.showMessage(f"Đã thêm: {dlg.result['label']}")

    def _edit_task(self, cfg):
        dlg = TaskEditorDialog(self, cfg)
        if dlg.exec_() == QDialog.Accepted and dlg.result:
            buttons = self.current_profile["buttons"]
            idx = next((i for i, b in enumerate(buttons) if b.get("id") == cfg.get("id")), None)
            if idx is not None:
                buttons[idx] = dlg.result
            save_config(self.config_data)
            self._rebuild_grid()
            self.status_bar.showMessage(f"Đã cập nhật: {dlg.result['label']}")

    def _clone_task(self, cfg):
        new_task = copy.deepcopy(cfg)
        new_task["id"] = cfg.get("id", "task") + "_copy"
        new_task["label"] = cfg["label"] + " (Copy)"
        self.current_profile["buttons"].append(new_task)
        save_config(self.config_data)
        self._rebuild_grid()
        self.status_bar.showMessage(f"Đã nhân bản: {cfg['label']}")

    def _delete_task(self, cfg):
        reply = QMessageBox.question(
            self, "Xóa tác vụ",
            f"Bạn có chắc muốn xóa tác vụ '{cfg['label']}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.current_profile["buttons"] = [
                b for b in self.current_profile["buttons"] if b.get("id") != cfg.get("id")
            ]
            save_config(self.config_data)
            self._rebuild_grid()
            self.status_bar.showMessage(f"Đã xóa: {cfg['label']}")

    # ── Run script ─────────────────────────────────────────────────────────────

    def _handle_button(self, cfg):
        if cfg.get("params"):
            dlg = ParamDialog(self, cfg)
            if dlg.exec_() != QDialog.Accepted:
                return
            args = dlg.result or {}
        else:
            args = {}
        self._run_script(cfg, args)

    def _run_script(self, cfg, args):
        script = Path(__file__).parent / cfg["script"]
        if not script.exists():
            QMessageBox.critical(self, "Lỗi", f"Script không tồn tại:\n{script}")
            return

        cmd = [sys.executable, str(script)]
        for k, v in args.items():
            cmd += [f"--{k}", str(v)]

        label = cfg["label"]
        self.status_bar.showMessage(f"Đang chạy: {label}…")

        panel = OutputPanel(self, label)
        panel.show()
        panel.append(f"$ {' '.join(cmd)}\n\n", "success")

        signals = WorkerSignals()
        signals.text_ready.connect(lambda t, g: panel.append(t, g))
        signals.finished.connect(self.status_bar.showMessage)

        def worker():
            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", errors="replace",
                    cwd=str(Path(__file__).parent),
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                )
                for line in proc.stdout:
                    signals.text_ready.emit(line, "")
                stderr_out = proc.stderr.read()
                if stderr_out:
                    signals.text_ready.emit("\n[STDERR]\n" + stderr_out, "error")
                rc = proc.wait()
                signals.text_ready.emit(f"\n[Thoát với mã: {rc}]\n",
                                        "success" if rc == 0 else "error")
                signals.finished.emit(f"Hoàn thành: {label} (code {rc})")
            except Exception as ex:
                signals.text_ready.emit(f"\nLỗi: {ex}\n", "error")
                signals.finished.emit("Lỗi khi chạy script")

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec_())
