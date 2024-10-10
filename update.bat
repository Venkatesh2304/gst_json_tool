@echo on
REM Stash changes in Git
git stash

REM Pull the latest changes with fast-forward
git pull --ff

pause
