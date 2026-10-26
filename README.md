# Quick Selection Translator (Windows)

A lightweight, system-wide floating translator for Windows. Highlight text anywhere (Chrome, Edge, PDF readers, Word, Discord) and press **Alt+T** to get an instant translation popup next to your cursor.

## Features
- **Works Everywhere:** Translates text across all browsers and desktop apps.
- **One-Click Language Switching:** Switch between **Telugu**, **Hindi**, and **English** instantly inside the popup.
- **Interactive Floating Window:** Draggable, 8-way resizable, scrollable for long passages, and stays on top until closed.
- **Quick Copy:** Copy the entire translation with one click or highlight specific words.

## Download & Use (No Python Required)
1. Go to the **[Releases](../../releases)** page on the right side of this repository.
2. Download `translator_app.exe` and double-click it to run it silently in the background.
3. Highlight any text on your screen and press **`Alt + T`**.
4. **Optional (Auto-Start with Windows):** Press `Win + R`, type `shell:startup`, press Enter, and place a shortcut to `translator_app.exe` inside that folder.

## Run from Source (For Developers)
```bash
pip install -r requirements.txt
python translator_app.py
```
