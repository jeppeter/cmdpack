
echo off
set filename=%~f0
for %%F in ("%filename%") do set script_dir=%%~dpF
set packagename=cmdpack

rmdir /Q /S %script_dir%dist 2>NUL
rmdir /Q /S %script_dir%%packagename% 2>NUL

rmdir /Q /S %script_dir%__pycache__ 2>NUL
rmdir /Q /S %script_dir%src\%packagename%\__pycache__ 2>NUL
rmdir /Q /S %script_dir%%packagename%.egg-info 2>NUL

del /Q /F %script_dir%%packagename%\__init__.py.touched 2>NUL
del /Q /F %script_dir%test\release\release.py.touched 2>NUL

del /Q /F %script_dir%%packagename%\__init__.py 2>NUL
del /Q /F %script_dir%src\%packagename%\__init_debug__.pyc 2>NUL
del /Q /F %script_dir%test\release\release.py 2>NUL
del /Q /F %script_dir%rtools.pyc 2>NUL

del /Q /F %script_dir%setup.py 2>NUL
