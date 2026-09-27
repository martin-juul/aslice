function append(this: Node, ...nodes: (Node | string)[]): void {
  for (const node of nodes) {
    this.appendChild(
      typeof node === 'string' ? document.createTextNode(node) : node,
    );
  }
}

function replaceChildren(this: Node, ...nodes: (Node | string)[]): void {
  while (this.firstChild) {
    this.removeChild(this.firstChild);
  }
  append.apply(this, nodes);
}

for (const prototype of [
  Element.prototype,
  Document.prototype,
  DocumentFragment.prototype,
]) {
  if (!prototype.append) {
    prototype.append = append;
  }
  if (!prototype.replaceChildren) {
    prototype.replaceChildren = replaceChildren;
  }
}

function closest(start: Element, selector: string): Element | null {
  let candidate: Element | null = start;
  while (candidate) {
    if (candidate.matches(selector)) {
      return candidate;
    }
    candidate = candidate.parentElement;
  }
  return null;
}

if (!Element.prototype.closest) {
  Element.prototype.closest = function (selector: string): Element | null {
    return closest(this, selector);
  };
}

if (!Blob.prototype.arrayBuffer) {
  Blob.prototype.arrayBuffer = function (): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as ArrayBuffer);
      reader.onerror = () => reject(reader.error);
      reader.readAsArrayBuffer(this);
    });
  };
}
