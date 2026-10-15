#!/bin/zsh
cd "$(dirname "$0")"
if [ -x .venv/bin/python ]; then
  .venv/bin/python start.py
else
  echo 'Önce README.md içindeki kurulumu tamamlayın.'
  read
fi
