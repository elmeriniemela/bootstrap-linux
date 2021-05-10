#!/bin/bash
# Referenced from vscode settings.json
# "terminal.integrated.shell.linux": "$HOME/.config/bootstrap-linux/files/tmux-vscode.sh",
tmux_session="vscode`pwd | sed s/[^a-zA-Z0-9_]/-/g`"
# Add hash so that parent folder is also opended to own session even if subfolder sessions exist.
# By default tmux attaches a session if substring matches, and we add a hash to break the match of parent folder to subfolder.
tmux_session_hashed=$tmux_session-$((0x$(sha1sum <<<$tmux_session|cut -c1-2)))
tmux -u attach-session -d -t $tmux_session_hashed || tmux -u new-session -s $tmux_session_hashed
