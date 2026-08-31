#!/usr/bin/env python3

'''
code file: lsetup.py
date: Aug 2026 (ml)
comments: Console program

'''
import os, sys
import subprocess
import shutil

# change working directory to path for this file
p = os.path.realpath(__file__)
appath = os.path.dirname(p)
os.chdir(appath)

# - - - - - - - - - - - - - - - - - - - - - - - -
# APP: tkedit.py
name = "TKedit Code Editor"
icon = appath + "/images/tked1.png"
exec = "python3 tkedit.py"
# - - - - - - - - - - - - - - - - - - - - - - - -

launcher_data = f'''
[Desktop Entry]
Version=1.0
Type=Application
Name={name}
Exec={exec}
Icon={icon}
Path={appath}
Terminal=false
'''

desktop_filename = os.path.expanduser(f"~/Desktop/{name}.desktop")
with open(desktop_filename, "w", encoding="utf-8") as fout:
    fout.write(launcher_data)
# copy launcher file to ~/.local/share/applications
dest = os.path.expanduser(f"~/.local/share/applications/{name}.desktop")
shutil.copy(desktop_filename, dest)
