#!/usr/bin/env python3
"""
scripts/m3u_to_json.py
Parse playlist.m3u in the repo root and write playlist.json with full metadata.
Usage: python3 scripts/m3u_to_json.py
"""
import re
import json
from pathlib import Path

M3U = Path('playlist.m3u')
OUT = Path('playlist.json')

attr_re = re.compile(r'(\w[\w-]*)="([^"]*)"')

def parse_extinf(line):
    # input: the #EXTINF line (without leading #EXTINF:...)
    # Example: -1 tvg-id="SCTV.id" tvg-logo="..." group-title="Indonesia Channels",SCTV
    result = {
        'tvg_id': None,
        'tvg_name': None,
        'tvg_logo': None,
        'group_title': None,
        'duration': None,
        'title': None,
        'raw': line.strip()
    }
    # split at first comma for title
    if ',' in line:
        before, title = line.split(',', 1)
        result['title'] = title.strip()
    else:
        before = line
    # duration is first token of before (e.g. -1)
    parts = before.strip().split()
    if parts:
        result['duration'] = parts[0]
    # find attributes
    for k, v in attr_re.findall(before):
        key = k.strip()
        if key.lower() == 'tvg-id':
            result['tvg_id'] = v
        elif key.lower() == 'tvg-name':
            result['tvg_name'] = v
        elif key.lower() == 'tvg-logo':
            result['tvg_logo'] = v
        elif key.lower() == 'group-title':
            result['group_title'] = v
        else:
            # keep others under raw_attrs
            result.setdefault('raw_attrs', {})[key] = v
    return result


def main():
    if not M3U.exists():
        print('playlist.m3u not found in repo root')
        return

    lines = [l.rstrip('\n') for l in M3U.read_text(encoding='utf-8', errors='replace').splitlines()]

    metadata = {}
    channels = []

    pending_vlcopt = []
    pending_kodiprop = []
    pending_exthttp = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith('#EXTM3U'):
            # collect header attributes if any
            if ' ' in line:
                parts = line.split(None, 1)
                # find url-tvg or other attrs
                for k, v in attr_re.findall(line):
                    metadata[k] = v
            i += 1
            continue
        if line.startswith('#EXTVLCOPT:'):
            pending_vlcopt.append(line[len('#EXTVLCOPT:'):])
            i += 1
            continue
        if line.startswith('#KODIPROP:'):
            pending_kodiprop.append(line[len('#KODIPROP:'):])
            i += 1
            continue
        if line.startswith('#EXTHTTP:'):
            # JSON text after colon
            try:
                json_text = line[len('#EXTHTTP:'):]
                pending_exthttp = json.loads(json_text)
            except Exception:
                pending_exthttp = {'raw': line[len('#EXTHTTP:'):]} 
            i += 1
            continue
        if line.startswith('#EXTINF:'):
            extinf = line[len('#EXTINF:'):]
            parsed = parse_extinf(extinf)
            # attach pending options
            if pending_vlcopt:
                parsed['extvlcopt'] = pending_vlcopt
            if pending_kodiprop:
                parsed['kodiprop'] = pending_kodiprop
            if pending_exthttp is not None:
                parsed['exthttp'] = pending_exthttp
            # now get next non-empty non-comment line as url
            url = None
            j = i + 1
            while j < len(lines):
                candidate = lines[j].strip()
                if candidate == '':
                    j += 1
                    continue
                if candidate.startswith('#'):
                    # if another comment appears before URL, break and set url to None
                    # but usually URL is next line; we'll skip comments
                    j += 1
                    continue
                url = candidate
                break
            parsed['url'] = url
            channels.append(parsed)
            # clear pendings
            pending_vlcopt = []
            pending_kodiprop = []
            pending_exthttp = None
            i = j + 1 if url is not None else i + 1
            continue
        # other comments are ignored
        i += 1

    out = {
        'source': 'playlist.m3u',
        'metadata': metadata,
        'channels_count': len(channels),
        'channels': channels
    }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {OUT} with {len(channels)} channels')

if __name__ == '__main__':
    main()
