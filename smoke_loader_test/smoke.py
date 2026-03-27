import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import re
from datetime import datetime
import webbrowser
import sys

# ===== константы =====
SMOKE_FILE_PREFIXES = ("YP01MM000001", "MM01MM000001")

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

# ===== выбор лог файла =====
log_file = filedialog.askopenfilename(
    title="Выберите лог файл loader",
    filetypes=[("Log files", "*.log"), ("All files", "*.*")]
)

if not log_file:
    messagebox.showerror("Ошибка", "Лог файл не выбран")
    sys.exit()

# ===== диапазон времени =====
start_time = simpledialog.askstring(
    "Временной диапазон",
    "Введите ВРЕМЯ НАЧАЛА анализа (HH:MM)\nНапример: 08:30"
)

end_time = simpledialog.askstring(
    "Временной диапазон",
    "Введите ВРЕМЯ КОНЦА анализа (HH:MM)\nНапример: 09:10"
)

if not start_time or not end_time:
    messagebox.showerror("Ошибка", "Не указан временной диапазон")
    sys.exit()

try:
    datetime.strptime(start_time, "%H:%M")
    datetime.strptime(end_time, "%H:%M")
except ValueError:
    messagebox.showerror("Ошибка", "Неверный формат времени HH:MM")
    sys.exit()

# ===== имя отчета =====
now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

default_name = f"smoke_report_{now}.html"

report_file = filedialog.asksaveasfilename(
    title="Куда сохранить HTML отчет",
    defaultextension=".html",
    initialfile=default_name,
    filetypes=[("HTML files", "*.html")]
)

if not report_file:
    messagebox.showerror("Ошибка", "Не выбрано место сохранения отчета")
    sys.exit()

# ===== читаем лог =====
lines = read_log_file(log_file)

# ===== парсинг =====
tests = []

current_file = None
expected = None
reject_message = ""

runtime_error = None
runtime_error_time = None

for line in lines:

    log_time = parse_log_time(line)

    in_range = log_time is not None and start_time <= log_time <= end_time

    # ===== RuntimeException =====
    if in_range and "java.lang.RuntimeException:" in line:
        runtime_error = line.strip()
        runtime_error_time = log_time
        break

    # ===== сообщение Reject field =====
    m = re.search(r"(Reject field .+)", line)
    if m and in_range:
        reject_message = m.group(1).strip()

    # ===== начало обработки файла =====
    m = re.search(r"Processing file (\S+)", line)

    if m:
        current_file = m.group(1)
        expected = None
        reject_message = ""

    # ===== ожидаемый результат =====
    m = re.search(r"comment:\s*(.+)", line)

    if m:
        expected = m.group(1).strip()

    # ===== завершение обработки =====
    m = re.search(r"Finished file (\S+); status:\s*(\w+)", line)

    if m:

        file_name = m.group(1)
        status = m.group(2)

        if file_name.startswith(SMOKE_FILE_PREFIXES) and in_range:
            tests.append((file_name, expected or "", status, reject_message))

# ===== RuntimeException отчет =====
if runtime_error:

    html = f"""
<html>
<head>
<meta charset="UTF-8">
<title>Smoke Test Report</title>
<style>
body {{ font-family: Arial; }}
.error {{
background:#ffc7ce;
padding:20px;
border:2px solid red;
}}
</style>
</head>
<body>

<h2>SMOKE TEST REPORT</h2>

<div class="error">

<b>Критическая ошибка loader</b><br><br>

Время ошибки:<br>
<b>{runtime_error_time}</b><br><br>

Сообщение:<br>
{runtime_error}

<br><br>
Анализ остановлен.

</div>

</body>
</html>
"""

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(html)

    webbrowser.open(f"file://{report_file}")

    sys.exit()

# ===== анализ =====

rows = []

failed_files = []
skipped_files = []

pass_count = 0
fail_count = 0
skip_count = 0

for file_name, expected, status, reject_message in tests:

    if expected == "":
        result = "SKIPPED"
        skip_count += 1
        skipped_files.append(file_name)

    elif "OK" in expected and status == "done":
        result = "PASS"
        pass_count += 1

    elif "ERROR" in expected and status == "rejected":
        result = "PASS"
        pass_count += 1

    elif ("NOTFOUND" in expected or "NOTUPDATE" in expected) and status == "done":
        result = "PASS"
        pass_count += 1
    else:
        result = "FAIL"
        fail_count += 1
        failed_files.append(file_name)

    rows.append((file_name, expected, status, result, reject_message))

total = pass_count + fail_count + skip_count
percent = (pass_count / total) * 100 if total else 0

# ===== HTML отчет =====

html = f"""
<html>
<head>
<meta charset="UTF-8">
<title>Smoke Test Report</title>

<style>

body {{ font-family: Arial; }}

table {{
border-collapse: collapse;
width:100%;
}}

th, td {{
border:1px solid #ddd;
padding:8px;
}}

th {{
background:#f2f2f2;
}}

.PASS {{ background:#c6efce; }}
.FAIL {{ background:#ffc7ce; }}
.SKIPPED {{ background:#fff2cc; }}

</style>

</head>

<body>

<h2>SMOKE TEST REPORT</h2>

<p>
<b>Total:</b> {total}
&nbsp;&nbsp;<b>PASS:</b> {pass_count}
&nbsp;&nbsp;<b>FAIL:</b> {fail_count}
&nbsp;&nbsp;<b>SKIPPED:</b> {skip_count}
&nbsp;&nbsp;<b>Success Rate:</b> {percent:.2f}%
</p>

<table>

<tr>
<th>File</th>
<th>Expected</th>
<th>Actual Status</th>
<th>Result</th>
<th>Reject Message</th>
</tr>
"""

for r in rows:
    html += f"<tr class='{r[3]}'><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td></tr>"

html += "</table>"

# ===== список FAIL =====

if failed_files:

    html += "<h3>Failed Files:</h3><ul>"

    for f in failed_files:
        html += f"<li>{f}</li>"

    html += "</ul>"

# ===== список SKIPPED =====

if skipped_files:

    html += "<h3>Skipped Files (eventComment отсутствует в логе):</h3><ul>"

    for f in skipped_files:
        html += f"<li>{f}</li>"

    html += "</ul>"

html += f"<p><b>Версия схемы:</b> 5.0</p>"
html += f"<p>Report saved at: {report_file}</p>"

html += "</body></html>"

# ===== запись отчета =====

with open(report_file, "w", encoding="utf-8") as f:
    f.write(html)

# ===== открыть отчет =====

webbrowser.open(f"file://{report_file}")