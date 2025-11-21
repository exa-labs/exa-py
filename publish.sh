rm -rf dist/**
python3 setup.py sdist bdist_wheel
uv run twine upload dist/*
