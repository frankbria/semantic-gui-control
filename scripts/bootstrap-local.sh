#!/usr/bin/env bash
set -euo pipefail

mkdir -p "$HOME/projects/semantic-gui-control"
cp -R . "$HOME/projects/semantic-gui-control"
cd "$HOME/projects/semantic-gui-control"

git init

git add .
git commit -m "Initialize semantic GUI control specs"

printf '\nLocal repo created at %s\n' "$HOME/projects/semantic-gui-control"
printf 'To create and push the GitHub repo with gh CLI:\n'
printf '  gh repo create frankbria/semantic-gui-control --private --source=. --remote=origin --push\n'
printf 'or for public:\n'
printf '  gh repo create frankbria/semantic-gui-control --public --source=. --remote=origin --push\n'
