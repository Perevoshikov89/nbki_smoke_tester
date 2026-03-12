import tkinter as tk
from tkinter import filedialog, messagebox
import re
import csv
import os
from datetime import datetime
from openpyxl import Workbook

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

# ===== имя CSV отчета =====
now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
default_name = f"smoke_report_{now}.csv"

# ===== выбор места сохранения =====
report_file = filedialog.asksaveasfilename(
    title="Куда сохранить CSV отчет",
    defaultextension=".csv",
    initialfile=default_name,
    filetypes=[("CSV files", "*.csv")]
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
    rows.append([file_name, expected, status, result])

# ===== запись CSV =====
with open(report_file, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f, delimiter=";")
    writer.writerow(["file", "expected", "actual_status", "result"])
    for r in rows:
        writer.writerow(r)

# ===== конвертация CSV в Excel с автоподбором колонок =====
wb = Workbook()
ws = wb.active
ws.title = "Smoke Report"

# читаем CSV и переносим в Excel
with open(report_file, newline='', encoding='utf-8-sig') as f:
    reader = csv.reader(f, delimiter=';')
    for row in reader:
        ws.append(row)

# автоподбор ширины колонок
for col in ws.columns:
    max_length = 0
    column = col[0].column_letter
    for cell in col:
        if cell.value:
            max_length = max(max_length, len(str(cell.value)))
    ws.column_dimensions[column].width = max_length + 3

# сохраняем Excel рядом с CSV
xlsx_file = report_file.rsplit('.', 1)[0] + ".xlsx"
wb.save(xlsx_file)

# ===== итог =====
total = pass_count + fail_count
percent = (pass_count / total) * 100 if total else 0

summary = f"""
SMOKE TEST RESULT

PASS: {pass_count}
FAIL: {fail_count}
TOTAL: {total}

SUCCESS RATE: {percent:.2f} %
"""
if failed_files:
    summary += "\nFAILED FILES:\n"
    for f in failed_files:
        summary += f"{f}\n"

summary += f"\n\nОтчеты сохранены:\nCSV: {report_file}\nExcel: {xlsx_file}"
messagebox.showinfo("Smoke тест завершен", summary)

# ===== открыть папку с отчетами =====
report_folder = os.path.dirname(report_file)
os.startfile(report_folder)