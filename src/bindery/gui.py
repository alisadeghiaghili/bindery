"""Desktop GUI for bindery (tkinter).

Thin shell over :func:`bindery.orchestration.pipeline.run_job`. All assemble
logic stays in the pipeline; this module wires widgets, a worker thread,
progress events, page reorder/exclude, and a first-page preview thumbnail.
"""

from __future__ import annotations

import contextlib
import queue
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from bindery import get_version
from bindery.adapters.fs import discover_page_files
from bindery.exceptions import BinderyError
from bindery.models.config import JobConfig
from bindery.models.crop import MarginSpec
from bindery.models.page import PageFile
from bindery.orchestration.pipeline import run_job, select_pages, transform_page
from bindery.orchestration.progress import ProgressEvent

__all__ = ["BinderyApp", "main"]


class BinderyApp:
    """Main window: pick folders, set options, reorder pages, preview, assemble.

    Examples:
        >>> callable(BinderyApp)
        True
    """

    def __init__(self) -> None:
        """Create the main window, widgets, and worker plumbing."""
        self.root = tk.Tk()
        self.root.title(f"bindery {get_version()}")
        self.root.minsize(640, 560)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._source_var = tk.StringVar()
        self._output_var = tk.StringVar()
        self._margin_var = tk.IntVar(value=0)
        self._dpi_var = tk.IntVar(value=300)
        self._grayscale_var = tk.BooleanVar(value=False)
        self._stamp_var = tk.BooleanVar(value=False)
        self._force_var = tk.BooleanVar(value=False)
        self._title_var = tk.StringVar()
        self._author_var = tk.StringVar()
        self._rotate_var = tk.StringVar(value="0")
        self._page_size_var = tk.StringVar()
        self._compress_var = tk.StringVar(value="lossless")
        self._status_var = tk.StringVar(value="Ready")
        self._page_entries: list[dict[str, Any]] = []
        self._preview_photo: Any = None

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
        ttk.Label(opts, text="Rotate").grid(row=0, column=4, padx=4)
        ttk.Combobox(
            opts,
            textvariable=self._rotate_var,
            values=("0", "90", "180", "270"),
            width=5,
            state="readonly",
        ).grid(row=0, column=5, padx=4)
        ttk.Label(opts, text="Page").grid(row=0, column=6, padx=4)
        ttk.Combobox(
            opts,
            textvariable=self._page_size_var,
            values=("", "a4", "letter"),
            width=8,
        ).grid(row=0, column=7, padx=4)
        ttk.Label(opts, text="Compress").grid(row=1, column=0, padx=4)
        ttk.Combobox(
            opts,
            textvariable=self._compress_var,
            values=("lossless", "jpeg"),
            width=8,
            state="readonly",
        ).grid(row=1, column=1, padx=4)
        ttk.Checkbutton(opts, text="Grayscale", variable=self._grayscale_var).grid(
            row=1, column=2, padx=4
        )
        ttk.Checkbutton(opts, text="Stamp pages", variable=self._stamp_var).grid(
            row=1, column=3, padx=4
        )
        ttk.Checkbutton(opts, text="Force rebuild", variable=self._force_var).grid(
            row=1, column=4, padx=4
        )

        meta = ttk.Frame(main)
        meta.grid(row=3, column=0, columnspan=3, sticky="ew", padx=padx, pady=pady)
        meta.columnconfigure(1, weight=1)
        meta.columnconfigure(3, weight=1)
        ttk.Label(meta, text="Title").grid(row=0, column=0, sticky="w", padx=4)
        ttk.Entry(meta, textvariable=self._title_var).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Label(meta, text="Author").grid(row=0, column=2, sticky="w", padx=4)
        ttk.Entry(meta, textvariable=self._author_var).grid(row=0, column=3, sticky="ew", padx=4)

        pages_frame = ttk.LabelFrame(main, text="Pages (order + include)", padding=6)
        pages_frame.grid(row=4, column=0, columnspan=3, sticky="nsew", padx=padx, pady=pady)
        pages_frame.columnconfigure(0, weight=1)
        pages_frame.rowconfigure(0, weight=1)
        self._pages_list = tk.Listbox(
            pages_frame, height=7, selectmode="extended", exportselection=False
        )
        self._pages_list.grid(row=0, column=0, sticky="nsew")
        page_btns = ttk.Frame(pages_frame)
        page_btns.grid(row=0, column=1, sticky="ns", padx=6)
        ttk.Button(page_btns, text="Up", command=self._page_up).grid(row=0, column=0, pady=2)
        ttk.Button(page_btns, text="Down", command=self._page_down).grid(row=1, column=0, pady=2)
        ttk.Button(page_btns, text="Include/Exclude", command=self._toggle_exclude).grid(
            row=2, column=0, pady=2
        )
        ttk.Button(page_btns, text="Reload", command=self._reload_pages).grid(
            row=3, column=0, pady=2
        )

        preview_row = ttk.Frame(main)
        preview_row.grid(row=5, column=0, columnspan=3, sticky="ew", padx=padx, pady=pady)
        self._preview_label = ttk.Label(preview_row, text="Preview: (none)")
        self._preview_label.grid(row=0, column=0, sticky="w")
        ttk.Button(preview_row, text="Preview first included page", command=self._preview).grid(
            row=0, column=1, padx=8
        )

        btns = ttk.Frame(main)
        btns.grid(row=6, column=0, columnspan=3, sticky="ew", padx=padx, pady=pady)
        self._start_btn = ttk.Button(btns, text="Assemble", command=self._start)
        self._start_btn.grid(row=0, column=0, padx=4)
        self._cancel_btn = ttk.Button(
            btns, text="Cancel", command=self._cancel_job, state="disabled"
        )
        self._cancel_btn.grid(row=0, column=1, padx=4)

        self._progress = ttk.Progressbar(main, mode="determinate", maximum=100)
        self._progress.grid(row=7, column=0, columnspan=3, sticky="ew", padx=padx, pady=pady)

        self._log = tk.Text(main, height=8, wrap="word", state="disabled")
        self._log.grid(row=8, column=0, columnspan=3, sticky="nsew", padx=padx, pady=pady)
        main.rowconfigure(8, weight=1)

        ttk.Label(main, textvariable=self._status_var).grid(
            row=9, column=0, columnspan=3, sticky="w", padx=padx, pady=pady
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
            self._reload_pages()

    def _browse_output(self) -> None:
        """Open a file picker for the output PDF."""
        chosen = filedialog.asksaveasfilename(
            title="Save PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if chosen:
            self._output_var.set(chosen)

    def _reload_pages(self) -> None:
        """Load source pages into the reorder list (all included by default)."""
        source = self._source_var.get().strip()
        self._pages_list.delete(0, "end")
        self._page_entries = []
        if not source:
            return
        try:
            pages = discover_page_files(Path(source))
        except BinderyError as exc:
            messagebox.showerror("bindery", str(exc))
            return
        for page in pages:
            self._page_entries.append({"name": page.name, "included": True})
            self._pages_list.insert("end", page.name)

    def _selected_page_indices(self) -> list[int]:
        """Return selected listbox indices.

        Returns:
            list[int]: Zero-based indices of selected rows.
        """
        raw = self._pages_list.curselection()  # type: ignore[no-untyped-call]
        return [int(i) for i in raw]

    def _refresh_page_list(self) -> None:
        """Redraw the listbox from ``_page_entries``."""
        selected = set(self._selected_page_indices())
        self._pages_list.delete(0, "end")
        for entry in self._page_entries:
            label = entry["name"] if entry["included"] else f"[excluded] {entry['name']}"
            self._pages_list.insert("end", label)
        for index in selected:
            if index < self._pages_list.size():
                self._pages_list.selection_set(index)

    def _page_up(self) -> None:
        """Move selected pages up one slot."""
        indices = self._selected_page_indices()
        if not indices or indices[0] == 0:
            return
        for index in indices:
            self._page_entries[index - 1], self._page_entries[index] = (
                self._page_entries[index],
                self._page_entries[index - 1],
            )
        self._refresh_page_list()
        for index in indices:
            self._pages_list.selection_set(max(0, index - 1))

    def _page_down(self) -> None:
        """Move selected pages down one slot."""
        indices = self._selected_page_indices()
        if not indices or indices[-1] >= len(self._page_entries) - 1:
            return
        for index in reversed(indices):
            self._page_entries[index + 1], self._page_entries[index] = (
                self._page_entries[index],
                self._page_entries[index + 1],
            )
        self._refresh_page_list()
        for index in indices:
            self._pages_list.selection_set(min(len(self._page_entries) - 1, index + 1))

    def _toggle_exclude(self) -> None:
        """Toggle include/exclude on selected pages."""
        indices = self._selected_page_indices()
        if not indices:
            return
        for index in indices:
            self._page_entries[index]["included"] = not self._page_entries[index]["included"]
        self._refresh_page_list()

    def _included_names(self) -> tuple[str, ...]:
        """Return included page names in list order.

        Returns:
            tuple[str, ...]: Names passed to :class:`JobConfig`.
        """
        return tuple(entry["name"] for entry in self._page_entries if entry["included"])

    def _build_config(self) -> JobConfig:
        """Build a :class:`JobConfig` from the form.

        Returns:
            JobConfig: Validated job settings.

        Raises:
            BinderyError: On validation failure.
            ValueError: On invalid numeric widgets.
        """
        page_names = self._included_names()
        if not page_names:
            raise BinderyError("at least one page must be included")
        return JobConfig(
            source_dir=Path(self._source_var.get().strip()),
            output_path=Path(self._output_var.get().strip()),
            margins=MarginSpec.uniform(int(self._margin_var.get())),
            grayscale=bool(self._grayscale_var.get()),
            stamp_page_numbers=bool(self._stamp_var.get()),
            dpi=int(self._dpi_var.get()),
            force=bool(self._force_var.get()),
            title=self._title_var.get() or None,
            author=self._author_var.get() or None,
            rotate=int(str(self._rotate_var.get())),
            page_size=self._page_size_var.get().strip() or None,
            compress=self._compress_var.get() or "lossless",
            page_names=page_names,
        )

    def _start(self) -> None:
        """Validate form and start a background assemble job."""
        if self._worker is not None and self._worker.is_alive():
            return
        source = self._source_var.get().strip()
        output = self._output_var.get().strip()
        if not source or not output:
            messagebox.showerror("bindery", "Source folder and output PDF are required.")
            return
        if not self._page_entries:
            self._reload_pages()

        try:
            config = self._build_config()
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

    def _preview(self) -> None:
        """Transform the first included page and show a thumbnail."""
        source = self._source_var.get().strip()
        if not source or not self._page_entries:
            messagebox.showerror("bindery", "Select a source folder first.")
            return
        try:
            config = self._build_config()
            discovered = discover_page_files(config.source_dir)
            selected = select_pages(discovered, config.page_names)
            if not selected:
                raise BinderyError("no included pages to preview")
            page = selected[0]
            work_dir = Path(tempfile.mkdtemp(prefix="bindery-preview-"))
            written = transform_page(PageFile(path=page.path, index=0), config, work_dir)
            try:
                from PIL import Image, ImageTk

                with Image.open(written) as src:
                    preview = src.convert("RGB")
                    preview.thumbnail((180, 220))
                    self._preview_photo = ImageTk.PhotoImage(preview)
                self._preview_label.configure(image=self._preview_photo, text="")
                self._append_log(f"Preview {page.name} → {written}")
                self._status_var.set("Preview ready")
            finally:
                import shutil

                shutil.rmtree(work_dir, ignore_errors=True)
        except (BinderyError, ValueError, OSError) as exc:
            messagebox.showerror("bindery", str(exc))

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
