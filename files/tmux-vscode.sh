#!/bin/sh
SESSION="vscode`pwd | sed s/[^a-zA-Z0-9_]/-/g`"
tmux attach-session -d -t $SESSION || tmux new-session -s $SESSION
