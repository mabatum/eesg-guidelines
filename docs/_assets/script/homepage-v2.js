(() => {
  'use strict';

  function detectSiteRoot() {
    const ownScript = [...document.scripts].find((script) =>
      /\/_assets\/script\/homepage-v2\.js(?:[?#]|$)/.test(script.src || ''),
    );
    if (ownScript?.src) return new URL('../../', ownScript.src);
    return new URL('./', window.location.href);
  }

  function isHomepage() {
    const root = detectSiteRoot();
    const rootPath = root.pathname.endsWith('/') ? root.pathname : `${root.pathname}/`;
    let path = window.location.pathname;
    if (path.startsWith(rootPath)) path = path.slice(rootPath.length);
    path = path.replace(/^\/+|\/+$/g, '');
    return path === '' || path === 'index.html';
  }

  function enhance() {
    const home = isHomepage();
    document.documentElement.classList.toggle('eesg-homepage', home);
    if (!home) return;

    const content = document.querySelector('.dc-doc-page__content');
    if (!content || content.dataset.eesgHomeEnhanced) return;
    const headings = [...content.querySelectorAll('h2')];
    if (!headings.length) return;

    const search = document.createElement('button');
    search.type = 'button';
    search.className = 'eesg-home-search';
    search.setAttribute('aria-label', 'Поиск по рекомендациям');
    search.setAttribute('aria-haspopup', 'dialog');
    search.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" stroke="currentColor" stroke-width="1.5"/><path d="m15.5 15.5 4.5 4.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg><span>Найти рекомендацию</span><kbd>Ctrl / ⌘ K</kbd>';
    search.addEventListener('click', () => document.dispatchEvent(new Event('eesg:open-search')));
    headings[0].before(search);

    const grid = document.createElement('div');
    grid.className = 'eesg-home-collections';
    search.after(grid);

    for (const heading of headings) {
      const sectionLink = [...heading.querySelectorAll('a[href]')].find(a =>
        !a.classList.contains('yfm-anchor') && a.getAttribute('aria-hidden') !== 'true'
        && !a.getAttribute('href').startsWith('#'),
      );
      const nodes = [];
      let next = heading.nextElementSibling;
      while (next && next.tagName !== 'H2') {
        nodes.push(next);
        next = next.nextElementSibling;
      }

      if (sectionLink) {
        const card = document.createElement('section');
        card.className = 'eesg-home-collection';
        grid.appendChild(card);
        card.appendChild(heading);
        const intro = nodes.find(node => node.tagName === 'P');
        if (intro) card.appendChild(intro);
        const list = nodes.find(node => node.tagName === 'UL');
        if (list) {
          const details = document.createElement('details');
          details.className = 'eesg-home-page-list';
          const summary = document.createElement('summary');
          summary.textContent = `Страницы раздела · ${list.children.length}`;
          details.append(summary, list);
          card.appendChild(details);
        }
        for (const node of nodes) {
          if (node !== intro && node !== list) card.appendChild(node);
        }
      } else {
        const details = document.createElement('details');
        details.className = 'eesg-home-guide';
        const summary = document.createElement('summary');
        heading.before(details);
        summary.appendChild(heading);
        details.appendChild(summary);
        details.append(...nodes);
      }
    }
    // A single published collection should expose its clinical destinations immediately.
    if (grid.children.length === 1) {
      const pages = grid.querySelector('details');
      if (pages) pages.open = true;
    }
    content.dataset.eesgHomeEnhanced = 'true';
  }

  let scheduled = false;
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      enhance();
    });
  }

  document.documentElement.classList.toggle('eesg-homepage', isHomepage());
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enhance, {once: true});
  } else {
    enhance();
  }
  new MutationObserver(schedule).observe(document.documentElement, {childList: true, subtree: true});
  window.addEventListener('popstate', schedule);
})();
