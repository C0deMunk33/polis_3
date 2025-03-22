
import os
import shutil
try:
    os.remove("sqlite_db.db")
except FileNotFoundError:
    pass

try:
    shutil.rmtree("chroma_db.db")
except FileNotFoundError:
    pass

# delete all folders in the current directory ending with .db
for file in os.listdir("."):
    if os.path.isdir(file) and file.endswith(".db"):
        shutil.rmtree(file)
