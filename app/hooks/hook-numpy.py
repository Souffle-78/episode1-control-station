"""Collect NumPy for the frozen app.

PyInstaller's bundled NumPy hook assumes a conda/pip environment and can fail
inside the FreeCAD Python environment used to build this app.  This local
hook has no such dependency: it simply collects the whole installed package.
"""
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("numpy")
