import csv
import re
import os
import io
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Loose gmail matcher — finds gmail inside a cell even with extra text
GMAIL_IN_CELL_RE = re.compile(
    r"[A-Za-z0-9._%+\-]+@(?:gmail\.com|googlemail\.com)\b",
    re.IGNORECASE,
)
# Any-email matcher (for reporting totals)
ANY_EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
)
# Header matcher for Google Contacts export
EMAIL_COL_RE = re.compile(r"E-?mail\s*\d*\s*-\s*Value", re.IGNORECASE)


class GmailExtractorApp:
    def __init__(self, root):
        self.root = root
        root.title("Gmail Batch Extractor (Debug)")
        root.geometry("1000x720")
        root.minsize(860, 600)

        self.emails = []
        self.batches = []
        self.debug_lines = []

        self._build_ui()

    # ---------------- UI ----------------
    def _build_ui(self):
        pad = {"padx": 8, "pady": 6}

        top = ttk.LabelFrame(self.root, text="1. Select Google Contacts CSV")
        top.pack(fill="x", **pad)

        self.csv_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.csv_var).pack(
            side="left", fill="x", expand=True, padx=6, pady=6)
        ttk.Button(top, text="Browse…", command=self.pick_csv).pack(
            side="left", padx=6, pady=6)
        ttk.Button(top, text="Extract", command=self.extract).pack(
            side="left", padx=6, pady=6)
        ttk.Button(top, text="Inspect CSV", command=self.inspect_csv).pack(
            side="left", padx=6, pady=6)

        opts = ttk.LabelFrame(self.root, text="2. Options")
        opts.pack(fill="x", **pad)

        ttk.Label(opts, text="Batch size:").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        self.batch_size = tk.IntVar(value=50)
        ttk.Spinbox(opts, from_=1, to=500, textvariable=self.batch_size,
                    width=6, command=self.rebatch).grid(row=0, column=1, sticky="w")

        self.include_googlemail = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Include @googlemail.com",
                        variable=self.include_googlemail,
                        command=self.extract).grid(row=0, column=2, padx=12, sticky="w")

        self.dedupe_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Remove duplicates",
                        variable=self.dedupe_var,
                        command=self.extract).grid(row=0, column=3, padx=12, sticky="w")

        self.loose_mode = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Loose match (find gmail inside any cell)",
                        variable=self.loose_mode,
                        command=self.extract).grid(row=0, column=4, padx=12, sticky="w")

        # Split pane: batches | log
        mid = ttk.Panedwindow(self.root, orient="horizontal")
        mid.pack(fill="both", expand=True, **pad)

        # Left: batches
        left = ttk.LabelFrame(mid, text="3. Batches")
        mid.add(left, weight=1)

        self.batch_list = tk.Listbox(left, height=6, exportselection=False)
        self.batch_list.pack(side="top", fill="x", padx=6, pady=6)
        self.batch_list.bind("<<ListboxSelect>>", self.show_batch)

        self.text = tk.Text(left, wrap="none", height=10)
        self.text.pack(side="top", fill="both", expand=True, padx=6, pady=6)

        # Right: debug log
        right = ttk.LabelFrame(mid, text="4. Debug Log")
        mid.add(right, weight=1)

        self.log_text = tk.Text(right, wrap="word", height=10,
                                bg="#111", fg="#0f0", insertbackground="#0f0")
        self.log_text.pack(side="top", fill="both", expand=True, padx=6, pady=(6, 0))

        log_btns = ttk.Frame(right)
        log_btns.pack(fill="x", padx=6, pady=6)
        ttk.Button(log_btns, text="Copy Log", command=self.copy_log).pack(side="left", padx=4)
        ttk.Button(log_btns, text="Save Log…", command=self.save_log).pack(side="left", padx=4)
        ttk.Button(log_btns, text="Clear Log", command=self.clear_log).pack(side="left", padx=4)

        # Actions
        act = ttk.Frame(self.root)
        act.pack(fill="x", **pad)

        ttk.Button(act, text="Copy current batch",
                   command=self.copy_current).pack(side="left", padx=4)
        ttk.Button(act, text="Copy ALL emails",
                   command=self.copy_all).pack(side="left", padx=4)
        ttk.Button(act, text="Export batches to folder…",
                   command=self.export_batches).pack(side="left", padx=4)
        ttk.Button(act, text="Export as .txt",
                   command=self.export_txt).pack(side="left", padx=4)

        self.status = tk.StringVar(value="Ready.")
        ttk.Label(self.root, textvariable=self.status, anchor="w",
                  relief="sunken").pack(fill="x", side="bottom")

    # ---------------- Logging ----------------
    def log(self, msg=""):
        self.debug_lines.append(str(msg))
        self.log_text.insert("end", str(msg) + "\n")
        self.log_text.see("end")
        self.root.update_idletasks()

    def clear_log(self):
        self.debug_lines.clear()
        self.log_text.delete("1.0", "end")

    def copy_log(self):
        payload = "\n".join(self.debug_lines)
        self.root.clipboard_clear()
        self.root.clipboard_append(payload)
        self.status.set(f"Copied {len(self.debug_lines)} log line(s) to clipboard.")

    def save_log(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile="csv_debug_log.txt",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.debug_lines))
        self.status.set(f"Saved log to {path}")

    # ---------------- Logic ----------------
    def pick_csv(self):
        path = filedialog.askopenfilename(
            title="Select Google Contacts CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self.csv_var.set(path)
            self.extract()

    # --- encoding & delimiter sniffing ---
    def _read_text_flexible(self, path):
        """Try UTF-8, UTF-8-BOM, then UTF-16. Return (text, encoding_used)."""
        with open(path, "rb") as f:
            raw = f.read()
        self.log(f"[file] size = {len(raw)} bytes")

        if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
            return raw.decode("utf-16"), "utf-16"
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                return raw.decode(enc), enc
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace"), "utf-8(replace)"

    def _sniff_delimiter(self, sample):
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            return dialect.delimiter
        except Exception:
            return ","

    def _read_csv_rows(self, path):
        text, enc = self._read_text_flexible(path)
        self.log(f"[file] encoding used = {enc}")

        sample = text[:8192]
        delim = self._sniff_delimiter(sample)
        self.log(f"[file] delimiter detected = {delim!r}")

        reader = csv.DictReader(io.StringIO(text), delimiter=delim)
        headers = reader.fieldnames or []
        self.log(f"[csv] {len(headers)} column(s):")
        for h in headers:
            self.log(f"      - {h!r}")

        rows = list(reader)
        self.log(f"[csv] {len(rows)} data row(s)")
        return headers, rows

    def _find_email_columns(self, headers):
        email_cols = [h for h in headers if h and EMAIL_COL_RE.search(h)]
        if email_cols:
            self.log(f"[cols] matched E-mail N - Value pattern: {email_cols}")
            return email_cols

        email_cols = [h for h in headers if h and "mail" in h.lower()]
        if email_cols:
            self.log(f"[cols] fallback (header contains 'mail'): {email_cols}")
            return email_cols

        self.log("[cols] WARNING: no email-like columns found.")
        return []

    # ---------------- INSPECT ----------------
    def inspect_csv(self):
        """Report per-column stats: non-empty count, sample values, @ count."""
        path = self.csv_var.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showinfo("No file", "Pick a CSV first.")
            return

        self.log("=" * 60)
        self.log(f"[inspect] {path}")

        try:
            headers, rows = self._read_csv_rows(path)
        except Exception as e:
            self.log(f"[ERROR] reading CSV: {e}")
            messagebox.showerror("Error reading CSV", str(e))
            return

        if not rows:
            self.log("[inspect] no data rows.")
            self.status.set("CSV has no data rows.")
            return

        self.log(f"[inspect] analyzing {len(headers)} column(s) across {len(rows)} row(s)")
        self.log("-" * 60)
        self.log(f"{'#':>3}  {'non-empty':>9}  {'@count':>6}  column")
        self.log("-" * 60)

        total_cells_with_at = 0
        for i, h in enumerate(headers, 1):
            nonempty = 0
            at_count = 0
            for r in rows:
                v = r.get(h)
                if v is None:
                    continue
                s = str(v).strip()
                if s:
                    nonempty += 1
                    at_count += s.count("@")
            total_cells_with_at += at_count
            flag = ""
            if at_count > 0:
                flag = "  <-- has @"
            elif "mail" in (h or "").lower():
                flag = "  <-- header says email, but empty!"
            self.log(f"{i:>3}  {nonempty:>9}  {at_count:>6}  {h}{flag}")

        self.log("-" * 60)
        self.log(f"[inspect] total '@' occurrences across ALL cells: {total_cells_with_at}")

        # Quick verdict
        email_cols = [h for h in headers if h and EMAIL_COL_RE.search(h)]
        if not email_cols and total_cells_with_at == 0:
            self.log("[inspect] VERDICT: This CSV contains NO email data at all.")
            self.log("          It is a phone/name-only export.")
        elif email_cols and total_cells_with_at == 0:
            self.log("[inspect] VERDICT: Email columns exist but are all empty.")
        elif total_cells_with_at > 0:
            self.log("[inspect] VERDICT: Email data present. Click 'Extract' to pull gmail addresses.")

        self.status.set(
            f"Inspected {len(headers)} columns, {len(rows)} rows, "
            f"{total_cells_with_at} '@' chars total."
        )

    # ---------------- EXTRACT ----------------
    def extract(self):
        path = self.csv_var.get().strip()
        if not path or not os.path.isfile(path):
            return

        self.log("=" * 60)
        self.log(f"[run] {path}")

        try:
            headers, rows = self._read_csv_rows(path)
        except Exception as e:
            self.log(f"[ERROR] reading CSV: {e}")
            messagebox.showerror("Error reading CSV", str(e))
            return

        if not rows:
            self.log("[ERROR] CSV has no data rows.")
            self.status.set("CSV has no rows.")
            return

        self.log("[sample] first row values:")
        for k, v in list(rows[0].items())[:25]:
            self.log(f"      {k!r} = {v!r}")

        email_cols = self._find_email_columns(headers)
        scan_all_cells = not email_cols
        if scan_all_cells:
            self.log("[cols] -> scanning ALL cells for gmail addresses")

        loose = self.loose_mode.get()
        allow_googlemail = self.include_googlemail.get()

        raw_emails = set()
        rows_with_email = 0

        for row in rows:
            row_hit = False
            cells = row.values() if scan_all_cells else (row.get(c) for c in email_cols)
            for cell in cells:
                if not cell:
                    continue
                s = str(cell)
                if loose:
                    for m in GMAIL_IN_CELL_RE.finditer(s):
                        raw_emails.add(m.group(0).lower())
                        row_hit = True
                    for m in ANY_EMAIL_RE.finditer(s):
                        raw_emails.add(m.group(0).lower())
                else:
                    for part in re.split(r"[;,\s]+", s.strip()):
                        if part and "@" in part:
                            raw_emails.add(part.strip().lower())
                            row_hit = True
            if row_hit:
                rows_with_email += 1

        self.log(f"[scan] {len(raw_emails)} unique email(s) total (any domain)")
        self.log(f"[scan] {rows_with_email} row(s) contributed at least one email")

        gmail_only = []
        non_gmail = []
        for e in raw_emails:
            if GMAIL_IN_CELL_RE.fullmatch(e):
                if allow_googlemail or e.endswith("@gmail.com"):
                    gmail_only.append(e)
            else:
                non_gmail.append(e)

        self.log(f"[filter] {len(gmail_only)} gmail address(es)")
        self.log(f"[filter] {len(non_gmail)} non-gmail address(es) skipped")
        if non_gmail[:10]:
            self.log("[filter] sample non-gmail skipped:")
            for e in non_gmail[:10]:
                self.log(f"      {e}")

        if self.dedupe_var.get():
            gmail_only = sorted(set(gmail_only))
        else:
            gmail_only = sorted(gmail_only)

        self.emails = gmail_only
        self.rebatch()

        if not gmail_only:
            self.log("[result] ZERO gmail addresses found.")
            self.log("         Click 'Inspect CSV' to see which columns have data.")
        else:
            self.log(f"[result] {len(gmail_only)} gmail address(es) ready.")

        self.status.set(
            f"Found {len(gmail_only)} Gmail address(es) from {len(raw_emails)} total email(s)."
        )

    def rebatch(self):
        try:
            size = max(1, int(self.batch_size.get()))
        except Exception:
            size = 50
        self.batches = [self.emails[i:i + size] for i in range(0, len(self.emails), size)]

        self.batch_list.delete(0, "end")
        for i, b in enumerate(self.batches, 1):
            self.batch_list.insert("end", f"Batch {i}  ({len(b)} emails)")

        if self.batches:
            self.batch_list.selection_set(0)
            self.show_batch()
        else:
            self.text.delete("1.0", "end")

    def _current_index(self):
        sel = self.batch_list.curselection()
        return sel[0] if sel else None

    def show_batch(self, _evt=None):
        idx = self._current_index()
        if idx is None:
            return
        self.text.delete("1.0", "end")
        self.text.insert("1.0", "\n".join(self.batches[idx]))

    # ---------------- Actions ----------------
    def copy_current(self):
        idx = self._current_index()
        if idx is None:
            return
        payload = ", ".join(self.batches[idx])
        self.root.clipboard_clear()
        self.root.clipboard_append(payload)
        self.status.set(f"Copied batch {idx + 1} ({len(self.batches[idx])} emails).")

    def copy_all(self):
        if not self.emails:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(", ".join(self.emails))
        self.status.set(f"Copied ALL {len(self.emails)} emails.")

    def export_txt(self):
        if not self.emails:
            messagebox.showinfo("Nothing to export", "Extract emails first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile="gmail_emails.txt",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.emails))
        self.status.set(f"Saved {len(self.emails)} emails.")

    def export_batches(self):
        if not self.batches:
            messagebox.showinfo("Nothing to export", "Extract emails first.")
            return
        folder = filedialog.askdirectory(title="Choose folder for batches")
        if not folder:
            return
        for i, b in enumerate(self.batches, 1):
            fname = os.path.join(folder, f"batch_{i:03d}.txt")
            with open(fname, "w", encoding="utf-8") as f:
                f.write(", ".join(b))
        self.status.set(f"Wrote {len(self.batches)} batch file(s).")


if __name__ == "__main__":
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    GmailExtractorApp(root)
    root.mainloop()