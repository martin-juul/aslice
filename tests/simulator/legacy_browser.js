// Exercise fallback paths in a current engine; this is not Safari 9 qualification.
(function () {
  var prototype = EventTarget.prototype;
  var add = prototype.addEventListener;
  var remove = prototype.removeEventListener;
  prototype.addEventListener = function (type, listener, options) {
    add.call(this, type, listener, !!options);
  };
  prototype.removeEventListener = function (type, listener, options) {
    remove.call(this, type, listener, !!options);
  };

  [
    'fetch',
    'AbortController',
    'AbortSignal',
    'ResizeObserver',
    'TextEncoder',
    'TextDecoder',
    'PointerEvent',
    'WebAssembly',
    'OffscreenCanvas',
    'IntersectionObserver',
    'structuredClone',
    'BigInt',
    'EventTarget',
  ].forEach(function (name) {
    delete window[name];
  });
  Object.defineProperty(crypto, 'randomUUID', {
    value: undefined,
    writable: true,
  });
  delete Blob.prototype.arrayBuffer;
  delete HTMLAnchorElement.prototype.download;
  Object.defineProperty(document, 'fonts', { value: undefined });
  [Element.prototype, Document.prototype, DocumentFragment.prototype].forEach(
    function (target) {
      delete target.append;
      delete target.replaceChildren;
    },
  );

  var context = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (kind, options) {
    if (kind === 'webgl2') {
      return null;
    }
    return context.call(this, kind, options);
  };
})();
