(() => {
  'use strict';

  const INDEX = Array.isArray(window.EESG_SEARCH_INDEX) ? window.EESG_SEARCH_INDEX : [];
  const TRIGGER_ID = 'eesg-title-search-trigger';
  const DIALOG_ID = 'eesg-title-search-dialog';
  let activeIndex = -1;
  let previousFocus = null;

  const normalize = (value) =>
    String(value || '')
      .toLocaleLowerCase('ru-RU')
      .replaceAll('ё', 'е')
      .replace(/[^a-zа-я0-9+.-]+/gi, ' ')
      .replace(/\s+/g, ' ')
      .trim();

  const prepared = INDEX.map((item) => ({
    ...item,
    titleNorm: normalize(item.title),
    contextNorm: normalize((item.breadcrumbs || []).join(' ')),
  }));

  function score(item, query) {
    const terms = query.split(' ').filter(Boolean);
    if (!terms.length) return 0;

    const inTitle = terms.every((term) => item.titleNorm.includes(term));
    const inAll = terms.every(
      (term) => item.titleNorm.includes(term) || item.contextNorm.includes(term),
    );
    if (!inAll) return 0;

    let value = 100;
    if (item.titleNorm === query) value += 1000;
    else if (item.titleNorm.startsWith(query)) value += 700;
    else if (item.titleNorm.includes(query)) value += 500;
    else if (inTitle) value += 350;

    for (const term of terms) {
      if (item.titleNorm.startsWith(term)) value += 80;
      else if (item.titleNorm.includes(term)) value += 50;
      else if (item.contextNorm.includes(term)) value += 15;
    }
    return value;
  }

  function search(query) {
    const q = normalize(query);
    if (!q) return [];
    return prepared
      .map((item) => ({ item, score: score(item, q) }))
      .filter((entry) => entry.score > 0)
      .sort((a, b) => b.score - a.score || a.item.title.length - b.item.title.length)
      .slice(0, 12)
      .map((entry) => entry.item);
  }

  function icon() {
    return `
      <svg aria-hidden="true" viewBox="0 0 24 24" width="20" height="20" fill="none">
        <circle cx="11" cy="11" r="6.5" stroke="currentColor" stroke-width="2" />
        <path d="m16 16 4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
      </svg>`;
  }

  function ensureDialog() {
    let root = document.getElementById(DIALOG_ID);
    if (root) return root;

    root = document.createElement('div');
    root.id = DIALOG_ID;
    root.className = 'eesg-search-dialog';
    root.hidden = true;
    root.innerHTML = `
      <div class="eesg-search-backdrop" data-search-close></div>
      <section class="eesg-search-panel" role="dialog" aria-modal="true" aria-labelledby="eesg-search-title">
        <div class="eesg-search-head">
          <div>
            <h2 id="eesg-search-title">Поиск по рекомендациям</h2>
            <p>Поиск выполняется только по названиям страниц и разделов.</p>
          </div>
          <button class="eesg-search-close" type="button" data-search-close aria-label="Закрыть поиск">×</button>
        </div>
        <label class="eesg-search-input-wrap">
          <span class="eesg-search-input-icon">${icon()}</span>
          <input id="eesg-search-input" type="search" inputmode="search" autocomplete="off"
                 placeholder="Например: лейомиосаркома, трабектедин, биопсия"
                 aria-label="Поиск по названиям рекомендаций" />
        </label>
        <div class="eesg-search-meta" id="eesg-search-meta"></div>
        <div class="eesg-search-results" id="eesg-search-results" role="listbox"></div>
        <div class="eesg-search-hint"><kbd>↑</kbd><kbd>↓</kbd> выбор · <kbd>Enter</kbd> открыть · <kbd>Esc</kbd> закрыть</div>
      </section>`;

    document.body.appendChild(root);
    root.querySelectorAll('[data-search-close]').forEach((element) => {
      element.addEventListener('click', closeSearch);
    });
    root.querySelector('#eesg-search-input').addEventListener('input', (event) => {
      renderResults(event.target.value);
    });
    return root;
  }

  function openSearch() {
    const root = ensureDialog();
    previousFocus = document.activeElement;
    root.hidden = false;
    document.documentElement.classList.add('eesg-search-open');
    activeIndex = -1;
    const input = root.querySelector('#eesg-search-input');
    input.value = '';
    renderResults('');
    requestAnimationFrame(() => input.focus());
  }

  function closeSearch() {
    const root = document.getElementById(DIALOG_ID);
    if (!root || root.hidden) return;
    root.hidden = true;
    document.documentElement.classList.remove('eesg-search-open');
    if (previousFocus && typeof previousFocus.focus === 'function') previousFocus.focus();
  }

  function renderResults(value) {
    const root = ensureDialog();
    const results = root.querySelector('#eesg-search-results');
    const meta = root.querySelector('#eesg-search-meta');
    const query = normalize(value);
    activeIndex = -1;

    if (!query) {
      meta.textContent = `${INDEX.length} страниц в указателе`;
      results.innerHTML = '<div class="eesg-search-empty">Начните вводить название заболевания, препарата или раздела.</div>';
      return;
    }

    const matches = search(query);
    meta.textContent = matches.length
      ? `Найдено: ${matches.length}${matches.length === 12 ? '+' : ''}`
      : 'Совпадений нет';

    if (!matches.length) {
      results.innerHTML = '<div class="eesg-search-empty">Попробуйте другое или более короткое название.</div>';
      return;
    }

    results.replaceChildren(
      ...matches.map((item, index) => {
        const link = document.createElement('a');
        link.className = 'eesg-search-result';
        link.href = new URL(item.url, document.baseURI).href;
        link.setAttribute('role', 'option');
        link.dataset.searchIndex = String(index);

        const title = document.createElement('span');
        title.className = 'eesg-search-result-title';
        title.textContent = item.title;
        link.appendChild(title);

        if (item.breadcrumbs && item.breadcrumbs.length) {
          const context = document.createElement('span');
          context.className = 'eesg-search-result-context';
          context.textContent = item.breadcrumbs.join(' › ');
          link.appendChild(context);
        }
        return link;
      }),
    );
  }

  function selectResult(next) {
    const root = ensureDialog();
    const items = [...root.querySelectorAll('.eesg-search-result')];
    if (!items.length) return;
    items.forEach((item) => item.classList.remove('is-active'));
    activeIndex = (next + items.length) % items.length;
    items[activeIndex].classList.add('is-active');
    items[activeIndex].scrollIntoView({ block: 'nearest' });
  }

  function makeTrigger() {
    const button = document.createElement('button');
    button.id = TRIGGER_ID;
    button.className = 'eesg-search-trigger';
    button.type = 'button';
    button.setAttribute('aria-label', 'Поиск по рекомендациям');
    button.title = 'Поиск по рекомендациям (Ctrl/⌘ K)';
    button.innerHTML = `${icon()}<span>Поиск</span>`;
    button.addEventListener('click', openSearch);
    return button;
  }

  function mountTrigger() {
    if (document.getElementById(TRIGGER_ID)) return true;
    const target = document.querySelector('.pc-desktop-navigation__right');
    if (!target) return false;
    target.prepend(makeTrigger());
    return true;
  }

  document.addEventListener('keydown', (event) => {
    const root = document.getElementById(DIALOG_ID);
    const open = root && !root.hidden;

    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      openSearch();
      return;
    }
    if (!open) return;

    if (event.key === 'Escape') {
      event.preventDefault();
      closeSearch();
    } else if (event.key === 'ArrowDown') {
      event.preventDefault();
      selectResult(activeIndex + 1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      selectResult(activeIndex - 1);
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      const selected = root.querySelectorAll('.eesg-search-result')[activeIndex];
      if (selected) {
        event.preventDefault();
        selected.click();
      }
    }
  });

  const observer = new MutationObserver(() => mountTrigger());
  observer.observe(document.documentElement, { childList: true, subtree: true });
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      ensureDialog();
      mountTrigger();
    }, { once: true });
  } else {
    ensureDialog();
    mountTrigger();
  }
})();
