@echo off
rem ---------- 防闪退保护 ----------
rem 若脚本遇到 cmd 解析级致命错误，窗口会直接消失；
rem 这里用 cmd /k 重新启动自身，保证出错后窗口仍然保留，可以看到完整错误信息。
if not defined TOK_GUARD (
    set "TOK_GUARD=1"
    echo.
    echo [防护] 正在以保护模式启动脚本...
    echo （若脚本遇到致命错误，本窗口不会自动关闭，可完整查看错误信息）
    echo.
    cmd /k ""%~f0""
    exit /b 0
)
setlocal EnableDelayedExpansion
rem ============================================================
rem  Tokisaki 更新工具（发布者用，更新 master 并推送到自己的 fork）
rem  流程: 检查未提交改动 -> master 拉官方仓库最新
rem        -> 本地分支 rebase 到 master 上
rem        -> 拉 fork 最新分支(防止强推覆盖新提交)
rem        -> 推送到 GitHub fork（朋友们从这里拉取）
rem  注意: 本脚本需要你的 GitHub 凭据和可用的代理/网络。
rem
rem  本脚本只存在于功能分支，checkout master 会把它从工作区删掉，
rem  cmd 读不到下一行就会报「找不到批处理文件」。因此从仓库里启动时
rem  先复制到 %TEMP% 再执行副本；副本不在仓库里，切分支不会把它删掉。
rem ============================================================

rem 仓库根目录：从仓库内启动时就是脚本所在目录；从 %TEMP% 副本启动时由 TOK_REPO 传入
if not defined TOK_REPO set "TOK_REPO=%~dp0"
if "!TOK_REPO:~-1!"=="\" set "TOK_REPO=!TOK_REPO:~0,-1!"

rem 还在仓库目录里时，改从临时副本执行，避免 checkout master 删掉正在运行的脚本
echo "%~f0" | findstr /I /C:"%TEMP%\\" >nul
if errorlevel 1 (
    set "TOK_COPY=%TEMP%\tokisaki-push-fork.bat"
    copy /Y "%~f0" "!TOK_COPY!" >nul
    if errorlevel 1 (
        echo [错误] 无法把脚本复制到临时目录: !TOK_COPY!
        echo        checkout master 会删除仓库里的本脚本，不能直接在仓库内继续。
        pause
        exit /b 1
    )
    echo.
    echo [防护] 已复制到临时目录再执行，避免切换 master 时脚本被删掉。
    echo.
    rem cmd /k 是新进程，不会继承这里的 setlocal 变量，仓库路径必须写进启动命令
    cmd /k "set TOK_REPO=!TOK_REPO!&& "!TOK_COPY!""
    exit /b 0
)

set "GIT=%TOK_REPO%\toolkit\Git\cmd\git.exe"
if not exist "%GIT%" set "GIT=%TOK_REPO%\toolkit\Git\mingw64\bin\git.exe"
set "BRANCH=fix/mumu-adb-root"
set "OFFICIAL=https://gitcode.com/OnmyojiAutoScript/OnmyojiAutoScript.git"
set "FORK_URL=https://github.com/tokisakijsq1/OnmyojiAutoScript.git"

rem 清理可能干扰 bundled git 的继承环境变量
set "GIT_EXEC_PATH="
set "GIT_DIR="
set "GIT_WORK_TREE="
set "GIT_INDEX_FILE="
set "GIT_EDITOR="
set "GIT_PAGER=cat"

rem Bundled git 的 remote helper 在 mingw64\bin，必须加入 PATH
set "PATH=%TOK_REPO%\toolkit\Git\cmd;%TOK_REPO%\toolkit\Git\mingw64\bin;%PATH%"

cd /d "%TOK_REPO%"

echo.
echo ============================================
echo   Tokisaki 更新工具（更新 master 并推送 fork）
echo ============================================
echo.

if not exist "%GIT%" (
    echo [错误] 未找到 git: %GIT%
    echo        请先在本项目目录运行（toolkit 文件夹必须存在）。
    goto :fail
)

rem ---------- 网络探测 ----------
call :detect_network
if not defined NET_OK (
    echo.
    echo [错误] 卡在网络检测：代理不可用且 GitHub 直连不通。
    echo        请开启代理软件后重试。
    goto :fail
)
echo        网络方案: !NET_DESC!
echo.

echo [1/5] 检查未提交改动...
set DIRTY=
for /f "delims=" %%i in ('"%GIT%" status --porcelain --untracked-files=no') do set DIRTY=1
if defined DIRTY (
    echo [错误] 有未提交的改动，请先提交或撤销。
    echo         运行 "git status" 查看具体文件。
    goto :fail
)

echo.
echo [2/5] 更新 master（官方仓库 gitcode）...
"%GIT%" remote set-url origin %OFFICIAL%
if errorlevel 1 goto :fail
"%GIT%" checkout master
if errorlevel 1 goto :fail
"%GIT%" !GIT_PROXY_ARGS! pull --ff-only origin master
if errorlevel 1 (
    echo.
    echo [错误] 卡在步骤2：从官方仓库 gitcode 拉取 master 失败。
    echo        gitcode 国内一般可直连；失败多为网络波动，请重试本脚本。
    goto :fail
)

echo.
echo [3/5] 将 %BRANCH% 分支 rebase 到最新 master 上...
"%GIT%" checkout %BRANCH%
if errorlevel 1 goto :fail
"%GIT%" rebase master
if errorlevel 1 (
    echo.
    echo [错误] rebase 出现冲突，请手动处理：
    echo   1. 编辑冲突文件后: "%GIT%" add ^<文件^>
    echo   2. 继续 rebase:    "%GIT%" rebase --continue
    echo   或放弃 rebase:     "%GIT%" rebase --abort
    echo 处理完成前不要再次运行本脚本。
    goto :fail
)

echo.
echo [4/5] 拉取 fork 上 %BRANCH% 的最新状态（防止强推覆盖新提交）...
"%GIT%" remote add fork %FORK_URL% 2>nul
"%GIT%" !GIT_PROXY_ARGS! fetch fork %BRANCH%
if errorlevel 1 (
    echo [警告] 拉取 fork 失败（网络问题）。将直接尝试推送；如推送被拒绝请重试。
    goto :push
)
rem fork 上有本地没有的提交时提示（推送仍会执行，只是不静默强推）
for /f "delims=" %%c in ('"%GIT%" rev-list %BRANCH%..fork/%BRANCH% 2^>nul') do (
    echo [警告] fork 上存在本地没有的提交: %%c
    echo        推送将使用 --force-with-lease 覆盖。如需保留请先手动合并。
)

:push
echo.
echo [5/5] 推送到 GitHub fork（朋友们从这里拉取）...
"%GIT%" !GIT_PROXY_ARGS! push --force-with-lease fork %BRANCH%
if errorlevel 1 (
    echo.
    echo [错误] 卡在步骤5：推送到 fork 失败。
    echo        常见原因:
    echo          - 代理没开或端口不对（本脚本探测到的方案: !NET_DESC!）
    echo          - GitHub 凭据失效: 运行 git config --global credential.helper wincred
    echo            然后手动执行: git push -f fork %BRANCH%
    echo        本地分支是完好的，只有 fork 落后了。
    goto :fail
)

echo.
echo [完成] 当前提交:
"%GIT%" log --oneline -5
echo.
echo 全部完成。请手动启动 OAS（oasx.exe）。
%SystemRoot%\System32\timeout.exe /t 5 /nobreak >nul
exit /b 0

:fail
echo.
echo 已中止。
pause
exit /b 1

rem ---------- 网络探测（与安装脚本同一套逻辑） ----------
:detect_network
set "NET_OK="
set "GIT_PROXY_ARGS="
set "NET_DESC="

rem 1) 仓库里已配置的代理
for /f "tokens=2 delims==" %%p in ('"%GIT%" config --get http.https://github.com.proxy 2^>nul') do set "PROXY=%%p"
if defined PROXY (
    call :test_proxy "%PROXY%"
    if not errorlevel 1 goto :dn_done
    echo [提示] 仓库配置的代理 %PROXY% 不可用，尝试自动探测...
    set "PROXY="
)
rem 2) 常见本地代理端口
for %%P in (7890 7897 10809 10808 47890 33210) do (
    if not defined PROXY (
        call :test_proxy "http://127.0.0.1:%%P"
        if not errorlevel 1 set "PROXY=http://127.0.0.1:%%P"
    )
)
rem 3) Windows 系统代理
if not defined PROXY (
    for /f "tokens=3" %%a in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable 2^>nul ^| findstr ProxyEnable') do set "SYS_ENABLE=%%a"
    for /f "tokens=3" %%a in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer 2^>nul ^| findstr ProxyServer') do set "SYS_PROXY=%%a"
    if defined SYS_ENABLE if "!SYS_ENABLE!"=="0x1" if defined SYS_PROXY (
        echo !SYS_PROXY! | findstr "=" >nul && (for /f "tokens=2 delims==" %%b in ("!SYS_PROXY!") do set "SYS_PROXY=%%b")
        echo !SYS_PROXY! | findstr "http" >nul || set "SYS_PROXY=http://!SYS_PROXY!"
        call :test_proxy "!SYS_PROXY!"
        if not errorlevel 1 set "PROXY=!SYS_PROXY!"
    )
)
:dn_done
if defined PROXY (
    set "NET_OK=1"
    set "GIT_PROXY_ARGS=-c http.https://github.com.proxy=%PROXY% -c credential.helper=wincred"
    set "NET_DESC=使用代理 %PROXY%"
    goto :eof
)
rem 4) 直连 github（git 协议端点实测）
"%GIT%" -c http.https://github.com.proxy= -c credential.helper=wincred ls-remote --heads %FORK_URL% %BRANCH% >nul 2>&1
if not errorlevel 1 (
    set "NET_OK=1"
    set "GIT_PROXY_ARGS=-c http.https://github.com.proxy= -c credential.helper=wincred"
    set "NET_DESC=直连 GitHub（无代理）"
    goto :eof
)
goto :eof

:test_proxy
rem %1 = 代理地址；curl 走该代理访问 github 成功返回 0
if "%~1"=="" exit /b 1
curl -s --connect-timeout 3 --max-time 8 -x "%~1" -o NUL -w "%%{http_code}" https://github.com 2>nul | findstr "200 301 302" >nul
exit /b %errorlevel%
