import os
import re
import json
import sys
import ctypes
import tkinter as tk
from tkinter import filedialog, messagebox, Menu
from tkinterdnd2 import DND_FILES, TkinterDnD
from datetime import datetime


def resource_path(relative_path):
    """Gets the absolute path to the resource, compatible with PyInstaller."""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


def clean_text(text):
    """Replaces umlauts and removes special characters for the Nokia."""
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "ß": "ss",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return re.sub(r"[^a-zA-Z0-9\s\.\!\?\-\:\(\)\,\/]", "", text).strip()


class ToolTip:
    """Creates a small hover window (tooltip) for GUI elements."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 20

        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("tahoma", 8, "normal"),
        )
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


class Event:
    def __init__(
        self, start="", end="", summary="", location="", description="", rrule=""
    ):
        self.start = start.split("Z")[0].split("+")[0]
        self.end_orig = end.split("Z")[0].split("+")[0] if end else self.start

        self.summary_clean = clean_text(summary)
        self.location_clean = clean_text(location)
        self.rrule_orig = rrule
        self.final_summary = ""

    def get_interval(self):
        if not self.rrule_orig:
            return 1
        match = re.search(r"INTERVAL=(\d+)", self.rrule_orig.upper())
        return int(match.group(1)) if match else 1

    def translate_and_build_summary(self):
        r = self.rrule_orig.upper()
        interval = self.get_interval()
        logic_str = ""

        # Round-up logic (adds a note to clarify the change)
        if r and interval > 1:
            start_dt = datetime.strptime(self.start[:8], "%Y%m%d")
            kw = start_dt.isocalendar()[1]
            unit = "W" if "WEEKLY" in r else "D"
            logic_str = f"({interval}{unit}-W{kw})"

        title = self.summary_clean
        location = self.location_clean

        def assemble(t, g, log):
            res = t
            if g:
                res += f", {g}"
            if log:
                res += f" {log}"
            return res

        test_summary = assemble(title, location, logic_str)

        if len(test_summary) > 40 and location:
            location = ""
            test_summary = assemble(title, location, logic_str)

        if len(test_summary) > 40:
            suffix_len = len(f" {logic_str}") if logic_str else 0
            max_title_len = 40 - suffix_len
            title = title[:max_title_len].strip()
            test_summary = assemble(title, "", logic_str)

        self.final_summary = test_summary

        prefix = ""
        if r:
            if "DAILY" in r:
                prefix = "D1"
            elif "WEEKLY" in r:
                prefix = "W1"
            elif "MONTHLY" in r:
                prefix = "MD1"
            elif "YEARLY" in r:
                prefix = "YD1"

        return f"{prefix} {self.start}" if prefix else ""

    def toVCS(self):
        rrule_nokia = self.translate_and_build_summary()

        nokia_end = self.end_orig
        if rrule_nokia:
            until_date = "20991231"
            match = re.search(r"UNTIL=([0-9]{8})", self.rrule_orig.upper())
            if match:
                until_date = match.group(1)

            end_time = self.end_orig[8:] if len(self.end_orig) > 8 else "T000000"
            nokia_end = f"{until_date}{end_time}"

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:1.0",
            "BEGIN:VEVENT",
            f"SUMMARY;CHARSET=UTF-8:{self.final_summary}",
            f"DTSTART:{self.start}",
            f"DTEND:{nokia_end}",
        ]

        if rrule_nokia:
            lines.append(f"RRULE:{rrule_nokia}")

        lines.append(f"AALARM:{self.start};;;")
        lines.append("END:VEVENT")
        lines.append("END:VCALENDAR")

        return "\r\n".join(lines)

    def get_filename(self):
        clean_title = re.sub(r"[^a-zA-Z0-9]", "", self.summary_clean.replace(" ", "_"))
        return f"{clean_title[:15]}_{self.start[:15]}.vcs"


class Calendar:
    def __init__(self, file_path):
        self.events = []
        if not os.path.exists(file_path):
            return
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            tmp = {
                "start": "",
                "end": "",
                "summary": "",
                "location": "",
                "description": "",
                "rrule": "",
            }
            in_ev = False
            for line in f:
                line = line.strip()
                if line.startswith("BEGIN:VEVENT"):
                    in_ev = True
                elif line.startswith("END:VEVENT"):
                    self.events.append(Event(**tmp))
                    tmp = {
                        "start": "",
                        "end": "",
                        "summary": "",
                        "location": "",
                        "description": "",
                        "rrule": "",
                    }
                    in_ev = False
                elif in_ev and ":" in line:
                    try:
                        k_f, v = line.split(":", 1)
                        k = k_f.split(";")[0]
                        if k == "DTSTART":
                            tmp["start"] = v
                        elif k == "DTEND":
                            tmp["end"] = v
                        elif k == "SUMMARY":
                            tmp["summary"] = v
                        elif k == "LOCATION":
                            tmp["location"] = v
                        elif k == "RRULE":
                            tmp["rrule"] = v
                    except (ValueError, IndexError):
                        continue
                    except Exception as e:
                        print(f"Unexpected error parsing line '{line}': {e}")
                        continue

    def scan(self, all_past=False):
        self.events.sort(key=lambda x: x.start)
        today = datetime.now().strftime("%Y%m%d")
        return [
            e for e in self.events if all_past or (e.start[:8] >= today or e.rrule_orig)
        ]


class NokiaConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Coca - S30+ iCal to VCS Converter")
        self.root.geometry("500x450")
        self.root.resizable(False, False)

        # --- Taskbar fix for Windows ---
        try:
            myappid = "nokia.s30plus.converter.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        # Load the icon for the window
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.file_paths = []
        self.config_path = os.path.join(
            os.path.expanduser("~"), ".s30_converter_cfg.json"
        )

        self.max_events_var = tk.StringVar(value="0")
        self.out_dir_var = tk.StringVar(value=os.path.join(os.getcwd(), "vcs_files"))
        self.all_past_var = tk.BooleanVar(value=False)

        self.load_settings()

        # --- Top Frame ---
        top_frame = tk.Frame(root)
        top_frame.pack(fill=tk.X, padx=20, pady=(15, 5))

        self.add_btn = tk.Button(
            top_frame, text="Add .ics", command=self.add_files, width=10
        )
        self.add_btn.pack(side=tk.LEFT)
        ToolTip(self.add_btn, "Select one or more .ics files from your PC.")

        tk.Label(top_frame, text="Selected Files:", font=("Arial", 9, "bold")).pack(
            side=tk.LEFT, padx=20
        )

        # --- Listbox Frame ---
        list_frame = tk.Frame(root)
        list_frame.pack(padx=20, pady=5, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            yscrollcommand=scrollbar.set,
            font=("Arial", 10),
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)

        # Drag & Drop registration for the listbox
        self.listbox.drop_target_register(DND_FILES)  # type: ignore
        self.listbox.dnd_bind("<<Drop>>", self.drop_files)  # type: ignore

        self.listbox.bind("<Delete>", self.remove_selected)
        ToolTip(
            self.listbox,
            "Drag & Drop your .ics files here!\nMultiple selection enabled.\nPress 'Del' or right-click to remove files.",
        )

        self.context_menu = Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Delete", command=self.remove_selected)
        self.listbox.bind("<Button-3>", self.show_context_menu)

        # --- Settings Frame ---
        settings_frame = tk.Frame(root)
        settings_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(settings_frame, text="Amount of events to process per file:").grid(
            row=0, column=0, sticky="w", pady=2
        )
        self.max_events_entry = tk.Entry(
            settings_frame, textvariable=self.max_events_var, width=5
        )
        self.max_events_entry.grid(row=0, column=1, sticky="w", padx=5)
        ToolTip(
            self.max_events_entry,
            "Maximum number of events to process per file.\n'0' means: Process ALL events in the file.",
        )

        tk.Label(settings_frame, text="Output Folder:").grid(
            row=1, column=0, sticky="w", pady=5
        )
        folder_frame = tk.Frame(settings_frame)
        folder_frame.grid(row=1, column=1, sticky="w", padx=5)

        self.out_dir_entry = tk.Entry(
            folder_frame, textvariable=self.out_dir_var, width=30
        )
        self.out_dir_entry.pack(side=tk.LEFT)
        ToolTip(
            self.out_dir_entry,
            "The folder where the converted .vcs files will be saved.",
        )

        self.browse_btn = tk.Button(
            folder_frame, text="...", command=self.choose_folder, width=3
        )
        self.browse_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(self.browse_btn, "Browse for output folder.")

        self.chk_past = tk.Checkbutton(
            settings_frame, text="Export past events", variable=self.all_past_var
        )
        self.chk_past.grid(row=2, column=0, columnspan=2, sticky="w", pady=2)
        ToolTip(
            self.chk_past,
            "If checked, past events will also be exported.\nOtherwise, only events from today onwards\n(incl. ongoing past series) are exported.",
        )

        # --- Convert Button ---
        self.convert_btn = tk.Button(
            root,
            text="Convert Files",
            command=self.process_files,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5,
        )
        self.convert_btn.pack(pady=(5, 15))
        ToolTip(self.convert_btn, "Starts converting all files currently in the list.")

    def load_settings(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                    if "max_events" in config:
                        self.max_events_var.set(config["max_events"])
                    if "out_dir" in config:
                        self.out_dir_var.set(config["out_dir"])
                    if "all_past" in config:
                        self.all_past_var.set(config["all_past"])
        except Exception:
            pass

    def save_settings(self):
        try:
            config = {
                "max_events": self.max_events_var.get(),
                "out_dir": self.out_dir_var.get(),
                "all_past": self.all_past_var.get(),
            }
            with open(self.config_path, "w") as f:
                json.dump(config, f)
        except Exception:
            pass

    def on_closing(self):
        self.save_settings()
        self.root.destroy()

    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Select .ics files", filetypes=[("ICS files", "*.ics")]
        )
        for f in files:
            if f not in self.file_paths:
                self.file_paths.append(f)
                self.listbox.insert(tk.END, os.path.basename(f))

    def drop_files(self, event):
        files = self.root.tk.splitlist(event.data)
        for f in files:
            if f.lower().endswith(".ics") and f not in self.file_paths:
                self.file_paths.append(f)
                self.listbox.insert(tk.END, os.path.basename(f))

    def remove_selected(self, event=None):
        selection = self.listbox.curselection()
        if not selection:
            return
        for i in reversed(selection):
            self.listbox.delete(i)
            del self.file_paths[i]

    def show_context_menu(self, event):
        try:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.listbox.nearest(event.y))
            self.listbox.activate(self.listbox.nearest(event.y))
            self.context_menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            pass
        finally:
            self.context_menu.grab_release()

    def choose_folder(self):
        folder = filedialog.askdirectory(
            title="Select Output Folder", initialdir=self.out_dir_var.get()
        )
        if folder:
            self.out_dir_var.set(folder)

    def process_files(self):
        if not self.file_paths:
            messagebox.showwarning(
                "No Files", "Please add at least one .ics file to the list."
            )
            return

        out_dir = self.out_dir_var.get()
        if not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir)
            except Exception as e:
                messagebox.showerror(
                    "Error", f"Could not create output directory:\n{e}"
                )
                return

        try:
            max_limit = int(self.max_events_var.get())
        except ValueError:
            messagebox.showerror(
                "Invalid Input", "Amount of events must be a valid number."
            )
            return

        self.save_settings()

        all_past = self.all_past_var.get()
        total_files = 0
        total_events = 0

        for file_path in self.file_paths:
            cal = Calendar(file_path)
            found_events = cal.scan(all_past=all_past)

            total_found = len(found_events)
            if total_found == 0:
                continue

            limit = max_limit if max_limit > 0 else total_found
            export_count = min(limit, total_found)

            for i in range(export_count):
                ev = found_events[i]
                vcs_text = ev.toVCS()
                path = os.path.join(out_dir, ev.get_filename())
                with open(path, "w", encoding="latin-1", errors="replace") as f:
                    f.write(vcs_text)
                total_events += 1

            total_files += 1

        messagebox.showinfo(
            "Success",
            f"Done!\n\nProcessed {total_files} file(s).\nCreated {total_events} .vcs files in:\n{out_dir}",
        )


if __name__ == "__main__":
    # Use TkinterDnD instead of tk.Tk() for Drag & Drop support
    root = TkinterDnD.Tk()
    app = NokiaConverterApp(root)
    root.mainloop()
