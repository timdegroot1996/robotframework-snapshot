@REM release package

python -m pip install --upgrade pip build twine
rmdir /s /q .\dist\ 2>nul
python -m build
python -m twine check dist/*
python -m twine upload --verbose --repository pypi dist/*
@REM after this manually enter PYPI token

rmdir /s /q .\dist\
