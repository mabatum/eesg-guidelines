(() => {
  'use strict';

  const STATUS_CLASSES = [
    ['утверж', 'is-approved'],
    ['реценз', 'is-review'],
    ['архив', 'is-archive'],
    ['проект', 'is-draft'],
    ['тест', 'is-test'],
  ];

  function statusClass(value) {
    const normalized = String(value || '').toLocaleLowerCase('ru-RU');
    const found = STATUS_CLASSES.find(([needle]) => normalized.includes(needle));
    return found ? found[1] : 'is-other';
  }

  function parseMetadata(paragraph) {
    const parts = String(paragraph.textContent || '')
      .split('·')
      .map((part) => part.trim())
      .filter(Boolean);

    if (!parts.some((part) => /^(Раздел|Статус|Версия):/i.test(part))) return null;

    const meta = document.createElement('div');
    meta.className = 'eesg-update-meta';
    let status = '';

    for (const part of parts) {
      const match = part.match(/^([^:]+):\s*(.+)$/);
      if (!match) continue;
      const labelText = match[1].trim();
      const valueText = match[2].trim();
      const chip = document.createElement('span');
      chip.className = 'eesg-update-chip';

      if (labelText.toLocaleLowerCase('ru-RU') === 'статус') {
        status = valueText;
        chip.classList.add('eesg-update-chip_status', statusClass(valueText));
      } else if (labelText.toLocaleLowerCase('ru-RU') === 'версия') {
        chip.classList.add('eesg-update-chip_version');
      } else if (labelText.toLocaleLowerCase('ru-RU') === 'раздел') {
        chip.classList.add('eesg-update-chip_section');
      }

      const label = document.createElement('span');
      label.className = 'eesg-update-chip__label';
      label.textContent = labelText;
      const value = document.createElement('span');
      value.className = 'eesg-update-chip__value';
      value.textContent = valueText;
      chip.append(label, value);
      meta.appendChild(chip);
    }

    return { meta, status };
  }

  function enhance() {
    const h1 = [...document.querySelectorAll('h1')].find(
      (node) => (node.textContent || '').trim() === 'Последние обновления',
    );
    if (!h1 || document.documentElement.classList.contains('eesg-updates-enhanced')) return;

    document.documentElement.classList.add('eesg-updates-page', 'eesg-updates-enhanced');
    const root = h1.closest('article, main') || h1.parentElement;
    if (!root) return;

    const headings = [...root.querySelectorAll('h2')];
    const cards = [];

    for (const dateHeading of headings) {
      dateHeading.classList.add('eesg-updates-date');
      let node = dateHeading.nextElementSibling;
      while (node && node.tagName !== 'H2') {
        if (node.tagName !== 'H3') {
          node = node.nextElementSibling;
          continue;
        }

        const card = document.createElement('section');
        card.className = 'eesg-update-card';
        dateHeading.parentNode.insertBefore(card, node);

        const title = node;
        let cursor = node.nextElementSibling;
        card.appendChild(title);
        while (cursor && cursor.tagName !== 'H2' && cursor.tagName !== 'H3') {
          const next = cursor.nextElementSibling;
          card.appendChild(cursor);
          cursor = next;
        }

        const metadataParagraph = [...card.querySelectorAll('p')].find((paragraph) =>
          /(?:Раздел|Статус|Версия):/i.test(paragraph.textContent || ''),
        );
        if (metadataParagraph) {
          const parsed = parseMetadata(metadataParagraph);
          if (parsed) {
            metadataParagraph.replaceWith(parsed.meta);
            card.dataset.status = parsed.status;
          }
        }

        cards.push(card);
        node = cursor;
      }
    }

    const statuses = [...new Set(cards.map((card) => card.dataset.status).filter(Boolean))];
    if (statuses.length > 1 && headings.length) {
      const filters = document.createElement('div');
      filters.className = 'eesg-update-filters';
      filters.setAttribute('aria-label', 'Фильтр по статусу');

      const values = ['Все', ...statuses];
      values.forEach((value, index) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'eesg-update-filter';
        if (index === 0) button.classList.add('is-active');
        button.textContent = value;
        button.addEventListener('click', () => {
          filters.querySelectorAll('button').forEach((item) => item.classList.remove('is-active'));
          button.classList.add('is-active');
          cards.forEach((card) => {
            card.hidden = value !== 'Все' && card.dataset.status !== value;
          });
          headings.forEach((heading) => {
            let cursor = heading.nextElementSibling;
            let hasVisible = false;
            while (cursor && cursor.tagName !== 'H2') {
              if (cursor.classList?.contains('eesg-update-card') && !cursor.hidden) hasVisible = true;
              cursor = cursor.nextElementSibling;
            }
            heading.hidden = !hasVisible;
          });
        });
        filters.appendChild(button);
      });

      headings[0].parentNode.insertBefore(filters, headings[0]);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enhance, { once: true });
  } else {
    enhance();
  }
})();
