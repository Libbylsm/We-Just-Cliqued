import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout, QStackedWidget
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QScreen

import json
import random
from google import genai

# -------------------------------
# Config/Initialisation
# -------------------------------

def get_client():
    """Initialize Gemini client."""
    return genai.Client(api_key="AIzaSyCdEiOJY_7be_TPXjvlPkYhFD7-vOoiRqo")

# -------------------------------
# Dialogue Handling
# -------------------------------

def load_dialogue(filename="dialogue.json"):
    """Load JSON file with conversation"""
    with open(filename, "r") as f:
        data = json.load(f)
    return data.get("dialogue", [])

def get_other_speaker(dialogue, user_speaker):
    """Retrieve other speaker, given who the user is"""
    for line in dialogue:
        speaker = line.get("speaker")
        if speaker and speaker != user_speaker:
            return speaker
    # If no other speaker found, return a placeholder
    return "OtherSpeaker"

def append_to_dialogue(dialogue, speaker, text):
    """Add a new line to dialogue list"""
    dialogue.append({"speaker": speaker, "line": text})

# -------------------------------
# Prompt Building
# -------------------------------

def build_user_response_options_prompt(dialogue, user_speaker, last_line):
    """Build prompt asking Gemini to generate 4 possible user responses in random order.
    Responses: polite/neurotypical, rude, neurodivergent, walk away (randomized).
    """
    context = "\n".join(f"{d['speaker']}: {d['line']}" for d in dialogue)
    prompt = f"""
You are simulating a conversation between speakers.

Conversation so far:
{context}

The other speaker just said:
"{last_line}"

Generate these 3 possible types of responses for {user_speaker}:
1. Polite/neurotypical (least backlash)
2. Obviously rude
3. Neurodivergent-style (honest but may seem rude)

Ensure these are human-like, natural responses.

Then include a 4th option: "Walk away." (no response)

Return strictly in this format without anything before/after
[
  {{"type": "polite", "text": "..."}},
  {{"type": "rude", "text": "..."}},
  {{"type": "neurodivergent", "text": "..."}},
  {{"type": "walk_away", "text": "Walk away"}}
]
"""
    return prompt

def build_speaker_response_prompt(dialogue, speaker, last_line):
    """Build prompt asking Gemini to generate a response from the other speaker,
    based on the previous lines in the dialogue.
    """
    context = "\n".join(f"{d['speaker']}: {d['line']}" for d in dialogue)
    prompt = f"""
You are simulating a conversation.

One speaker is "{speaker}".
The last line from the other talking party is:
"{last_line}"

Based on the conversation so far and maintaining the personality consistently so far, generate a natural human-like response from "{speaker}". 

Return only the text.
"""
    return prompt

def build_analysis_prompt(dialogue, speaker, text):
    """Build prompt asking Gemini to analyse the other speaker's response
    """
    context = "\n".join(f"{d['speaker']}: {d['line']}" for d in dialogue)
    prompt = f"""
You are an expert in conversational analysis.

You are given a dialogue between two people so far:
{context}

The speaker of the last line spoken is {speaker} and they have just said {text}

Analyse their last line.
Focus on:
- Tone and emotional nuance  
- Implied meaning or subtext  
- Possible intent or motivation  
- How the line affects the conversation dynamic

Return a concise but helpful explanation (3–5 sentences).
"""
    return prompt

def build_feedback_prompt(dialogue, speaker, text):
    """Build prompt asking Gemini to give feedback on user's decision - how it aligns with neurotypicals and implications that may be interpreted
    """
    context = "\n".join(f"{d['speaker']}: {d['line']}" for d in dialogue)
    prompt = f"""
You are an expert in social communication coaching, helping neurodiverse people understand how their words might be interpreted by neurotypical listeners.

You are given a dialogue between two people so far:
{context}

Focus on the last line spoken by {speaker}, which is {text} and provide feedback as if you are advising a neurodiverse person who wants to understand how their words might be received by neurotypicals.

Explain how the speaker’s last line might be perceived by neurotypical people. If any possible unintended negative interpretations (e.g., sounding rude, dismissive, defensive, blunt), point them out. Offer gentle, concrete advice or alternative phrasing that could convey the same intent more clearly or diplomatically.

Return a concise but helpful explanation (3–5 sentences).

"""
    return prompt


# -------------------------------
# Gemini API Calls
# -------------------------------

def ask_gemini(client, prompt, model="gemini-2.5-flash"):
    """Send a prompt and return the model's response"""
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text.strip()

# -------------------------------
# Text Display / User Interaction
# -------------------------------

def conv_options_str_to_list(options_str):
    # print("Current string input of options")
    # print(options_str)
    options_list = json.loads(options_str)
    return options_list

######################################################


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

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt, QTimer

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QHBoxLayout
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

class SimulateScreen(QWidget):
    """Chat simulation screen (visual novel style with 'Next' button)"""
    def __init__(self, switch_to_home):
        super().__init__()
        layout = QVBoxLayout()

        # --- Top bar with Back button ---
        back_btn = QPushButton("Back")
        back_btn.clicked.connect(switch_to_home)
        layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # --- Chat bubble (AI responses / dialogue text) ---
        self.chat_bubble = QLabel("Buddy: Hello! Ready to practice chatting?")
        self.chat_bubble.setWordWrap(True)
        self.chat_bubble.setStyleSheet(
            "background-color: #E0E0E0; border-radius: 10px; padding: 10px; font-size: 14px;"
        )
        layout.addWidget(self.chat_bubble)

        # --- ghost image + dialogue box layout ---
        char_layout = QHBoxLayout()

        # Display box (read-only, backend-driven text)
        self.display_box = QTextEdit()
        self.display_box.setReadOnly(True)
        self.display_box.setText("Buddy: Let's begin the conversation simulation.")
        self.display_box.setFixedHeight(80)
        self.display_box.setStyleSheet(
            "background-color: #f5f5f5; border-radius: 8px; padding: 8px; font-size: 14px;"
        )

        # "Next" button (replaces submit)
        self.next_btn = QPushButton("Next")
        self.next_btn.setFixedWidth(80)
        self.next_btn.clicked.connect(self.do_something)

        # Layout for text + button
        input_layout = QVBoxLayout()
        input_layout.addWidget(self.display_box)
        input_layout.addWidget(self.next_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # ghost image
        self.ghost = QLabel()
        self.ghost.setPixmap(QPixmap("ghost.png").scaled(
            150, 150, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))

        char_layout.addLayout(input_layout)
        char_layout.addWidget(self.ghost)

        layout.addLayout(char_layout)
        self.setLayout(layout)

        # Example dialogue sequence
        self.dialogue_lines = [
            "Buddy: Let's start with a quick warm-up.",
            "Buddy: Imagine you're meeting someone new at an event.",
            "Buddy: They smile and ask what you’re studying — how would you respond?",
            "Buddy: That’s great! Let’s move on to another scenario."
        ]
        self.current_line = 0

    # --- "Next" button functionality ---
    def do_something(self):
        """Advance through dialogue or trigger backend updates."""
        self.current_line += 1
        if self.current_line < len(self.dialogue_lines):
            self.display_box.setText(self.dialogue_lines[self.current_line])
        else:
            self.display_box.setText("Buddy: That’s all for now! 🎉")
            self.next_btn.setDisabled(True)




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
