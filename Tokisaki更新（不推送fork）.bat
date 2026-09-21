@echo off
setlocal EnableDelayedExpansion
rem ============================================================
rem  Tokisaki 更新工具（使用者用，不推送 fork）
rem  流程: master 拉官方仓库最新 -> 拉取 Tokisaki fork 最新分支
rem        -> rebase 到最新 master 上
rem  兼容三种初始状态:
rem    A. 官方 easy-install 装的纯 master -> 自动从 fork 拉分支
rem    B. 用「Tokisaki自动化脚本安装.bat」装好的 -> 直接更新
rem    C. fork 有新提交 -> rebase 到最新 master 上
rem ============================================================

set "GIT=%~dp0toolkit\Git\cmd\git.exe"
if not exist "%GIT%" set "GIT=%~dp0toolkit\Git\mingw64\bin\git.exe"
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
set "PATH=%~dp0toolkit\Git\cmd;%~dp0toolkit\Git\mingw64\bin;%PATH%"

cd /d "%~dp0"

echo.
echo ============================================
echo   Tokisaki 更新工具（不推送 fork）
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
    echo [错误] 卡在网络检测：
    echo        - gitcode（官方仓库）连接失败，且
    echo        - GitHub（Tokisaki fork）代理/直连都不通。
    echo        请检查网络（必要时开启代理软件）后重新运行本脚本。
    goto :fail
)
echo        网络方案: !NET_DESC!
echo.

echo [1/4] 检查未提交改动...
rem 首次引导（纯 master 安装）时没有 Tokisaki 分支，也没有本地改动需要保护，跳过检查
"%GIT%" show-ref --verify --quiet refs/heads/%BRANCH%
if errorlevel 1 goto :bootstrap
set DIRTY=
for /f "delims=" %%i in ('"%GIT%" status --porcelain --untracked-files=no') do set DIRTY=1
if defined DIRTY (
    echo [错误] 有未提交的改动，请先提交或撤销。
    echo         运行 "git status" 查看具体文件。
    goto :fail
)
:bootstrap

echo.
echo [2/4] 更新 master（官方仓库 gitcode，一般可直连）...
"%GIT%" remote set-url origin %OFFICIAL%
if errorlevel 1 goto :fail
"%GIT%" checkout master
if errorlevel 1 goto :fail
"%GIT%" !GIT_PROXY_ARGS_OFFICIAL! pull --ff-only origin master
if errorlevel 1 (
    echo.
    echo [错误] 卡在步骤2：从官方仓库 gitcode 拉取 master 失败。
    echo        可能原因: 网络波动 / gitcode 临时不可访问。
    echo        请稍后重试本脚本。
    goto :fail
)

echo.
echo [3/4] 获取 Tokisaki 分支最新代码（来自 GitHub fork）...
"%GIT%" show-ref --verify --quiet refs/heads/%BRANCH%
if errorlevel 1 (
    echo        本地还没有 %BRANCH% 分支，从 Tokisaki 的 fork 拉取...
    "%GIT%" remote add fork %FORK_URL% 2>nul
    "%GIT%" !GIT_PROXY_ARGS_FORK! fetch fork %BRANCH%
    if errorlevel 1 (
        echo.
        echo [错误] 卡在步骤3：从 GitHub fork 拉取 %BRANCH% 失败。
        echo        探测到的网络方案: !NET_DESC!
        echo        GitHub 需要能访问：请开启代理后重试。
        goto :fail
    )
    "%GIT%" checkout -b %BRANCH% --track fork/%BRANCH%
    if errorlevel 1 goto :fail
    goto :rebase_step
)
rem 已有分支：检查 fork remote，拉最新
"%GIT%" remote get-url fork >nul 2>&1 || "%GIT%" remote add fork %FORK_URL%
"%GIT%" !GIT_PROXY_ARGS_FORK! fetch fork %BRANCH%
if errorlevel 1 (
    echo.
    echo [错误] 卡在步骤3：从 GitHub fork 获取最新 %BRANCH% 失败。
    echo        探测到的网络方案: !NET_DESC!
    echo        请开启代理后重试（本地代码不受影响）。
    goto :fail
)
"%GIT%" checkout %BRANCH%
if errorlevel 1 goto :fail
rem fork 上有新提交就合并进来（fast-forward，无本地分叉时安全）
for /f "delims=" %%c in ('"%GIT%" rev-list %BRANCH%..fork/%BRANCH% 2^>nul') do set "FORK_NEW=1"
if defined FORK_NEW (
    echo        fork 有新提交，合并到本地...
    "%GIT%" merge --ff-only fork/%BRANCH%
    if errorlevel 1 (
        echo [警告] 本地分支与 fork 出现分叉，无法 fast-forward。
        echo        将以 fork 最新代码为准（本地独有提交会被保留在 reflog 里）。
        echo        如需人工处理请运行: git rebase fork/%BRANCH%
        "%GIT%" reset --hard fork/%BRANCH%
    )
) else (
    echo        fork 无新提交，使用本地分支。
)

:rebase_step
echo.
echo [4/4] 将 %BRANCH% rebase 到最新 master 上...
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

rem ---------- 网络探测 ----------
rem gitcode（官方 master）一般国内直连；github（fork）按 代理->直连 逐级探测
:detect_network
set "NET_OK="
set "GIT_PROXY_ARGS_OFFICIAL="
set "GIT_PROXY_ARGS_FORK="
set "NET_DESC="

rem 1) 仓库里已配置的 github 代理
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
rem github 的访问方式
if defined PROXY (
    set "GIT_PROXY_ARGS_FORK=-c http.https://github.com.proxy=%PROXY% -c credential.helper=wincred"
    set "NET_DESC=GitHub 使用代理 %PROXY%"
) else (
    rem 无代理：实测 github 直连，通则直连，不通则仍按直连走（由报错告知用户）
    "%GIT%" -c http.https://github.com.proxy= ls-remote --heads %FORK_URL% %BRANCH% >nul 2>&1
    if not errorlevel 1 (
        set "GIT_PROXY_ARGS_FORK=-c http.https://github.com.proxy= -c credential.helper=wincred"
        set "NET_DESC=GitHub 直连（无代理）"
    ) else (
        set "GIT_PROXY_ARGS_FORK=-c credential.helper=wincred"
        set "NET_DESC=GitHub 代理/直连均不通（将失败，见下方报错）"
    )
)
rem gitcode 官方仓库：始终直连（gitcode 无需代理）
"%GIT%" -c http.https://gitcode.com.proxy= ls-remote --heads %OFFICIAL% master >nul 2>&1
if errorlevel 1 (
    echo [警告] gitcode（官方仓库）当前无法连接，master 更新将失败。
)
set "NET_OK=1"
goto :eof

:test_proxy
rem %1 = 代理地址；curl 走该代理访问 github 成功返回 0
if "%~1"=="" exit /b 1
curl -s --connect-timeout 3 --max-time 8 -x "%~1" -o NUL -w "%%{http_code}" https://github.com 2>nul | findstr "200 301 302" >nul
exit /b %errorlevel%
