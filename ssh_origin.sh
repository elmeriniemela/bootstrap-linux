#/bin/bash
#-- Script to automate https://help.github.com/articles/why-is-git-always-asking-for-my-password

REPO_URL=`git remote get-url origin | perl -pe 's|https://.*@|https://|'`
if [ -z "$REPO_URL" ]; then
  echo "-- ERROR:  Could not identify Repo url."
  echo "   It is possible this repo is already using SSH instead of HTTPS."
  exit
fi
HOST=`echo $REPO_URL | sed -Ene's#https://([^/]*)/([^/]*)/([^\.]*)(\.git){0,1}#\1#p'`
USER=`echo $REPO_URL | sed -Ene's#https://([^/]*)/([^/]*)/([^\.]*)(\.git){0,1}#\2#p'`
REPO=`echo $REPO_URL | sed -Ene's#https://([^/]*)/([^/]*)/([^\.]*)(\.git){0,1}#\3#p'`
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
echo "$CHANGE_CMD"
`$CHANGE_CMD`

echo "Success"