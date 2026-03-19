#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
REPO_ROOT="$WORKSPACE_ROOT/repo"
cd "$REPO_ROOT"

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

mkdir -p "$WORKSPACE_ROOT/results/tts/jetson_demo"

exec "$WORKSPACE_ROOT/env/wake_word_jetson/bin/python" voice_pipeline_tts_gui_demo.py "$@"
