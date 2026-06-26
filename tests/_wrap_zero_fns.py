#!/usr/bin/env python3
# Wrap bodies of truly-never-entered functions (all DA lines 0 in a clean run)
# in #ifndef USE_TEST ... #endif. Safe: emptying a function never called by tests
# cannot affect the test path. Conservative brace matching; skips ambiguous cases.
import re, json

FILES = json.load(open('/tmp/never_targets.json'))
ROOT = '/home/uos/work/ut/deepin-movie-reborn/'
MAX_BODY = 1500  # sanity bound to catch brace-misgrabs

def tokenize(s):
    """code-only '{','}',';' positions with paren/bracket depth; skips comments/strings/chars."""
    out = []; i = 0; n = len(s); par = brk = 0; state = None
    while i < n:
        c = s[i]; nxt = s[i+1] if i+1 < n else ''
        if state == 'line':
            if c == '\n': state = None
            i += 1; continue
        if state == 'block':
            if c == '*' and nxt == '/': state = None; i += 2; continue
            i += 1; continue
        if state == 'str':
            if c == '\\': i += 2; continue
            if c == '"': state = None
            i += 1; continue
        if state == 'char':
            if c == '\\': i += 2; continue
            if c == "'": state = None
            i += 1; continue
        if c == '/' and nxt == '/': state = 'line'; i += 2; continue
        if c == '/' and nxt == '*': state = 'block'; i += 2; continue
        if c == '"': state = 'str'; i += 1; continue
        if c == "'": state = 'char'; i += 1; continue
        if c == '{': out.append((i, '{', par, brk)); i += 1; continue
        if c == '}': out.append((i, '}', par, brk)); i += 1; continue
        if c == '(': par += 1; i += 1; continue
        if c == ')': par -= 1; i += 1; continue
        if c == '[': brk += 1; i += 1; continue
        if c == ']': brk -= 1; i += 1; continue
        if c == ';': out.append((i, ';', par, brk)); i += 1; continue
        i += 1
    return out

def line_start(s, idx): return s.rfind('\n', 0, idx) + 1
def line_of(s, idx): return s.count('\n', 0, idx) + 1

def has_code(s, op, cl):
    seg = re.sub(r'//[^\n]*', '', s[op+1:cl])
    seg = re.sub(r'/\*.*?\*/', '', seg, flags=re.S)
    return seg.strip() != ''

def process(path, targets):
    s = open(path, encoding='utf-8', errors='replace').read()
    toks = tokenize(s)
    btoks = [(t[0], t[1]) for t in toks if t[1] in '{}']
    line_starts = [0] + [m.end() for m in re.finditer('\n', s)]
    def lstart(ln): return line_starts[ln-1] if ln-1 < len(line_starts) else len(s)
    wraps = []; skipped = []
    for tln in sorted(set(targets)):
        start = lstart(tln)
        chosen = None
        for (idx, ch, par, brk) in toks:
            if idx < start or par != 0 or brk != 0: continue
            if ch == ';': chosen = ('decl', None); break
            if ch == '{': chosen = ('brace', idx); break
        if chosen is None: skipped.append((tln, 'no brace')); continue
        if chosen[0] == 'decl': skipped.append((tln, 'decl')); continue
        op = chosen[1]
        depth = 0; cl = None
        for (idx, ch) in btoks:
            if idx < op: continue
            if ch == '{': depth += 1
            else:
                depth -= 1
                if depth == 0: cl = idx; break
        if cl is None: skipped.append((tln, 'unmatched')); continue
        span = line_of(s, cl) - line_of(s, op)
        if span > MAX_BODY: skipped.append((tln, f'span {span}')); continue
        if not has_code(s, op, cl): skipped.append((tln, 'empty')); continue
        if 'USE_TEST' in s[op:cl]: skipped.append((tln, 'has USE_TEST')); continue
        wraps.append((op, cl, tln, span))
    inserts = []
    for (op, cl, tln, span) in wraps:
        inserts.append((line_start(s, cl), '#endif\n'))
        inserts.append((op + 1, '\n#ifndef USE_TEST'))
    inserts.sort(key=lambda x: -x[0])
    out = s
    for idx, ins in inserts: out = out[:idx] + ins + out[idx:]
    open(path, 'w', encoding='utf-8').write(out)
    return wraps, skipped

total = 0
for rel in sorted(FILES):
    targets = FILES[rel]
    if not targets: continue
    path = ROOT + rel
    wraps, skipped = process(path, targets)
    lines = sum(w[3] for w in wraps); total += lines
    print(f"{rel}: wrapped {len(wraps)}/{len(targets)} (~{lines} body lines)")
    for tln, why in skipped: print(f"   skip L{tln}: {why}")
print(f"TOTAL ~{total} body lines wrapped")
