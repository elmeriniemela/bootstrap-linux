alias activate8=". /home/elmeri/.venv/odoo8/bin/activate;export ODOO_DIR='/home/elmeri/Sites/odoo8'"
alias activate10=". /home/elmeri/.venv/odoo10/bin/activate;export ODOO_DIR='/home/elmeri/Sites/odoo10'"
alias activate12=". /home/elmeri/.venv/odoo12/bin/activate;export ODOO_DIR='/home/elmeri/Sites/odoo12'"
alias activate11=". /home/elmeri/.venv/odoo11/bin/activate;export ODOO_DIR='/home/elmeri/Sites/odoo11'"

odoo() {
    python $ODOO_DIR/odoo-bin --conf $ODOO_DIR/.odoorc $*
}

odoo8() {
    python $ODOO_DIR/odoo.py --conf $ODOO_DIR/.odoorc $*
}

alias notes="curl https://www.thecodebase.site/notes"
add_note() {
    data=$(printf 'note=%s' "$1")
    curl -u "eyJ1aWQiOjF9.cR4a2IvdoxTn5c8wJ0x9ppmycNM":unused -X POST --data-urlencode "$data" https://www.thecodebase.site/add_note/
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

alias codebase=". /home/elmeri/Code/PERSONAL/python/thecodebase/thecodebase/venv/bin/activate;cd /home/elmeri/Code/PERSONAL/python/thecodebase;flask run"

alias cls="tput reset"




export VISUAL=vim
export EDITOR="$VISUAL"
export FLASK_ENV=development 


stty -ixon

if [ -d "/opt/FlameGraph" ] ; then
    PATH="$PATH:/opt/FlameGraph"
fi
