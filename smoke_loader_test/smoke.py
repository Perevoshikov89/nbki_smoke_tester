import re
import csv
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)  # автоматический сброс цвета после строки

log_file = "logs/loader.log"
now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
report_file = f"reports/smoke_report_{now}.csv"

tests = []
current_file = None
expected = None

# читаем лог
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

pass_count = 0
fail_count = 0
rows = []
failed_files = []

print("\nSMOKE RESULTS\n")

for file_name, expected, status in tests:
    if expected is None:
        continue

    if "OK" in expected and status == "done":
        result = "PASS"
        pass_count += 1
        color = Fore.GREEN
    elif "ERROR" in expected and status == "rejected":
        result = "PASS"
        pass_count += 1
        color = Fore.GREEN
    else:
        result = "FAIL"
        fail_count += 1
        color = Fore.RED
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

# запись отчета CSV
with open(report_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, delimiter=";")
    writer.writerow(["file", "expected", "actual_status", "result"])
    for r in rows:
        writer.writerow(r)

print("\nОтчет сохранен:")
print(report_file)