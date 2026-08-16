(() => {
  'use strict';

  const clean = (value) => (value || '').replace(/\s+/g, ' ').trim();

  function sectionHeading(title) {
    return Array.from(document.querySelectorAll('h2')).find(
      (heading) => clean(heading.textContent) === title,
    );
  }

  function findLead() {
    const h1 = document.querySelector('h1');
    if (!h1) return;

    let cursor = h1.nextElementSibling;
    let seenMeta = false;
    while (cursor && cursor.tagName !== 'H2') {
      const text = clean(cursor.textContent);
      if (cursor.classList?.contains('eesg-page-meta') || text.startsWith('Статус:')) {
        seenMeta = true;
      } else if (seenMeta && cursor.tagName === 'P' && text.startsWith('Клинические рекомендации,')) {
        cursor.classList.add('eesg-home-lead');
        const quickLinks = cursor.nextElementSibling;
        if (quickLinks?.tagName === 'P' && quickLinks.querySelectorAll('a').length >= 4) {
          quickLinks.classList.add('eesg-home-quick-links');
        }
        return;
      }
      cursor = cursor.nextElementSibling;
    }
  }

  function ensureRecommendationsAnchor() {
    const heading = sectionHeading('Рекомендации');
    if (!heading) return;
    heading.id = 'rekomendatsii';

    if (window.location.hash === '#rekomendatsii') {
      requestAnimationFrame(() => heading.scrollIntoView({block: 'start'}));
    }
  }

  function enhanceCards(title, modifier = '', allUpdatesLabel = '') {
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
      const link = node.querySelector?.('a');
      if (allUpdatesLabel && link && clean(link.textContent) === allUpdatesLabel) {
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
    grid.dataset.e2e = `eesg-home-${title === 'Рекомендации' ? 'recommendations' : title === 'Разделы портала' ? 'portal' : 'recent'}`;

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
    findLead();
    ensureRecommendationsAnchor();
    enhanceCards('Рекомендации', 'eesg-home-grid--recommendations');
    enhanceCards('Разделы портала', 'eesg-home-grid--portal');
    enhanceCards('Недавно обновлено', 'eesg-home-grid--recent', 'Все обновления рекомендаций');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, {once: true});
  } else {
    init();
  }
})();
