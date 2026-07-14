import json
import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

SCRIPT_DIR = Path(__file__).resolve().parent
TARGET = SCRIPT_DIR.parent / "dist" / "settings.json"
DEFAULT = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "PRANA_ELEX"


def browse():
    folder = filedialog.askdirectory(title="Select save location", initialdir=entry.get() or str(DEFAULT))
    if folder:
        entry.delete(0, tk.END)
        entry.insert(0, folder)


def on_next():
    path = entry.get().strip()
    if not path:
        messagebox.showwarning("Warning", "Please select a save location.")
        return
    p = Path(path)
    if not p.exists():
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot create directory:\n{e}")
            return
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps({"data_dir": str(p)}, indent=2), encoding="utf-8")
    root.destroy()


root = tk.Tk()
root.title("PRANA ELEX — Setup")
root.geometry("520x160")
root.resizable(False, False)

frame = tk.Frame(root, padx=20, pady=20)
frame.pack(fill=tk.BOTH, expand=True)

tk.Label(frame, text="Save Location", anchor="w").pack(fill=tk.X)

row = tk.Frame(frame)
row.pack(fill=tk.X, pady=(4, 16))

entry = tk.Entry(row)
entry.insert(0, str(DEFAULT))
entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

tk.Button(row, text="Browse...", command=browse).pack(side=tk.RIGHT)

btn_frame = tk.Frame(frame)
btn_frame.pack(fill=tk.X)

tk.Button(btn_frame, text="Next", command=on_next, width=12).pack(side=tk.RIGHT)

root.mainloop()
