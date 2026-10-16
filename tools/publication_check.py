"""Heuristic tracked-file hygiene; never a comprehensive secret-scan guarantee."""
from pathlib import Path
import re
import subprocess


def main():
    files=subprocess.check_output(['git','ls-files','-z'],text=True).split('\0');bad=[]
    for name in filter(None,files):
        p=Path(name)
        if any(part in ['.venv','__pycache__','.codex','.agents','AGENTS.md'] for part in p.parts) or name.startswith('results/local/') or p.is_symlink():bad.append(name)
        data=p.read_bytes()
        if len(data)>10*1024*1024:bad.append(name+': oversized')
        try:s=data.decode()
        except UnicodeDecodeError:bad.append(name+': binary');continue
        if name!=__file__.split('/')[-1] and name!='tools/publication_check.py':
            patterns=[r'/Users/[A-Za-z_][A-Za-z0-9_-]+/',r'/home/[A-Za-z_][A-Za-z0-9_-]+/',r'-----BEGIN [A-Z ]*PRIVATE KEY-----',r'gh[pousr]_[A-Za-z0-9]{20,}',r'github_pat_[A-Za-z0-9_]{20,}']
            if any(re.search(x,s) for x in patterns):bad.append(name+': path/secret pattern')
    if bad:raise ValueError(bad)
    print(f'Heuristic hygiene passed for {len(list(filter(None,files)))} tracked files')
if __name__=='__main__':main()
