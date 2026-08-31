#!/bin/env bash

cat << 'EOF'
OPEN THIS SCRIPT IN YOUR "APPS" DIRECTORY
SCRIPT WILL CREATE "SWAB" APP DIRECTORY

-----------------------------
 Will install the following:
-----------------------------

TKedit Code Editor
and python modules


HIT CTRL-C TO QUIT OR ENTER TO CONTINUE
EOF
read -n 1

echo __________________________________
echo Begin installing needed packages
echo ----------------------------------

pip3 install -r requirements.txt

echo "setting up config ..."

mkdir "/home/$USER/.config/tkedit"
cp -v tkedit.ini "/home/$USER/.config/tkedit"
cp -v images/tkedit256.png "/home/$USER/.config/tkedit"
cp -v images/tked1.png "/home/$USER/.config/tkedit"
./cmpy tkedit.py

sleep 2

python3 lsetup.py

cat << 'EOF'

vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
There should be a new icon on
your desktop.
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
EOF

