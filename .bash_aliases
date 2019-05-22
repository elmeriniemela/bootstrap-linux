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
    TOKEN="eyJ1aWQiOjEsInRpbWUiOiIyMDE5LTA1LTAyIDE0OjQ5OjI0LjE2MDMxMCJ9.ehnllVNGn2App8Hz8WiuKkohqFs"
    curl -u "$TOKEN":unused -X POST --data-urlencode "$data" https://www.thecodebase.site/add_note/
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
export ANSIBLE_DEBUG=0

stty -ixon

if [ -d "/opt/FlameGraph" ] ; then
    PATH="$PATH:/opt/FlameGraph"
fi


ssh_origin() {
    REPO_URL=`git remote -v | grep -m1 '^origin' | sed -Ene's#.*(https://[^[:space:]]*).*#\1#p'`
    if [ -z "$REPO_URL" ]; then
    echo "-- ERROR:  Could not identify Repo url."
    echo "   It is possible this repo is already using SSH instead of HTTPS."
    exit
    fi
    HOST=`echo $REPO_URL | sed -Ene's#https://([^/]*)/([^/]*)/(.*).git#\1#p'`
    USER=`echo $REPO_URL | sed -Ene's#https://([^/]*)/([^/]*)/(.*).git#\2#p'`
    REPO=`echo $REPO_URL | sed -Ene's#https://([^/]*)/([^/]*)/(.*).git#\3#p'`
    if [ -z "$USER" ]; then
    echo "-- ERROR:  Could not identify User."
    exit
    fi

    if [ -z "$REPO" ]; then
    echo "-- ERROR:  Could not identify Repo."
    exit
    fi

    if [ -z "$HOST" ]; then
    echo "-- ERROR:  Could not identify Host."
    exit
    fi

    NEW_URL="git@$HOST:$USER/$REPO.git"
    echo "Changing repo url from "
    echo "  '$REPO_URL'"
    echo "      to "
    echo "  '$NEW_URL'"
    echo ""

    CHANGE_CMD="git remote set-url origin $NEW_URL"
    `$CHANGE_CMD`

    echo "Success"
}

https_origin() {
    REPO_URL=`git remote -v | grep -m1 '^origin' | sed -Ene's#.*(git@[^[:space:]]*).*#\1#p'`
    if [ -z "$REPO_URL" ]; then
    echo "-- ERROR:  Could not identify Repo url."
    echo "   It is possible this repo is already using SSH instead of HTTPS."
    exit
    fi
    HOST=`echo $REPO_URL | sed -Ene's#git@([^:]*):([^/]*)/(.*).git#\1#p'`
    USER=`echo $REPO_URL | sed -Ene's#git@([^:]*):([^/]*)/(.*).git#\2#p'`
    REPO=`echo $REPO_URL | sed -Ene's#git@([^:]*):([^/]*)/(.*).git#\3#p'`

    echo $REPO_URL
    echo $HOST
    echo $USER
    echo $REPO
    if [ -z "$USER" ]; then
    echo "-- ERROR:  Could not identify User."
    exit
    fi

    if [ -z "$REPO" ]; then
    echo "-- ERROR:  Could not identify Repo."
    exit
    fi

    if [ -z "$HOST" ]; then
    echo "-- ERROR:  Could not identify Host."
    exit
    fi

    NEW_URL="https://$HOST/$USER/$REPO.git"
    echo "Changing repo url from "
    echo "  '$REPO_URL'"
    echo "      to "
    echo "  '$NEW_URL'"
    echo ""

    CHANGE_CMD="git remote set-url origin $NEW_URL"
    echo "$CHANGE_CMD"
    `$CHANGE_CMD`

    echo "Success"

}

alias ssh_dis="mv ~/.ssh/* ~/SSH_DISABLED/;ssh-add -D"
alias ssh_en="mv ~/SSH_DISABLED/* ~/.ssh/;ssh-add -l"

add_ssh() {
    /usr/local/bin/python3.7 /home/elmeri/Code/PERSONAL/python/linux_install/install.py add_ssh $*
}

