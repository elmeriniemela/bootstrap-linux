alias activate8=". /home/elmeri/.venv/odoo8/bin/activate;export ODOO_DIR='/home/elmeri/Code/work/odoo/8/odoo8'"
alias activate10=". /home/elmeri/.venv/odoo10/bin/activate;export ODOO_DIR='/home/elmeri/Code/work/odoo/10/odoo10'"
alias activate11=". /home/elmeri/.venv/odoo11/bin/activate;export ODOO_DIR='/home/elmeri/Code/work/odoo/11/odoo11'"
alias activate12=". /home/elmeri/.venv/odoo12/bin/activate;export ODOO_DIR='/home/elmeri/Code/work/odoo/12/odoo12'"

odoo() {
    python $ODOO_DIR/odoo-bin --conf $ODOO_DIR/.odoorc $*
}

odoo8() {
    python $ODOO_DIR/odoo.py --conf $ODOO_DIR/.odoorc $*
}

alias create_module="/home/elmeri/Code/addons12/odoo_manager/venv/bin/python /home/elmeri/Code/addons12/odoo_manager/odoo_manager/manager.py"

alias notes="curl https://www.thecodebase.site/notes"
alias notes="cat ~/.notes"
add_note() {
    data=$(printf 'note=%s' "$1")
    TOKEN="eyJ1aWQiOjEsInRpbWUiOiIyMDE5LTA1LTAyIDE0OjQ5OjI0LjE2MDMxMCJ9.ehnllVNGn2App8Hz8WiuKkohqFs"
    curl -u "$TOKEN":unused -X POST --data-urlencode "$data" https://www.thecodebase.site/add_note/
}

add_note() {
    echo """$1""" >> ~/.notes
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

alias codebase=". /home/elmeri/.venv/flask/bin/activate;cd /home/elmeri/Code/PERSONAL/python/thecodebase;flask run"

alias cls="tput reset"




export VISUAL=vim
export EDITOR="$VISUAL"
export FLASK_ENV=development 
export ANSIBLE_DEBUG=0

stty -ixon

if [ -d "/opt/FlameGraph" ] ; then
    PATH="$PATH:/opt/FlameGraph"
fi

current_dir() {
    SOURCE="${BASH_SOURCE[0]}"
    while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
        DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
        SOURCE="$(readlink "$SOURCE")"
        [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
    done
    DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
}


ssh_origin() {
    current_dir
    bash $DIR/ssh_origin.sh
}

https_origin() {
    current_dir
    bash $DIR/https_origin.sh
}

npm-upgrade() {
    current_dir
    bash $DIR/npm-upgrade.sh
}

alias ssh_dis="mv ~/.ssh/* ~/SSH_DISABLED/;ssh-add -D"
alias ssh_en="mv ~/SSH_DISABLED/* ~/.ssh/;ssh-add -l"

add_ssh() {
    /usr/bin/python3.6 /home/elmeri/Code/PERSONAL/python/linux_install/install.py add_ssh $*
}

