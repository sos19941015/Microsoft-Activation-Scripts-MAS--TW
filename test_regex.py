import re
sl = 'set "eline=echo: &call :dk_color %Red% "==== ERROR ====" &echo:"'
# find all dk_color calls
for m in re.finditer(r'call\s+:dk_color\w*(\s+(?:"[^"]*"|\S+))+', sl, re.IGNORECASE):
    args = m.group(0)
    print('Found call:', args)
    # The actual dk_color call might be followed by &echo:", so we should just grab quoted strings inside the matched call
    for qm in re.finditer(r'"([^"]+)"', args):
        print('  Quoted:', qm.group(1))

print("---------")
sl2 = 'call :dk_color2 %White% "Text 1" %Green% "Text 2"'
for m in re.finditer(r'call\s+:dk_color\w*(\s+(?:"[^"]*"|\S+))+', sl2, re.IGNORECASE):
    args = m.group(0)
    print('Found call:', args)
    for qm in re.finditer(r'"([^"]+)"', args):
        print('  Quoted:', qm.group(1))
