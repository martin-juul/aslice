"""Exercise packaging and lifecycle on a disposable Linux Python host."""

import subprocess
import sys

subprocess.run([sys.executable, '-m', 'pip', 'install', '-r',
                'tools/simulator/runtime-requirements.txt'], check=True)
subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests/dev'], check=True)
