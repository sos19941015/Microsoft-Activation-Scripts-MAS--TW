import requests, re
url = 'https://raw.githubusercontent.com/massgravel/Microsoft-Activation-Scripts/master/MAS/All-In-One-Version-KL/MAS_AIO.cmd'
lines = requests.get(url).content.decode('utf-8-sig', errors='replace').splitlines()

for i, line in enumerate(lines):
    if re.match(r'^\s*set\s+"[A-Za-z_]+=', line) and re.search(r'[A-Za-z]{4,}', line):
        val = line.split('=', 1)[1]
        if not re.search(r'(?:%\w+%|\\|/|\^|&|\||\()', val):
            print(f'L{i+1}: {line.strip()}')
    elif re.match(r'^\s*choice\b', line, re.IGNORECASE):
        print(f'L{i+1}: {line.strip()}')
