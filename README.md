# Gmail Batch Extractor (Debug)

A small Tkinter desktop app for pulling Gmail addresses out of a Google Contacts CSV export, deduplicating them, splitting them into batches, and exporting or copying the results. It includes a built-in debug log and a CSV inspector so you can see exactly what the tool is reading.

---

## Features

- **CSV import** — reads Google Contacts CSV exports with automatic encoding detection (UTF-16, UTF-8, UTF-8-BOM, CP1252, Latin-1) and delimiter sniffing (`,` `;` `\t` `|`).
- **Gmail extraction**
  - Targets the standard Google Contacts `E-mail N - Value` columns.
  - Falls back to scanning any column whose header contains `mail`.
  - If no email-like columns exist, scans **every cell** in the file.
- **Loose matching mode** — finds a Gmail address even when it's embedded inside a larger string (e.g. `John <john.doe@gmail.com>`).
- **Optional `@googlemail.com` inclusion** — toggle on/off.
- **Deduplication** — collapse repeated addresses.
- **Batching** — split results into chunks of a configurable size (1–500).
- **CSV Inspector** — per-column report showing non-empty counts, `@` counts, and sample verdicts, so you can tell at a glance whether the CSV actually contains email data.
- **Debug log** — colour-coded log pane with Copy / Save / Clear buttons.
- **Export options** — copy the current batch, copy all emails, export a single `.txt`, or export one file per batch into a chosen folder.

---

## Requirements

- **Python 3.7+**
- Tkinter (bundled with standard CPython on Windows/macOS; on Linux you may need `python3-tk`)

No third-party packages are required.

---

## Installation

1. Save the script as e.g. `gmail_extractor.py`.
2. (Linux only, if needed) install Tkinter:
   ```bash
   sudo apt install python3-tk
   ```

---

## Usage

Run the script:

```bash
python gmail_extractor.py
```

Then, in the window:

1. **Select Google Contacts CSV** — click **Browse…** and pick your CSV. Extraction runs automatically.
2. **Options** — set batch size, and toggle:
   - *Include @googlemail.com*
   - *Remove duplicates*
   - *Loose match (find gmail inside any cell)*
3. **Batches** — click a batch in the list to preview it on the left.
4. **Debug Log** — watch the right-hand pane for details on encoding, columns found, matches, and any warnings.
5. **Actions** — copy the current batch, copy everything, export a single `.txt`, or export one `.txt` per batch into a folder.

### Inspecting a CSV first

If extraction returns nothing, click **Inspect CSV**. It prints a table like:

```
  #  non-empty  @count  column
  1        250       0  First Name
  2        250       0  Last Name
  3        118     118  E-mail 1 - Value
...
```

This tells you whether the CSV has any emails at all, or whether the email column is simply empty.

---

## Output formats

- **Copy current batch / Copy ALL** — comma-separated list on the clipboard.
- **Export as .txt** — one email per line.
- **Export batches to folder…** — writes `batch_001.txt`, `batch_002.txt`, … each containing a comma-separated batch.

---

## Notes & limitations

- The tool is *Gmail-focused*. Other addresses are detected and counted in the log, but only Gmail (`@gmail.com`, and optionally `@googlemail.com`) are kept.
- **Loose mode** may pick up addresses that appear in notes, signatures, or other free-text fields. Turn it off if you want strict column-based extraction only.
- All processing is local — no network access, no data leaves your machine.

---

## Troubleshooting

| Symptom | Try this |
|---|---|
| `Found 0 Gmail address(es)` | Click **Inspect CSV** to verify the file actually contains emails, and check the log for detected columns. |
| Emails found but not the ones you expect | Disable **Loose match** to restrict extraction to email columns only. |
| Weird characters in output | The log shows which encoding was used; re-export the CSV as UTF-8 from Google Contacts if possible. |
| Batch size won't change | Click into the spinbox or use the arrows — the list rebuilds automatically. |

---

## License

Use at your own risk. No warranty provided.
