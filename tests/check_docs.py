"""Offline CommonMark/GFM link and citation checks; see CONTRIBUTING.md."""
from __future__ import annotations
import argparse
import os
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import unicodedata
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
from mdit_py_plugins.deflist import deflist_plugin

PARSER = MarkdownIt('commonmark', {'html': True}).enable('table').use(deflist_plugin)
DOCNAME = r'(?:DATABASE|STATE-AND-RECOVERY|SYSTEM-VOLUMES|PACKAGE-FORMAT|ORCHARD-POLICY|HOMEBREW-REVIEW|BUILD-INFRA|KEY-RUNBOOK|NOMENCLATURE|REPOSITORIES|SLICE-FORMAT|CONTRIBUTING|AUTHORING|TOOLCHAIN|GENESIS|MANUAL|DESIGN|SETUP|SECURITY|HELPERS|REVIEW)(?:\.md)?'
CITATION = re.compile(r'(?:(?P<doc>'+DOCNAME+r')\s+)?§{1,2}(?P<num>\d+(?:\.\d+)*)')

@dataclass
class Finding:
    file: str
    line: int
    rule: str
    message: str
    severity: str = 'error'

def slug(title):
    """GitHub-style heading IDs, including literal underscores in code spans."""
    return ''.join(c for c in title.lower() if c in '_- ' or unicodedata.category(c)[0] in 'LN').replace(' ', '-')

def inventory(root):
    names = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard'],cwd=root,text=True).splitlines()
    return sorted({root / n for n in names if n.lower().endswith('.md') and not n.startswith(('.agents/', '.codex/')) and (root / n).is_file()})

def historical(path, heading):
    # Named, bounded records; links remain checked even when citations are historical.
    return heading == 'History' or (path.name == 'HOMEBREW-REVIEW.md' and heading.startswith('8. ')) or (path.name == 'REPOSITORIES.md' and heading.startswith('9. '))

class Anchors(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.append(attrs['id'])
        elif tag=='a' and 'name' in attrs:self.ids.append(attrs['name'])

class Document:
    def __init__(self, path, root):
        self.path=path; self.root=root; self.name=path.relative_to(root).as_posix()
        self.text=path.read_text(encoding='utf-8'); self.lines=self.text.splitlines()
        self.env={}
        self.tokens=PARSER.parse(self.text, self.env)
        self.ids={}; self.sections={}; self.headings=[]; self.findings=[]
        self.inline=[]; self.explicit=[]; self.history_lines=set(); self.literal_lines=set()
        used=set(); previous=0; history=False; original=False; pending=[]
        for i,t in enumerate(self.tokens):
            line=(t.map or [0])[0]+1
            if t.type=='heading_open':
                title=''.join(c.content for c in self.tokens[i+1].children or [] if c.type in ('text','code_inline'))
                level=int(t.tag[1]); generated=slug(title); suffix=0; ident=generated
                while ident in used:suffix+=1; ident=f'{generated}-{suffix}'
                used.add(ident)
                if ident in self.ids:self.add(line,'duplicate-anchor',f'Generated ID collides with explicit anchor: {ident}')
                number=re.match(r'^(\d+(?:\.\d+)*)\.?\s',title)
                num=number[1] if number else None
                self.ids[ident]=(num,line)
                for anchor,where in pending:self.ids[anchor]=(num,where)
                pending=[]
                if num:self.sections[num]=(ident,line,title)
                self.headings.append((line,level,title,ident,num))
                if level==2:history=historical(path,title)
                if title=='Full captured source' and '/refs/' in '/'+self.name:original=True
                if previous and level>previous+1:self.add(line,'heading-level','Heading skips a level','warning')
                previous=level
            if history and t.map:self.history_lines.update(range(t.map[0]+1,t.map[1]+1))
            if original:continue
            if t.type in ('html_block','html_inline'):
                parser=Anchors(); parser.feed(t.content)
                for ident in parser.ids:
                    if ident in self.ids:self.add(line,'duplicate-anchor',f'Duplicate anchor: {ident}')
                    self.ids[ident]=(None,line); pending.append((ident,line)); self.explicit.append((ident,line))
            if t.type in ('fence','code_block'):
                self.literal_lines.update(range(t.map[0]+1,t.map[1]+1))
                if t.type=='fence':
                    closing=self.lines[t.map[1]-1].strip()
                    if not re.fullmatch(re.escape(t.markup[0])+r'{'+str(len(t.markup))+r',}\s*',closing):self.add(line,'fence','Unclosed code fence')
                    if not t.info and not history:self.add(line,'fence-language','Code fence needs a language','warning')
            if t.type=='inline':self.inline.append((line,t,history or (i>0 and self.tokens[i-1].type=='heading_open')))
            if t.type=='table_open' and t.map:
                widths=[]
                for source_line in self.lines[t.map[0]:t.map[1]]:
                    cells=re.split(r'(?<!\\)\|',source_line.strip().strip('|'))
                    widths.append(len(cells))
                if len(set(widths))>1:self.add(line,'table-columns','Table rows have inconsistent cell counts; escape literal pipes')
        # Inline HTML IDs are uncommon but must participate in duplicate detection.
        for line,t,_ in self.inline:
            for child in t.children or []:
                if child.type=='html_inline':
                    p=Anchors();p.feed(child.content)
                    for ident in p.ids:
                        if ident in self.ids:self.add(line,'duplicate-anchor',f'Duplicate anchor: {ident}')
                        self.ids[ident]=(None,line)
        for duplicate in self.env.get('duplicate_refs',[]):
            self.add(duplicate['map'][0]+1,'reference-definition','Duplicate reference definition')
        for ident,(num,line) in list(self.ids.items()):
            if num is None and re.fullmatch(r'\s*<a (?:id|name)="[^"]+"></a>\s*',self.lines[line-1]):
                following=next((h for h in self.headings if h[0]>line),None)
                if following and all(not x.strip() for x in self.lines[line:following[0]-1]):
                    self.ids[ident]=(following[4],line)

    def add(self,line,rule,message,severity='error'):
        self.findings.append(Finding(self.name,line,rule,message,severity))

def local_target(doc,url,line=1):
    parsed=urlsplit(url)
    if parsed.scheme or parsed.netloc:return None
    raw=unquote(parsed.path)
    p=Path(os.path.abspath(doc.path.parent/raw)) if raw else doc.path
    try:
        p.resolve().relative_to(doc.root.resolve())
        relative=p.relative_to(doc.root.resolve())
    except ValueError:
        doc.add(line,'path-escape',f'Link escapes repository: {url}');return None
    # Do not let Windows silently accept case-only misspellings.
    parent=doc.root.resolve()
    for part in relative.parts:
        if not parent.is_dir() or part not in {c.name for c in parent.iterdir()}:
            return (p,unquote(parsed.fragment),False)
        parent=parent/part
    return p,unquote(parsed.fragment),True

def check(root, paths=None):
    root=Path(root).resolve(); docs={p.resolve():Document(p.resolve(),root) for p in (paths or inventory(root))}
    for doc in docs.values():
        for line,t,history in doc.inline:
            children=t.children or []; depth=0
            for i,c in enumerate(children):
                if c.type=='link_open':
                    depth+=1
                    end=next((j for j in range(i+1,len(children)) if children[j].type=='link_close'),len(children))
                    label=''.join(x.content for x in children[i+1:end] if x.type in ('text','code_inline'))
                    url=c.attrGet('href') or ''
                elif c.type=='image':label=c.content;url=c.attrGet('src') or ''
                elif c.type=='link_close':depth-=1;continue
                else:
                    if c.type=='text' and depth==0 and not history:
                        for m in CITATION.finditer(c.content):
                            if m['doc']:doc.add(line,'unlinked-citation',f'Link cross-document citation: {m[0]}')
                            elif doc.path.parent.name!='refs' and m['num'] not in doc.sections:doc.add(line,'citation-owner',f'No local section {m[0]}; name and link its owner')
                        if re.search(r'\]\(|\[[^\]]+\]\[[^\]]*\]',c.content):doc.add(line,'link-syntax','Malformed or unresolved Markdown link')
                    continue
                target=local_target(doc,url,line)
                if target is None:continue
                path,fragment,exists=target
                if not exists:doc.add(line,'local-file',f'Missing or wrong-case local target: {url}');continue
                if path.suffix.lower()!='.md':continue
                dest=docs.get(path)
                if dest is None:dest=Document(path,root)
                if fragment and fragment not in dest.ids:doc.add(line,'fragment',f'Unknown fragment: {url}');continue
                if history:continue
                refs=list(CITATION.finditer(label))
                if refs:
                    if len(refs)>1 or re.search(r'§\d[\d.]*\s*[–—-]\s*§?\d',label):doc.add(line,'citation-range','Link each section separately')
                    m=refs[0]; num=dest.ids.get(fragment,(None,0))[0]
                    if m['num']!=num:doc.add(line,'citation-number',f'Label {m[0]} disagrees with destination section {num}: {url}')
                    owner=(m['doc'] or '').removesuffix('.md')
                    if owner=='REVIEW':owner='HOMEBREW-REVIEW'
                    if path!=doc.path and not owner:doc.add(line,'citation-label','Cross-document label must name the document')
                    if owner and owner!=path.stem:doc.add(line,'citation-document',f'Label names {owner}, target is {path.stem}')
    return [f for d in docs.values() for f in d.findings],docs

def main():
    import json
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--json',action='store_true');args=ap.parse_args()
    findings,docs=check(args.root)
    if args.json:print(json.dumps({'documents':len(docs),'findings':[asdict(f) for f in findings]},ensure_ascii=False,indent=2))
    else:
        for f in findings:print(f'{f.file}:{f.line}: {f.severity} {f.rule}: {f.message}')
        print(f'Checked {len(docs)} Markdown documents: {sum(f.severity=="error" for f in findings)} errors, {sum(f.severity=="warning" for f in findings)} warnings. Offline only.')
    return int(any(f.severity=='error' for f in findings))

if __name__=='__main__':raise SystemExit(main())
