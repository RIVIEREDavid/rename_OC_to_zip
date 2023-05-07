import tempfile
from pathlib import Path

test_temp = tempfile.TemporaryDirectory()
print(test_temp)
chemin = Path(__file__).resolve()

concat = str(test_temp) / chemin
print(concat)