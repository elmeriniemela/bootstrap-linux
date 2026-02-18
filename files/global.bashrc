#
# ~/.bashrc
#

[[ $- != *i* ]] && return

colors() {
    local fgc bgc vals seq0

    printf "Color escapes are %s\n" '\e[${value};...;${value}m'
    printf "Values 30..37 are \e[33mforeground colors\e[m\n"
    printf "Values 40..47 are \e[43mbackground colors\e[m\n"
    printf "Value  1 gives a  \e[1mbold-faced look\e[m\n\n"

    # foreground colors
    for fgc in {30..37}; do
        # background colors
        for bgc in {40..47}; do
            fgc=${fgc#37} # white
            bgc=${bgc#40} # black

            vals="${fgc:+$fgc;}${bgc}"
            vals=${vals%%;}

            seq0="${vals:+\e[${vals}m}"
            printf "  %-9s" "${seq0:-(default)}"
            printf " ${seq0}TEXT\e[m"
            printf " \e[${vals:+${vals+$vals;}}1mBOLD\e[m"
        done
        echo; echo
    done
}

[ -r /usr/share/bash-completion/bash_completion ] && . /usr/share/bash-completion/bash_completion

# Change the window title of X terminals
# case ${TERM} in
#     xterm*|rxvt*|Eterm*|aterm|kterm|gnome*|interix|konsole*)
#         PROMPT_COMMAND='echo -ne "\033]0;${USER}@${HOSTNAME%%.*}:${PWD/#$HOME/\~}\007"'
#         ;;
#     screen*)
#         PROMPT_COMMAND='echo -ne "\033_${USER}@${HOSTNAME%%.*}:${PWD/#$HOME/\~}\033\\"'
#         ;;
# esac

use_color=true

# Set colorful PS1 only on colorful terminals.
# dircolors --print-database uses its own built-in database
# instead of using /etc/DIR_COLORS.  Try to use the external file
# first to take advantage of user additions.  Use internal bash
# globbing instead of external grep binary.
safe_term=${TERM//[^[:alnum:]]/?}   # sanitize TERM
match_lhs=""
[[ -f ~/.dir_colors   ]] && match_lhs="${match_lhs}$(<~/.dir_colors)"
[[ -f /etc/DIR_COLORS ]] && match_lhs="${match_lhs}$(</etc/DIR_COLORS)"
[[ -z ${match_lhs}    ]] \
    && type -P dircolors >/dev/null \
    && match_lhs=$(dircolors --print-database)
[[ $'\n'${match_lhs} == *$'\n'"TERM "${safe_term}* ]] && use_color=true

if ${use_color} ; then
    # Enable colors for ls, etc.  Prefer ~/.dir_colors #64489
    if type -P dircolors >/dev/null ; then
        if [[ -f ~/.dir_colors ]] ; then
            eval $(dircolors -b ~/.dir_colors)
        elif [[ -f /etc/DIR_COLORS ]] ; then
            eval $(dircolors -b /etc/DIR_COLORS)
        fi
    fi

    # https://misc.flogisoft.com/bash/tip_colors_and_formatting
    if [ "$HOSTNAME" = homeserver ]; then
        normalcolor='33m'
        rootcolorrr='36m'
    else
        normalcolor='32m'
        rootcolorrr='31m'
    fi


    if [[ ${EUID} == 0 ]] ; then
        PS1="\[\e[1;$rootcolorrr\][\u@\h\[\e[1;37m\] \w\[\e[1;$rootcolorrr\]]\$\[\e[00m\] "
    else
        PS1="\[\e[1;$normalcolor\][\u@\h\[\e[1;37m\] \w\[\e[1;$normalcolor\]]\$\[\e[00m\] "
    fi

    alias ls='ls --color=auto'
    alias grep='grep --colour=auto'
    alias egrep='egrep --colour=auto'
    alias fgrep='fgrep --colour=auto'
else
    if [[ ${EUID} == 0 ]] ; then
        # show root@ when we don't have colors
        PS1='\u@\h \w \$ '
    else
        PS1='\u@\h \w \$ '
    fi
fi

# export PYENV_ROOT="$HOME/.pyenv"
# [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
# eval "$(pyenv init -)"

unset use_color safe_term match_lhs sh

alias cp="cp -i"                          # confirm before overwriting something
alias df='df -h'                          # human-readable sizes
alias free='free -m'                      # show sizes in MB
alias np='nano -w PKGBUILD'
alias more=less
alias feh="feh --scale-down --auto-zoom"

xhost +local:root > /dev/null 2>&1

complete -cf sudo

# Bash won't get SIGWINCH if another process is in the foreground.
# Enable checkwinsize so that bash will check the terminal size when
# it regains control.  #65623
# http://cnswww.cns.cwru.edu/~chet/bash/FAQ (E11)
shopt -s checkwinsize

shopt -s expand_aliases

# export QT_SELECT=4

# Enable history appending instead of overwriting.  #139609
shopt -s histappend

#
# # ex - archive extractor
# # usage: ex <file>
ex ()
{
  if [ -f $1 ] ; then
    case $1 in
      *.tar.bz2)   tar xjf $1   ;;
      *.tar.gz)    tar xzf $1   ;;
      *.bz2)       bunzip2 $1   ;;
      *.rar)       unrar x $1     ;;
      *.gz)        gunzip $1    ;;
      *.tar)       tar xf $1    ;;
      *.tbz2)      tar xjf $1   ;;
      *.tgz)       tar xzf $1   ;;
      *.zip)       unzip $1     ;;
      *.Z)         uncompress $1;;
      *.7z)        7z x $1      ;;
      *)           echo "'$1' cannot be extracted via ex()" ;;
    esac
  else
    echo "'$1' is not a valid file"
  fi
}

# \w in PS1 means show full path in bash!!


# Eternal bash history.
# ---------------------
# Undocumented feature which sets the size to "unlimited".
# http://stackoverflow.com/questions/9457233/unlimited-bash-history
export HISTFILESIZE=
export HISTSIZE=
export HISTTIMEFORMAT="[%F %T] "
# Change the file location because certain bash sessions truncate .bash_history file upon close.
# http://superuser.com/questions/575479/bash-history-truncated-to-500-lines-on-each-login
export HISTFILE=~/.bash_eternal_history
export HISTIGNORE=' *' # lines starting with ' ' will not be saved to history
# Force prompt to write history after every command.
# http://superuser.com/questions/20900/bash-history-loss
PROMPT_COMMAND="history -a"

[[ -r "/usr/share/bash-completion/completions/git" ]] && . "/usr/share/bash-completion/completions/git"

alias dotfiles='/usr/bin/git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME'
__git_complete dotfiles __git_main
alias server='/usr/bin/git --git-dir=$HOME/.server/ --work-tree=$HOME'
__git_complete server __git_main


activate() {
    if [[ $1 == odoo* ]];
    then
        # ${1:4} removes 'odoo' from odoo12 leaving just the number
        if [ -z "$2" ]
        then
            echo "Specify odoo config file i.e. odoorc.conf"
            return
        fi
        export ODOO_CONFIG_FILE=$2
        export ODOO_VERSION_DIR=$HOME"/Odoo/${1:4}"
    fi
    . ~/.venv/$1/bin/activate
}

_venv_completer () {
    # https://askubuntu.com/questions/707610/bash-completion-for-custom-command-to-complete-static-directory-tree
    local cur
    COMPREPLY=()
    cur=${COMP_WORDS[COMP_CWORD]}
    k=0
    i="~/.venv" # the directory from where to start
    for j in $( compgen -f "$i/$cur" ); do # loop trough the possible completions
        [ -d "$j" ] && j="${j}/" || j="${j} " # if its a dir add a shlash, else a space
        COMPREPLY[k++]=${j#$i/} # remove the directory prefix from the array
    done
    return 0
}

complete -o nospace -F _venv_completer activate

odoo() {
    if [ -f "$ODOO_VERSION_DIR/odoo/odoo-bin" ] ; then
        python $ODOO_VERSION_DIR/odoo/odoo-bin $* --conf $ODOO_VERSION_DIR/$ODOO_CONFIG_FILE
    else
        python $ODOO_VERSION_DIR/odoo/odoo.py $* --conf $ODOO_VERSION_DIR/$ODOO_CONFIG_FILE
    fi;
}


ssh_clipboard(){
    cat ~/.ssh/$1 | xclip -selection clipboard
}


_ssh_clipboard_completer () {
    # https://askubuntu.com/questions/707610/bash-completion-for-custom-command-to-complete-static-directory-tree
    local cur
    COMPREPLY=()
    cur=${COMP_WORDS[COMP_CWORD]}
    k=0
    i="~/.ssh" # the directory from where to start
    for j in $( compgen -f "$i/$cur" ); do # loop trough the possible completions
        [ -d "$j" ] && j="${j}/" || j="${j} " # if its a dir add a shlash, else a space
        COMPREPLY[k++]=${j#$i/} # remove the directory prefix from the array
    done
    return 0
}

complete -o nospace -F _ssh_clipboard_completer ssh_clipboard


config_pull(){(
    set -e # Fail early
    if [ -z "$1" ]
    then
        echo "Specify hostname"
        return
    fi
    rsync -avWPL "$1".ssh/ ~/.ssh
    rsync -avWPL "$1".bash_eternal_history ~/.bash_eternal_history
    rsync -avWPL "$1".psql_history ~/.psql_history
    rsync -avWPL "$1".python_history ~/.python_history
    rsync -avWPL "$1".cert ~/.cert
    rsync -avWPL "$1"VPN/ ~/VPN
)}

data_pull(){(
    set -e # Fail early
    if [ -z "$1" ]
    then
        echo "Specify hostname"
        return
    fi
    rsync --exclude 'lock' -avWPL "$1".thunderbird/ ~/.thunderbird
    rsync --exclude '*.log' -avWPL "$1".config/syncthing/ ~/.config/syncthing
    rsync -avWPL "$1"School/ ~/School
    rsync -avWPL "$1"Projects/ ~/Projects
    rsync --exclude 'odoo-dbs' -avWPL "$1"Odoo/ ~/Odoo
)}


config_push(){(
    set -e # Fail early
    if [ -z "$1" ]
    then
        echo "Specify dir"
        return
    fi
    rsync -avWPL ~/.ssh/ $1/.ssh
    rsync -avWPL ~/.bash_eternal_history $1/.bash_eternal_history
    rsync -avWPL ~/.psql_history $1/.psql_history
    rsync -avWPL ~/.python_history $1/.python_history
    rsync -avWPL ~/.cert/ $1/.cert
    rsync -avWPL ~/VPN/ $1/VPN
)}

data_push(){(
    set -e # Fail early
    if [ -z "$1" ]
    then
        echo "Specify dir"
        return
    fi
    rsync --exclude 'lock' -avWPL ~/.thunderbird/ $1/.thunderbird
    rsync --exclude '*.log' -avWPL ~/.config/syncthing/ $1/.config/syncthing
    rsync -avWPL ~/School/ $1/School
    rsync -avWPL ~/Projects/ $1/Projects
    rsync --exclude 'odoo-dbs' -avWPL ~/Odoo/ $1/Odoo
)}



venv() {
    python3 -m venv ~/.venv/$1 ${@:2}
}


add_note() {
    echo """$*""" >> ~/.notes
}

rm_submodule() {
    git submodule deinit -f -- "$1"
    rm -rf ".git/modules/a/$1"
    git rm -rf "$1"
}

# export MODULE="Odoo/16/odoo" && server submodule deinit -f -- "$MODULE" && rm -rf ".server/modules/a/$MODULE" && server rm -rf "$MODULE"

hard_reset_submodules() {
    git clean -xfdf
    git submodule foreach --recursive git clean -xfdf
    git reset --hard
    git submodule foreach --recursive git reset --hard
    git submodule update --init --recursive
}



alias cls="tput reset && clear"
alias gitignore="cp /home/elmeri/Projects/odoo_manager/odoo_manager/module_template/.gitignore ."


if [ -d "/opt/FlameGraph" ] ; then
    PATH="$PATH:/opt/FlameGraph"
fi

PATH="~/.cargo/bin:~/.local/bin:$PATH"

update_dir() {
    if [ -z "$current_dir" ]
    then
        SOURCE="${BASH_SOURCE[0]}"
        while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
            parent_dir="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
            SOURCE="$(readlink "$SOURCE")"
            [[ $SOURCE != /* ]] && SOURCE="$parent_dir/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
        done
        parent_dir="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
        current_dir=$(dirname "${parent_dir}")
    fi
}


alias ssh_dis="mv ~/.ssh/* ~/SSH_DISABLED/;ssh-add -D"
alias ssh_en="mv ~/SSH_DISABLED/* ~/.ssh/;ssh-add -l"

_bootstrap_linux_completions()
{
    update_dir
    readarray -t n < $current_dir/files/autocomplete
    COMPREPLY=()

    for i in "${n[@]}"
    do
        if [[ $COMP_CWORD == 1 && $i != "main" && $i == ${COMP_WORDS[COMP_CWORD]}* ]]; then
            COMPREPLY+=($i)
        fi
    done
}

complete -F _bootstrap_linux_completions bootstrap-linux


[ -r /usr/bin/neofetch ] &&  /usr/bin/neofetch --disable gpu

stty -ixon

export ANDROID_SDK=/home/elmeri/Android/Sdk
export VISUAL=vim
export EDITOR=vim
export FLASK_ENV=development
export ANSIBLE_DEBUG=0
