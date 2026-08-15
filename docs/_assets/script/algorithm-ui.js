(() => {
  'use strict';

  function enhanceDiagram(mermaid) {
    if (mermaid.dataset.eesgAlgorithm === 'true' || !mermaid.querySelector('svg')) return false;
    mermaid.dataset.eesgAlgorithm = 'true';

    const wrapper = document.createElement('section');
    wrapper.className = 'eesg-algorithm';
    const toolbar = document.createElement('div');
    toolbar.className = 'eesg-algorithm__toolbar';

    const label = document.createElement('span');
    label.className = 'eesg-algorithm__label';
    label.textContent = 'Алгоритм';

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'eesg-algorithm__expand';
    button.textContent = 'Развернуть';
    button.setAttribute('aria-label', 'Развернуть алгоритм');

    const parent = mermaid.parentNode;
    parent.insertBefore(wrapper, mermaid);
    wrapper.append(toolbar, mermaid);
    toolbar.append(label, button);

    function setExpanded(expanded) {
      wrapper.classList.toggle('is-expanded', expanded);
      document.documentElement.classList.toggle('eesg-algorithm-open', expanded);
      button.textContent = expanded ? 'Закрыть' : 'Развернуть';
      button.setAttribute('aria-label', expanded ? 'Закрыть алгоритм' : 'Развернуть алгоритм');
    }

    button.addEventListener('click', () => setExpanded(!wrapper.classList.contains('is-expanded')));
    wrapper.addEventListener('click', (event) => {
      if (wrapper.classList.contains('is-expanded') && event.target === wrapper) setExpanded(false);
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && wrapper.classList.contains('is-expanded')) setExpanded(false);
    });
    return true;
  }

  function scan() {
    document.querySelectorAll('.mermaid').forEach(enhanceDiagram);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', scan, { once: true });
  } else {
    scan();
  }

  const observer = new MutationObserver(scan);
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
