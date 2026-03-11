import re

log_file = "logs/loader.log"

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


pass_count = 0
fail_count = 0

print("\nSMOKE RESULTS\n")

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

    print(f"{result:5} | {file_name:40} | expected: {expected} | got: {status}")


print("\nSUMMARY")
print("PASS:", pass_count)
print("FAIL:", fail_count)
print("TOTAL:", pass_count + fail_count)