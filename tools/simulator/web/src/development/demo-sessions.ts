import type { Command } from '../shared/protocol';
import type { SessionOutput } from '../features/sessions/model';
import { decode } from '../shared/bytes';
import { DemoOutput } from './demo-output';
import { terminalSamples } from './terminal-samples';
import type { TerminalSample } from './terminal-samples';

type SessionCommand = Extract<
  Command,
  {
    action:
      | 'shell'
      | 'exec'
      | 'debug'
      | 'session-read'
      | 'session-write'
      | 'session-resize'
      | 'session-close';
  }
>;

export class DemoSessions {
  private sessions = new Map<
    string,
    { name: string; info: SessionOutput; output: DemoOutput; failRead: boolean }
  >();

  list(name: string): SessionOutput[] {
    return [...this.sessions.values()]
      .filter((session) => session.name === name)
      .map((session) => session.info);
  }

  execute(command: SessionCommand): unknown {
    if (
      command.action === 'shell' ||
      command.action === 'exec' ||
      command.action === 'debug'
    ) {
      const id = crypto.randomUUID();
      const info: SessionOutput = {
        id,
        pid: 400 + this.sessions.size,
        mode: command.mode,
        kind: command.action,
        exit_code: command.action === 'exec' ? 0 : null,
        cursor: 0,
        data: '',
        truncated: false,
      };
      const output = new DemoOutput();
      output.append(
        `UI demo: ${command.action} preview. No commands execute.\r\n${command.action === 'debug' ? '(demo lldb) ' : '$ '}`,
      );
      this.sessions.set(id, {
        name: command.name,
        info,
        output,
        failRead: false,
      });
      return info;
    }
    const session = this.sessions.get(command.session);
    if (!session || session.name !== command.name) {
      throw new Error('Unknown demo session.');
    }
    if (command.action === 'session-read') {
      if (session.failRead) {
        session.failRead = false;
        throw new Error(
          'Demo output connection interrupted. Use Reconnect output to continue.',
        );
      }
      return {
        ...session.info,
        ...session.output.read(command.cursor),
      };
    }
    if (command.action === 'session-write') {
      const text = new TextDecoder().decode(decode(command.data));
      session.output.append(
        text.replaceAll('\r', '\r\n[demo input received]\r\n$ '),
      );
    } else if (command.action === 'session-close') {
      session.info.exit_code = 0;
    }
    return {};
  }

  sample(name: string, id: string, sample: TerminalSample): void {
    const session = this.sessions.get(id);
    if (!session || session.name !== name || session.info.exit_code !== null) {
      throw new Error('Select a running demo session first.');
    }
    if (sample === 'disconnect') {
      session.failRead = true;
    } else if (sample === 'exit') {
      session.output.append('\r\n[Demo session exited]\r\n\u001b]9;4;0\u0007');
      session.info.exit_code = 0;
    } else {
      session.output.append(terminalSamples[sample]);
    }
  }
}
