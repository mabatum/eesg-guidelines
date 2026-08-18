/* Замечания к фрагментам текста без регистрации.
 *
 * Выделение внутри статьи -> кнопка «Замечание» -> окно с цитатой и полем
 * текста. Отправка уходит на адрес из feedback-config.js; если он не задан,
 * открывается письмо с тем же содержимым, чтобы обратная связь работала и до
 * настройки приёмника.
 */
(() => {
  'use strict';

  const CFG = Object.assign(
    { endpoint: '', contentType: 'text/plain;charset=utf-8', mailto: '', project: 'EESG' },
    window.EESG_FEEDBACK || {},
  );

  const CONTENT_SELECTORS = ['.dc-doc-page__main', '.dc-doc-page__content', '.yfm', 'main', 'article'];
  const MAX_QUOTE = 600;
  const clean = (value) => String(value || '').replace(/\s+/g, ' ').trim();

  function contentRoot() {
    for (const selector of CONTENT_SELECTORS) {
      const node = document.querySelector(selector);
      if (node) return node;
    }
    return document.body;
  }

  /* Ближайший заголовок над выделением: по нему рабочая группа находит место. */
  function nearestHeading(node) {
    let el = node instanceof Element ? node : node?.parentElement;
    while (el && el !== document.body) {
      let sibling = el.previousElementSibling;
      while (sibling) {
        if (/^H[1-4]$/.test(sibling.tagName)) return sibling;
        const nested = sibling.querySelectorAll?.('h1,h2,h3,h4');
        if (nested?.length) return nested[nested.length - 1];
        sibling = sibling.previousElementSibling;
      }
      el = el.parentElement;
    }
    return document.querySelector('h1');
  }

  function headingInfo(range) {
    const heading = range ? nearestHeading(range.startContainer) : document.querySelector('h1');
    if (!heading) return { title: '', anchor: '' };
    const id = heading.getAttribute('id') || heading.querySelector('[id]')?.id || '';
    return { title: clean(heading.textContent), anchor: id ? `#${id}` : '' };
  }

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  };

  function buildDialog({ quote, heading }) {
    const overlay = el('div', 'eesg-fb-overlay');
    const dialog = el('div', 'eesg-fb-dialog');
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');

    dialog.append(el('h2', null, quote ? 'Замечание к фрагменту' : 'Замечание к странице'));
    dialog.append(
      el(
        'p',
        'eesg-fb-hint',
        'Замечание уходит рабочей группе вместе с цитатой и адресом страницы. Регистрация не нужна, имя и контакт — по желанию.',
      ),
    );
    if (quote) dialog.append(el('blockquote', 'eesg-fb-quote', quote));

    const commentField = el('div', 'eesg-fb-field');
    const commentLabel = el('label', null, 'Что не так или что предложить');
    const comment = el('textarea');
    comment.required = true;
    comment.placeholder =
      'Например: доза приведена по протоколу исследования, но в нашей практике применяется другая; или: положение противоречит источнику под номером 4.';
    comment.id = 'eesg-fb-comment';
    commentLabel.setAttribute('for', comment.id);
    commentField.append(commentLabel, comment);

    const row = el('div', 'eesg-fb-row');
    const nameField = el('div', 'eesg-fb-field');
    const nameLabel = el('label', null, 'Имя и место работы — по желанию');
    const name = el('input');
    name.type = 'text';
    name.id = 'eesg-fb-name';
    name.autocomplete = 'name';
    nameLabel.setAttribute('for', name.id);
    nameField.append(nameLabel, name);

    const contactField = el('div', 'eesg-fb-field');
    const contactLabel = el('label', null, 'Почта для ответа — по желанию');
    const contact = el('input');
    contact.type = 'email';
    contact.id = 'eesg-fb-contact';
    contact.autocomplete = 'email';
    contactLabel.setAttribute('for', contact.id);
    contactField.append(contactLabel, contact);
    row.append(nameField, contactField);

    const actions = el('div', 'eesg-fb-actions');
    const status = el('span', 'eesg-fb-status');
    const cancel = el('button', 'eesg-fb-cancel', 'Отмена');
    cancel.type = 'button';
    const send = el('button', 'eesg-fb-send', 'Отправить');
    send.type = 'button';
    actions.append(status, cancel, send);

    dialog.append(commentField, row, actions);
    overlay.append(dialog);

    return { overlay, dialog, comment, name, contact, status, cancel, send, heading, quote };
  }

  function payloadOf(parts) {
    return {
      project: CFG.project,
      page_title: clean(document.title),
      page_url: window.location.href.split('#')[0] + (parts.heading.anchor || ''),
      section: parts.heading.title,
      quote: parts.quote || '',
      comment: clean(parts.comment.value),
      author: clean(parts.name.value),
      contact: clean(parts.contact.value),
      sent_at: new Date().toISOString(),
      user_agent: navigator.userAgent,
    };
  }

  function mailtoFallback(data) {
    if (!CFG.mailto) return false;
    const body = [
      `Страница: ${data.page_title}`,
      `Адрес: ${data.page_url}`,
      data.section ? `Раздел: ${data.section}` : '',
      data.quote ? `\nЦитата:\n${data.quote}` : '',
      `\nЗамечание:\n${data.comment}`,
      data.author ? `\nАвтор: ${data.author}` : '',
      data.contact ? `Контакт: ${data.contact}` : '',
    ]
      .filter(Boolean)
      .join('\n');
    window.location.href =
      `mailto:${CFG.mailto}?subject=${encodeURIComponent('Замечание к рекомендациям EESG')}` +
      `&body=${encodeURIComponent(body)}`;
    return true;
  }

  let active = null;

  function close(parts) {
    parts?.overlay?.remove();
    if (active === parts) active = null;
  }

  async function submit(parts) {
    const data = payloadOf(parts);
    if (!data.comment) {
      parts.status.dataset.kind = 'error';
      parts.status.textContent = 'Напишите замечание.';
      parts.comment.focus();
      return;
    }

    parts.send.disabled = true;
    parts.status.dataset.kind = '';
    parts.status.textContent = 'Отправляем…';

    if (!CFG.endpoint) {
      parts.status.textContent = 'Открываем письмо…';
      if (!mailtoFallback(data)) {
        parts.status.dataset.kind = 'error';
        parts.status.textContent = 'Приём замечаний ещё не настроен.';
        parts.send.disabled = false;
        return;
      }
      window.setTimeout(() => close(parts), 600);
      return;
    }

    try {
      const response = await fetch(CFG.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': CFG.contentType },
        body: JSON.stringify(data),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      parts.status.dataset.kind = 'ok';
      parts.status.textContent = 'Спасибо, замечание отправлено.';
      window.setTimeout(() => close(parts), 1200);
    } catch (error) {
      parts.status.dataset.kind = 'error';
      parts.status.textContent = 'Не отправилось. Открыть письмо?';
      parts.send.textContent = 'Письмом';
      parts.send.disabled = false;
      parts.send.onclick = () => mailtoFallback(data);
    }
  }

  function openDialog({ quote, heading }) {
    if (active) close(active);
    const parts = buildDialog({ quote, heading });
    active = parts;
    parts.cancel.addEventListener('click', () => close(parts));
    parts.send.addEventListener('click', () => submit(parts));
    parts.overlay.addEventListener('mousedown', (event) => {
      if (event.target === parts.overlay) close(parts);
    });
    document.addEventListener('keydown', function onKey(event) {
      if (event.key === 'Escape') {
        close(parts);
        document.removeEventListener('keydown', onKey);
      }
    });
    document.body.append(parts.overlay);
    parts.comment.focus();
  }

  /* ---- кнопка у выделения ---- */

  let selectButton = null;

  function hideSelectButton() {
    selectButton?.remove();
    selectButton = null;
  }

  function showSelectButton(rect, payload) {
    hideSelectButton();
    selectButton = el('button', 'eesg-fb-select', 'Замечание');
    selectButton.type = 'button';
    const top = window.scrollY + rect.top - 44;
    selectButton.style.top = `${Math.max(window.scrollY + 8, top)}px`;
    selectButton.style.left = `${Math.max(8, window.scrollX + rect.left)}px`;
    selectButton.addEventListener('mousedown', (event) => event.preventDefault());
    selectButton.addEventListener('click', () => {
      hideSelectButton();
      openDialog(payload);
    });
    document.body.append(selectButton);
  }

  function onSelectionSettled() {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || selection.rangeCount === 0) {
      hideSelectButton();
      return;
    }
    const range = selection.getRangeAt(0);
    if (!contentRoot().contains(range.commonAncestorContainer)) {
      hideSelectButton();
      return;
    }
    let quote = clean(selection.toString());
    if (quote.length < 8) {
      hideSelectButton();
      return;
    }
    if (quote.length > MAX_QUOTE) quote = `${quote.slice(0, MAX_QUOTE)}…`;
    const rect = range.getBoundingClientRect();
    if (!rect || (!rect.width && !rect.height)) {
      hideSelectButton();
      return;
    }
    showSelectButton(rect, { quote, heading: headingInfo(range) });
  }

  function init() {
    document.addEventListener('mouseup', () => window.setTimeout(onSelectionSettled, 10));
    document.addEventListener('touchend', () => window.setTimeout(onSelectionSettled, 250));
    document.addEventListener('selectionchange', () => window.setTimeout(onSelectionSettled, 120));
    document.addEventListener('scroll', hideSelectButton, { passive: true });
    document.addEventListener('mousedown', (event) => {
      if (selectButton && !selectButton.contains(event.target)) hideSelectButton();
    });

    const fab = el('button', 'eesg-fb-fab', 'Замечание к странице');
    fab.type = 'button';
    fab.addEventListener('click', () => openDialog({ quote: '', heading: headingInfo(null) }));
    document.body.append(fab);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
