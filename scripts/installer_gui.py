#!/usr/bin/env python3
"""
Cross-platform portfolio installer.

The GUI intentionally uses Tkinter from Python's standard library so it can be
packaged as a Windows EXE and launched from Linux with a small shell wrapper.
"""

from __future__ import annotations

import json
import importlib.util
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from tkinter import BooleanVar, Canvas, StringVar, Tk, Toplevel, messagebox
from tkinter import ttk


if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).resolve().parent
    RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", ROOT))
else:
    ROOT = Path(__file__).resolve().parents[1]
    RESOURCE_ROOT = ROOT

TEMPLATE_PATH = ROOT / "templates" / "portfolio.config.template.json"
BUNDLED_TEMPLATE_PATH = RESOURCE_ROOT / "templates" / "portfolio.config.template.json"
CONFIG_PATH = ROOT / "portfolio.config.json"
GENERATOR_PATH = ROOT / "scripts" / "generate_portfolio.py"
BUNDLED_GENERATOR_PATH = RESOURCE_ROOT / "scripts" / "generate_portfolio.py"

THEMES = ["matrix", "cyan", "ember", "violet", "mono"]
SOCIAL_FIELDS = [
    ("linkedin", "LinkedIn"),
    ("website", "Website"),
    ("email", "Email"),
    ("github", "GitHub"),
    ("x", "X / Twitter"),
    ("youtube", "YouTube"),
    ("instagram", "Instagram"),
    ("tiktok", "TikTok"),
    ("facebook", "Facebook"),
    ("threads", "Threads"),
    ("bluesky", "Bluesky"),
    ("mastodon", "Mastodon"),
    ("discord", "Discord"),
]


def find_npm() -> str:
    for candidate in ["npm.cmd", "npm"]:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise RuntimeError("Node.js/npm was not found. Install Node.js LTS, then run this installer again.")


def github_username(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    cleaned = cleaned.rstrip("/")
    match = re.search(r"github\.com[:/]+([^/\s]+)", cleaned, flags=re.I)
    if match:
        return match.group(1)
    return cleaned.lstrip("@")


def normalize_social(kind: str, value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if kind == "email" and "@" in value and not value.startswith("mailto:"):
        return f"mailto:{value}"
    if kind == "github":
        user = github_username(value)
        return f"https://github.com/{user}" if user else ""
    if kind == "linkedin" and not value.startswith(("http://", "https://")):
        return f"https://www.linkedin.com/in/{value.strip('/')}"
    if kind == "x" and not value.startswith(("http://", "https://")):
        return f"https://x.com/{value.lstrip('@')}"
    if kind == "bluesky" and not value.startswith(("http://", "https://")):
        return f"https://bsky.app/profile/{value.lstrip('@')}"
    if kind == "discord" and not value.startswith(("http://", "https://")):
        return value
    if not value.startswith(("http://", "https://", "mailto:")):
        return f"https://{value}"
    return value


def load_template() -> dict:
    path = TEMPLATE_PATH if TEMPLATE_PATH.exists() else BUNDLED_TEMPLATE_PATH
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def run_generator() -> None:
    path = GENERATOR_PATH if GENERATOR_PATH.exists() else BUNDLED_GENERATOR_PATH
    spec = importlib.util.spec_from_file_location("portfolio_generator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the GitHub importer.")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    module.CONFIG_PATH = CONFIG_PATH
    module.OUTPUT_PATH = ROOT / "src" / "data" / "portfolio.ts"
    module.CACHE_DIR = ROOT / ".portfolio-cache"
    module.run_generation(CONFIG_PATH)


class InstallerApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Portfolio Builder Installer")
        self.root.geometry("860x760")
        self.root.minsize(760, 560)
        self.root.configure(bg="#0b1110")

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.inputs: dict[str, StringVar] = {}
        self.social_inputs: dict[str, StringVar] = {}

        self.github_var = StringVar()
        self.theme_var = StringVar(value="matrix")
        self.custom_label_var = StringVar()
        self.custom_url_var = StringVar()
        self.status_var = StringVar(value="Ready to build your portfolio.")
        self.progress_var = StringVar(value="0%")

        self.build_ui()
        self.root.after(120, self.poll_events)

    def build_ui(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#0b1110")
        style.configure("Card.TFrame", background="#101a19", relief="flat")
        style.configure("TLabel", background="#0b1110", foreground="#eef8f4")
        style.configure("Muted.TLabel", background="#0b1110", foreground="#9fb6ae")
        style.configure("Card.TLabel", background="#101a19", foreground="#eef8f4")
        style.configure("TButton", padding=(14, 8), font=("Segoe UI", 10, "bold"))
        style.configure("TEntry", fieldbackground="#172321", foreground="#eef8f4", insertcolor="#eef8f4")
        style.configure("Horizontal.TProgressbar", troughcolor="#172321", background="#9df34f")

        outer = ttk.Frame(self.root, padding=24)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Portfolio Builder", font=("Segoe UI", 26, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text="Enter a GitHub profile, optional social links, and a theme. The installer imports repositories, builds project pages, and prepares the site.",
            style="Muted.TLabel",
            wraplength=740,
        ).pack(anchor="w", pady=(8, 18))

        scroll_shell = ttk.Frame(outer)
        scroll_shell.pack(fill="both", expand=True)

        canvas = Canvas(scroll_shell, bg="#0b1110", highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(scroll_shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        scroll_content = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=scroll_content, anchor="nw")

        def update_scroll_region(_: object | None = None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def update_canvas_width(event: object) -> None:
            canvas.itemconfigure(canvas_window, width=event.width)

        def on_mousewheel(event: object) -> None:
            delta = getattr(event, "delta", 0)
            if delta:
                canvas.yview_scroll(int(-1 * (delta / 120)), "units")

        scroll_content.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", update_canvas_width)
        canvas.bind_all("<MouseWheel>", on_mousewheel)

        form = ttk.Frame(scroll_content, style="Card.TFrame", padding=18)
        form.pack(fill="both", expand=True)

        self.add_entry(form, "GitHub URL or username", self.github_var, required=True, row=0)
        self.inputs["name"] = StringVar()
        self.inputs["role"] = StringVar(value="Developer")
        self.inputs["email"] = StringVar()
        self.inputs["location"] = StringVar()
        self.inputs["tagline"] = StringVar(value="I build practical software and reliable systems.")
        self.add_entry(form, "Display name", self.inputs["name"], row=1)
        self.add_entry(form, "Role/title", self.inputs["role"], row=2)
        self.add_entry(form, "Email", self.inputs["email"], row=3)
        self.add_entry(form, "Location", self.inputs["location"], row=4)
        self.add_entry(form, "Tagline", self.inputs["tagline"], row=5)

        ttk.Label(form, text="Theme", style="Card.TLabel").grid(row=6, column=0, sticky="w", pady=8)
        theme_box = ttk.Combobox(form, textvariable=self.theme_var, values=THEMES, state="readonly")
        theme_box.grid(row=6, column=1, sticky="ew", pady=8)

        ttk.Label(form, text="Social links are optional", style="Card.TLabel", font=("Segoe UI", 12, "bold")).grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(18, 8)
        )

        social_frame = ttk.Frame(form, style="Card.TFrame")
        social_frame.grid(row=8, column=0, columnspan=2, sticky="nsew")
        for index, (kind, label) in enumerate(SOCIAL_FIELDS):
            var = StringVar()
            self.social_inputs[kind] = var
            row = index // 2
            col = (index % 2) * 2
            ttk.Label(social_frame, text=label, style="Card.TLabel").grid(row=row, column=col, sticky="w", padx=(0, 8), pady=5)
            ttk.Entry(social_frame, textvariable=var).grid(row=row, column=col + 1, sticky="ew", padx=(0, 14), pady=5)
        social_frame.columnconfigure(1, weight=1)
        social_frame.columnconfigure(3, weight=1)

        custom = ttk.Frame(form, style="Card.TFrame")
        custom.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Label(custom, text="Custom label", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(custom, textvariable=self.custom_label_var).grid(row=0, column=1, sticky="ew", padx=(0, 14))
        ttk.Label(custom, text="Custom URL", style="Card.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 8))
        ttk.Entry(custom, textvariable=self.custom_url_var).grid(row=0, column=3, sticky="ew")
        custom.columnconfigure(1, weight=1)
        custom.columnconfigure(3, weight=1)

        form.columnconfigure(1, weight=1)
        form.rowconfigure(8, weight=1)

        footer = ttk.Frame(outer)
        footer.pack(fill="x", side="bottom", pady=(18, 0))

        progress_row = ttk.Frame(footer)
        progress_row.pack(fill="x")
        self.progress = ttk.Progressbar(progress_row, maximum=100, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True)
        ttk.Label(progress_row, textvariable=self.progress_var, width=6).pack(side="left", padx=(10, 0))
        ttk.Label(footer, textvariable=self.status_var, style="Muted.TLabel").pack(anchor="w", pady=(8, 12))

        buttons = ttk.Frame(footer)
        buttons.pack(fill="x")
        self.install_button = ttk.Button(buttons, text="Install Portfolio", command=self.start_install)
        self.install_button.pack(side="right")
        ttk.Button(
            buttons,
            text="Star on GitHub",
            command=lambda: webbrowser.open("https://github.com/Byanski/Portfolio-Dashboard"),
        ).pack(
            side="right", padx=(0, 10)
        )

    def add_entry(self, parent: ttk.Frame, label: str, var: StringVar, row: int, required: bool = False) -> None:
        suffix = " *" if required else ""
        ttk.Label(parent, text=f"{label}{suffix}", style="Card.TLabel").grid(row=row, column=0, sticky="w", pady=7)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", pady=7)

    def start_install(self) -> None:
        username = github_username(self.github_var.get())
        if not username:
            messagebox.showerror("GitHub Required", "Please enter a GitHub URL or username to continue.")
            return
        self.install_button.configure(state="disabled")
        threading.Thread(target=self.install, daemon=True).start()

    def emit(self, kind: str, payload: object) -> None:
        self.events.put((kind, payload))

    def poll_events(self) -> None:
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "progress":
                value, message = payload
                self.progress.configure(value=value)
                self.progress_var.set(f"{value}%")
                self.status_var.set(str(message))
            elif kind == "done":
                self.progress.configure(value=100)
                self.progress_var.set("100%")
                self.status_var.set("Install complete.")
                self.show_cloudflare_popup()
            elif kind == "error":
                self.install_button.configure(state="normal")
                messagebox.showerror("Install Failed", str(payload))
        self.root.after(120, self.poll_events)

    def install(self) -> None:
        try:
            config = self.build_config()
            self.emit("progress", (10, "Writing portfolio configuration..."))
            write_config(config)

            npm = find_npm()
            self.emit("progress", (25, "Installing frontend dependencies..."))
            self.run([npm, "install"])

            self.emit("progress", (52, "Importing and summarizing GitHub repositories..."))
            run_generator()

            self.emit("progress", (78, "Building the portfolio site..."))
            self.run([npm, "run", "build"])

            self.emit("progress", (92, "Finalizing install..."))
            self.emit("done", None)
        except Exception as error:
            self.emit("error", error)

    def build_config(self) -> dict:
        config = load_template()
        username = github_username(self.github_var.get())
        profile = config["profile"]
        profile["name"] = self.inputs["name"].get().strip() or username
        profile["role"] = self.inputs["role"].get().strip() or "Developer"
        profile["email"] = self.inputs["email"].get().strip()
        profile["location"] = self.inputs["location"].get().strip()
        profile["tagline"] = self.inputs["tagline"].get().strip() or profile["tagline"]
        profile["about"] = f"{profile['name']} is a developer building public projects on GitHub. Customize this section in portfolio.config.json."
        profile["availability"] = "Open to interesting technical projects."

        socials = [{"label": "GitHub", "url": f"https://github.com/{username}", "kind": "github"}]
        for kind, label in SOCIAL_FIELDS:
            if kind == "github":
                continue
            url = normalize_social(kind, self.social_inputs[kind].get())
            if url:
                mapped_kind = kind if kind in {"linkedin", "email"} else "custom"
                socials.append({"label": label, "url": url, "kind": mapped_kind})

        custom_url = normalize_social("custom", self.custom_url_var.get())
        custom_label = self.custom_label_var.get().strip() or "Custom"
        if custom_url:
            socials.append({"label": custom_label, "url": custom_url, "kind": "custom"})

        config["githubUsername"] = username
        config["theme"] = self.theme_var.get()
        config["socials"] = socials
        return config

    def run(self, command: list[str]) -> None:
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        if result.returncode != 0:
            details = result.stderr.strip() or result.stdout.strip() or "Command failed."
            raise RuntimeError(details)

    def show_cloudflare_popup(self) -> None:
        popup = Toplevel(self.root)
        popup.title("Cloudflare Tunnel Next Steps")
        popup.geometry("680x540")
        popup.configure(bg="#0b1110")
        popup.transient(self.root)
        popup.grab_set()

        frame = ttk.Frame(popup, padding=22)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Your portfolio is ready", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(
            frame,
            text="Thank you for supporting open source development. If this helped, please star the project on GitHub.",
            style="Muted.TLabel",
            wraplength=620,
        ).pack(anchor="w", pady=(8, 14))

        instructions = (
            "To expose this portfolio on the internet with Cloudflare Zero Trust:\n\n"
            "1. Create or sign in to a Cloudflare account.\n"
            "2. Open Zero Trust from the Cloudflare dashboard.\n"
            "3. Go to Networks > Tunnels and create a Cloudflare Tunnel.\n"
            "4. Install the connector on this computer using Cloudflare's command.\n"
            "5. Add a public hostname for your domain.\n"
            "6. Point the service URL to http://localhost:5173.\n"
            "7. Confirm the tunnel is healthy, then open your public hostname."
        )
        ttk.Label(frame, text=instructions, wraplength=620, justify="left").pack(anchor="w")

        links = ttk.Frame(frame)
        links.pack(anchor="w", pady=16)
        ttk.Button(links, text="Cloudflare Sign Up", command=lambda: webbrowser.open("https://dash.cloudflare.com/sign-up")).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            links,
            text="Zero Trust Dashboard",
            command=lambda: webbrowser.open("https://one.dash.cloudflare.com/"),
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            links,
            text="Tunnel Docs",
            command=lambda: webbrowser.open("https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/"),
        ).pack(side="left")

        acknowledged = BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="I have read these Cloudflare setup instructions.",
            variable=acknowledged,
        ).pack(anchor="w", pady=(18, 8))

        close_button = ttk.Button(frame, text="Close Installer", state="disabled", command=self.root.destroy)
        close_button.pack(anchor="e")

        def update_close_state(*_: object) -> None:
            close_button.configure(state="normal" if acknowledged.get() else "disabled")

        acknowledged.trace_add("write", update_close_state)
        popup.protocol("WM_DELETE_WINDOW", lambda: None)

    def run_app(self) -> None:
        self.root.mainloop()


def main() -> None:
    InstallerApp().run_app()


if __name__ == "__main__":
    main()
