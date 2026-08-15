(() => {
  const clean = (value) => (value || '').replace(/\s+/g, ' ').trim();

  function sectionHeading(title) {
    return Array.from(document.querySelectorAll('h2')).find(
      (heading) => clean(heading.textContent) === title,
    );
  }

  function enhance(title, modifier = '') {
    const heading = sectionHeading(title);
    if (!heading || heading.dataset.eesgEnhanced === 'true') return;

    const nodes = [];
    let cursor = heading.nextElementSibling;
    while (cursor && cursor.tagName !== 'H2') {
      nodes.push(cursor);
      cursor = cursor.nextElementSibling;
    }

    const groups = [];
    let current = null;
    let allUpdates = null;

    for (const node of nodes) {
      const link = node.querySelector?.('a[href*="updates.html"]');
      if (link && clean(link.textContent) === 'Все обновления') {
        allUpdates = node;
        continue;
      }

      if (node.tagName === 'H3') {
        current = [];
        groups.push(current);
      }
      if (current) current.push(node);
    }

    if (!groups.length) return;

    const grid = document.createElement('div');
    grid.className = `eesg-home-grid${modifier ? ` ${modifier}` : ''}`;
    grid.setAttribute('data-e2e', `eesg-home-${title === 'Основные разделы' ? 'sections' : 'recent'}`);

    for (const group of groups) {
      const card = document.createElement('article');
      card.className = 'eesg-home-card';
      for (const node of group) card.appendChild(node);
      grid.appendChild(card);
    }

    heading.insertAdjacentElement('afterend', grid);
    if (allUpdates) {
      allUpdates.classList.add('eesg-home-all-updates');
      grid.insertAdjacentElement('afterend', allUpdates);
    }
    heading.dataset.eesgEnhanced = 'true';
  }

  function init() {
    enhance('Основные разделы');
    enhance('Недавно обновлено', 'eesg-home-grid--recent');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, {once: true});
  } else {
    init();
  }
})();
