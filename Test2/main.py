"""Desktop buddy widget (Tkinter + pystray) that uses `gemini_client.generate_text`."""

import sys
print("[DEBUG] Python executable:", sys.executable)
print("[DEBUG] Python version:", sys.version)

import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
print("[DEBUG] Imported tkinter")

import pystray
print("[DEBUG] Imported pystray")

from PIL import Image, ImageDraw
print("[DEBUG] Imported PIL")

import os
import time

try:
    from gemini_client import generate_text, list_models
    print("[DEBUG] Imported gemini_client")
except Exception as e:
    print("[ERROR] Failed to import gemini_client:", e)
    # graceful fallbacks so UI won't crash if import fails
    def generate_text(prompt, max_output_tokens=200):
        raise RuntimeError("gemini_client not available")
    def list_models():
        raise RuntimeError("gemini_client not available")

def create_image() -> Image.Image:
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, 60, 60), fill=(255, 200, 100))
    d.ellipse((20, 22, 30, 32), fill=(255, 255, 255))
    d.ellipse((36, 22, 46, 32), fill=(255, 255, 255))
    d.arc((22, 30, 42, 50), start=0, end=180, fill=(80, 50, 30))
    return img


class ChatWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Buddy — Practice")
        self.root.geometry("420x320")

        self.text = ScrolledText(root, state='disabled', width=50, height=15)
        self.text.pack(padx=8, pady=6)

        bottom = tk.Frame(root)
        bottom.pack(fill='x', padx=8, pady=6)

        self.entry = tk.Entry(bottom, width=40)
        self.entry.pack(side='left', fill='x', expand=True)
        self.entry.bind('<Return>', self.send_message)

        send_btn = tk.Button(bottom, text="Send", command=self.send_message)
        send_btn.pack(side='left', padx=(6,0))

        # Button to list available models from the Gemini API
        models_btn = tk.Button(bottom, text="List Models", command=self.list_models_action)
        models_btn.pack(side='left', padx=(6,0))

    def append(self, sender: str, msg: str):
        self.text.configure(state='normal')
        self.text.insert('end', f"{sender}: {msg}\n\n")
        self.text.see('end')
        self.text.configure(state='disabled')

    def send_message(self, event=None):
        user_msg = self.entry.get().strip()
        if not user_msg:
            return
        self.entry.delete(0, 'end')
        self.append("You", user_msg)
        threading.Thread(target=self.get_bot_reply, args=(user_msg,), daemon=True).start()

    def get_bot_reply(self, prompt: str):
        system_prompt = (
            "You are a compassionate social coach for neurodivergent users. "
            "1) Reply as a friendly conversational partner. "
            "2) Provide 1-2 concise, actionable suggestions to improve the user's next response. "
            "Keep suggestions short, concrete, and supportive."
        )
        full_prompt = system_prompt + "\n\nUser: " + prompt
        try:
            reply = generate_text(full_prompt, max_output_tokens=200)
        except Exception as e:
            reply = f"(Error contacting Gemini API: {e})"
        # Ensure UI updates run on the Tk main thread
        self.root.after(0, lambda: self.append("Buddy", reply))

    def list_models_action(self):
        # Inform the user and run the network call off the UI thread
        self.append("System", "Listing available models...")
        threading.Thread(target=self._fetch_and_show_models, daemon=True).start()

    def _fetch_and_show_models(self):
        try:
            models = list_models()
            # annotate embedding models
            names = []
            text_capable_found = False
            for m in models:
                nm = m.get("name", str(m)) if isinstance(m, dict) else str(m)
                lower = nm.lower()
                if "embed" in lower or "embedding" in lower:
                    names.append(f"{nm} (embedding-only)")
                else:
                    names.append(nm)
                    text_capable_found = True
            msg = "Available models:\n" + "\n".join(names)
            if not text_capable_found:
                msg += (
                    "\n\nNote: No text-generation-capable models were detected. "
                    "Embedding models (marked above) cannot generate chat responses. "
                    "To fix this: ensure your API key/account has access to a generative/text model "
                    "(e.g. models/gemini-1.0 or bison/*), or set the GEMINI_MODEL environment variable "
                    "to a text-capable model name."
                )
        except Exception as e:
            msg = f"(Error listing models: {e})"
        # update UI on the main thread
        self.root.after(0, lambda: self.append("System", msg))


def start_tray(root: tk.Tk):
    image = create_image()
    icon = pystray.Icon("buddy", image, "Buddy")

    def on_click(icon_obj, item=None):
        # Schedule showing the window on the Tk main thread
        root.after(0, show_window)

    def show_window():
        if not root.winfo_viewable():
            root.deiconify()
            root.lift()

    # Add a menu to quit the app
    icon.menu = pystray.Menu(pystray.MenuItem('Open', lambda _: root.after(0, show_window)),
                            pystray.MenuItem('Quit', lambda _: (icon.stop(), root.quit())))

    def run_icon():
        try:
            icon.run()
        except Exception:
            pass

    t = threading.Thread(target=run_icon, daemon=True)
    t.start()


def main():
    print("[DEBUG] Starting app...")
    root = tk.Tk()
    print("[DEBUG] Created Tk root")
    root.deiconify()
    root.lift()
    print("[DEBUG] Window visible")
    app = ChatWindow(root)
    print("[DEBUG] Created chat window")

    print("[DEBUG] Starting tray icon...")
    start_tray(root)
    print("[DEBUG] Tray icon started")

    def first_run_message():
        app.append("System", "Click the tray icon and choose 'Open' to show this window.\nFirst-run: ensure GOOGLE_APPLICATION_CREDENTIALS is set or GEMINI_API_KEY is set.")

    root.after(200, first_run_message)

    try:
        root.mainloop()
    finally:
        time.sleep(0.1)


if __name__ == '__main__':
    main()
