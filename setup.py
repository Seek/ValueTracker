from distutils.core import setup
import py2exe

includes = []
excludes = ['pyreadline', 'difflib', 'doctest','PySide', 'PyQt4', 'PyQt5']
packages = []
dll_excludes = []
setup(
    options = {"py2exe": {"compressed": 2, 
                          "optimize": 2,
                          "includes": includes,
                          "excludes": excludes,
                          "packages": packages,
                          "dll_excludes": dll_excludes,
                          "bundle_files": 2,
                          "dist_dir": "dist",
                          "xref": False,
                          "skip_archive": False,
                          "ascii": False,
                          "custom_boot_script": '',
                         }
              },
    windows=['main.py']
)