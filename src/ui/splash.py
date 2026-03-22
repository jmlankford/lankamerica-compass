"""
splash.py — Splash screen for LankAmerica Compass
"""
from PyQt6.QtWidgets import QSplashScreen, QApplication
from PyQt6.QtGui import QPixmap, QFont, QColor, QPainter, QFontMetrics
from PyQt6.QtCore import Qt, QTimer, QRect
from pathlib import Path
from src.utils import get_assets_dir


class SplashScreen(QSplashScreen):
    def __init__(self):
        assets = get_assets_dir()
        logo_path = assets / "logo.png"

        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            if not pixmap.isNull():
                pixmap = pixmap.scaledToWidth(400, Qt.TransformationMode.SmoothTransformation)
            else:
                pixmap = self._make_text_pixmap()
        else:
            pixmap = self._make_text_pixmap()

        # Add extra height for tagline + progress bar
        final = QPixmap(pixmap.width(), pixmap.height() + 80)
        final.fill(QColor("#FFFFFF"))
        painter = QPainter(final)
        painter.drawPixmap(0, 0, pixmap)

        # Tagline
        font = QFont("Segoe UI", 12)
        painter.setFont(font)
        painter.setPen(QColor("#0D2B5C"))
        rect = QRect(0, pixmap.height() + 6, pixmap.width(), 28)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Personal Financial Planner")

        # Progress bar background
        bar_y = pixmap.height() + 44
        bar_h = 8
        bar_x = 20
        bar_w = pixmap.width() - 40
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#e0e8f0"))
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 4, 4)
        painter.setBrush(QColor("#E07B39"))
        painter.drawRoundedRect(bar_x, bar_y, int(bar_w * 0.0), bar_h, 4, 4)
        painter.end()

        super().__init__(final)
        self._pixmap_base = pixmap
        self._bar_x = bar_x
        self._bar_y = bar_y
        self._bar_w = bar_w
        self._bar_h = bar_h
        self._progress = 0
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        # Center on screen
        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.geometry()
            self.move(
                sg.center().x() - self.width() // 2,
                sg.center().y() - self.height() // 2
            )

        self._timer = QTimer()
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _make_text_pixmap(self) -> QPixmap:
        w, h = 440, 160
        pix = QPixmap(w, h)
        pix.fill(QColor("#FFFFFF"))
        p = QPainter(pix)
        p.setPen(QColor("#0D2B5C"))

        font = QFont("Segoe UI", 26, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(QRect(0, 30, w, 80), Qt.AlignmentFlag.AlignCenter, "LankAmerica Compass")

        font2 = QFont("Segoe UI", 13)
        p.setFont(font2)
        p.setPen(QColor("#1565C0"))
        p.drawText(QRect(0, 100, w, 40), Qt.AlignmentFlag.AlignCenter, "Financial Planning Made Simple")
        p.end()
        return pix

    def _tick(self):
        self._progress += 4
        if self._progress > 100:
            self._progress = 100
            self._timer.stop()
        self._redraw()

    def _redraw(self):
        canvas = self.pixmap().copy()
        painter = QPainter(canvas)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#e0e8f0"))
        painter.drawRoundedRect(
            self._bar_x, self._bar_y, self._bar_w, self._bar_h, 4, 4
        )
        filled = int(self._bar_w * self._progress / 100)
        painter.setBrush(QColor("#E07B39"))
        painter.drawRoundedRect(
            self._bar_x, self._bar_y, filled, self._bar_h, 4, 4
        )
        painter.end()
        self.setPixmap(canvas)

    def finish_with_delay(self, callback, ms: int = 2500):
        """Call callback after ms milliseconds."""
        QTimer.singleShot(ms, lambda: (self.close(), callback()))
