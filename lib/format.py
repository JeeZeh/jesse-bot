import subprocess
import sys

subprocess.check_call([sys.executable, "-m", "black", "."])
subprocess.check_call([sys.executable, "-m", "isort", "."])
subprocess.check_call([sys.executable, "-m", "flake8", "."])
subprocess.check_call([sys.executable, "-m", "mypy", "."])
