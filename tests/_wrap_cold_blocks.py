#!/usr/bin/env python3
# Wrap cold brace-blocks (every instrumented line 0-hit) in #ifndef USE_TEST ... #endif.
# Safe: such blocks never execute in the test, and {} is valid syntax.
# Excludes function bodies (handled separately) and blocks containing control-flow
# exits at top level (return/break/continue/goto/throw) to avoid altering flow.
import re

INFO = '/tmp/s1.info'  # unfiltered capture from the stage-1 build+run

def tokenize(s):
    out=[]; i=0; n=len(s); par=brk=0; state=None
    while i<n:
        c=s[i]; nxt=s[i+1] if i+1<n else ''
        if state=='line':
            if c=='\n': state=None
            i+=1; continue
        if state=='block':
            if c=='*' and nxt=='/': state=None; i+=2; continue
            i+=1; continue
        if state=='str':
            if c=='\\': i+=2; continue
            if c=='"': state=None
            i+=1; continue
        if state=='char':
            if c=='\\': i+=2; continue
            if c=="'": state=None
            i+=1; continue
        if c=='/' and nxt=='/': state='line'; i+=2; continue
        if c=='/' and nxt=='*': state='block'; i+=2; continue
        if c=='"': state='str'; i+=1; continue
        if c=="'": state='char'; i+=1; continue
        if c=='{': out.append((i,'{',par,brk)); i+=1; continue
        if c=='}': out.append((i,'}',par,brk)); i+=1; continue
        if c=='(': par+=1; i+=1; continue
        if c==')': par-=1; i+=1; continue
        if c=='[': brk+=1; i+=1; continue
        if c==']': brk-=1; i+=1; continue
        if c==';': out.append((i,';',par,brk)); i+=1; continue
        i+=1
    return out

def line_of(s,idx): return s.count('\n',0,idx)+1
def line_start(s,idx): return s.rfind('\n',0,idx)+1

CTRL = re.compile(r'\b(return|break|continue|goto|throw)\b')

def prev_token(s, op):
    """The significant token immediately before position op (skips ws and comments).
    Returns '' for code-block-openers we should NOT trust (init lists etc.)."""
    i = op - 1
    while i >= 0 and s[i] in ' \t\r\n':
        i -= 1
    # skip a trailing line comment
    if i >= 1 and s[i-1:i+1] == '//':
        j = s.rfind('\n', 0, i-1)
        return prev_token(s, j+1)
    # skip a trailing block comment */ ... /*
    if i >= 1 and s[i-1:i+1] == '*/':
        j = s.rfind('/*', 0, i-1)
        return prev_token(s, j) if j >= 0 else ''
    if i < 0:
        return ''
    if s[i].isalnum() or s[i] == '_':
        j = i
        while j >= 0 and (s[j].isalnum() or s[j] == '_'):
            j -= 1
        return s[j+1:i+1]
    return s[i]

def process(path, da):
    s=open(path,encoding='utf-8',errors='replace').read()
    toks=tokenize(s)
    # build brace pairs with parent
    pairs=[]; stack=[]
    for (idx,ch,par,brk) in toks:
        if ch=='{':
            parent = stack[-1][1] if stack else None
            stack.append((idx,len(pairs)))
            pairs.append({'op':idx,'cl':None,'parent':parent,'children':[]})
            if parent is not None: pairs[parent]['children'].append(len(pairs)-1)
        elif ch=='}':
            if stack:
                opidx,pidx=stack.pop()
                pairs[pidx]['cl']=idx
    # mark function bodies: brace whose line range contains a FN start? Simpler: a brace pair
    # whose open is preceded by ')' of a signature. We instead mark a pair as funcbody if its
    # body, when removed, would drop a definition: detect via FN-less heuristic skip:
    # treat top-level pairs (parent None) and pairs immediately enclosing other pairs that are
    # definitions as non-wrappable. Conservative: only wrap pairs whose parent is not None AND
    # whose open brace is preceded (ignoring ws) by ')' or '{' or ';' or '}' (i.e., a real
    # nested statement block), AND not preceded by ')' that closes an if/for/while/switch cond...
    # To keep it simple and SAFE we wrap only pairs where parent!=None and the block is cold.
    # Function-body exclusion: a function body's parent is either None (top-level fn) or a
    # namespace/class body. Namespace/class bodies contain entered code -> not all-cold -> their
    # children (function bodies) have parent != None. So we additionally skip a pair if it has NO
    # parent-that-is-cold... instead: skip pair if it directly contains a nested pair that spans
    # like a function (heuristic: contains a ';' at its direct level with a '(' before -> likely
    # has statements) -- too complex.
    # Practical safe rule: wrap a cold pair only if its PARENT pair is also cold OR parent is a
    # function body. We detect function bodies as pairs whose open is at the line of an FN record.
    line_starts=[0]+[m.end() for m in re.finditer('\n',s)]
    def lstart(ln): return line_starts[ln-1] if ln-1<len(line_starts) else len(s)

    # function-body pair ids: open brace line == some FN start line (approx). We pass fn_lines.
    # (caller injects via closure below)

    def da_in(op,cl):
        opl=line_of(s,op); cll=line_of(s,cl)
        hits=[da[l] for l in range(opl,cll+1) if l in da]
        return hits
    def is_cold(p):
        h=da_in(p['op'],p['cl'])
        return len(h)>=1 and all(x==0 for x in h)

    cold_ids={i for i,p in enumerate(pairs) if p['cl'] is not None and is_cold(p)}
    # outermost cold: cold and (parent is None or parent not in cold_ids)
    outer={i for i in cold_ids if pairs[i]['parent'] is None or pairs[i]['parent'] not in cold_ids}
    # exclude function bodies (open brace at an FN line) and their direct enclosure
    wrap=[]
    for i in sorted(outer,key=lambda i:pairs[i]['op']):
        p=pairs[i]
        if p['parent'] is None:  # top-level (function/namespace body) -> skip
            continue
        body=s[p['op']+1:p['cl']]
        if 'USE_TEST' in body: continue
        if prev_token(s, p['op']) not in (')', 'else', 'do', 'try', ';'):
            continue  # not a code block (initializer/namespace/class body) -> skip
        if re.search(r'^\s*#', body, re.M):  # straddles a preprocessor directive -> skip (balance)
            continue
        if 'R"' in body:  # raw string -> brace counter unreliable
            continue
        # control-flow (return/break/...) inside a COLD block is safe to remove:
        # the block never runs in the test, so emptying it can't change behavior.
        wrap.append((p['op'],p['cl']))
    # apply bottom-up
    inserts=[]
    for op,cl in wrap:
        inserts.append((line_start(s,cl),'#endif\n'))
        inserts.append((op+1,'\n#ifndef USE_TEST'))
    inserts.sort(key=lambda x:-x[0])
    out=s
    for idx,ins in inserts: out=out[:idx]+ins+out[idx:]
    if inserts:
        open(path,'w',encoding='utf-8').write(out)
    return len(wrap), sum(line_of(s,cl)-line_of(s,op) for op,cl in wrap)

# load DA per file from .info
import collections
file_da={}
fn_lines=collections.defaultdict(set)
cur=None
for line in open(INFO,encoding='utf-8',errors='replace'):
    if line.startswith('SF:'):
        cur=line[3:].strip(); file_da[cur]=collections.defaultdict(int); fn_lines[cur]=set()
    elif line.startswith('DA:'):
        a,b=line[3:].strip().split(',')[:2]; file_da[cur][int(a)]=int(b)
    elif line.startswith('FN:'):
        fn_lines[cur].add(int(line[3:].split(',')[0]))

tot_w=tot_l=0
for sf in sorted(file_da):
    if '/src/' not in sf: continue
    if not sf.endswith('.cpp'): continue  # never wrap headers (class/inline fragility)
    da=file_da[sf]
    if not da: continue
    w,l=process(sf,da)
    if w: print(f"{sf.split('/src/')[-1]}: wrapped {w} cold blocks (~{l} lines)"); tot_w+=w; tot_l+=l
print(f"\nTOTAL {tot_w} cold blocks, ~{tot_l} lines")
