# quickfix script to run after pyinstaller to fix packages manually
# can most likely be done better through proper pyinstaller config
cp -r static dist/launcher/
cp -r d-id dist/launcher/
cp -r version.txt dist/launcher/
cp -r migrations dist/launcher/
cp -r migrations dist/launcher/_internal/
cp -r venv/Lib/site-packages/chromadb/migrations/ dist/launcher/_internal/chromadb/
cp -r venv/Lib/site-packages/chromadb/migrations/__init__.py dist/launcher/_internal/chromadb/migrations/embeddings_queue
cp -r venv/Lib/site-packages/chromadb/migrations/__init__.py dist/launcher/_internal/chromadb/migrations/metadb
cp -r venv/Lib/site-packages/chromadb/migrations/__init__.py dist/launcher/_internal/chromadb/migrations/sysdb

mkdir dist/launcher/_internal/addons/
mkdir dist/launcher/addons/
