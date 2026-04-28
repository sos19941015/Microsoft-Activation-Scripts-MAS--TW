import re
sl = 'set "eline=echo: &call :dk_color %Red% "==== ERROR ====" &echo:"'
m = re.search(r'call\s+:dk_color[^&|<>]*', sl, re.IGNORECASE)
if m:
    args = m.group(0)
    print('Found call:', args)
    for qm in re.finditer(r'"([^"]+)"', args):
        print('  Quoted:', qm.group(1))

sl2 = 'call :dk_color %Blue% "Check this webpage for help - " %_Yellow% " %mas%troubleshoot"'
m2 = re.search(r'call\s+:dk_color[^&|<>]*', sl2, re.IGNORECASE)
if m2:
    args2 = m2.group(0)
    print('Found call 2:', args2)
    for qm in re.finditer(r'"([^"]+)"', args2):
        print('  Quoted 2:', qm.group(1))
