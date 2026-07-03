#!/bin/env bash

cat << 'EOF'
----------------------------
 Installing Needed software
----------------------------

execute with: tkedit.pyc

EOF

echo "Setting up required packages ..."

pip3 install -r requirements.txt --break-system-packages

echo "setting up config ..."

mkdir "/home/$USER/.config/tkedit"
cp -v tkedit.ini "/home/$USER/.config/tkedit"
cp -v images/tked1.png "/home/$USER/.config/tkedit"

./cmpy tkedit.py
