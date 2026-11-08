"""Check source integrity, citation links and overlay parity before publishing.

Edition 2026.11.1 merges the Russian Ministry of Health guideline «Саркомы костей»
(2025, ID 532_5) with the September evidence revision: every page cites the
guideline by printed page and cites primary studies by DOI.
"""
from pathlib import Path
import hashlib
import re

VERSION_RE = re.compile(r'\*\*Версия:\*\* \d{4}\.\d{1,2}\.\d+')  # edited in Wiki, so any edition number
SOURCE = Path('content-reviewed/bone-sarcomas')
GENERATED = Path('docs/gen_docs/bone-sarcomas')
PDF = Path('docs/_assets/sources/kr532-5-2025.pdf')
EXPECTED_SHA256 = '9eb35acb923d54a0d27878e925fd21eed6781966ec5b4bdc0a8d6c11710e4f3f'
# Drug marks (the crosses † ‡ were replaced on 08.11.2026): # off-label, ◊ not in the
# guideline, ◊# not in the guideline and not for this indication, § not registered,
# ¶ not in ЖНВЛП. «#» counts only right after a word, never in links or «#».
MARK = re.compile(r'◊#|◊|§|¶|(?<=[^\s#*\[(/«])#(?![\w=/#»-])')
NOTE = re.compile(r'^\*\*(◊#|◊|#|§|¶)\*\*\s*(.+)$', re.M)
# Options outside the guideline carry the procedure the working group requires
PHRASE = 'может быть рассмотрено врачебной комиссией регионального центра и онкологическим консилиумом федерального центра (НМИЦ) высшего уровня'
errors = []
if not PDF.exists() or hashlib.sha256(PDF.read_bytes()).hexdigest() != EXPECTED_SHA256:
    errors.append('Original clinical recommendation PDF is missing or changed.')
for path in SOURCE.rglob('*.md'):
    text = path.read_text()
    generated = GENERATED/path.relative_to(SOURCE)
    if not generated.exists() or generated.read_bytes() != path.read_bytes():
        errors.append(f'Reviewed/generated content differs: {path}')
    if '532_5' not in text or not VERSION_RE.search(text):
        errors.append(f'Source or edition metadata missing: {path}')
    if re.search(r'\{\{[^}]*\}\}|\{[a-z-]+\}', text):
        errors.append(f'Unresolved citation placeholder: {path}')
    for page in re.findall(r'kr532-5-2025\.pdf#page=(\d+)', text):
        if not 1 <= int(page) <= 75:
            errors.append(f'Invalid PDF page {page}: {path}')
    for printed, actual in re.findall(r'с\. (\d+)(?:–\d+)?\]\]?\([^)]*kr532-5-2025\.pdf#page=(\d+)\)', text):
        if int(actual) != int(printed) + 1:
            errors.append(f'Printed/PDF page mismatch: {path}: {printed}/{actual}')
    body = text.split('## Список литературы')[0]
    notes = dict(NOTE.findall(body))
    for mark in sorted(set(MARK.findall(NOTE.sub('', body))) - set(notes)):
        errors.append(f'Mark {mark} used without its footnote: {path}')
    if re.search('[†‡]', body):
        errors.append(f'Old cross mark † or ‡ left in text (now # and ◊): {path}')
    for mark in ('◊', '◊#', '§'):
        if mark in notes and PHRASE not in notes[mark]:
            errors.append(f'Footnote {mark} lacks the medical commission phrase: {path}')
    if '—' in text:
        errors.append(f'Long dash in text (house style uses a hyphen): {path}')
    for doi in re.findall(r'https://doi\.org/(\S+?)\)', text):
        if not re.match(r'10\.\d{4,9}/', doi):
            errors.append(f'Malformed DOI {doi}: {path}')
if len(list(SOURCE.rglob('*.md'))) != 8:
    errors.append('The eight original bone routes must remain present.')
built = Path('docs-html/_assets/sources/kr532-5-2025.pdf')
if not built.exists() or hashlib.sha256(built.read_bytes()).hexdigest() != EXPECTED_SHA256:
    errors.append('Published PDF differs from the clinical source.')
if errors:
    raise SystemExit('\n'.join(errors))
print(f'Clinical source validated: 8 routes, edition line, original PDF, citation offsets, footnote marks and overlay parity.')
