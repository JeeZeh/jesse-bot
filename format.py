import subprocess
import sys

subprocess.check_call([sys.executable, "-m", "black", ".", "lib", "cogs"])
subprocess.check_call([sys.executable, "-m", "isort", "."])
subprocess.check_call([sys.executable, "-m", "flake8", "."])
subprocess.check_call([sys.executable, "-m", "mypy", "."])
