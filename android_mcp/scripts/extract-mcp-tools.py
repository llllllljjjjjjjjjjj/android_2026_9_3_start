import glob, re, os

for f in sorted(glob.glob(r'android_mcp\servers\**\*.py', recursive=True)):
    if '__pycache__' in f or os.path.basename(f) == '__init__.py':
        continue
    try:
        src = open(f, encoding='utf-8').read()
    except Exception:
        continue
    tools = re.findall(r'@server\.tool\(\s*[\'"]([^\'"]+)[\'"]', src)
    if tools:
        print(os.path.relpath(f).replace('\\', '/'), '->', ', '.join(tools))
