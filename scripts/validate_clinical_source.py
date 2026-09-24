"""Check source integrity, source-page links and overlay parity before publishing."""
from pathlib import Path
import hashlib
import re

SOURCE = Path('content-reviewed/bone-sarcomas')
GENERATED = Path('docs/gen_docs/bone-sarcomas')
PDF = Path('docs/_assets/sources/kr532-5-2025.pdf')
EXPECTED_SHA256 = '9eb35acb923d54a0d27878e925fd21eed6781966ec5b4bdc0a8d6c11710e4f3f'
errors = []
if not PDF.exists() or hashlib.sha256(PDF.read_bytes()).hexdigest() != EXPECTED_SHA256:
    errors.append('Original clinical recommendation PDF is missing or changed.')
for path in SOURCE.rglob('*.md'):
    text = path.read_text()
    generated = GENERATED/path.relative_to(SOURCE)
    if not generated.exists() or generated.read_bytes() != path.read_bytes():
        errors.append(f'Reviewed/generated content differs: {path}')
    if '532_5' not in text or '**Версия:** 2026.09.3' not in text:
        errors.append(f'Source or edition metadata missing: {path}')
    if re.search(r'\{[a-z-]+\}', text):
        errors.append(f'Unresolved citation placeholder: {path}')
    for page in re.findall(r'kr532-5-2025\.pdf#page=(\d+)', text):
        if not 1 <= int(page) <= 75:
            errors.append(f'Invalid PDF page {page}: {path}')
    for printed, actual in re.findall(r'с\. (\d+)(?:–\d+)?\]\([^)]*#page=(\d+)\)',text):
        if int(actual) != int(printed) + 1:
            errors.append(f'Printed/PDF page mismatch: {path}: {printed}/{actual}')
    if re.search(r'https?://(?:doi\.org|www\.eviq\.org\.au)',text):
        errors.append(f'Previous-edition external clinical material remains: {path}')
if len(list(SOURCE.rglob('*.md'))) != 8:
    errors.append('The eight original bone routes must remain present.')
built = Path('docs-html/_assets/sources/kr532-5-2025.pdf')
if not built.exists() or hashlib.sha256(built.read_bytes()).hexdigest() != EXPECTED_SHA256:
    errors.append('Published PDF differs from the clinical source.')
if errors:
    raise SystemExit('\n'.join(errors))
print('Clinical source validated: 8 routes, original PDF, citation offsets and overlay parity.')
