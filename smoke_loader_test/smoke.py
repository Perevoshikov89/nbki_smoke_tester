import tkinter as tk
from tkinter import filedialog, messagebox
import re
import csv
import os
from datetime import datetime
from colorama import init, Fore, Style

# Инициализация цвета
init(autoreset=True)

# ===== GUI для выбора лог-файла =====
root = tk.Tk()
root.withdraw()  # скрываем главное окно

log_file = filedialog.askopenfilename(
    title="Выберите лог-файл",
    filetypes=[("Log files", "*.log"), ("All files", "*.*")]
)

if not log_file:
    messagebox.showerror("Ошибка", "Файл не выбран!")
    exit()

# ===== Настройка папки для отчетов =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
reports_dir = os.path.join(BASE_DIR, "reports")
os.makedirs(reports_dir, exist_ok=True)

now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
report_file = os.path.join(reports_dir, f"smoke_report_{now}.csv")

# ===== Чтение лог-файла и анализ =====
tests = []
current_file = None
expected = None

with open(log_file, encoding="utf-8") as f:
    for line in f:
        m = re.search(r'Processing file (\S+)', line)
        if m:
            current_file = m.group(1)
            expected = None

        m = re.search(r'comment:\s*(.+)', line)
        if m:
            expected = m.group(1)

        m = re.search(r'Finished file (\S+); status:\s*(\w+)', line)
        if m:
            file_name = m.group(1)
            status = m.group(2)
            tests.append((file_name, expected, status))

# ===== Анализ и вывод в консоль =====
rows = []
failed_files = []
pass_count = 0
fail_count = 0

for file_name, expected, status in tests:
    if expected is None:
        continue

    if "OK" in expected and status == "done":
        result = "PASS"
        color = Fore.GREEN
        pass_count += 1
    elif "ERROR" in expected and status == "rejected":
        result = "PASS"
        color = Fore.GREEN
        pass_count += 1
    else:
        result = "FAIL"
        color = Fore.RED
        fail_count += 1
        failed_files.append(file_name)

    print(f"{color}{result:5} | {file_name:40} | expected: {expected} | got: {status}{Style.RESET_ALL}")
    rows.append([file_name, expected, status, result])

total = pass_count + fail_count
percent = (pass_count / total) * 100 if total else 0

print("\nSUMMARY")
print(f"PASS: {pass_count}")
print(f"FAIL: {fail_count}")
print(f"TOTAL: {total}")
print(f"SMOKE RESULT: {percent:.2f}%")

if failed_files:
    print("\nFAILED TESTS:")
    for f in failed_files:
        print(f"- {f}")

# ===== Запись CSV =====
with open(report_file, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f, delimiter=";")
    writer.writerow(["file", "expected", "actual_status", "result"])
    for r in rows:
        writer.writerow(r)

messagebox.showinfo("Отчет готов", f"CSV отчет сохранен:\n{report_file}")

