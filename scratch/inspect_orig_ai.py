with open('scratch/aiConfigModal_original.html', 'r', encoding='utf-8') as f:
    text = f.read()

print("Original length:", len(text))
# Check if it has modal wrappers
print("First 300 chars:")
print(text[:300])
print("Last 300 chars:")
print(text[-300:])
