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
# 	xterm*|rxvt*|Eterm*|aterm|kterm|gnome*|interix|konsole*)
# 		PROMPT_COMMAND='echo -ne "\033]0;${USER}@${HOSTNAME%%.*}:${PWD/#$HOME/\~}\007"'
# 		;;
# 	screen*)
# 		PROMPT_COMMAND='echo -ne "\033_${USER}@${HOSTNAME%%.*}:${PWD/#$HOME/\~}\033\\"'
# 		;;
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

	if [[ ${EUID} == 0 ]] ; then
		PS1='\[\033[01;31m\][\u@\h\[\033[01;36m\] \w\[\033[01;31m\]]\$\[\033[00m\] '
	else
		PS1='\[\033[01;32m\][\u@\h\[\033[01;37m\] \w\[\033[01;32m\]]\$\[\033[00m\] '
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
# Force prompt to write history after every command.
# http://superuser.com/questions/20900/bash-history-loss
PROMPT_COMMAND="history -a"


alias dotfiles='/usr/bin/git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME'
[[ -r "/usr/share/bash-completion/completions/git" ]] && . "/usr/share/bash-completion/completions/git"
__git_complete dotfiles __git_main

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


odoo_coverage() {
    coverage run --source=$PWD $ODOO_DIR/odoo-bin $* --conf $ODOO_DIR/.odoorc.conf
    coverage html
}

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
    find . -path "*/migrations/*.py" -not -name "__init__.py" -not -name "content_*.py" -delete
    find . -path "*/migrations/*.pyc"  -delete
    dropdb thecodebase
    createdb thecodebase
    python manage.py makemigrations
    python manage.py migrate
}

alias gitignore="cp /home/elmeri/Code/personal/odoo_manager/odoo_manager/module_template/.gitignore ."
alias notes="curl https://www.thecodebase.tech/notes"
alias notes="cat ~/.notes"
add_note() {
    data=$(printf 'note=%s' "$1")
    TOKEN="eyJ1aWQiOjEsInRpbWUiOiIyMDE5LTA1LTAyIDE0OjQ5OjI0LjE2MDMxMCJ9.ehnllVNGn2App8Hz8WiuKkohqFs"
    curl -u "$TOKEN":unused -X POST --data-urlencode "$data" https://www.thecodebase.tech/add_note/
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


task_commit() {
    current_task="20215"
    git commit -m "[$current_task] $1"
}



bitbucket_commit() {
    if [ -z "$1" ]
    then
        echo "Specify branch name"
    else
        gitignore
        git init
        git checkout -b $1
        git add .
        git commit -m "Initial commit"
        module_name=${PWD##*/}
        git remote add origin git@bitbucket.org:sprintit/$module_name.git
        git push -u origin $1
    fi

}


alias cls="tput reset && clear"


fullgitstatus() {
    find . -type d -name '.git' | while read dir ; do sh -c "cd $dir/../ && echo -e \"\nGIT STATUS IN ${dir//\.git/}\" && git status -s" ; done
}


export VISUAL=vim
export EDITOR="$VISUAL"
export FLASK_ENV=development
export ANSIBLE_DEBUG=0


if [ -d "/opt/FlameGraph" ] ; then
    PATH="$PATH:/opt/FlameGraph"
fi

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


fix_origin() {
    REPO_URL=`git remote -v | grep -m1 '^origin' | awk '{ print $2 }'`
    NEW_URL="${REPO_URL/thecodebasesite/elmeriniemela}"
    echo "Changing repo url from "
    echo "  '$REPO_URL'"
    echo "      to "
    echo "  '$NEW_URL'"
    echo ""

    CHANGE_CMD="git remote set-url origin $NEW_URL"
    `$CHANGE_CMD`

    echo "Success"
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
    update_dir
    n=($(grep -Po "(?<=^def )[^_](.*?)\(" $current_dir/install.py | sed 's/(//'))
    COMPREPLY=()

    for i in "${n[@]}"
    do
        if [[ $COMP_CWORD == 1 && $i != "main" && $i == ${COMP_WORDS[COMP_CWORD]}* ]]; then
            COMPREPLY+=($i)
        fi
    done
}

complete -F _bootstrap_linux_completions bootstrap-linux

pull() {
    for d in */ ; do
        folder="$(basename $d)"
        echo $folder
        if [ -d "$folder" ]; then
            cd $folder
            bash /home/elmeri/.config/bootstrap-linux/ssh_origin.sh
            git pull && git submodule update --init
            cd ..
        fi
    done

}

add_access_file() {
    if [ -z "$1" ]; then
        echo "Specify model name (i.e partner_blocking_wizard)"
    else
        mkdir -p security
        if [ ! -f security/ir.model.access.csv ]; then
            echo "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink" > security/ir.model.access.csv
        fi

        rule="access_$1,access_$1,model_$1,base.group_user,1,1,1,1"

        if grep -q "$rule" security/ir.model.access.csv ; then
            echo "$rule exists"
        else
            echo "$rule" >> security/ir.model.access.csv
        fi

        if grep -q "security/ir.model.access.csv" __manifest__.py ; then
            echo "security/ir.model.access.csv in __manifest__.py exists"
        else
            sed -i "/.*data.*:.*\[/a\ \ \ \ \ \ \ \ 'security/ir.model.access.csv'," __manifest__.py
        fi
    fi
}


git_export() {
    if [ -z "$1" ]; then
        echo "Specify module name (i.e web_widget_colorpicker)"
    elif [ -z "$2" ]; then
        echo "Specify branch name (i.e 12.0)"
    else
        git init
        echo "*.pyc" >> .gitignore
        git checkout -b $2
        git add .
        git -c user.email="niemela.elmeri@gmail.com" -c user.name="Elmeri Niemelä" commit -m "Inital Commit"
        git remote add origin https://bitbucket.org/sprintit/$1.git
        git push --set-upstream origin $2
    fi
}

[ -r /usr/bin/neofetch ] &&  /usr/bin/neofetch --disable gpu

stty -ixon
