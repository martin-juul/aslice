import type { Machine } from './model';

export type MachineAction =
  | 'start'
  | 'stop'
  | 'force'
  | 'clone'
  | 'delete'
  | 'snapshot'
  | 'restore'
  | 'network-loss';

/** UI availability is advisory; the controller still validates every operation. */
export function unavailableReason(
  action: MachineAction,
  machine: Machine | undefined,
  statusKnown: boolean,
  pending: boolean,
): string | undefined {
  if (!statusKnown) {
    return 'Refresh the machine list to check the current state.';
  }
  if (!machine) {
    return 'Select a machine first.';
  }
  if (pending) {
    return 'Wait for the current machine operation to finish.';
  }
  const required = ['stop', 'force', 'network-loss'].includes(action)
    ? 'running'
    : 'stopped';
  if (machine.state !== required) {
    return required === 'running'
      ? 'This action requires a running machine.'
      : 'Shut down the machine before using this action.';
  }
  return undefined;
}
