alias activate10=". /home/elmeri/.venv/odoo10/bin/activate;cd /home/elmeri/Sites/odoo10"
alias activate12=". /home/elmeri/.venv/odoo12/bin/activate;cd /home/elmeri/Sites/odoo12"
alias activate11=". /home/elmeri/.venv/odoo11/bin/activate;cd /home/elmeri/Sites/odoo11"

alias notes="cat ~/.notes"
add_note() {
    echo "$1" >> ~/.notes
}
alias codebase=". /home/elmeri/Code/PERSONAL/python/thecodebase/thecodebase/venv/bin/activate;cd /home/elmeri/Code/PERSONAL/python/thecodebase;flask run"

alias cls="tput reset"

alias odoo="python odoo-bin --conf .odoorc"


export VISUAL=vim
export EDITOR="$VISUAL"
export FLASK_ENV=development 


stty -ixon

if [ -d "/opt/FlameGraph" ] ; then
    PATH="$PATH:/opt/FlameGraph"
fi
