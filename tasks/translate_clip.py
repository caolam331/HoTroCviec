"""
Live Clipboard Translator + Spell Checker
Tự động dịch hoặc kiểm tra chính tả khi người dùng copy text vào clipboard.
"""
import argparse
import html as _html
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

# ── CLI args ──────────────────────────────────────────────────────────────────
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
WARN_CLR   = "#FAB387"
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

# ── Spell check ────────────────────────────────────────────────────────────────
REMOTE_SERVER = "https://api.languagetool.org"

try:
    import language_tool_python as _ltp
    _spell_local: "_ltp.LanguageTool | None" = None
    _spell_remote: "_ltp.LanguageTool | None" = None
    HAS_SPELL = True

    def get_spell_tool(remote: bool = False):
        global _spell_local, _spell_remote
        if remote:
            if _spell_remote is None:
                _spell_remote = _ltp.LanguageTool('en-US', remote_server=REMOTE_SERVER)
            return _spell_remote
        else:
            if _spell_local is None:
                _spell_local = _ltp.LanguageTool('en-US')
            return _spell_local

except ImportError:
    HAS_SPELL = False

    def get_spell_tool(remote: bool = False):  # noqa: ARG001
        return None


def build_highlighted_html(text: str, match_dicts: list) -> str:
    """Build HTML with red-highlighted spelling/grammar errors from match dicts."""
    parts = []
    prev = 0
    for m in sorted(match_dicts, key=lambda x: x["offset"]):
        start = m["offset"]
        end = start + m["errorLength"]
        if start < prev or end > len(text):
            continue
        parts.append(_html.escape(text[prev:start]))
        err = _html.escape(text[start:end])
        tip = _html.escape(m["message"][:120])
        replacement = m["replacements"][0] if m["replacements"] else ""
        tip_full = f"{tip} → {_html.escape(replacement)}" if replacement else tip
        parts.append(
            f'<span style="background:{ERROR_CLR};color:#1E1E2E;border-radius:3px;'
            f'padding:1px 3px;cursor:help" title="{tip_full}">{err}</span>'
        )
        prev = end
    parts.append(_html.escape(text[prev:]))
    body = "".join(parts).replace("\n", "<br>")
    return (
        f'<div style="font-family:\'Segoe UI\',Arial,sans-serif;font-size:14px;'
        f'color:{TEXT_PRI};line-height:1.6">{body}</div>'
    )


# ── Workers ───────────────────────────────────────────────────────────────────
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
    done = pyqtSignal(str, str)
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


class SpellCheckWorker(QThread):
    done = pyqtSignal(list, str)   # (match_dicts, corrected_text)
    error = pyqtSignal(str)

    def __init__(self, text: str, remote: bool = False):
        super().__init__()
        self.text = text
        self.remote = remote

    @staticmethod
    def _get_len(m) -> int:
        """Find error-length attribute regardless of library version."""
        for attr in ("errorLength", "matchedLength", "length", "errorLen"):
            v = getattr(m, attr, None)
            if isinstance(v, int) and v > 0:
                return v
        # last resort: scan all attrs
        for attr in dir(m):
            if "length" in attr.lower():
                v = getattr(m, attr, None)
                if isinstance(v, int) and v > 0:
                    return v
        return 1

    def run(self):
        try:
            tool = get_spell_tool(remote=self.remote)
            matches = tool.check(self.text)

            # Debug: log actual Match attrs on first match
            if matches:
                import sys
                length_attrs = {a: getattr(matches[0], a) for a in dir(matches[0]) if not a.startswith("_")}
                print("Match attrs:", length_attrs, file=sys.stderr)

            # Build dicts without touching library utils (they use unstable attr names)
            match_dicts = [
                {
                    "offset": m.offset,
                    "errorLength": self._get_len(m),
                    "message": getattr(m, "message", ""),
                    "replacements": list(getattr(m, "replacements", []))[:5],
                }
                for m in matches
            ]

            # Apply corrections manually (no dependency on utils.correct)
            chars = list(self.text)
            delta = 0
            for d in match_dicts:
                if not d["replacements"]:
                    continue
                start = d["offset"] + delta
                end = start + d["errorLength"]
                rep = d["replacements"][0]
                chars[start:end] = list(rep)
                delta += len(rep) - d["errorLength"]
            corrected = "".join(chars)

            self.done.emit(match_dicts, corrected)
        except Exception as e:
            self.error.emit(str(e))


# ── Main Window ───────────────────────────────────────────────────────────────
class TranslatorWindow(QMainWindow):
    def __init__(self, sl: str, tl: str, copy_result: bool):
        super().__init__()
        self.sl = sl
        self.tl = tl
        self.copy_result = copy_result
        self._mode = "translate"          # 'translate' | 'spellcheck'
        self._server_remote = False       # False=local, True=remote
        self._translate_worker: TranslateWorker | None = None
        self._spell_worker: SpellCheckWorker | None = None
        self._last_text = ""
        self._loading_step = 0
        self._loading_timer = QTimer(self)
        self._loading_timer.setInterval(450)
        self._loading_timer.timeout.connect(self._tick_loading)

        self.setWindowTitle("Clipboard Translator & Spell Checker")
        self.setMinimumSize(800, 540)
        self.resize(900, 620)
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

        self._pin_btn = QPushButton("📌")
        self._pin_btn.setObjectName("secondary")
        self._pin_btn.setFixedWidth(36)
        self._pin_btn.setFixedHeight(30)
        self._pin_btn.setToolTip("Ghim luôn trên cùng")
        self._pin_btn.setCheckable(True)
        self._pin_btn.clicked.connect(self._toggle_pin)

        hdr.addWidget(icon_lbl)
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(self._status_dot)
        hdr.addWidget(self._pin_btn)
        main.addLayout(hdr)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background:{BORDER}; max-height:1px;")
        main.addWidget(sep)

        # ── Mode Toggle (pill-shaped segmented control) ────────────────────
        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(0)

        toggle_container = QFrame()
        toggle_container.setFixedHeight(38)
        toggle_container.setStyleSheet(
            f"QFrame {{ background:{SURFACE2}; border-radius:19px; "
            f"border:1px solid {BORDER}; }}"
        )
        tgl_layout = QHBoxLayout(toggle_container)
        tgl_layout.setContentsMargins(4, 4, 4, 4)
        tgl_layout.setSpacing(2)

        self._translate_mode_btn = QPushButton("🌐  Dịch")
        self._translate_mode_btn.setFixedHeight(28)
        self._translate_mode_btn.clicked.connect(lambda: self._set_mode("translate"))

        self._spell_mode_btn = QPushButton("✓  Sửa lỗi chính tả")
        self._spell_mode_btn.setFixedHeight(28)
        self._spell_mode_btn.clicked.connect(lambda: self._set_mode("spellcheck"))

        for btn in (self._translate_mode_btn, self._spell_mode_btn):
            btn.setStyleSheet("border-radius: 14px; padding: 2px 16px; font-size: 13px;")

        tgl_layout.addWidget(self._translate_mode_btn)
        tgl_layout.addWidget(self._spell_mode_btn)

        toggle_row.addStretch()
        toggle_row.addWidget(toggle_container)
        toggle_row.addStretch()
        main.addLayout(toggle_row)

        # ── Lang bar (translate mode only) ────────────────────────────────
        self._lang_bar_widget = QWidget()
        lang_bar = QHBoxLayout(self._lang_bar_widget)
        lang_bar.setContentsMargins(0, 0, 0, 0)
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
        self._copy_btn.clicked.connect(self._copy_output)

        self._action_btn = QPushButton("↺ Dịch lại")
        self._action_btn.setObjectName("secondary")
        self._action_btn.clicked.connect(self._redo_action)

        lang_bar.addWidget(sl_lbl)
        lang_bar.addWidget(self._sl_combo)
        lang_bar.addWidget(swap_btn)
        lang_bar.addWidget(tl_lbl)
        lang_bar.addWidget(self._tl_combo)
        lang_bar.addStretch()
        lang_bar.addWidget(self._action_btn)
        lang_bar.addWidget(self._copy_btn)
        main.addWidget(self._lang_bar_widget)

        # ── Spell mode action bar (hidden initially) ──────────────────────
        self._spell_bar_widget = QWidget()
        spell_bar = QHBoxLayout(self._spell_bar_widget)
        spell_bar.setContentsMargins(0, 0, 0, 0)
        spell_bar.setSpacing(8)

        self._error_count_lbl = QLabel("")
        self._error_count_lbl.setObjectName("lang_label")

        # Server toggle pill
        srv_container = QFrame()
        srv_container.setFixedHeight(30)
        srv_container.setStyleSheet(
            f"QFrame {{ background:{SURFACE2}; border-radius:15px; border:1px solid {BORDER}; }}"
        )
        srv_layout = QHBoxLayout(srv_container)
        srv_layout.setContentsMargins(3, 3, 3, 3)
        srv_layout.setSpacing(2)

        self._local_srv_btn = QPushButton("🖥 Local")
        self._local_srv_btn.setFixedHeight(22)
        self._local_srv_btn.clicked.connect(lambda: self._set_server(remote=False))

        self._remote_srv_btn = QPushButton("☁ Remote")
        self._remote_srv_btn.setFixedHeight(22)
        self._remote_srv_btn.clicked.connect(lambda: self._set_server(remote=True))

        for b in (self._local_srv_btn, self._remote_srv_btn):
            b.setStyleSheet("border-radius:11px; padding:0 10px; font-size:12px;")
        srv_layout.addWidget(self._local_srv_btn)
        srv_layout.addWidget(self._remote_srv_btn)

        self._copy_corrected_btn = QPushButton("📋 Sao chép bản đã sửa")
        self._copy_corrected_btn.clicked.connect(self._copy_output)

        self._recheck_btn = QPushButton("↺ Kiểm tra lại")
        self._recheck_btn.setObjectName("secondary")
        self._recheck_btn.clicked.connect(self._redo_action)

        spell_bar.addWidget(self._error_count_lbl)
        spell_bar.addStretch()
        spell_bar.addWidget(srv_container)
        spell_bar.addWidget(self._recheck_btn)
        spell_bar.addWidget(self._copy_corrected_btn)

        self._spell_bar_widget.setVisible(False)
        main.addWidget(self._spell_bar_widget)

        # Text panels
        panels = QHBoxLayout()
        panels.setSpacing(10)

        src_box = QVBoxLayout()
        self._src_lbl = QLabel("Văn bản gốc")
        self._src_lbl.setObjectName("lang_label")
        self._src_edit = QTextEdit()
        self._src_edit.setReadOnly(True)
        self._src_edit.setPlaceholderText("Copy bất kỳ text nào để bắt đầu…")
        src_box.addWidget(self._src_lbl)
        src_box.addWidget(self._src_edit)

        dst_box = QVBoxLayout()
        self._dst_lbl = QLabel("Bản dịch")
        self._dst_lbl.setObjectName("lang_label")
        self._dst_edit = QTextEdit()
        self._dst_edit.setReadOnly(True)
        self._dst_edit.setPlaceholderText("Kết quả sẽ hiển thị ở đây…")
        self._dst_edit.setStyleSheet(
            f"background:{SURFACE}; border-color:{ACCENT}; color:{TEXT_PRI};"
            f"border-radius:8px; padding:10px; font-size:14px;"
        )
        dst_box.addWidget(self._dst_lbl)
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

        self._update_toggle_style()
        self._update_server_style()

    def _make_combo(self, langs: list, default: str) -> QComboBox:
        cb = QComboBox()
        for k in langs:
            cb.addItem(LANG_LABELS.get(k, k), k)
        idx = langs.index(default) if default in langs else 0
        cb.setCurrentIndex(idx)
        return cb

    # ── Mode toggle ───────────────────────────────────────────────────────────
    def _set_mode(self, mode: str):
        if self._mode == mode:
            return
        self._mode = mode
        is_translate = mode == "translate"

        self._lang_bar_widget.setVisible(is_translate)
        self._spell_bar_widget.setVisible(not is_translate)

        if is_translate:
            self._dst_lbl.setText("Bản dịch")
            self._src_lbl.setText("Văn bản gốc")
            self._dst_edit.setStyleSheet(
                f"background:{SURFACE}; border-color:{ACCENT}; color:{TEXT_PRI};"
                f"border-radius:8px; padding:10px; font-size:14px;"
            )
            self._dst_edit.setPlaceholderText("Kết quả dịch sẽ hiển thị ở đây…")
            self._src_edit.setPlaceholderText("Copy bất kỳ text nào để bắt đầu dịch…")
        else:
            self._dst_lbl.setText("Văn bản đã sửa")
            self._src_lbl.setText("Văn bản gốc (lỗi được highlight đỏ)")
            self._dst_edit.setStyleSheet(
                f"background:{SURFACE}; border-color:{SUCCESS}; color:{TEXT_PRI};"
                f"border-radius:8px; padding:10px; font-size:14px;"
            )
            self._dst_edit.setPlaceholderText("Văn bản đã được sửa lỗi sẽ hiển thị ở đây…")
            self._src_edit.setPlaceholderText("Copy text tiếng Anh để kiểm tra lỗi chính tả…")
            if not HAS_SPELL:
                self._set_status("⚠ Cần cài: pip install language-tool-python", WARN_CLR)

        self._update_toggle_style()

        # Re-process current text in new mode
        if self._last_text:
            self._src_edit.setPlainText(self._last_text)
            self._dst_edit.clear()
            self._error_count_lbl.setText("")
            if is_translate:
                self._trigger_translate(self._last_text)
            else:
                self._trigger_spellcheck(self._last_text)

    def _update_toggle_style(self):
        active_style = (
            f"border-radius:14px; padding:2px 16px; font-size:13px;"
            f"background:{ACCENT}; color:white; border:none; font-weight:600;"
        )
        inactive_style = (
            f"border-radius:14px; padding:2px 16px; font-size:13px;"
            f"background:transparent; color:{TEXT_SEC}; border:none; font-weight:400;"
        )
        if self._mode == "translate":
            self._translate_mode_btn.setStyleSheet(active_style)
            self._spell_mode_btn.setStyleSheet(inactive_style)
        else:
            self._translate_mode_btn.setStyleSheet(inactive_style)
            self._spell_mode_btn.setStyleSheet(active_style)

    def _set_server(self, remote: bool):
        if self._server_remote == remote:
            return
        self._server_remote = remote
        self._update_server_style()
        label = "☁ Remote (api.languagetool.org)" if remote else "🖥 Local (localhost)"
        self._set_status(f"Server: {label}", ACCENT2)
        if self._last_text and self._mode == "spellcheck":
            self._trigger_spellcheck(self._last_text)

    def _update_server_style(self):
        active = (
            f"border-radius:11px; padding:0 10px; font-size:12px;"
            f"background:{ACCENT}; color:white; border:none; font-weight:600;"
        )
        inactive = (
            f"border-radius:11px; padding:0 10px; font-size:12px;"
            f"background:transparent; color:{TEXT_SEC}; border:none; font-weight:400;"
        )
        self._local_srv_btn.setStyleSheet(inactive if self._server_remote else active)
        self._remote_srv_btn.setStyleSheet(active if self._server_remote else inactive)

    # ── Watcher ───────────────────────────────────────────────────────────────
    def _start_watcher(self):
        self._watcher = ClipboardWatcher()
        self._watcher.new_text.connect(self._on_clipboard)
        self._watcher.start()

    def _on_clipboard(self, text: str):
        self._last_text = text
        self._src_edit.setPlainText(text)
        self._char_label.setText(f"{len(text)} ký tự")
        if self._mode == "translate":
            self._trigger_translate(text)
        else:
            self._trigger_spellcheck(text)

    # ── Translation ───────────────────────────────────────────────────────────
    def _tick_loading(self):
        dots = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
        self._loading_step = (self._loading_step + 1) % len(dots)
        label = "Đang dịch…" if self._mode == "translate" else "Đang kiểm tra…"
        self._status_dot.setText(f"{dots[self._loading_step]}  {label}")
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

    # ── Spell check ───────────────────────────────────────────────────────────
    def _trigger_spellcheck(self, text: str):
        if not text.strip():
            return
        if not HAS_SPELL:
            self._dst_edit.setPlainText(
                "⚠ Chưa cài language-tool-python.\n\n"
                "Chạy lệnh sau để cài:\n\n  pip install language-tool-python"
            )
            self._set_status("⚠ Thiếu thư viện", WARN_CLR)
            return

        self._loading_step = 0
        self._loading_timer.start()
        self._dst_edit.setPlainText("")
        self._dst_edit.setPlaceholderText("⏳  Đang kiểm tra lỗi chính tả…")
        self._error_count_lbl.setText("")

        if self._spell_worker and self._spell_worker.isRunning():
            self._spell_worker.quit()

        self._spell_worker = SpellCheckWorker(text, remote=self._server_remote)
        self._spell_worker.done.connect(self._on_spellchecked)
        self._spell_worker.error.connect(self._on_error)
        self._spell_worker.start()

    def _on_spellchecked(self, matches: list, corrected: str):
        self._loading_timer.stop()
        n = len(matches)

        # Highlight errors in source panel
        if n > 0:
            self._src_edit.setHtml(build_highlighted_html(self._last_text, matches))
        else:
            self._src_edit.setPlainText(self._last_text)

        # Show corrected text in destination panel
        self._dst_edit.setPlaceholderText("Văn bản đã được sửa lỗi sẽ hiển thị ở đây…")
        if n == 0:
            self._dst_edit.setPlainText("✓ Không tìm thấy lỗi nào!")
            self._error_count_lbl.setText("✓ Không có lỗi")
            self._error_count_lbl.setStyleSheet(f"color:{SUCCESS}; font-size:12px; font-weight:600;")
            self._set_status("✓ Không tìm thấy lỗi", SUCCESS)
        else:
            self._dst_edit.setPlainText(corrected)
            plural = "lỗi" if n == 1 else "lỗi"
            self._error_count_lbl.setText(f"⚠ Tìm thấy {n} {plural}")
            self._error_count_lbl.setStyleSheet(f"color:{WARN_CLR}; font-size:12px; font-weight:600;")
            self._set_status(f"⚠ {n} lỗi được tìm thấy", WARN_CLR)

        self._sb_label.setText(
            f"Gốc: {len(self._last_text)} ký tự  ·  {n} lỗi"
        )

    def _on_error(self, msg: str):
        self._loading_timer.stop()
        self._dst_edit.setPlaceholderText("")
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

    def _copy_output(self):
        text = self._dst_edit.toPlainText()
        if not text or text.startswith("✓ Không tìm thấy"):
            return
        QApplication.clipboard().setText(text)
        label = "📋 Đã sao chép bản dịch!" if self._mode == "translate" else "📋 Đã sao chép bản sửa!"
        self._set_status(label, ACCENT2)
        QTimer.singleShot(2000, lambda: self._set_status("● Đang theo dõi clipboard…", TEXT_SEC))

    def _redo_action(self):
        if not self._last_text:
            return
        if self._mode == "translate":
            self._trigger_translate(self._last_text)
        else:
            self._trigger_spellcheck(self._last_text)

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
