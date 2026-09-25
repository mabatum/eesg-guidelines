/* Anonymous feedback with hidden page context, submitted to Google Forms.
 * A normal HTML form POST displays the provider's response in an iframe.
 * The provider owns persistence and the submission confirmation.
 * Do not infer delivery from an iframe load, use no-cors POST, or store drafts as sent.
 */
(() => {
  'use strict';
  const CFG = Object.assign({formUrl: '', contextEntry: '', edition: '2026.09.3'}, window.EESG_FEEDBACK || {});
  const MAX_QUOTE = 600;
  const clean = (value) => String(value || '').replace(/\s+/g, ' ').trim();
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  };
  function contentRoot() {
    for (const selector of ['.dc-doc-page__body.yfm', '.dc-doc-page__content', '.yfm', 'article', 'main']) {
      const node = document.querySelector(selector);
      if (node) return node;
    }
    return null;
  }
  function headingInfo(range) {
    if (!range) return {title: 'Вся страница', anchor: ''};
    const root = contentRoot();
    const headings = root ? [...root.querySelectorAll('h1,h2,h3,h4')] : [];
    let heading;
    if (range) {
      const container = range.startContainer.nodeType === Node.ELEMENT_NODE ? range.startContainer : range.startContainer.parentElement;
      for (const candidate of headings) {
        if (candidate.contains(container) || (candidate.compareDocumentPosition(container) & Node.DOCUMENT_POSITION_FOLLOWING)) heading = candidate;
      }
    }
    const id = heading?.id || heading?.querySelector('[id]')?.id || '';
    const headingLabel = heading?.cloneNode(true);
    headingLabel?.querySelectorAll('[aria-hidden="true"],.visually-hidden').forEach(node => node.remove());
    return {title: clean(headingLabel?.textContent), anchor: id ? `#${id}` : ''};
  }
  function contextText({quote, heading}) {
    const page = new URL(location.href);
    page.search = '';
    page.hash = heading.anchor;
    return [
      'EESG · КР «Саркомы костей», 2025, ID 532_5',
      `Веб-редакция: ${CFG.edition}`,
      `Страница: ${clean(document.querySelector('h1')?.textContent || document.title)}`,
      `Раздел: ${heading.title || 'Вся страница'}`,
      `Ссылка: ${page.href}`,
      quote ? `Цитата:\n${quote}` : 'Общее замечание к странице',
    ].join('\n');
  }
  function formAddress(context) {
    const url = new URL(CFG.formUrl);
    if (url.protocol !== 'https:' || url.hostname !== 'docs.google.com' || !/^\/forms\/d\/e\/[^/]+\/viewform$/.test(url.pathname)) throw new Error('Invalid form URL');
    const fields = [CFG.contextEntry, CFG.commentEntry, CFG.nameEntry, CFG.contactEntry];
    if (fields.some(field => !/^entry\.\d+$/.test(field)) || new Set(fields).size !== fields.length) throw new Error('Invalid form fields');
    url.searchParams.set('embedded', 'true');
    url.searchParams.set('usp', 'pp_url');
    url.searchParams.set(CFG.contextEntry, context);
    return url;
  }
  let active = null;
  let selectionButton = null;
  const hideSelection = () => { selectionButton?.remove(); selectionButton = null; };
  function closeDialog() {
    if (!active) return;
    const {overlay, returnFocus, abort, overflow} = active;
    abort.abort();
    overlay.remove();
    document.body.style.overflow = overflow;
    active = null;
    returnFocus?.focus?.();
  }
  function openDialog(payload) {
    if (active) closeDialog();
    hideSelection();
    const returnFocus = document.activeElement;
    const abort = new AbortController();
    const overlay = el('div', 'eesg-fb-overlay');
    const dialog = el('section', 'eesg-fb-dialog');
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    dialog.setAttribute('aria-labelledby', 'eesg-fb-title');
    const header = el('div', 'eesg-fb-header');
    const title = el('h2', '', payload.quote ? 'Замечание к фрагменту' : 'Замечание к странице');
    title.id = 'eesg-fb-title';
    const cancel = el('button', 'eesg-fb-cancel', 'Закрыть');
    cancel.type = 'button';
    header.append(title, cancel);
    const hint = 'Без регистрации. Замечание получит редактор; имя и контакт можно не указывать. ' +
      (payload.quote ? 'К замечанию будут приложены ссылка и выбранный фрагмент.' : 'К замечанию будет приложена ссылка на эту страницу.');
    dialog.append(header, el('p', 'eesg-fb-hint', hint));
    const context = contextText(payload);
    if (payload.quote) dialog.append(el('blockquote', 'eesg-fb-quote', payload.quote));
    try {
      const url = formAddress(context);
      const form = el('form', 'eesg-fb-form');
      const action = new URL(url);
      action.pathname = action.pathname.replace(/viewform$/, 'formResponse');
      action.search = '?embedded=true';
      form.action = action.href;
      form.method = 'POST';
      form.acceptCharset = 'UTF-8';
      form.target = 'eesg-fb-response';
      function hidden(name, value) {
        const input = el('input');
        input.type = 'hidden';
        input.name = name;
        input.value = value;
        form.append(input);
      }
      hidden(CFG.contextEntry, context);
      hidden('fvv', '1');
      hidden('pageHistory', '0');
      function field(tag, id, name, labelText) {
        const wrapper = el('div', 'eesg-fb-field');
        const label = el('label', '', labelText);
        label.htmlFor = id;
        const input = el(tag);
        input.id = id;
        input.name = name;
        wrapper.append(label, input);
        return {wrapper, input};
      }
      const comment = field('textarea', 'eesg-fb-comment', CFG.commentEntry, 'Ваше замечание');
      comment.input.required = true;
      comment.input.rows = 5;
      comment.input.addEventListener('input', () => comment.input.setCustomValidity(''), {signal: abort.signal});
      const name = field('input', 'eesg-fb-name', CFG.nameEntry, 'Имя и организация — необязательно');
      const contact = field('input', 'eesg-fb-contact', CFG.contactEntry, 'Контакт для ответа — необязательно');
      const row = el('div', 'eesg-fb-row');
      row.append(name.wrapper, contact.wrapper);
      const actions = el('div', 'eesg-fb-actions');
      const send = el('button', 'eesg-fb-send', 'Отправить замечание');
      send.type = 'submit';
      actions.append(send);
      form.append(comment.wrapper, row, actions);
      dialog.append(form);

      const result = el('div', 'eesg-fb-result');
      result.hidden = true;
      const resultTitle = el('h3', '', 'Результат отправки');
      resultTitle.tabIndex = -1;
      const iframe = el('iframe', 'eesg-fb-frame');
      iframe.name = form.target;
      iframe.title = 'Подтверждение отправки от Google Forms';
      iframe.referrerPolicy = 'strict-origin-when-cross-origin';
      result.append(resultTitle, iframe);
      const footer = el('p', 'eesg-fb-hint eesg-fb-fallback');
      const link = el('a', '', 'Открыть форму отдельно');
      url.searchParams.delete('embedded');
      link.href = url.href;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      footer.append(document.createTextNode('Если подтверждение не появилось: '), link);
      result.append(footer);
      dialog.append(result);
      let submitted = false;
      form.addEventListener('submit', event => {
        if (submitted) { event.preventDefault(); return; }
        comment.input.setCustomValidity(clean(comment.input.value) ? '' : 'Введите текст замечания.');
        if (!form.reportValidity()) { event.preventDefault(); return; }
        // Keep a recovery link with the user's text; never claim success locally.
        for (const input of [comment.input, name.input, contact.input]) url.searchParams.set(input.name, input.value);
        link.href = url.href;
        submitted = true;
        send.disabled = true;
        form.hidden = true;
        result.hidden = false;
        resultTitle.focus();
      }, {signal: abort.signal});
    } catch {
      const status = el('p', 'eesg-fb-unavailable', 'Приём замечаний временно недоступен. Форма ещё не подключена; замечание не отправлено.');
      status.setAttribute('role', 'status');
      dialog.append(status);
    }
    overlay.append(dialog);
    active = {overlay, returnFocus, abort, overflow: document.body.style.overflow};
    document.body.style.overflow = 'hidden';
    document.body.append(overlay);
    cancel.addEventListener('click', closeDialog, {signal: abort.signal});
    overlay.addEventListener('click', event => { if (event.target === overlay) closeDialog(); }, {signal: abort.signal});
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') closeDialog();
      if (event.key === 'Tab') {
        const nodes = [...dialog.querySelectorAll('button,a[href],iframe,input:not([type="hidden"]),textarea')]
          .filter(node => !node.disabled && node.getClientRects().length);
        const first = nodes[0], last = nodes[nodes.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    }, {signal: abort.signal});
    (dialog.querySelector('textarea') || cancel).focus();
  }
  function onSelection() {
    if (active) return;
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || !selection.rangeCount) return hideSelection();
    const range = selection.getRangeAt(0);
    const root = contentRoot();
    if (!root?.contains(range.commonAncestorContainer)) return hideSelection();
    let quote = clean(selection.toString());
    if (!quote) return hideSelection();
    if (quote.length > MAX_QUOTE) quote = `${quote.slice(0, MAX_QUOTE)}…`;
    const rect = range.getBoundingClientRect();
    if (!rect.width && !rect.height) return hideSelection();
    const payload = {quote, heading: headingInfo(range)};
    hideSelection();
    selectionButton = el('button', 'eesg-fb-select', 'Замечание');
    selectionButton.type = 'button';
    selectionButton.style.top = `${Math.max(scrollY + 8, scrollY + rect.top - 44)}px`;
    selectionButton.style.left = `${Math.min(Math.max(8, rect.left + scrollX), scrollX + innerWidth - 130)}px`;
    selectionButton.addEventListener('mousedown', event => event.preventDefault());
    selectionButton.addEventListener('click', () => openDialog(payload));
    document.body.append(selectionButton);
  }
  function init() {
    if (document.querySelector('.eesg-fb-fab')) return;
    let selectionTimer;
    const deferSelection = () => { clearTimeout(selectionTimer); selectionTimer = setTimeout(onSelection, 160); };
    for (const event of ['mouseup','touchend','selectionchange']) document.addEventListener(event, deferSelection);
    document.addEventListener('scroll', hideSelection, {passive: true});
    const fab = el('button', 'eesg-fb-fab', 'Оставить замечание');
    fab.type = 'button';
    fab.addEventListener('click', () => openDialog({quote: '', heading: headingInfo(null)}));
    document.body.append(fab);
    document.addEventListener('click', event => {
      const link = event.target.closest?.('a[href]');
      if (link && new URL(link.href).hash === '#feedback') {
        event.preventDefault(); openDialog({quote: '', heading: headingInfo(null)});
      }
    });
    if (location.hash === '#feedback') openDialog({quote: '', heading: headingInfo(null)});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
