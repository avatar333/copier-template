#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"

if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${ROOT_DIR}/requirements.txt"

printf '\n'
printf 'Virtual environment ready.\n'
printf 'Activate it with:\n'
printf '  source .venv/bin/activate\n'
printf 'Then run:\n'
printf '  flask --app run.py db upgrade\n'
printf '  flask --app run.py run\n'
