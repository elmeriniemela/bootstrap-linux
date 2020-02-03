
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
# Force prompt to write history after every command.
# http://superuser.com/questions/20900/bash-history-loss
PROMPT_COMMAND="history -a"


activate() {
    if [[ $1 == odoo* ]];
    then
        # ${1:4} removes 'odoo' from odoo12 leaving just the number
        export ODOO_DIR=$HOME"/Code/work/odoo/${1:4}/odoo"
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


odoo() {
    version="$(cut -d'/' -f7 <<<$ODOO_DIR)"
    if (( version < 10  ));
    then
        python $ODOO_DIR/odoo.py $* --conf $ODOO_DIR/.odoorc.conf
    else
        python $ODOO_DIR/odoo-bin $* --conf $ODOO_DIR/.odoorc.conf
    fi;
}

venv() {
    python3 -m venv ~/.venv/$1 ${@:2}
}


clean_migrations () {
    # find . -path "*/migrations/*.py" -not -name "__init__.py" -not -name "content_*.py" -delete
    find . -path "*/migrations/*.pyc"  -delete
    dropdb thecodebase
    createdb thecodebase
    python manage.py makemigrations
    python manage.py migrate
}


alias notes="curl https://www.thecodebase.site/notes"
alias notes="cat ~/.notes"
add_note() {
    data=$(printf 'note=%s' "$1")
    TOKEN="eyJ1aWQiOjEsInRpbWUiOiIyMDE5LTA1LTAyIDE0OjQ5OjI0LjE2MDMxMCJ9.ehnllVNGn2App8Hz8WiuKkohqFs"
    curl -u "$TOKEN":unused -X POST --data-urlencode "$data" https://www.thecodebase.site/add_note/
}

add_note() {
    echo """$*""" >> ~/.notes
}

rm_submodule() {
    git submodule deinit -f -- "$1"
    rm -rf ".git/modules/a/$1"
    git rm -f "$1"
}

hard_reset_submodules() {
    git clean -xfdf
    git submodule foreach --recursive git clean -xfdf
    git reset --hard
    git submodule foreach --recursive git reset --hard
    git submodule update --init --recursive
}


alias cls="tput reset && clear"




export VISUAL=vim
export EDITOR="$VISUAL"
export FLASK_ENV=development
export ANSIBLE_DEBUG=0

stty -ixon

if [ -d "/opt/FlameGraph" ] ; then
    PATH="$PATH:/opt/FlameGraph"
fi

update_dir() {
    # if [ -z "$current_dir" ]
    # then
        SOURCE="${BASH_SOURCE[0]}"
        while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
            parent_dir="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
            SOURCE="$(readlink "$SOURCE")"
            [[ $SOURCE != /* ]] && SOURCE="$parent_dir/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
        done
        parent_dir="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
        current_dir=$(dirname "${parent_dir}")
    # fi
}


ssh_origin() {
    update_dir
    bash $current_dir/ssh_origin.sh
}

https_origin() {
    update_dir
    bash $current_dir/https_origin.sh
}

npm-upgrade() {
    update_dir
    bash $current_dir/npm-upgrade.sh
}

alias ssh_dis="mv ~/.ssh/* ~/SSH_DISABLED/;ssh-add -D"
alias ssh_en="mv ~/SSH_DISABLED/* ~/.ssh/;ssh-add -l"

_bootstrap_linux_completions()
{
    COMPREPLY=($(bootstrap-linux _bash_complete $COMP_CWORD ${COMP_WORDS[COMP_CWORD]} | tr -d '[],'))
}

complete -F _bootstrap_linux_completions bootstrap-linux
