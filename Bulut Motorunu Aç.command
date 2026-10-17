#!/bin/zsh
cd "$(dirname "$0")"
.venv/bin/python scripts/worker_service.py install
