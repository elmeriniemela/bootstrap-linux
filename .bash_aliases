alias activate8="activate odoo8; ODOO_DIR=$HOME'/Code/work/odoo/8/odoo'"
alias activate10="activate odoo10;export ODOO_DIR=$HOME'/Code/work/odoo/10/odoo'"
alias activate11="activate odoo11;export ODOO_DIR=$HOME'/Code/work/odoo/11/odoo'"
alias activate12="activate odoo12;export ODOO_DIR=$HOME'/Code/work/odoo/12/odoo'"

activate() {
    . ~/.venv/$1/bin/activate
}

odoo() {
    python $ODOO_DIR/odoo-bin --conf $ODOO_DIR/.odoorc.conf $*
}

odoo8() {
    python $ODOO_DIR/odoo.py --conf $ODOO_DIR/.odoorc.conf $*
}


clean_migrations () {
    find . -path "*/migrations/*.py" -not -name "__init__.py" -not -name "content_*.py" -delete
    find . -path "*/migrations/*.pyc"  -delete
    dropdb thecodebase
    createdb thecodebase
    python manage.py makemigrations && python manage.py migrate
}


alias create_module="/home/elmeri/.venv/odoo_manager/bin/python3.6 /home/elmeri/Code/work/odoo/odoo_manager/odoo_manager/manager.py"

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
    /usr/bin/python3.6 ~/Code/personal/python/linux_install/install.py add_ssh $*
}

