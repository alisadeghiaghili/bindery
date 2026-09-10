"""Desktop GUI for bindery (tkinter).

Thin shell over :func:`bindery.orchestration.pipeline.run_job`. All assemble
logic stays in the pipeline; this module only wires widgets, a worker thread,
and progress events.
"""

from __future__ import annotations

import contextlib
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from bindery import get_version
from bindery.exceptions import BinderyError
from bindery.models.config import JobConfig
from bindery.models.crop import MarginSpec
from bindery.orchestration.pipeline import run_job
from bindery.orchestration.progress import ProgressEvent

__all__ = ["BinderyApp", "main"]


class BinderyApp:
    """Main window: pick folders, set options, run assemble in a worker thread.

    Examples:
        >>> callable(BinderyApp)
        True
    """

    def __init__(self) -> None:
        """Create the main window, widgets, and worker plumbing."""
        self.root = tk.Tk()
        self.root.title(f"bindery {get_version()}")
        self.root.minsize(520, 420)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._source_var = tk.StringVar()
        self._output_var = tk.StringVar()
        self._margin_var = tk.IntVar(value=0)
        self._dpi_var = tk.IntVar(value=300)
        self._grayscale_var = tk.BooleanVar(value=False)
        self._stamp_var = tk.BooleanVar(value=False)
        self._force_var = tk.BooleanVar(value=False)
        self._status_var = tk.StringVar(value="Ready")

        self._events: queue.Queue[ProgressEvent | tuple[str, object]] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._cancel = threading.Event()

        self._build_layout()
        self._after_id = self.root.after(50, self._poll_events)

    def _build_layout(self) -> None:
        """Create widgets and grid layout."""
        padx, pady = 8, 4
        main = ttk.Frame(self.root, padding=12)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        ttk.Label(main, text="Source folder").grid(
            row=0, column=0, sticky="w", padx=padx, pady=pady
        )
        ttk.Entry(main, textvariable=self._source_var).grid(
            row=0, column=1, sticky="ew", padx=padx, pady=pady
        )
        ttk.Button(main, text="Browse…", command=self._browse_source).grid(
            row=0, column=2, padx=padx, pady=pady
        )

        ttk.Label(main, text="Output PDF").grid(row=1, column=0, sticky="w", padx=padx, pady=pady)
        ttk.Entry(main, textvariable=self._output_var).grid(
            row=1, column=1, sticky="ew", padx=padx, pady=pady
        )
        ttk.Button(main, text="Browse…", command=self._browse_output).grid(
            row=1, column=2, padx=padx, pady=pady
        )

        opts = ttk.Frame(main)
        opts.grid(row=2, column=0, columnspan=3, sticky="ew", padx=padx, pady=pady)
        ttk.Label(opts, text="Margin").grid(row=0, column=0, padx=4)
        ttk.Spinbox(opts, from_=0, to=200, textvariable=self._margin_var, width=6).grid(
            row=0, column=1, padx=4
        )
        ttk.Label(opts, text="DPI").grid(row=0, column=2, padx=4)
        ttk.Spinbox(opts, from_=36, to=600, textvariable=self._dpi_var, width=6).grid(
            row=0, column=3, padx=4
        )
        ttk.Checkbutton(opts, text="Grayscale", variable=self._grayscale_var).grid(
            row=0, column=4, padx=4
        )
        ttk.Checkbutton(opts, text="Stamp pages", variable=self._stamp_var).grid(
            row=0, column=5, padx=4
        )
        ttk.Checkbutton(opts, text="Force rebuild", variable=self._force_var).grid(
            row=0, column=6, padx=4
        )

        btns = ttk.Frame(main)
        btns.grid(row=3, column=0, columnspan=3, sticky="ew", padx=padx, pady=pady)
        self._start_btn = ttk.Button(btns, text="Assemble", command=self._start)
        self._start_btn.grid(row=0, column=0, padx=4)
        self._cancel_btn = ttk.Button(
            btns, text="Cancel", command=self._cancel_job, state="disabled"
        )
        self._cancel_btn.grid(row=0, column=1, padx=4)

        self._progress = ttk.Progressbar(main, mode="determinate", maximum=100)
        self._progress.grid(row=4, column=0, columnspan=3, sticky="ew", padx=padx, pady=pady)

        self._log = tk.Text(main, height=10, wrap="word", state="disabled")
        self._log.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=padx, pady=pady)
        main.rowconfigure(5, weight=1)

        ttk.Label(main, textvariable=self._status_var).grid(
            row=6, column=0, columnspan=3, sticky="w", padx=padx, pady=pady
        )

    def _append_log(self, line: str) -> None:
        """Append ``line`` to the log widget.

        Args:
            line: Text to append (newline added).
        """
        self._log.configure(state="normal")
        self._log.insert("end", line + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _browse_source(self) -> None:
        """Open a directory picker for the source folder."""
        chosen = filedialog.askdirectory(title="Select page folder")
        if chosen:
            self._source_var.set(chosen)
            if not self._output_var.get():
                self._output_var.set(str(Path(chosen).with_suffix("")) + ".pdf")

    def _browse_output(self) -> None:
        """Open a file picker for the output PDF."""
        chosen = filedialog.asksaveasfilename(
            title="Save PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if chosen:
            self._output_var.set(chosen)

    def _start(self) -> None:
        """Validate form and start a background assemble job."""
        if self._worker is not None and self._worker.is_alive():
            return
        source = self._source_var.get().strip()
        output = self._output_var.get().strip()
        if not source or not output:
            messagebox.showerror("bindery", "Source folder and output PDF are required.")
            return

        try:
            config = JobConfig(
                source_dir=Path(source),
                output_path=Path(output),
                margins=MarginSpec.uniform(int(self._margin_var.get())),
                grayscale=bool(self._grayscale_var.get()),
                stamp_page_numbers=bool(self._stamp_var.get()),
                dpi=int(self._dpi_var.get()),
                force=bool(self._force_var.get()),
            )
        except (BinderyError, ValueError) as exc:
            messagebox.showerror("bindery", str(exc))
            return

        self._cancel.clear()
        self._start_btn.configure(state="disabled")
        self._cancel_btn.configure(state="normal")
        self._status_var.set("Running…")
        self._append_log(f"Starting {config.source_dir} → {config.output_path}")
        self._worker = threading.Thread(target=self._run_worker, args=(config,), daemon=True)
        self._worker.start()

    def _run_worker(self, config: JobConfig) -> None:
        """Execute :func:`run_job` off the UI thread.

        Args:
            config: Job settings from the form.
        """

        def on_progress(event: ProgressEvent) -> None:
            self._events.put(event)
            if self._cancel.is_set():
                raise BinderyError("cancelled by user")

        try:
            report = run_job(config, on_progress=on_progress)
            self._events.put(("done", report))
        except BinderyError as exc:
            self._events.put(("error", str(exc)))
        except Exception as exc:  # noqa: BLE001 - worker must not kill the process
            self._events.put(("error", f"unexpected: {exc}"))

    def _cancel_job(self) -> None:
        """Request cooperative cancel of the running job."""
        self._cancel.set()
        self._status_var.set("Cancelling…")

    def _poll_events(self) -> None:
        """Drain worker events on the UI thread (50ms tick)."""
        try:
            while True:
                item = self._events.get_nowait()
                if isinstance(item, ProgressEvent):
                    self._handle_progress(item)
                else:
                    kind, payload = item
                    if kind == "done":
                        self._handle_done(payload)
                    else:
                        self._handle_error(str(payload))
        except queue.Empty:
            pass
        self._after_id = self.root.after(50, self._poll_events)

    def _handle_progress(self, event: ProgressEvent) -> None:
        """Update progress bar and log from a pipeline event."""
        self._progress["value"] = event.fraction * 100
        label = event.current or event.message or event.stage
        self._status_var.set(f"{event.stage}: {label}")
        if event.stage in ("discover", "assemble", "skipped", "done"):
            self._append_log(f"[{event.stage}] {event.message or event.current or ''}")
        elif event.stage == "transform" and event.completed == event.total:
            self._append_log(f"[transform] {event.total} pages ready")

    def _handle_done(self, report: Any) -> None:
        """Finish the job UI state on success."""
        skipped = getattr(report, "skipped", False)
        prefix = "Up to date" if skipped else "Wrote"
        self._append_log(f"{prefix}: {report.output_path} ({report.page_count} pages)")
        self._status_var.set("Done")
        self._progress["value"] = 100
        self._start_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")

    def _handle_error(self, message: str) -> None:
        """Finish the job UI state on failure or cancel."""
        self._append_log(f"Error: {message}")
        self._status_var.set("Error" if "cancel" not in message.lower() else "Cancelled")
        self._start_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")

    def _on_close(self) -> None:
        """Cancel any job and destroy the window."""
        self._cancel.set()
        with contextlib.suppress(Exception):
            self.root.after_cancel(self._after_id)
        self.root.destroy()

    def run(self) -> None:
        """Enter the Tk main loop.

        Examples:
            >>> callable(BinderyApp.run)
            True
        """
        self.root.mainloop()


def main(argv: list[str] | None = None) -> int:
    """Launch the bindery GUI.

    Args:
        argv: Unused; present for CLI symmetry.

    Returns:
        int: Exit code (``0``).

    Examples:
        >>> callable(main)
        True
    """
    del argv
    app = BinderyApp()
    app.run()
    return 0
