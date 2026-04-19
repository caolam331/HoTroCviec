"""
Live Clipboard Translator
Tự động dịch khi người dùng copy text vào clipboard.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QStatusBar, QTextEdit, QVBoxLayout, QWidget,
)

# ── CLI args (tương thích với task runner của main.py) ────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--source_lang", default="auto")
parser.add_argument("--target_lang", default="vi")
parser.add_argument("--copy_result", default="True")
args, _ = parser.parse_known_args()

LANG_LABELS = {
    "auto": "Tự động",
    "en":   "English",
    "vi":   "Tiếng Việt",
    "ja":   "日本語",
    "ko":   "한국어",
    "zh":   "中文",
    "fr":   "Français",
    "de":   "Deutsch",
    "es":   "Español",
    "ru":   "Русский",
    "th":   "ภาษาไทย",
}
SOURCE_LANGS = list(LANG_LABELS.keys())
TARGET_LANGS = [k for k in LANG_LABELS if k != "auto"]


# ── Translate ─────────────────────────────────────────────────────────────────
def google_translate(text: str, sl: str, tl: str) -> str:
    url = (
        "https://translate.googleapis.com/translate_a/single"
        f"?client=gtx&sl={sl}&tl={tl}&dt=t&q={urllib.parse.quote(text)}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return "".join(seg[0] for seg in data[0] if seg[0])


# ── Clipboard worker ───────────────────────────────────────────────────────────
class ClipboardWatcher(QThread):
    new_text = pyqtSignal(str)

    def __init__(self, interval_ms: int = 400):
        super().__init__()
        self._interval = interval_ms / 1000
        self._last = ""
        self._running = True

    def run(self):
        while self._running:
            try:
                cb = QApplication.clipboard().text()
                if cb and cb != self._last:
                    self._last = cb
                    self.new_text.emit(cb)
            except Exception:
                pass
            time.sleep(self._interval)

    def stop(self):
        self._running = False


class TranslateWorker(QThread):
    done = pyqtSignal(str, str)   # (translation, detected_lang)
    error = pyqtSignal(str)

    def __init__(self, text: str, sl: str, tl: str):
        super().__init__()
        self.text = text
        self.sl = sl
        self.tl = tl

    def run(self):
        try:
            result = google_translate(self.text, self.sl, self.tl)
            self.done.emit(result, self.sl)
        except urllib.error.URLError as e:
            self.error.emit(f"Lỗi mạng: {e.reason}")
        except Exception as e:
            self.error.emit(str(e))


# ── Styles ────────────────────────────────────────────────────────────────────
DARK_BG    = "#1E1E2E"
SURFACE    = "#2A2A3E"
SURFACE2   = "#313145"
ACCENT     = "#7C5CFC"
ACCENT2    = "#5B8DEF"
TEXT_PRI   = "#CDD6F4"
TEXT_SEC   = "#6C7086"
SUCCESS    = "#A6E3A1"
ERROR_CLR  = "#F38BA8"
BORDER     = "#45475A"

STYLE_SHEET = f"""
QMainWindow, QWidget {{
    background: {DARK_BG};
    color: {TEXT_PRI};
    font-family: 'Segoe UI', Arial, sans-serif;
}}
QComboBox {{
    background: {SURFACE2};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px 10px;
    min-width: 130px;
    font-size: 13px;
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE2};
    color: {TEXT_PRI};
    selection-background-color: {ACCENT};
    border: 1px solid {BORDER};
}}
QTextEdit {{
    background: {SURFACE};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 10px;
    font-size: 14px;
    line-height: 1.5;
}}
QPushButton {{
    background: {ACCENT};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton:hover {{ background: #9B7FFD; }}
QPushButton:pressed {{ background: #6A4EDB; }}
QPushButton#secondary {{
    background: {SURFACE2};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    font-weight: 400;
}}
QPushButton#secondary:hover {{ background: {BORDER}; }}
QLabel#header {{
    font-size: 18px;
    font-weight: 700;
    color: {TEXT_PRI};
    letter-spacing: 0.5px;
}}
QLabel#lang_label {{
    font-size: 11px;
    font-weight: 600;
    color: {TEXT_SEC};
    text-transform: uppercase;
    letter-spacing: 1px;
}}
QLabel#status_dot {{
    font-size: 11px;
    color: {TEXT_SEC};
}}
QFrame#divider {{
    background: {BORDER};
    max-width: 1px;
    margin: 0 6px;
}}
QStatusBar {{
    background: {SURFACE};
    color: {TEXT_SEC};
    font-size: 12px;
    border-top: 1px solid {BORDER};
}}
"""


# ── Main Window ───────────────────────────────────────────────────────────────
class TranslatorWindow(QMainWindow):
    def __init__(self, sl: str, tl: str, copy_result: bool):
        super().__init__()
        self.sl = sl
        self.tl = tl
        self.copy_result = copy_result
        self._translate_worker: TranslateWorker | None = None
        self._last_text = ""
        self._char_count = 0
        self._loading_step = 0
        self._loading_timer = QTimer(self)
        self._loading_timer.setInterval(450)
        self._loading_timer.timeout.connect(self._tick_loading)

        self.setWindowTitle("Clipboard Translator")
        self.setMinimumSize(760, 520)
        self.resize(860, 600)
        self.setStyleSheet(STYLE_SHEET)

        self._build_ui()
        self._start_watcher()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(16, 12, 16, 12)
        main.setSpacing(10)

        # Header row
        hdr = QHBoxLayout()
        hdr.setSpacing(10)

        icon_lbl = QLabel("🌐")
        icon_lbl.setFont(QFont("Segoe UI Emoji", 20))
        title = QLabel("Clipboard Translator")
        title.setObjectName("header")

        self._status_dot = QLabel("● Đang theo dõi clipboard…")
        self._status_dot.setObjectName("status_dot")

        hdr.addWidget(icon_lbl)
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(self._status_dot)
        main.addLayout(hdr)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background:{BORDER}; max-height:1px;")
        main.addWidget(sep)

        # Lang bar
        lang_bar = QHBoxLayout()
        lang_bar.setSpacing(8)

        sl_lbl = QLabel("NGUỒN")
        sl_lbl.setObjectName("lang_label")
        self._sl_combo = self._make_combo(SOURCE_LANGS, self.sl)
        self._sl_combo.currentIndexChanged.connect(self._on_lang_change)

        swap_btn = QPushButton("⇄")
        swap_btn.setObjectName("secondary")
        swap_btn.setFixedWidth(36)
        swap_btn.setToolTip("Đổi ngôn ngữ")
        swap_btn.clicked.connect(self._swap_langs)

        tl_lbl = QLabel("ĐÍCH")
        tl_lbl.setObjectName("lang_label")
        self._tl_combo = self._make_combo(TARGET_LANGS, self.tl)
        self._tl_combo.currentIndexChanged.connect(self._on_lang_change)

        self._copy_btn = QPushButton("📋 Sao chép bản dịch")
        self._copy_btn.setObjectName("secondary")
        self._copy_btn.clicked.connect(self._copy_translation)

        self._retranslate_btn = QPushButton("↺ Dịch lại")
        self._retranslate_btn.setObjectName("secondary")
        self._retranslate_btn.clicked.connect(self._retranslate)

        self._pin_btn = QPushButton("📌")
        self._pin_btn.setObjectName("secondary")
        self._pin_btn.setFixedWidth(36)
        self._pin_btn.setToolTip("Ghim luôn trên cùng")
        self._pin_btn.setCheckable(True)
        self._pin_btn.clicked.connect(self._toggle_pin)

        lang_bar.addWidget(sl_lbl)
        lang_bar.addWidget(self._sl_combo)
        lang_bar.addWidget(swap_btn)
        lang_bar.addWidget(tl_lbl)
        lang_bar.addWidget(self._tl_combo)
        lang_bar.addStretch()
        lang_bar.addWidget(self._retranslate_btn)
        lang_bar.addWidget(self._copy_btn)
        lang_bar.addWidget(self._pin_btn)
        main.addLayout(lang_bar)

        # Text panels
        panels = QHBoxLayout()
        panels.setSpacing(10)

        src_box = QVBoxLayout()
        src_lbl = QLabel("Văn bản gốc")
        src_lbl.setObjectName("lang_label")
        self._src_edit = QTextEdit()
        self._src_edit.setReadOnly(True)
        self._src_edit.setPlaceholderText("Copy bất kỳ text nào để bắt đầu dịch…")
        src_box.addWidget(src_lbl)
        src_box.addWidget(self._src_edit)

        dst_box = QVBoxLayout()
        dst_lbl = QLabel("Bản dịch")
        dst_lbl.setObjectName("lang_label")
        self._dst_edit = QTextEdit()
        self._dst_edit.setReadOnly(True)
        self._dst_edit.setPlaceholderText("Kết quả dịch sẽ hiển thị ở đây…")
        self._dst_edit.setStyleSheet(
            f"background:{SURFACE}; border-color:{ACCENT}; color:{TEXT_PRI};"
            f"border-radius:8px; padding:10px; font-size:14px;"
        )
        dst_box.addWidget(dst_lbl)
        dst_box.addWidget(self._dst_edit)

        panels.addLayout(src_box)
        panels.addLayout(dst_box)
        main.addLayout(panels, stretch=1)

        # Status bar
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._sb_label = QLabel("Chờ clipboard…")
        sb.addWidget(self._sb_label)
        self._char_label = QLabel("")
        sb.addPermanentWidget(self._char_label)

    def _make_combo(self, langs: list, default: str) -> QComboBox:
        cb = QComboBox()
        for k in langs:
            cb.addItem(LANG_LABELS.get(k, k), k)
        idx = langs.index(default) if default in langs else 0
        cb.setCurrentIndex(idx)
        return cb

    # ── Watcher ───────────────────────────────────────────────────────────────
    def _start_watcher(self):
        self._watcher = ClipboardWatcher()
        self._watcher.new_text.connect(self._on_clipboard)
        self._watcher.start()

    def _on_clipboard(self, text: str):
        self._last_text = text
        self._src_edit.setPlainText(text)
        self._char_label.setText(f"{len(text)} ký tự")
        self._trigger_translate(text)

    # ── Translation ───────────────────────────────────────────────────────────
    def _tick_loading(self):
        dots = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
        self._loading_step = (self._loading_step + 1) % len(dots)
        self._status_dot.setText(f"{dots[self._loading_step]}  Đang dịch…")
        self._status_dot.setStyleSheet(f"color:{ACCENT2}; font-size:13px;")

    def _trigger_translate(self, text: str):
        if not text.strip():
            return
        sl = self._sl_combo.currentData()
        tl = self._tl_combo.currentData()
        self._loading_step = 0
        self._loading_timer.start()
        self._dst_edit.setPlainText("")
        self._dst_edit.setPlaceholderText("⏳  Đang dịch…")

        if self._translate_worker and self._translate_worker.isRunning():
            self._translate_worker.quit()

        self._translate_worker = TranslateWorker(text, sl, tl)
        self._translate_worker.done.connect(self._on_translated)
        self._translate_worker.error.connect(self._on_error)
        self._translate_worker.start()

    def _on_translated(self, result: str, detected: str):
        self._loading_timer.stop()
        self._dst_edit.setPlaceholderText("Kết quả dịch sẽ hiển thị ở đây…")
        self._dst_edit.setPlainText(result)
        tl = self._tl_combo.currentData()
        sl_name = LANG_LABELS.get(detected, detected)
        tl_name = LANG_LABELS.get(tl, tl)
        self._set_status(f"✓ {sl_name} → {tl_name}", SUCCESS)
        self._sb_label.setText(
            f"Gốc: {len(self._last_text)} ký tự  ·  Dịch: {len(result)} ký tự"
        )

    def _on_error(self, msg: str):
        self._loading_timer.stop()
        self._dst_edit.setPlaceholderText("Kết quả dịch sẽ hiển thị ở đây…")
        self._dst_edit.setPlainText(f"[Lỗi] {msg}")
        self._set_status(f"✗ {msg}", ERROR_CLR)

    def _set_status(self, text: str, color: str = TEXT_SEC):
        self._status_dot.setText(text)
        self._status_dot.setStyleSheet(f"color:{color}; font-size:11px;")

    # ── Actions ───────────────────────────────────────────────────────────────
    def _swap_langs(self):
        sl = self._sl_combo.currentData()
        tl = self._tl_combo.currentData()
        if sl == "auto":
            return
        sl_idx = SOURCE_LANGS.index(tl) if tl in SOURCE_LANGS else 0
        tl_idx = TARGET_LANGS.index(sl) if sl in TARGET_LANGS else 0
        self._sl_combo.setCurrentIndex(sl_idx)
        self._tl_combo.setCurrentIndex(tl_idx)

    def _on_lang_change(self):
        if self._last_text:
            self._trigger_translate(self._last_text)

    def _copy_translation(self):
        text = self._dst_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self._set_status("📋 Đã sao chép!", ACCENT2)
            QTimer.singleShot(2000, lambda: self._set_status("● Đang theo dõi clipboard…", TEXT_SEC))

    def _retranslate(self):
        if self._last_text:
            self._trigger_translate(self._last_text)

    def _toggle_pin(self, checked: bool):
        flags = self.windowFlags()
        if checked:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
            self._pin_btn.setToolTip("Bỏ ghim")
            self._pin_btn.setStyleSheet(f"background:{ACCENT}; color:white; border-radius:6px;")
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
            self._pin_btn.setToolTip("Ghim luôn trên cùng")
            self._pin_btn.setStyleSheet("")
        self.show()

    def closeEvent(self, event):
        self._watcher.stop()
        self._watcher.wait(500)
        event.accept()


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    sl = args.source_lang
    tl = args.target_lang
    copy_result = str(args.copy_result).lower() in ("true", "1", "yes")

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")

    win = TranslatorWindow(sl, tl, copy_result)
    win.show()
    win.raise_()
    win.activateWindow()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
else:
    main()
