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

  if (!isHomepage()) return;

  // The global header already provides portal navigation. On the landing page,
  // the left global TOC and right article TOC repeat the same choices and make
  // the page look substantially denser than the clinical pages.
  document.documentElement.classList.add('eesg-homepage');
})();
