with open('scratch/test_script_2.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(max(0, 1835 - 15), min(len(lines), 1835 + 15)):
    print(f"{i+1}: {lines[i]}", end='')
