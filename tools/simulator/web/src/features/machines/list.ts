import type { Machine } from './model';

export type MachineListStatus = 'loading' | 'ready' | 'unavailable';

export function renderMachineList(
  list: HTMLDivElement,
  machines: readonly Machine[],
  selected: string | null,
  status: MachineListStatus,
  select: (name: string) => void,
): void {
  const document = list.ownerDocument;
  const active = document.activeElement;
  const focusedName =
    active instanceof HTMLElement && list.contains(active)
      ? active.dataset.machine
      : undefined;
  const fragment = document.createDocumentFragment();
  let focusTarget: HTMLButtonElement | undefined;
  for (const machine of machines) {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'machine-row';
    row.dataset.machine = machine.name;
    row.classList.toggle('selected', machine.name === selected);
    row.setAttribute('aria-pressed', String(machine.name === selected));
    const name = document.createElement('span');
    name.className = 'machine-name';
    name.textContent = machine.name;
    const state = document.createElement('span');
    state.className = 'machine-state';
    state.textContent =
      status === 'ready' ? machine.state : 'Status unavailable';
    row.append(name, state);
    row.addEventListener('click', () => select(machine.name));
    fragment.append(row);
    if (focusedName === machine.name) {
      focusTarget = row;
    }
  }
  if (!machines.length) {
    const empty = document.createElement('p');
    empty.className = 'machine-list-empty';
    empty.textContent =
      status === 'loading'
        ? 'Retrieving machines…'
        : status === 'unavailable'
          ? 'Machine list unavailable. Refresh to try again.'
          : 'No machines yet. Use Create machine to add one.';
    fragment.append(empty);
  }
  list.replaceChildren(fragment);
  focusTarget?.focus();
}
