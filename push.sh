#!/bin/bash


#Get the current branch name
BRANCH=$(git rev-parse --abbrev-ref HEAD)

#Define a default commit message
COMMIT_MESSAGE="Auto Commit - $(date "+%Y-%m-%d %H:%M:%S")"

echo "Checking Status......"
git status

echo "Adding Changes......"
git add .

echo "Committing Changes..."
git commit -m "$COMMIT_MESSAGE"

echo "Pushing to origin/$BRANCH..."
git push -u origin "$BRANCH"

echo "Done!"