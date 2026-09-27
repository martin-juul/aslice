export function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className = '',
  text = '',
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}

export function button(text: string, action: () => void): HTMLButtonElement {
  const node = element('button', '', text);
  node.type = 'button';
  node.addEventListener('click', action);
  return node;
}

export function search(label: string): HTMLInputElement {
  const node = element('input');
  node.type = 'search';
  node.placeholder = label;
  node.setAttribute('aria-label', label);
  return node;
}
