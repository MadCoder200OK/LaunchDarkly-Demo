"""Refresh exact README links from purpose-marked feature blocks; --check is read-only."""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
START = re.compile(r'^\s*(?:#|//) DEMO START ([\w-]+): (.+)$')
END = re.compile(r'^\s*(?:#|//) DEMO END ([\w-]+)\s*$')


@dataclass(frozen=True)
class Block:
    path: str
    start: int
    end: int
    purpose: str

    def link(self):
        return f'[{self.path} · lines {self.start}–{self.end}]({self.path}#L{self.start}-L{self.end})'

    def readme_link(self):
        return f'[{Path(self.path).name} · lines {self.start}–{self.end}]({self.path}#L{self.start}-L{self.end})'


def code_blocks(root):
    blocks = {}
    paths = [root / 'dev.py', *sorted((root / 'backend/app').glob('*.py')),
             *sorted((root / 'frontend/src').rglob('*.js')),
             *sorted((root / 'frontend/src').rglob('*.jsx'))]
    for path in paths:
        stack = []
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if match := START.match(line):
                key, purpose = match.groups()
                if key in blocks or any(item[0] == key for item in stack):
                    raise ValueError(f'Duplicate code marker: {key}')
                stack.append((key, number, purpose))
            elif match := END.match(line):
                key = match[1]
                if not stack or stack[-1][0] != key:
                    raise ValueError(f'Unbalanced code marker: {path}:{number}')
                _, start, purpose = stack.pop()
                blocks[key] = Block(path.relative_to(root).as_posix(), start, number, purpose)
        if stack:
            raise ValueError(f'Unclosed code marker: {path}')
    return blocks


def refresh(source, blocks):
    # Generation metadata belongs in tooling, not in the reader's setup guide.
    source = re.sub(r'\n\n\*\*Implementation:\*\* [^\n]*', '', source)
    sections = json.loads((ROOT / 'scripts/readme_sections.json').read_text())
    for section in sections:
        anchor = section['after']
        if source.count(anchor) != 1:
            raise ValueError(f'Update the README reference anchor for {section["features"]}')
        links = ' · '.join(blocks[key].readme_link() for key in section['features'])
        source = source.replace(anchor, f'{anchor}\n\n**Implementation:** {links}', 1)
    return source


def implementation_map(blocks):
    lines = ['# Implementation map', '',
             'Complete feature blocks, including their purpose and exact source boundaries. '
             'Links include the START and END comments. Paths are relative to the project root.', '',
             '| Feature / purpose | Implementation |', '| --- | --- |']
    for block in blocks.values():
        link = block.link().replace(f']({block.path}#', f'](../{block.path}#')
        lines.append(f'| {block.purpose} | {link} |')
    return '\n'.join(lines) + '\n'


def validate_links(source, root):
    # Markdown links/images only: localhost commands and example .env values are not links.
    for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', source):
        target = target.strip('<>')
        parsed = urlparse(target)
        if parsed.scheme or parsed.netloc:
            if parsed.scheme != 'https' or parsed.hostname != 'launchdarkly.com' or not parsed.path.startswith('/docs/'):
                raise ValueError(f'Only LaunchDarkly docs may be external README links: {target}')
        elif parsed.path and not (root / parsed.path).is_file():
            raise ValueError(f'Missing README target: {target}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'README.md'
    source = path.read_text()
    blocks = code_blocks(ROOT)
    updated = refresh(source, blocks)
    map_path = ROOT / 'docs/code-map.md'
    updated_map = implementation_map(blocks)
    if not args.check:
        map_path.write_text(updated_map)
    validate_links(updated, ROOT)
    validate_links(updated_map, ROOT / 'docs')
    if args.check and (source != updated or not map_path.exists() or map_path.read_text() != updated_map):
        raise SystemExit('README line references are stale. Run python3 scripts/update_readme.py')
    if not args.check:
        path.write_text(updated)
    print('README code ranges, local assets, and external links verified.')


if __name__ == '__main__':
    main()
