(() => {
  'use strict';

  const LABELS = new Map([
    ['статус', 'status'],
    ['версия', 'version'],
    ['обновлено', 'updated'],
    ['следующий пересмотр', 'review'],
    ['рабочая группа', 'group'],
  ]);

  function findMetadataParagraph() {
    const h1 = document.querySelector('main h1, article h1, h1');
    if (!h1) return null;

    let node = h1.nextElementSibling;
    for (let i = 0; node && i < 4; i += 1, node = node.nextElementSibling) {
      if (node.tagName === 'P' && /Статус:/i.test(node.textContent || '')) return node;
    }
    return null;
  }

  function parseParts(text) {
    return String(text || '')
      .split('·')
      .map((part) => part.trim())
      .map((part) => {
        const match = part.match(/^([^:]+):\s*(.+)$/);
        if (!match) return null;
        const label = match[1].trim();
        const value = match[2].trim();
        const kind = LABELS.get(label.toLocaleLowerCase('ru-RU'));
        return kind && value ? { label, value, kind } : null;
      })
      .filter(Boolean);
  }

  function statusClass(value) {
    const normalized = value.toLocaleLowerCase('ru-RU');
    if (normalized.includes('утверж')) return 'is-approved';
    if (normalized.includes('реценз')) return 'is-review';
    if (normalized.includes('архив')) return 'is-archive';
    if (normalized.includes('проект')) return 'is-draft';
    if (normalized.includes('тест')) return 'is-test';
    return 'is-other';
  }

  function enhanceMetadata() {
    if (document.querySelector('.eesg-page-meta')) return true;
    const paragraph = findMetadataParagraph();
    if (!paragraph) return false;

    const parts = parseParts(paragraph.textContent);
    if (!parts.length) return false;

    const container = document.createElement('div');
    container.className = 'eesg-page-meta';
    container.setAttribute('aria-label', 'Служебная информация о странице');

    for (const part of parts) {
      const item = document.createElement('span');
      item.className = `eesg-page-meta__item eesg-page-meta__item_${part.kind}`;
      if (part.kind === 'status') item.classList.add(statusClass(part.value));

      const label = document.createElement('span');
      label.className = 'eesg-page-meta__label';
      label.textContent = part.label;

      const value = document.createElement('span');
      value.className = 'eesg-page-meta__value';
      value.textContent = part.value;

      item.append(label, value);
      container.appendChild(item);
    }

    paragraph.replaceWith(container);
    return true;
  }

  function markChangelog() {
    document.querySelectorAll('h2, h3').forEach((heading) => {
      if ((heading.textContent || '').trim().toLocaleLowerCase('ru-RU') === 'что изменилось') {
        heading.classList.add('eesg-changelog-heading');
      }
    });
  }

  function run() {
    enhanceMetadata();
    markChangelog();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run, { once: true });
  } else {
    run();
  }

  const observer = new MutationObserver(() => run());
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
