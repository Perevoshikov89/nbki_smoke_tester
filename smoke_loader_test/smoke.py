import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import re
from datetime import datetime
import webbrowser
import sys
from pathlib import Path

# ===== константы =====
SMOKE_FILE_PREFIXES = ("YP01MM000001", "MM01MM000001")



# ===== соответствие ожидаемого результата и статуса loader =====

EXPECTED_STATUS = {
    "OK": "done",
    "ERROR": "rejected",
    "WRONGBLOCK": "rejected",
    "LASTRECORD": "rejected",
    "ORG.XML.SAX.SAXPARSEEXCEPTION": "rejected",
    "SUBJECT NOTFOUND": "rejected",
    "NOTFOUND": "done",
    "NOTUPDATE": "done",
}


# ===== чтение лога =====
def read_log_file(path):
    encodings = ["utf-8", "cp1251", "windows-1251"]
    for enc in encodings:
        try:
            with open(path, encoding=enc) as f:
                return f.readlines()
        except UnicodeDecodeError:
            continue
    raise Exception("Не удалось определить кодировку лог файла")

# ===== парсинг времени =====
def parse_log_time(line):
    m = re.match(r"(\d{2}\.\d{2}\.\d{4})\s+(\d{2}):(\d{2}):(\d{2})\.\d{3}", line)
    if m:
        return f"{m.group(2)}:{m.group(3)}"
    return None


# ===== GUI =====
root = tk.Tk()
root.withdraw()

# ===== лог файл =====
log_file = filedialog.askopenfilename(
    title="Выберите лог файл loader",
    filetypes=[("Log files", "*.log"), ("All files", "*.*")]
)

if not log_file:
    messagebox.showerror("Ошибка", "Лог файл не выбран")
    sys.exit()

# ===== время =====

start_time = simpledialog.askstring(
    "Укажите время начала обработки",
    "HH:MM"
)

end_time = simpledialog.askstring(
    "Укажите время конца обработки",
    "HH:MM"
)

if not start_time or not end_time:
    sys.exit()

try:
    datetime.strptime(start_time, "%H:%M")
    datetime.strptime(end_time, "%H:%M")
except ValueError:
    messagebox.showerror(
        "Ошибка",
        "Введите время в формате HH:MM"
    )
    sys.exit()




# ===== Выбор папки с тестовыми файлами XML =====
xml_folder = filedialog.askdirectory(title="Выберите папку с тестовыми файлами XML")
if not xml_folder:
    sys.exit()

# ===== отчет =====
now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

default_name = f"smoke_test_report_{now}.html"

report_file = filedialog.asksaveasfilename(
    title="Выберете место сохранения HTML отчета",
    defaultextension=".html",
    initialfile=default_name,
    filetypes=[("HTML files", "*.html")]
)

if not report_file:
    sys.exit()

# ===== XML словарь =====
xml_map = {}

for xml_file in Path(xml_folder).glob("*.xml"):

    if not xml_file.name.startswith(SMOKE_FILE_PREFIXES):
        continue

    text = xml_file.read_text(encoding="utf-8", errors="ignore")

    m = re.search(r'eventComment="([^"]+)"', text, re.IGNORECASE)
    event_comment = m.group(1) if m else ""

    exp = re.search(
    r"EXP:\s*(OK|ERROR|WRONGBLOCK|LASTRECORD|ORG\.XML\.SAX\.SAXPARSEEXCEPTION|SUBJECT\s+NOTFOUND|NOTFOUND|NOTUPDATE)",
    event_comment,
    re.IGNORECASE
)

    expected = ""

    if exp:
        expected = re.sub(
            r"\s+",
            " ",
            exp.group(1).upper()
        ).strip()

    xml_map[xml_file.name] = {
        "event_comment": event_comment,
        "expected": expected
    }
    

print(f"XML loaded: {len(xml_map)}")

# ===== ЛОГ =====
lines = read_log_file(log_file)

results = {}
reject_messages = {}

runtime_error = None
runtime_error_time = None

for line in lines:

    log_time = parse_log_time(line)
    if not log_time:
        continue

    in_range = start_time <= log_time <= end_time

    if in_range and "java.lang.RuntimeException:" in line:
        runtime_error = line.strip()
        runtime_error_time = log_time
        break

    # reject message
    rej = re.search(r"(Reject field .+)", line)
    if rej:
        reject_msg = rej.group(1).strip()
    else:
        reject_msg = None

    # finished file
    m = re.search(r"Finished file (\S+); status:\s*(\w+)", line)

    if m and in_range:

        file_name = re.sub(r"\.\d+$", "", m.group(1))

        if not file_name.startswith(SMOKE_FILE_PREFIXES):
            continue

        status = m.group(2)

        results[file_name] = {
            "status": status,
        }

        if reject_msg:
            reject_messages[file_name] = reject_msg


# ===== если crash =====
if runtime_error:
    html = f"""
    <html><body>
    <h2>CRITICAL ERROR</h2>
    <p>{runtime_error_time}</p>
    <pre>{runtime_error}</pre>
    </body></html>
    """

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(html)

    webbrowser.open("file://" + report_file)
    sys.exit()

# ===== АНАЛИЗ =====
rows = []
failed = []
skipped = []

pass_count = 0
fail_count = 0
skip_count = 0

for file_name, xml in xml_map.items():

    expected = xml["expected"]
    event_comment = xml["event_comment"]

    actual = results.get(file_name)

    if not actual:
        result = "SKIPPED"
        status = ""
        reject = ""
        skip_count += 1
        skipped.append(file_name)

    else:
        status = actual["status"]
        reject = reject_messages.get(file_name, "")

        expected_status = EXPECTED_STATUS.get(expected)

        if expected_status is None:

            result = "SKIPPED"
            skip_count += 1
            skipped.append(file_name)

        elif status == expected_status:

            result = "PASS"
            pass_count += 1

        else:

            result = "FAIL"
            fail_count += 1
            failed.append(file_name)

    rows.append((file_name, event_comment, expected, status, result, reject))


total = pass_count + fail_count + skip_count
percent = (pass_count / total) * 100 if total else 0


# ===== HTML =====
html = f"""
<html>
<head>
<style>
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border: 1px solid #ccc; padding: 5px; }}
.PASS {{ background: #c6efce; }}
.FAIL {{ background: #ffc7ce; }}
.SKIPPED {{ background: #fff2cc; }}
</style>
</head>
<body>

<h2>SMOKE-TEST REPORT</h2>

<p>
Total: {total} |
PASS: {pass_count} |
FAIL: {fail_count} |
SKIP: {skip_count} |
{percent:.2f}%
</p>

<table>
<tr>
<th>File</th>
<th>EventComment</th>
<th>Expected</th>
<th>Actual</th>
<th>Result</th>
<th>Reject</th>
</tr>
"""

for r in rows:
    html += f"""
<tr class="{r[4]}">
<td>{r[0]}</td>
<td>{r[1]}</td>
<td>{r[2]}</td>
<td>{r[3]}</td>
<td>{r[4]}</td>
<td>{r[5]}</td>
</tr>
"""

html += """
</table>
</body>
</html>
"""

with open(report_file, "w", encoding="utf-8") as f:
    f.write(html)

webbrowser.open("file://" + report_file)
