import type { Machine } from './model';

const capabilityNames = new Map<string, string>([
  ['unchanged-cli', 'Unchanged CLI binaries'],
  ['cocoa-input', 'Cocoa display and input'],
  ['document-persistence', 'Document persistence'],
  ['lldb-parent-child', 'Parent and child debugging'],
  ['guest-isolation', 'Guest isolation'],
  ['lifecycle-recovery', 'Lifecycle recovery'],
  ['aslice-compatibility', 'aslice compatibility'],
  ['cli', 'CLI applications'],
  ['cocoa', 'Cocoa applications'],
  ['debugger', 'Debugging'],
]);

const statusNames = new Map<string, string>([
  ['pending', 'Pending verification'],
  ['unverified', 'Unverified'],
  ['passed', 'Reported passed'],
  ['failed', 'Reported failed'],
  ['unavailable', 'Unavailable'],
]);

function propertyList(
  document: Document,
  entries: readonly (readonly [string, string])[],
): HTMLDListElement {
  const list = document.createElement('dl');
  list.className = 'machine-properties';
  for (const [label, value] of entries) {
    const row = document.createElement('div');
    const term = document.createElement('dt');
    term.textContent = label;
    const description = document.createElement('dd');
    description.textContent = value;
    row.append(term, description);
    list.append(row);
  }
  return list;
}

function capabilities(document: Document, value: unknown): HTMLElement {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const entries = Object.entries(value).map(
      ([key, status]): [string, string] => [
        capabilityNames.get(key) ?? key,
        typeof status === 'string'
          ? (statusNames.get(status) ?? status)
          : 'See technical details',
      ],
    );
    if (entries.length) {
      return propertyList(document, entries);
    }
  }
  const empty = document.createElement('p');
  empty.textContent =
    value === undefined ||
    value === null ||
    (typeof value === 'object' &&
      !Array.isArray(value) &&
      !Object.keys(value).length)
      ? 'No capability results reported.'
      : 'See Technical details for the reported capability data.';
  return empty;
}

/** Report the controller's claims without promoting missing data to verification. */
export function mountMachineDetails(
  container: HTMLDivElement,
): (machine: Machine | undefined) => void {
  const document = container.ownerDocument;
  const configurationTitle = document.createElement('h3');
  configurationTitle.textContent = 'Configuration';
  const configuration = document.createElement('div');
  const capabilitiesTitle = document.createElement('h3');
  capabilitiesTitle.textContent = 'Compatibility';
  const results = document.createElement('div');
  const details = document.createElement('details');
  const summary = document.createElement('summary');
  summary.textContent = 'Technical details';
  const identifiers = document.createElement('div');
  const rawLabel = document.createElement('h4');
  rawLabel.textContent = 'Reported capability data';
  const raw = document.createElement('pre');
  details.append(summary, identifiers, rawLabel, raw);
  container.replaceChildren(
    configurationTitle,
    configuration,
    capabilitiesTitle,
    results,
    details,
  );
  let displayedName: string | undefined;

  return (machine): void => {
    container.hidden = !machine;
    if (machine?.name !== displayedName) {
      details.open = false;
      displayedName = machine?.name;
    }
    if (!machine) {
      configuration.replaceChildren();
      results.replaceChildren();
      identifiers.replaceChildren();
      raw.textContent = '';
      return;
    }
    const memory =
      machine.memory_mib % 1024 === 0
        ? `${machine.memory_mib / 1024} GiB`
        : `${machine.memory_mib} MiB`;
    configuration.replaceChildren(
      propertyList(document, [
        ['Processors', String(machine.cpus)],
        ['Memory', memory],
        ['Disk capacity', `${machine.disk_gib} GiB`],
      ]),
    );
    results.replaceChildren(capabilities(document, machine.capabilities));
    identifiers.replaceChildren(
      propertyList(document, [
        ['Base image ID', machine.base],
        ['Runtime SHA-256', machine.runtime_sha256],
      ]),
    );
    raw.textContent =
      JSON.stringify(machine.capabilities, null, 2) ?? 'Not reported';
  };
}
