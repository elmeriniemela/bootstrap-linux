alias activate8=". /home/elmeri/.venv/odoo8/bin/activate;cd /home/elmeri/Sites/odoo8"
alias activate10=". /home/elmeri/.venv/odoo10/bin/activate;cd /home/elmeri/Sites/odoo10"
alias activate12=". /home/elmeri/.venv/odoo12/bin/activate;cd /home/elmeri/Sites/odoo12"
alias activate11=". /home/elmeri/.venv/odoo11/bin/activate;cd /home/elmeri/Sites/odoo11"

alias notes="cat ~/.notes"
add_note() {
    echo "$1" >> ~/.notes
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

alias odoo="python odoo-bin --conf .odoorc"
alias odoo8="python odoo.py --conf .odoorc"


export VISUAL=vim
export EDITOR="$VISUAL"
export FLASK_ENV=development 


stty -ixon

if [ -d "/opt/FlameGraph" ] ; then
    PATH="$PATH:/opt/FlameGraph"
fi
