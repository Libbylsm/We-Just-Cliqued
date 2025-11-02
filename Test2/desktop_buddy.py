import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout, QStackedWidget
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QScreen



class BuddyWidget(QWidget):
    """Tiny draggable widget with corner snapping"""
    SNAP_MARGIN = 10  # distance from screen edge after snapping

    def __init__(self, switch_to_home):
        super().__init__()

        # Load ghost
        pixmap = QPixmap("ghost.png").scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.ghost = QLabel(self)
        self.ghost.setPixmap(pixmap)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.ghost)
        self.setLayout(layout)

        # Window size slightly larger than ghost
        padding = 8
        self.setFixedSize(pixmap.width() + padding, pixmap.height() + padding)

        # Always on top, frameless
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.show()

        # Click ghost to expand
        self.ghost.mousePressEvent = lambda e: switch_to_home()

        # Dragging support
        self._is_dragging = False
        self._drag_start_position = None

    # --- Drag events ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if self._is_dragging:
            self._is_dragging = False
            self.snap_to_corner()

    # --- Snap the widget to nearest screen corner ---
    def snap_to_corner(self):
        screen_geometry = self.screen().geometry()  # get current screen
        x, y = self.x(), self.y()
        w, h = self.width(), self.height()
        margin = self.SNAP_MARGIN

        # Distances to corners
        distances = {
            "top_left": (x, y),
            "top_right": (screen_geometry.width() - x - w, y),
            "bottom_left": (x, screen_geometry.height() - y - h),
            "bottom_right": (screen_geometry.width() - x - w, screen_geometry.height() - y - h)
        }
        # Find nearest corner
        nearest_corner = min(distances, key=lambda k: distances[k][0]**2 + distances[k][1]**2)

        # Snap position
        if nearest_corner == "top_left":
            self.move(margin, margin)
        elif nearest_corner == "top_right":
            self.move(screen_geometry.width() - w - margin, margin)
        elif nearest_corner == "bottom_left":
            self.move(margin, screen_geometry.height() - h - margin)
        elif nearest_corner == "bottom_right":
            self.move(screen_geometry.width() - w - margin, screen_geometry.height() - h - margin)






class HomeScreen(QWidget):
    """Main menu: Simulate / Discuss / History"""
    def __init__(self, switch_to_simulate, switch_to_discuss, switch_to_history, switch_to_widget):
        super().__init__()
        layout = QVBoxLayout()

        self.title = QLabel("Welcome to Your Desktop Buddy!")
        self.title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(self.title, alignment=Qt.AlignmentFlag.AlignCenter)

        # Menu buttons
        for name, func in [("Simulate", switch_to_simulate),
                           ("Discuss", switch_to_discuss),
                           ("History", switch_to_history)]:
            btn = QPushButton(name)
            btn.setFixedHeight(40)
            btn.setStyleSheet("font-size: 16px; padding: 8px;")
            btn.clicked.connect(func)
            layout.addWidget(btn)

        # Minimize button
        minimize_btn = QPushButton("Minimize to Widget")
        minimize_btn.setFixedHeight(35)
        minimize_btn.setStyleSheet("font-size: 14px; padding: 6px;")
        minimize_btn.clicked.connect(switch_to_widget)
        layout.addWidget(minimize_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)



from PyQt6.QtGui import QKeyEvent
from PyQt6.QtCore import Qt

class SimulateScreen(QWidget):
    """Chat simulation screen"""
    def __init__(self, switch_to_home):
        super().__init__()
        layout = QVBoxLayout()

        # Top bar with back button
        back_btn = QPushButton("Back")
        back_btn.clicked.connect(switch_to_home)
        layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # Chat bubble (AI responses)
        self.chat_bubble = QLabel("Buddy: Hello! Ready to practice chatting?")
        self.chat_bubble.setWordWrap(True)
        self.chat_bubble.setStyleSheet(
            "background-color: #E0E0E0; border-radius: 10px; padding: 10px; font-size: 14px;"
        )
        layout.addWidget(self.chat_bubble)

        # ghost image + user input layout
        char_layout = QHBoxLayout()
        self.user_input = QTextEdit()
        self.user_input.setPlaceholderText("Type your response here...")
        self.user_input.setFixedHeight(50)

        self.submit_btn = QPushButton("Submit")
        self.submit_btn.setFixedWidth(80)
        self.submit_btn.clicked.connect(self.submit_text)

        # Put user input and submit button in a vertical layout
        input_layout = QVBoxLayout()
        input_layout.addWidget(self.user_input)
        input_layout.addWidget(self.submit_btn)

        self.ghost = QLabel()
        self.ghost.setPixmap(QPixmap("ghost.png").scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio))

        char_layout.addLayout(input_layout)
        char_layout.addWidget(self.ghost)

        layout.addLayout(char_layout)
        self.setLayout(layout)

    # --- Override keyPressEvent to handle Enter ---
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Return and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            # Enter pressed without Shift → submit
            self.submit_text()
            event.accept()
        else:
            super().keyPressEvent(event)

    # --- Submit callback ---
    def submit_text(self):
        user_msg = self.user_input.toPlainText().strip()
        if not user_msg:
            return
        self.chat_bubble.setText(f"You: {user_msg}")
        self.user_input.clear()

        # Here you would later call your Gemini backend (Placeholder for Gemini API response):
        # threading.Thread(target=self.get_gemini_response, args=(user_msg,), daemon=True).start()




class DiscussScreen(QWidget):
    """Placeholder"""
    def __init__(self, switch_to_home):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Discuss Page (coming soon)"))
        btn = QPushButton("Back")
        btn.clicked.connect(switch_to_home)
        layout.addWidget(btn)
        self.setLayout(layout)


class HistoryScreen(QWidget):
    """Chat history page"""
    def __init__(self, switch_to_home):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Chat History (coming soon)"))
        del_btn = QPushButton("Delete History")
        back_btn = QPushButton("Back")
        back_btn.clicked.connect(switch_to_home)
        layout.addWidget(del_btn)
        layout.addWidget(back_btn)
        self.setLayout(layout)


class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desktop Buddy")

        self.stack = QStackedWidget()
        self.widget = BuddyWidget(self.show_home)
        # pass switch_to_widget as last parameter
        self.home = HomeScreen(self.show_simulate, self.show_discuss, self.show_history, self.show_widget)
        self.simulate = SimulateScreen(self.show_home)
        self.discuss = DiscussScreen(self.show_home)
        self.history = HistoryScreen(self.show_home)

        for page in [self.widget, self.home, self.simulate, self.discuss, self.history]:
            self.stack.addWidget(page)

        layout = QVBoxLayout()
        layout.addWidget(self.stack)
        self.setLayout(layout)
        self.show_widget()  # start with small widget


    def show_widget(self):
        self.stack.setCurrentWidget(self.widget)
        self.resize(120, 120)

    def show_home(self):
        self.stack.setCurrentWidget(self.home)
        self.resize(400, 400)

    def show_simulate(self):
        self.stack.setCurrentWidget(self.simulate)
        self.resize(600, 400)

    def show_discuss(self):
        self.stack.setCurrentWidget(self.discuss)
        self.resize(400, 400)

    def show_history(self):
        self.stack.setCurrentWidget(self.history)
        self.resize(400, 400)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())
