#/bin/bash
#-- Script to automate https://help.github.com/articles/why-is-git-always-asking-for-my-password

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

CHANGE_CMD="git remote set-url $REMOTE $NEW_URL"
echo "$CHANGE_CMD"
`$CHANGE_CMD`

echo "Success"