import re
import requests
url = 'https://get.activated.win/'
content = requests.get(url).text
lines = content.splitlines()

for line in lines:
    segments = []
    # match Write-Host, Write-Output, Write-Warning, Write-Progress
    # Note: Write-Warning might have double quotes with variables like "Hash ($hash) mismatch, aborting!`nReport this issue at $troubleshoot"
    # Write-Progress has parameters like -Activity "Downloading..." -Status "Please wait"
    
    # We can match all strings that belong to Write-* commands
    if re.search(r'Write-(?:Host|Output|Warning|Progress)', line, re.IGNORECASE):
        for m in re.finditer(r'''["']([^"']{3,})["']''', line):
            segments.append(m.group(1))
    
    if segments:
        print(line.strip())
        for s in segments:
            print('  ->', s)
