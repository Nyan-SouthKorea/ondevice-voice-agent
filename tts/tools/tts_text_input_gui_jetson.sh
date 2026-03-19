#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$WORKSPACE_ROOT"

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
export LANG="${LANG:-ko_KR.UTF-8}"

if [[ -z "${LC_CTYPE:-}" || "${LC_CTYPE:-}" == "C" || "${LC_CTYPE:-}" == "C.UTF-8" ]]; then
  export LC_CTYPE="$LANG"
fi

if [[ -z "${LC_ALL:-}" || "${LC_ALL:-}" == "C" || "${LC_ALL:-}" == "C.UTF-8" ]]; then
  export LC_ALL="$LANG"
fi

export XMODIFIERS="${XMODIFIERS:-@im=ibus}"
export GTK_IM_MODULE="${GTK_IM_MODULE:-ibus}"
export QT_IM_MODULE="${QT_IM_MODULE:-ibus}"

mkdir -p results/tts/jetson_demo/piper_ko_text_input_gui

exec /usr/bin/python3 repo/tts/tools/tts_text_input_gui.py "$@"
