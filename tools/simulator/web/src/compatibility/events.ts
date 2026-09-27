type Listener = EventListenerOrEventListenerObject;
interface Registration {
  type: string;
  listener: Listener;
  capture: boolean;
  wrapped: EventListener;
  cleanup: () => void;
}

function supportsSignal(): boolean {
  const probe = document.createElement('span');
  const controller = new AbortController();
  let called = false;
  probe.addEventListener(
    'probe',
    () => {
      called = true;
    },
    { signal: controller.signal },
  );
  controller.abort();
  probe.dispatchEvent(new Event('probe'));
  return !called;
}

// Safari 9 treats an options object as capture=true. Normalize once and signal
// as well, so feature teardown and request ownership retain their semantics.
function installOptions(prototype: EventTarget): void {
  // These originals are intentionally invoked with an explicit receiver below.
  // oxlint-disable-next-line typescript/unbound-method
  const add = prototype.addEventListener;
  // oxlint-disable-next-line typescript/unbound-method
  const remove = prototype.removeEventListener;
  const registrations = new WeakMap<EventTarget, Registration[]>();

  prototype.addEventListener = function (
    type: string,
    listener: Listener | null,
    options?: boolean | AddEventListenerOptions,
  ): void {
    if (!listener) {
      return;
    }
    const settings =
      typeof options === 'object' ? options : { capture: !!options };
    const capture = !!settings.capture;
    if (settings.signal?.aborted) {
      return;
    }
    const records = registrations.get(this) ?? [];
    if (
      records.some(
        (record) =>
          record.type === type &&
          record.listener === listener &&
          record.capture === capture,
      )
    ) {
      return;
    }
    const record: Registration = {
      type,
      listener,
      capture,
      wrapped: (event) => {
        if (settings.once) {
          record.cleanup();
        }
        if (typeof listener === 'function') {
          listener.call(this, event);
        } else {
          listener.handleEvent(event);
        }
      },
      cleanup: () => {
        remove.call(this, type, record.wrapped, capture);
        const index = records.indexOf(record);
        if (index !== -1) {
          records.splice(index, 1);
        }
        settings.signal?.removeEventListener('abort', record.cleanup);
      },
    };
    records.push(record);
    registrations.set(this, records);
    add.call(this, type, record.wrapped, capture);
    settings.signal?.addEventListener('abort', record.cleanup);
  };

  prototype.removeEventListener = function (
    type: string,
    listener: Listener | null,
    options?: boolean | EventListenerOptions,
  ): void {
    const capture = typeof options === 'object' ? !!options.capture : !!options;
    const record = registrations
      .get(this)
      ?.find(
        (item) =>
          item.type === type &&
          item.listener === listener &&
          item.capture === capture,
      );
    if (record) {
      record.cleanup();
    } else {
      remove.call(this, type, listener, capture);
    }
  };
}

if (!supportsSignal()) {
  // Older WebKit exposes the interface methods without an EventTarget global.
  const installed = new Set<object>();
  for (const target of [
    window,
    document,
    new XMLHttpRequest(),
    WebSocket.prototype,
  ]) {
    let prototype: object | null = target;
    while (
      prototype &&
      !Object.prototype.hasOwnProperty.call(prototype, 'addEventListener')
    ) {
      prototype = Object.getPrototypeOf(prototype) as object | null;
    }
    if (prototype && !installed.has(prototype)) {
      installOptions(prototype as EventTarget);
      installed.add(prototype);
    }
  }
}
