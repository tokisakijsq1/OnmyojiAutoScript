@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   Tokisaki update script
echo   sync master from upstream runhey/OnmyojiAutoScript
echo ============================================
echo.

REM ---------- STEP 0: environment check ----------
REM NOTE: STEP var must NOT contain parentheses, or %STEP% expansion
REM inside an if-block would close the block early
set "STEP=0/3 environment check"
echo [STEP %STEP%] checking worktree...

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo [ERROR] not a git repo: %cd%
    goto :fail
)

if exist ".git\rebase-merge" (
    echo [ERROR] a previous rebase is still in progress.
    echo        to finish it:   git rebase --continue
    echo        to discard it:  git rebase --abort
    goto :fail
)

REM only tracked-file changes block rebase; untracked files like this script are fine
git diff --quiet --ignore-submodules
if errorlevel 1 (
    echo [ERROR] uncommitted changes found, commit or discard them first:
    git status --short
    goto :fail
)

git remote get-url upstream >nul 2>&1
if errorlevel 1 (
    echo [INFO] adding upstream remote...
    git remote add upstream https://github.com/runhey/OnmyojiAutoScript.git
    if errorlevel 1 goto :fail
)

echo [OK] worktree clean, starting update.
echo.

REM ---------- STEP 1: fetch upstream ----------
set "STEP=1/3 fetch upstream - git fetch upstream master"
echo [STEP %STEP%]
git fetch upstream master
if errorlevel 1 (
    echo [ERROR] fetch failed, check network or proxy.
    goto :fail
)
echo [OK] upstream master fetched.
echo.

REM ---------- STEP 2: rebase onto upstream master ----------
set "STEP=2/3 rebase - git rebase upstream/master"
echo [STEP %STEP%]
git rebase upstream/master
if errorlevel 1 (
    echo.
    echo [ERROR] rebase conflict, stopped at: %STEP%
    echo        conflicted files:
    git diff --name-only --diff-filter=U
    echo.
    echo        how to resolve, choose one:
    echo        A. fix conflicts in the files above, then run:
    echo              git add .
    echo              git rebase --continue
    echo           then run this script again.
    echo        B. discard this update, restore to previous state:
    echo              git rebase --abort
    goto :fail
)
echo [OK] rebase done, Tokisaki is now on top of latest upstream.
echo.

REM ---------- STEP 3: show result ----------
set "STEP=3/3 done"
echo [STEP %STEP%] last 5 commits on current branch:
echo.
git log --oneline -5
echo.
echo ============================================
echo   Update finished! Local is up to date.
echo ============================================
pause
exit /b 0

:fail
echo.
echo ============================================
echo   Script stopped at step: %STEP%
echo   Check the error messages above.
echo ============================================
pause
exit /b 1
