import re
import requests
url = 'https://get.activated.win/'
content = requests.get(url).text
lines = content.splitlines()

for line in lines:
    segments = []
    if re.search(r'\bWrite-(?:Host|Output|Warning|Progress)\b', line, re.IGNORECASE):
        for m in re.finditer(r'"([^"]+)"|\'([^\']+)\'', line):
            text = m.group(1) or m.group(2)
            if len(text) > 2:
                segments.append(text)
    
    if segments:
        print(line.strip())
        for s in segments:
            print('  ->', s)
