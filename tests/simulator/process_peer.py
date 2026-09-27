"""Controlled OS-test peer; remains alive after losing its simulator channel."""
import json
from pathlib import Path
import socket
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.simulator.protocol import receive, send

descriptor = json.loads(Path(sys.argv[1]).read_text())
connection = socket.create_connection((descriptor['host'], descriptor['port']), timeout=5)
send(connection, {'version': 1, 'operation': 'hello',
                  'identity': descriptor['identity'], 'token': descriptor['token']})
print(json.dumps(receive(connection)), flush=True)
for line in sys.stdin:
    request = json.loads(line)
    if request == 'disconnect':
        connection.close()
        result = {'disconnected': True}
    elif request == 'exit':
        break
    else:
        try:
            send(connection, request)
            result = receive(connection)
        except (EOFError, OSError):
            connection.close()
            result = {'disconnected': True}
    print(json.dumps(result), flush=True)
connection.close()
