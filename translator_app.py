import os
import sys
import time
import threading
import queue
import urllib.request
import urllib.parse
import json
import winreg
import tkinter as tk
import keyboard
import pyperclip
import pystray
from PIL import Image, ImageDraw, ImageFont

SHORTCUT = 'alt+t'
current_lang = 'te'
LANGUAGES = [('Telugu', 'te'), ('Hindi', 'hi'), ('English', 'en')]
is_busy = False
ui_queue = queue.Queue()
APP_NAME = "QuickSelectionTranslator"

def get_exe_path():
    return sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)

def is_startup_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False

def set_startup(enable=True):
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
    if enable:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{get_exe_path()}" --silent')
    else:
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
    winreg.CloseKey(key)

def create_tray_image():
    img = Image.new('RGBA', (64, 64), color=(30, 30, 46, 255))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4, 4, 60, 60], radius=12, fill=(137, 180, 250, 255))
    d.text((20, 14), "T", fill=(17, 17, 27, 255), font_size=36)
    return img

def translate_text(text, target_lang):
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t"
    data = urllib.parse.urlencode({'q': text}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=8) as response:
        res = json.loads(response.read().decode('utf-8'))
        return "".join([item[0] for item in res[0] if item[0]])

def build_popup(master, original_text, initial_translation, initial_lang):
    for widget in master.winfo_children():
        if isinstance(widget, tk.Toplevel):
            widget.destroy()

    win = tk.Toplevel(master)
    win.overrideredirect(True)
    win.attributes("-topmost", True)

    cache = {initial_lang: initial_translation}
    active_state = {'text': initial_translation, 'lang': initial_lang}

    lines = (len(initial_translation) // 42) + initial_translation.count('\n') + 2
    init_w = 460 if len(initial_translation) > 140 else 390
    init_h = max(140, min(380, lines * 26 + 50))

    scr_w = win.winfo_screenwidth()
    scr_h = win.winfo_screenheight()
    x = min(win.winfo_pointerx() + 15, scr_w - init_w - 20)
    y = min(win.winfo_pointery() + 15, scr_h - init_h - 50)
    win.geometry(f"{init_w}x{init_h}+{max(10, x)}+{max(10, y)}")

    BORDER = 6
    outer = tk.Frame(win, bg="#45475a")
    outer.pack(fill="both", expand=True)

    inner = tk.Frame(outer, bg="#1e1e2e")
    inner.pack(fill="both", expand=True, padx=BORDER, pady=BORDER)

    header = tk.Frame(inner, bg="#181825", cursor="fleur")
    header.pack(fill="x")

    def start_move(event):
        win._drag_x = event.x_root - win.winfo_x()
        win._drag_y = event.y_root - win.winfo_y()

    def do_move(event):
        nx = event.x_root - win._drag_x
        ny = event.y_root - win._drag_y
        win.geometry(f"+{nx}+{ny}")

    header.bind("<ButtonPress-1>", start_move)
    header.bind("<B1-Motion>", do_move)

    lang_frame = tk.Frame(header, bg="#181825")
    lang_frame.pack(side="left", padx=4, pady=3)

    lang_btns = {}
    def update_lang_buttons(selected_code):
        for name, code in LANGUAGES:
            btn = lang_btns[code]
            if code == selected_code:
                btn.config(bg="#89b4fa", fg="#11111b", font=("Segoe UI", 9, "bold"))
            else:
                btn.config(bg="#313244", fg="#cdd6f4", font=("Segoe UI", 9))

    def set_text_box(new_text):
        if not win.winfo_exists():
            return
        active_state['text'] = new_text
        text_box.config(state="normal")
        text_box.delete("1.0", "end")
        text_box.insert("1.0", new_text)
        text_box.config(state="disabled")

    def switch_language(lang_code):
        global current_lang
        current_lang = lang_code
        active_state['lang'] = lang_code
        update_lang_buttons(lang_code)
        if lang_code in cache:
            set_text_box(cache[lang_code])
            return
        if not original_text:
            return
        set_text_box("Translating...")
        def fetch():
            try:
                res = translate_text(original_text, lang_code)
                cache[lang_code] = res
                ui_queue.put(lambda: set_text_box(res))
            except Exception as e:
                ui_queue.put(lambda err=e: set_text_box(f"Translation error: {err}"))
        threading.Thread(target=fetch, daemon=True).start()

    for name, code in LANGUAGES:
        b = tk.Button(
            lang_frame, text=f" {name} ", bd=0, cursor="hand2",
            padx=4, pady=1, command=lambda c=code: switch_language(c)
        )
        b.pack(side="left", padx=2)
        lang_btns[code] = b
    update_lang_buttons(initial_lang)

    close_btn = tk.Button(
        header, text=" ✕ ", fg="#f38ba8", bg="#181825",
        activebackground="#f38ba8", activeforeground="#11111b",
        bd=0, font=("Segoe UI", 9, "bold"), cursor="hand2", command=win.destroy
    )
    close_btn.pack(side="right", padx=4, pady=2)

    def copy_all():
        pyperclip.copy(active_state['text'])
        copy_btn.config(text=" ✓ Copied ", fg="#a6e3a1")
        win.after(1500, lambda: copy_btn.config(text=" 📋 Copy ", fg="#89b4fa") if win.winfo_exists() else None)

    copy_btn = tk.Button(
        header, text=" 📋 Copy ", fg="#89b4fa", bg="#181825",
        activebackground="#313244", activeforeground="#cdd6f4",
        bd=0, font=("Segoe UI", 9), cursor="hand2", command=copy_all
    )
    copy_btn.pack(side="right", padx=4, pady=2)

    body = tk.Frame(inner, bg="#1e1e2e")
    body.pack(fill="both", expand=True)

    scrollbar = tk.Scrollbar(
        body, orient="vertical", bg="#313244", troughcolor="#1e1e2e",
        activebackground="#585b70", highlightthickness=0, bd=0, width=10
    )
    scrollbar.pack(side="right", fill="y")

    text_box = tk.Text(
        body, fg="#cdd6f4", bg="#1e1e2e", font=("Nirmala UI", 12),
        wrap="word", bd=0, padx=12, pady=10, highlightthickness=0,
        selectbackground="#585b70", yscrollcommand=scrollbar.set
    )
    text_box.insert("1.0", initial_translation)
    text_box.config(state="disabled")
    text_box.bind("<Button-1>", lambda e: text_box.focus_set())
    text_box.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=text_box.yview)

    def get_resize_mode(ex, ey, w, h):
        m = ""
        if ey < BORDER + 4: m += "n"
        elif ey > h - BORDER - 4: m += "s"
        if ex < BORDER + 4: m += "w"
        elif ex > w - BORDER - 4: m += "e"
        return m

    cursors = {
        "n": "sb_v_double_arrow", "s": "sb_v_double_arrow",
        "e": "sb_h_double_arrow", "w": "sb_h_double_arrow",
        "ne": "size_ne_sw", "sw": "size_ne_sw",
        "nw": "size_nw_se", "se": "size_nw_se", "": ""
    }

    def on_border_motion(event):
        mode = get_resize_mode(event.x, event.y, win.winfo_width(), win.winfo_height())
        outer.config(cursor=cursors.get(mode, ""))

    def start_resize(event):
        win._rmode = get_resize_mode(event.x, event.y, win.winfo_width(), win.winfo_height())
        win._rx = event.x_root
        win._ry = event.y_root
        win._rw = win.winfo_width()
        win._rh = win.winfo_height()
        win._rwx = win.winfo_x()
        win._rwy = win.winfo_y()

    def do_resize(event):
        mode = getattr(win, "_rmode", "")
        if not mode: return
        dx = event.x_root - win._rx
        dy = event.y_root - win._ry
        nw, nh, nx, ny = win._rw, win._rh, win._rwx, win._rwy
        min_w, min_h = 280, 110
        if "e" in mode: nw = max(min_w, win._rw + dx)
        if "s" in mode: nh = max(min_h, win._rh + dy)
        if "w" in mode:
            nw = max(min_w, win._rw - dx)
            if nw > min_w: nx = win._rwx + dx
        if "n" in mode:
            nh = max(min_h, win._rh - dy)
            if nh > min_h: ny = win._rwy + dy
        win.geometry(f"{nw}x{nh}+{nx}+{ny}")

    outer.bind("<Motion>", on_border_motion)
    outer.bind("<ButtonPress-1>", start_resize)
    outer.bind("<B1-Motion>", do_resize)
    win.bind("<Escape>", lambda e: win.destroy())

def capture_and_translate():
    global is_busy
    if is_busy:
        return
    is_busy = True
    try:
        old_clipboard = pyperclip.paste()
        pyperclip.copy("")
        keyboard.release('alt')
        keyboard.release('t')
        time.sleep(0.08)
        keyboard.send('ctrl+c')
        time.sleep(0.15)
        selected_text = pyperclip.paste().strip()
        pyperclip.copy(old_clipboard)
        if not selected_text:
            return
        lang = current_lang
        translated = translate_text(selected_text, lang)
        ui_queue.put(lambda: build_popup(master_root, selected_text, translated, lang))
    except Exception as e:
        ui_queue.put(lambda err=e: build_popup(master_root, "", f"Translation error: {err}", current_lang))
    finally:
        time.sleep(0.5)
        is_busy = False

def toggle_startup(icon, item):
    set_startup(not is_startup_enabled())

def quit_app(icon, item):
    icon.stop()
    ui_queue.put(master_root.quit)

def setup_tray():
    # Automatically enable startup the very first time a user runs the .exe
    if getattr(sys, 'frozen', False) and "--silent" not in sys.argv:
        set_startup(True)

    menu = pystray.Menu(
        pystray.MenuItem("Quick Translator (Alt+T)", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Run on Windows Startup", toggle_startup, checked=lambda item: is_startup_enabled()),
        pystray.MenuItem("Exit Translator", quit_app)
    )
    icon = pystray.Icon(APP_NAME, create_tray_image(), "Quick Translator (Alt+T)", menu)
    threading.Thread(target=icon.run, daemon=True).start()

    if "--silent" not in sys.argv:
        ui_queue.put(lambda: build_popup(
            master_root,
            "Welcome! Quick Translator is now running in the background. Highlight any text and press Alt+T to translate.",
            "✅ Quick Translator is active!\n\n• Highlight any text and press Alt+T.\n• Switch between Telugu, Hindi, and English at the top.\n• Right-click the blue 'T' icon in your Windows system tray (near the clock) to exit or manage startup.",
            'en'
        ))

master_root = tk.Tk()
master_root.withdraw()

def poll_queue():
    while not ui_queue.empty():
        task = ui_queue.get()
        task()
    master_root.after(50, poll_queue)

keyboard.add_hotkey(SHORTCUT, lambda: threading.Thread(target=capture_and_translate, daemon=True).start(), suppress=True)
setup_tray()
master_root.after(50, poll_queue)
master_root.mainloop()