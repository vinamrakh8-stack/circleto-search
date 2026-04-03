import sys, time, io, webbrowser
import numpy as np
import mss
import pyautogui
import cv2

from PIL import Image
import win32clipboard

from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QComboBox
)
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QPoint, QRect

# -------- Clipboard --------
def copy_image_to_clipboard(img):
    output = io.BytesIO()
    img.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:]
    output.close()

    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    win32clipboard.CloseClipboard()

# -------- Overlay --------
class Overlay(QWidget):
    def __init__(self, target, mode, parent=None):
        super().__init__()
        self.start = QPoint()
        self.end = QPoint()
        self.points = []
        self.drawing = False

        self.target = target
        self.mode = mode
        self.parent = parent

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.showFullScreen()
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)

        # dark overlay
        painter.setBrush(QColor(0, 0, 0, 120))
        painter.drawRect(self.rect())

        if self.mode == "Rectangle":
            if not self.start.isNull() and not self.end.isNull():
                rect = QRect(self.start, self.end)

                # clear selected area (no drawing in final image)
                painter.setCompositionMode(QPainter.CompositionMode_Clear)
                painter.drawRect(rect)

                # optional border (only visual, not in image)
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                painter.setPen(QPen(QColor(0, 255, 0), 2))
                painter.drawRect(rect)

        elif self.mode == "Pencil":
            if len(self.points) > 1:
                painter.setPen(QPen(QColor(0, 150, 255), 3))
                for i in range(len(self.points) - 1):
                    painter.drawLine(self.points[i], self.points[i+1])

    # -------- Mouse --------
    def mousePressEvent(self, e):
        if self.mode == "Rectangle":
            self.start = e.pos()
            self.end = self.start
        else:
            self.drawing = True
            self.points = [e.pos()]
        self.update()

    def mouseMoveEvent(self, e):
        if self.mode == "Rectangle":
            self.end = e.pos()
        else:
            if self.drawing:
                self.points.append(e.pos())
        self.update()

    def mouseReleaseEvent(self, e):
        if self.mode == "Rectangle":
            self.end = e.pos()
        else:
            self.drawing = False
            self.points.append(e.pos())

        self.capture_and_search()

        # reset
        self.start = QPoint()
        self.end = QPoint()
        self.points = []
        self.update()

        self.close()
        if self.parent:
            self.parent.show()  # FIX: allows reuse

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            if self.parent:
                self.parent.show()

    # -------- Capture --------
    def capture_and_search(self):
        with mss.mss() as sct:
            screen = np.array(sct.grab(sct.monitors[1]))

        if self.mode == "Rectangle":
            x1 = min(self.start.x(), self.end.x())
            y1 = min(self.start.y(), self.end.y())
            x2 = max(self.start.x(), self.end.x())
            y2 = max(self.start.y(), self.end.y())

            if x2 - x1 < 5 or y2 - y1 < 5:
                return

            crop = screen[y1:y2, x1:x2]

        elif self.mode == "Pencil":
            if len(self.points) < 3:
                return

            pts = np.array([[p.x(), p.y()] for p in self.points], dtype=np.int32)
            x, y, w, h = cv2.boundingRect(pts)
            crop = screen[y:y+h, x:x+w]

        img = Image.fromarray(crop)
        copy_image_to_clipboard(img)
        open_target(self.target)

# -------- Open Target --------
def open_target(target):
    if target == "Google":
        webbrowser.open("https://lens.google.com/")
        time.sleep(2)
        pyautogui.hotkey("ctrl", "v")

    elif target == "ChatGPT":
        webbrowser.open("https://chat.openai.com/")
        time.sleep(2)
        pyautogui.hotkey("ctrl", "v")

    elif target == "Copilot":
        webbrowser.open("https://copilot.microsoft.com/")
        time.sleep(2)
        pyautogui.hotkey("ctrl", "v")

# -------- Main UI --------
class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rectangle + Pencil Search App")
        self.setGeometry(300, 200, 320, 250)

        layout = QVBoxLayout()

        layout.addWidget(QLabel("Select Search Platform"))
        self.platform = QComboBox()
        self.platform.addItems(["Google", "ChatGPT", "Copilot"])
        layout.addWidget(self.platform)

        layout.addWidget(QLabel("Select Mode"))
        self.mode = QComboBox()
        self.mode.addItems(["Rectangle", "Pencil"])
        layout.addWidget(self.mode)

        self.start_btn = QPushButton("Start Selection")
        self.start_btn.clicked.connect(self.start_overlay)
        layout.addWidget(self.start_btn)

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.clicked.connect(self.close)
        layout.addWidget(self.exit_btn)

        self.setLayout(layout)

    def start_overlay(self):
        self.hide()
        self.overlay = Overlay(
            self.platform.currentText(),
            self.mode.currentText(),
            parent=self
        )
        self.overlay.show()

# -------- Run --------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec_())