import tkinter as tk
from tkinter import filedialog, messagebox
import re
import os
from datetime import datetime
import webbrowser

# ===== функция чтения файла с автоопределением кодировки =====
def read_log_file(path):
    encodings = ["utf-8", "cp1251", "windows-1251"]
    for enc in encodings:
        try:
            with open(path, encoding=enc) as f:
                return f.readlines()
        except UnicodeDecodeError:
            continue
    raise Exception("Не удалось определить кодировку лог файла")

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
    exit()

# ===== имя HTML отчета =====
now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
default_name = f"smoke_report_{now}.html"

# ===== выбор места сохранения =====
report_file = filedialog.asksaveasfilename(
    title="Куда сохранить HTML отчет",
    defaultextension=".html",
    initialfile=default_name,
    filetypes=[("HTML files", "*.html")]
)
if not report_file:
    messagebox.showerror("Ошибка", "Не выбрано место сохранения отчета")
    exit()

# ===== читаем лог =====
lines = read_log_file(log_file)

# ===== парсинг =====
tests = []
current_file = None
expected = None

for line in lines:
    m = re.search(r'Processing file (\S+)', line)
    if m:
        current_file = m.group(1)
        expected = None
    m = re.search(r'comment:\s*(.+)', line)
    if m:
        expected = m.group(1).strip()
    m = re.search(r'Finished file (\S+); status:\s*(\w+)', line)
    if m:
        file_name = m.group(1)
        status = m.group(2)
        tests.append((file_name, expected, status))

# ===== анализ =====
rows = []
failed_files = []
pass_count = 0
fail_count = 0

for file_name, expected, status in tests:
    if expected is None:
        continue
    if "OK" in expected and status == "done":
        result = "PASS"
        pass_count += 1
    elif "ERROR" in expected and status == "rejected":
        result = "PASS"
        pass_count += 1
    else:
        result = "FAIL"
        fail_count += 1
        failed_files.append(file_name)
    rows.append((file_name, expected, status, result))

total = pass_count + fail_count
percent = (pass_count / total) * 100 if total else 0

# ===== генерация HTML =====
html = f"""
<html>
<head>
    <meta charset="UTF-8">
    <title>Smoke Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .PASS {{ background-color: #c6efce; }}
        .FAIL {{ background-color: #ffc7ce; }}
    </style>
</head>
<body>
    <h2>SMOKE TEST REPORT</h2>
    <p><b>Total:</b> {total} &nbsp;&nbsp; <b>PASS:</b> {pass_count} &nbsp;&nbsp; <b>FAIL:</b> {fail_count} &nbsp;&nbsp; <b>Success Rate:</b> {percent:.2f}%</p>
    <table>
        <tr>
            <th>File</th>
            <th>Expected</th>
            <th>Actual Status</th>
            <th>Result</th>
        </tr>
"""

for r in rows:
    status_class = r[3]
    html += f"<tr class='{status_class}'>"
    html += f"<td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td>"
    html += "</tr>"

html += "</table>"

if failed_files:
    html += "<h3>Failed Files:</h3><ul>"
    for f in failed_files:
        html += f"<li>{f}</li>"
    html += "</ul>"

html += "<p><b>Версия схемы:</b> 5.0</p>"
html += f"<p>Report saved at: {report_file}</p></body></html>"

# ===== запись в файл =====
with open(report_file, "w", encoding="utf-8") as f:
    f.write(html)

# ===== открыть отчет в браузере =====
webbrowser.open(f"file://{report_file}")