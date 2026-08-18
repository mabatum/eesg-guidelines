(() => {
  'use strict';

  const BONE_PATHS = new Set(['bone-sarcomas/', 'bone-sarcomas/index.html']);
  const DESCRIPTIONS = new Map([
    ['Общие принципы ведения первичных опухолей кости', 'Диагностика, стадирование, биопсия и общая лечебная тактика.'],
    ['Остеосаркома', 'Диагностика и лечение локализованного и распространённого заболевания.'],
    ['Хондросаркома', 'Хирургическая тактика и системное лечение отдельных подтипов.'],
    ['Саркома Юинга', 'Мультимодальное лечение и системная терапия.'],
    ['Гигантоклеточная опухоль кости', 'Диагностика, оценка риска и показания к локальному и системному лечению.'],
    ['Хордома', 'Локальное лечение и системная терапия распространённого заболевания.'],
    ['Редкие опухоли кости', 'Практические положения для редких первичных опухолей кости.'],
  ]);

  const clean = (value) => String(value || '').replace(/\s+/g, ' ').trim();

  function detectSiteRoot() {
    const ownScript = [...document.scripts].find((script) =>
      /\/_assets\/script\/section-landing-v1\.js(?:[?#]|$)/.test(script.src || ''),
    );
    if (ownScript?.src) return new URL('../../', ownScript.src);
    return new URL('./', window.location.href);
  }

  const SITE_ROOT = detectSiteRoot();

  function currentPath() {
    const rootPath = SITE_ROOT.pathname.endsWith('/') ? SITE_ROOT.pathname : `${SITE_ROOT.pathname}/`;
    let path = window.location.pathname;
    if (path.startsWith(rootPath)) path = path.slice(rootPath.length);
    return path || 'index.html';
  }

  function findHeading(title) {
    return [...document.querySelectorAll('h2')].find((node) => clean(node.textContent) === title) || null;
  }

  function removeSection(title) {
    const heading = findHeading(title);
    if (!heading) return;
    let node = heading;
    while (node) {
      const next = node.nextElementSibling;
      node.remove();
      node = next;
      if (node?.tagName === 'H2') break;
    }
  }

  function shortenIntro(content) {
    const h1 = content.querySelector('h1');
    if (!h1) return;
    let node = h1.nextElementSibling;
    while (node && node.tagName !== 'H2') {
      const text = clean(node.textContent);
      if (node.tagName === 'P' && text.startsWith('Раздел охватывает первичные злокачественные опухоли кости')) {
        node.textContent = 'Раздел посвящён диагностике и лечению первичных опухолей кости у взрослых.';
        return;
      }
      node = node.nextElementSibling;
    }
  }

  function makeKeyPrinciple(content) {
    const paragraphs = [...content.querySelectorAll('p')];
    const principle = paragraphs.find((node) =>
      clean(node.textContent).startsWith('Больной с подозрением на первичную опухоль кости направляется'),
    );
    if (!principle || principle.closest('.eesg-key-principle')) return;

    const callout = document.createElement('aside');
    callout.className = 'eesg-key-principle';
    callout.setAttribute('aria-label', 'Ключевой клинический принцип');

    const label = document.createElement('div');
    label.className = 'eesg-key-principle__label';
    label.textContent = 'Ключевой клинический принцип';

    principle.parentNode?.insertBefore(callout, principle);
    callout.appendChild(label);
    callout.appendChild(principle);

    const evidence = callout.nextElementSibling;
    if (evidence?.tagName === 'BLOCKQUOTE') {
      evidence.classList.add('eesg-key-principle__evidence');
      callout.appendChild(evidence);
    }
  }

  function buildCards() {
    const heading = findHeading('Страницы раздела');
    if (!heading || heading.dataset.eesgLandingEnhanced === 'true') return false;

    let table = heading.nextElementSibling;
    while (table && table.tagName !== 'H2' && table.tagName !== 'TABLE') table = table.nextElementSibling;
    if (!table || table.tagName !== 'TABLE') return false;

    const links = [...table.querySelectorAll('tbody tr a')];
    if (!links.length) return false;

    const grid = document.createElement('div');
    grid.className = 'eesg-section-card-grid';

    for (const sourceLink of links) {
      const title = clean(sourceLink.textContent);
      const card = document.createElement('a');
      card.className = 'eesg-section-card';
      card.href = sourceLink.href;

      const cardTitle = document.createElement('span');
      cardTitle.className = 'eesg-section-card__title';
      cardTitle.textContent = title;

      const description = document.createElement('span');
      description.className = 'eesg-section-card__description';
      description.textContent = DESCRIPTIONS.get(title) || 'Открыть клинический раздел.';

      const arrow = document.createElement('span');
      arrow.className = 'eesg-section-card__arrow';
      arrow.setAttribute('aria-hidden', 'true');
      arrow.textContent = '→';

      card.append(cardTitle, description, arrow);
      grid.appendChild(card);
    }

    table.replaceWith(grid);
    heading.dataset.eesgLandingEnhanced = 'true';

    let node = grid.nextElementSibling;
    while (node && node.tagName !== 'H2') {
      const next = node.nextElementSibling;
      node.remove();
      node = next;
    }
    return true;
  }

  function enhanceBoneLanding() {
    if (!BONE_PATHS.has(currentPath())) return true;
    const h1 = document.querySelector('.dc-doc-page__content h1, main h1, article h1, h1');
    if (!h1) return false;
    const content = h1.closest('.dc-doc-page__content') || h1.parentElement;
    if (!content) return false;

    document.body.classList.add('eesg-section-landing-page');
    content.classList.add('eesg-section-landing');
    shortenIntro(content);
    makeKeyPrinciple(content);
    buildCards();
    removeSection('Общие положения раздела');
    removeSection('Список литературы');
    return true;
  }

  function run() {
    if (document.documentElement.dataset.eesgSectionLandingReady === '1') return;
    if (enhanceBoneLanding()) document.documentElement.dataset.eesgSectionLandingReady = '1';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run, {once: true});
  } else {
    run();
  }

  const observer = new MutationObserver(() => {
    if (document.documentElement.dataset.eesgSectionLandingReady === '1') {
      observer.disconnect();
      return;
    }
    run();
  });
  observer.observe(document.documentElement, {childList: true, subtree: true});
})();
