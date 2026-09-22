@echo off
rem ---------- 防闪退保护 ----------
rem 如果脚本遇到 cmd 解析级致命错误（如“此时不应有...”）窗口会直接消失；
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
rem  Tokisaki 自动化脚本安装（新机器一键安装）
rem  在一个空的文件夹里运行本脚本，它会：
rem    1. 下载官方 easy-install 包（toolkit: Python 3.10 + Git）
rem    2. 通过 GitHub 克隆 Tokisaki 分支（fix/mumu-adb-root）
rem       直连失败时自动尝试多个国内加速镜像
rem    3. 修改 config/deploy.yaml（AutoUpdate=false）
rem    4. 下载并解压 oasx.exe（新版界面）
rem    4b. 同步本脚本旁边的 oas.exe（旧版界面，git 不跟踪它）
rem    5. 用阿里云镜像安装 Python 依赖
rem  以后更新：双击「Tokisaki更新（不推送fork）.bat」
rem ============================================================

rem ---------- 固定设置 ----------
set "BRANCH=fix/mumu-adb-root"
set "FORK=https://github.com/tokisakijsq1/OnmyojiAutoScript.git"
set "OFFICIAL=https://gitcode.com/OnmyojiAutoScript/OnmyojiAutoScript.git"
set "EASY_RAR_URL=https://github.com/runhey/OnmyojiAutoScript/releases/download/oas-install-v1.0.0/OnmyojiAutoScript-easy-install.rar"
set "OASX_API=https://api.github.com/repos/runhey/OASX/releases/latest"
set "OASX_DL_PREFIX=https://github.com/runhey/OASX/releases/download"
set "DL_DIR=%TEMP%\tokisaki_oas_install"

rem ---------- 网络设置 ----------
rem PROXY：留空表示自动探测；也可以手动填 http://127.0.0.1:7890 这样的地址
rem 探测顺序：手动指定 -> 常见代理端口(7890/7897/10809/10808/47890) -> 系统代理设置 -> 直连
rem GitHub 访问顺序：代理 -> 直连 -> ghproxy.net 镜像 -> gh-proxy.com 镜像
set "PROXY="
set "GH_MIRROR_1=https://ghproxy.net/"
set "GH_MIRROR_2=https://gh-proxy.com/"

rem 清理可能干扰 bundled git 的继承环境变量
set "GIT_EXEC_PATH="
set "GIT_DIR="
set "GIT_WORK_TREE="
set "GIT_INDEX_FILE="
set "GIT_EDITOR="
set "GIT_PAGER=cat"

cd /d "%~dp0"
set "ROOT=%CD%"

echo.
echo ============================================
echo   Tokisaki 自动化脚本安装
echo   目标目录: %ROOT%
echo ============================================
echo.

rem ---------- 0. 基础检查 ----------
if exist "%ROOT%\script.py" (
    echo [错误] 当前目录已经是 OAS 项目目录，请把本脚本放到一个**空的**新文件夹里再运行。
    goto :fail
)

where curl >nul 2>&1
if errorlevel 1 (
    echo [错误] 系统缺少 curl（Win10 1803+ 自带），无法下载文件。
    goto :fail
)
where powershell >nul 2>&1
if errorlevel 1 (
    echo [错误] 系统缺少 powershell，无法解压 zip。
    goto :fail
)

mkdir "%DL_DIR%" 2>nul

rem ---------- 网络探测 ----------
call :detect_network
if not defined NET_OK (
    echo.
    echo [错误] 网络探测失败：既没有可用代理，GitHub 直连也不通，镜像站也连不上。
    echo        卡在这一步说明：本机无法访问 GitHub。
    echo        请先开启代理软件（或检查代理端口），再重新运行本脚本。
    goto :fail
)
echo.
echo        网络方案: !NET_DESC!
echo.

rem ---------- 1. toolkit: python + git ----------
rem 注意: 不使用括号块。从括号块内部 call 的子例程，其中的延迟扩展(!var!)、
rem      括号和重定向都会被父块解析器破坏，所以这里全部用 goto 结构。
if exist "%ROOT%\toolkit\python.exe" goto :toolkit_ready
echo [1/5] 下载官方 easy-install 包（toolkit: Python 3.10 + Git）...
if exist "%DL_DIR%\easy.rar" goto :easy_downloaded
call :download_file "%EASY_RAR_URL%" "%DL_DIR%\easy.rar" 65
if errorlevel 1 (
    echo [错误] easy-install 包下载失败（卡在步骤1）。
    echo        已尝试: 代理/直连/镜像 全部失败。请检查网络后重试。
    goto :fail
)
goto :easy_checked
:easy_downloaded
echo       复用上次下载的 easy.rar
:easy_checked
for %%A in ("%DL_DIR%\easy.rar") do set "EASY_SIZE=%%~zA"
if !EASY_SIZE! LSS 1000000 (
    echo [错误] easy.rar 下载不完整（!EASY_SIZE! 字节），删除后重试。
    del "%DL_DIR%\easy.rar"
    goto :fail
)
echo        解压 toolkit 到项目目录（需几分钟）...
call :unrar "%DL_DIR%\easy.rar" "%DL_DIR%"
if errorlevel 1 goto :fail
if not exist "%DL_DIR%\OnmyojiAutoScript-easy-install\toolkit\python.exe" (
    echo [错误] 解压后未找到 toolkit，解压失败。
    goto :fail
)
robocopy "%DL_DIR%\OnmyojiAutoScript-easy-install\toolkit" "%ROOT%\toolkit" /E /NFL /NDL /NJH /NJS >nul
if !ERRORLEVEL! GEQ 8 (
    echo [错误] 复制 toolkit 失败（robocopy 代码 !ERRORLEVEL!）。
    goto :fail
)
echo        toolkit 就绪。
goto :toolkit_done
:toolkit_ready
echo [1/5] toolkit 已存在，跳过下载。
:toolkit_done

set "GIT=%ROOT%\toolkit\Git\cmd\git.exe"
if not exist "%GIT%" set "GIT=%ROOT%\toolkit\Git\mingw64\bin\git.exe"
if not exist "%GIT%" (
    echo [错误] toolkit 里没有 git.exe。
    goto :fail
)
set "PYTHON=%ROOT%\toolkit\python.exe"
set "PATH=%ROOT%\toolkit\Git\cmd;%ROOT%\toolkit\Git\mingw64\bin;%PATH%"

rem 给 bundled git 配好代理与凭据（写进新克隆仓库的全局配置）
call :setup_git_env

rem ---------- 2. clone Tokisaki 分支 ----------
echo.
echo [2/5] 克隆 Tokisaki 分支（%BRANCH%）...
echo        方式A: git 直连/代理克隆...
"%GIT%" clone --branch %BRANCH% "%FORK%" "%ROOT%" 2>nul
if not errorlevel 1 goto :clone_ok
echo        方式A失败，方式B: 通过镜像站下载分支压缩包...
call :clone_via_mirror
if not errorlevel 1 goto :clone_ok
echo.
echo [错误] 卡在步骤2：无法从 GitHub 获取 Tokisaki 分支。
echo        已尝试: git克隆（代理/直连）+ 镜像下载（ghproxy.net / gh-proxy.com）。
echo        请确认代理可用后重新运行（已下载的 toolkit 不会重复下载）。
goto :fail
:clone_ok
"%GIT%" -C "%ROOT%" remote set-url origin %OFFICIAL%
echo        已克隆，并把 origin 指回官方仓库（更新走官方 master）。
"%GIT%" -C "%ROOT%" log --oneline -3

rem ---------- 3. patch deploy.yaml ----------
echo.
echo [3/5] 修改 config\deploy.yaml（AutoUpdate=false）...
if not exist "%ROOT%\config\deploy.yaml" (
    echo [提示] 仓库里没有 config\deploy.yaml（正常：它是本地文件），正在生成...
    if not exist "%ROOT%\config" mkdir "%ROOT%\config"
    if exist "%DL_DIR%\OnmyojiAutoScript-easy-install\config\deploy.yaml" (
        copy /y "%DL_DIR%\OnmyojiAutoScript-easy-install\config\deploy.yaml" "%ROOT%\config\deploy.yaml" >nul
    ) else (
        echo.
        echo [提示] 没有找到官方 deploy.yaml 模板（easy-install 包里的那份）。
        echo        请选择：
        echo          Y = 我自己去获取模板。脚本先停在这里，
        echo              把 deploy.yaml 放到 config\deploy.yaml 后重新运行即可继续。
        echo          N = 先用 master 的默认配置生成一份。
        echo              这份只保证能启动，设备、模拟器等配置需要你之后自己改。
        echo.
        %SystemRoot%\System32\choice.exe /c YN /m "没有模板，是否改为自己获取"
        if errorlevel 2 goto :deploy_use_default
        echo.
        echo [暂停] 请自行获取 deploy.yaml，放到下面这个位置后重新运行本脚本：
        echo        %ROOT%\config\deploy.yaml
        goto :fail
    )
)
goto :deploy_ready
:deploy_use_default
echo        按 master 默认配置生成，之后请自行修改 config\deploy.yaml。
call :write_deploy_template "%ROOT%\config\deploy.yaml"
:deploy_ready
> "%TEMP%\tokisaki_patch_deploy.ps1" echo $p = '%ROOT%\config\deploy.yaml'
>> "%TEMP%\tokisaki_patch_deploy.ps1" echo $t = Get-Content $p -Raw
>> "%TEMP%\tokisaki_patch_deploy.ps1" echo $t = $t -replace '(?m)^(\s*AutoUpdate:\s*)true\s*$', '$1false'
>> "%TEMP%\tokisaki_patch_deploy.ps1" echo [IO.File]::WriteAllText($p, $t)
powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\tokisaki_patch_deploy.ps1"
del "%TEMP%\tokisaki_patch_deploy.ps1" >nul 2>&1
findstr /r /c:"AutoUpdate: *false" "%ROOT%\config\deploy.yaml" >nul
if errorlevel 1 (
    echo [错误] AutoUpdate 修改失败，请手动把 config\deploy.yaml 里 AutoUpdate 改为 false。
    goto :fail
)
echo        AutoUpdate: false  已生效（exe 启动时不再自动更新）。

rem ---------- 4. oasx.exe ----------
echo.
echo [4/5] 下载最新 oasx.exe（新版界面）...
set "OASX_VER="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "(Invoke-RestMethod '%OASX_API%').tag_name"`) do set "OASX_VER=%%i"
if "%OASX_VER%"=="" (
    echo [警告] 查询 OASX 最新版本失败，回退到已知版本 v0.3.2。
    set "OASX_VER=v0.3.2"
)
echo        版本: %OASX_VER%
call :download_file "%OASX_DL_PREFIX%/%OASX_VER%/oasx_%OASX_VER%_windows.zip" "%DL_DIR%\oasx.zip" 10
if errorlevel 1 (
    echo [错误] 卡在步骤4：oasx 下载失败（代理/直连/镜像都已尝试）。
    goto :fail
)
echo        解压 oasx 到项目根目录...
if exist "%DL_DIR%\oasx_unpack" rmdir /s /q "%DL_DIR%\oasx_unpack"
mkdir "%DL_DIR%\oasx_unpack"
powershell -NoProfile -Command "Expand-Archive -Force '%DL_DIR%\oasx.zip' '%DL_DIR%\oasx_unpack'"
if errorlevel 1 (
    echo [错误] oasx 解压失败。
    goto :fail
)
robocopy "%DL_DIR%\oasx_unpack" "%ROOT%" /E /NFL /NDL /NJH /NJS >nul
if !ERRORLEVEL! GEQ 8 (
    echo [错误] 解压内容复制到项目目录失败。
    goto :fail
)
if not exist "%ROOT%\oasx.exe" (
    echo [错误] 未找到 oasx.exe。
    goto :fail
)
echo        oasx.exe 就绪。

echo.
echo [4b] 同步 oas.exe（旧版界面）...
rem oas.exe 被 .gitignore 排除，克隆带不过去，只能从本脚本旁边复制
if not exist "%~dp0oas.exe" (
    echo [提示] 本脚本旁边没有 oas.exe，跳过。旧版界面需要的话，把它和本脚本放在一起后重新运行。
    goto :oas_done
)
rem 源和目标是同一个文件时（脚本就放在项目目录里）不要复制，否则 copy 会把文件截断
if /i "%~dp0"=="%ROOT%\" goto :oas_done
if exist "%ROOT%\oas.exe" del "%ROOT%\oas.exe"
copy /y "%~dp0oas.exe" "%ROOT%\" >nul
if exist "%ROOT%\oas.exe" (
    echo        oas.exe 已同步。
) else (
    echo [警告] oas.exe 复制失败，旧版界面不可用，oasx.exe 不受影响。
)
:oas_done

rem ---------- 5. python dependencies ----------
echo.
echo [5/5] 安装 Python 依赖（用阿里云镜像，约几分钟）...
"%PYTHON%" -m pip install -r "%ROOT%\requirements.txt" -i https://mirrors.aliyun.com/pypi/simple/ --no-warn-script-location
if errorlevel 1 (
    echo        阿里云镜像失败，改用清华镜像重试...
    "%PYTHON%" -m pip install -r "%ROOT%\requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple --no-warn-script-location
    if errorlevel 1 (
        echo [错误] 卡在步骤5：依赖安装失败（阿里云/清华镜像都不通）。
        echo        可稍后手动执行:
        echo        "%PYTHON%" -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
        goto :fail
    )
)

echo.
echo ============================================
echo   安装完成！
echo   双击 oasx.exe 即可启动（首次启动较慢）。
echo   以后更新：双击 Tokisaki更新（不推送fork）.bat
echo ============================================
echo.
%SystemRoot%\System32\choice.exe /c YN /t 30 /d Y /m "是否现在删除下载缓存（%DL_DIR%）"
if errorlevel 2 goto :keep
rmdir /s /q "%DL_DIR%"
:keep
pause
exit /b 0

:fail
echo.
echo 安装已中止。已完成的步骤不会重复执行，修复问题后重新运行本脚本即可。
pause
exit /b 1

rem ============================================================
rem  辅助函数
rem ============================================================

rem ---------- 网络探测：设置 GIT_PROXY_ARGS / CURL_PROXY_ARGS / NET_DESC / NET_OK ----------
:detect_network
set "NET_OK="
set "GIT_PROXY_ARGS="
set "CURL_PROXY_ARGS="

rem 1) 手动指定的代理优先
if defined PROXY (
    call :test_proxy "!PROXY!"
    if errorlevel 1 (
        echo [警告] 手动指定的代理 !PROXY! 不可用，尝试自动探测...
        set "PROXY="
    )
)
rem 2) 常见本地代理端口
for %%P in (7890 7897 10809 10808 47890 33210) do (
    if not defined PROXY (
        call :test_proxy "http://127.0.0.1:%%P"
        if not errorlevel 1 set "PROXY=http://127.0.0.1:%%P"
    )
)
rem 3) Windows 系统代理设置
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
:proxy_probe_done
if defined PROXY (
    set "NET_OK=1"
    set "GIT_PROXY_ARGS=-c http.https://github.com.proxy=%PROXY% -c credential.helper=wincred"
    set "CURL_PROXY_ARGS=-x %PROXY%"
    set "NET_DESC=使用代理 %PROXY%"
    goto :detect_github
)

rem 4) 直连测试
call :test_direct
if not errorlevel 1 (
    set "NET_OK=1"
    set "GIT_PROXY_ARGS=-c credential.helper=wincred"
    set "CURL_PROXY_ARGS="
    set "NET_DESC=直连（无代理）"
    goto :detect_github
)

rem 5) 代理和直连都不通，测镜像站
curl -s --connect-timeout 8 --max-time 15 -o NUL -w "%%{http_code}" "https://ghproxy.net/https://raw.githubusercontent.com/runhey/OASX/master/README.md" 2>nul | findstr "200" >nul
if not errorlevel 1 (
    set "NET_OK=1"
    set "GIT_PROXY_ARGS=-c credential.helper=wincred"
    set "CURL_PROXY_ARGS="
    set "NET_DESC=直连 GitHub 不通，使用镜像站下载"
    goto :detect_github
)
goto :eof

rem ---------- test_proxy <地址>：curl 走该代理访问 github，成功返回 0 ----------
:test_proxy
if "%~1"=="" exit /b 1
curl -s --connect-timeout 3 --max-time 8 -x "%~1" -o NUL -w "%%{http_code}" https://github.com 2>nul | findstr "200 301 302" >nul
exit /b %errorlevel%

rem ---------- test_direct：无代理直连 github 端点，成功返回 0 ----------
:test_direct
curl -s --connect-timeout 8 --max-time 15 -o NUL -w "%%{http_code}" "https://github.com/tokisakijsq1/OnmyojiAutoScript.git/info/refs?service=git-upload-pack" 2>nul | findstr "200 301 302" >nul
exit /b %errorlevel%

:detect_github
rem 记录 GitHub 可达方式：DIRECT / MIRROR（供 clone 和下载选择）
set "GH_MODE=MIRROR"
if defined PROXY (
    set "GH_MODE=PROXY"
    goto :eof
)
curl -s --connect-timeout 8 --max-time 15 -o NUL -w "%%{http_code}" "https://github.com/tokisakijsq1/OnmyojiAutoScript.git/info/refs?service=git-upload-pack" 2>nul | findstr "200 301 302" >nul
if not errorlevel 1 set "GH_MODE=DIRECT"
goto :eof

rem ---------- setup_git_env: 克隆完成后给仓库写持久配置 ----------
:setup_git_env
if defined PROXY (
    "%GIT%" config --global http.https://github.com.proxy "%PROXY%"
    echo        已为 git 配置 GitHub 代理: %PROXY%
)
"%GIT%" config --global credential.https://github.com.helper wincred
"%GIT%" config --global core.longpaths true
goto :eof

rem ---------- download_file url out min_size ----------
rem 按 GH_MODE 依次尝试：PROXY/DIRECT 直链 -> 镜像1 -> 镜像2
:download_file
set "URL=%~1"
set "OUT=%~2"
set "MINSZ=%~3"
rem 用 call %%VAR%% 而不是 !VAR!：本函数会被括号块内的 call 调用，延迟扩展在那里会被拆碎
if defined CURL_PROXY_ARGS call curl -sL %%CURL_PROXY_ARGS%% --connect-timeout 15 --max-time 600 -o "%OUT%" "%URL%"
if not defined CURL_PROXY_ARGS curl -sL --connect-timeout 15 --max-time 600 -o "%OUT%" "%URL%"
call :check_size "%OUT%" %MINSZ%
if not errorlevel 1 goto :dl_ok
echo        直链下载失败，尝试镜像1...
curl -sL --connect-timeout 15 --max-time 600 -o "%OUT%" "%GH_MIRROR_1%%URL%"
call :check_size "%OUT%" %MINSZ%
if not errorlevel 1 goto :dl_ok
echo        镜像1失败，尝试镜像2...
curl -sL --connect-timeout 15 --max-time 600 -o "%OUT%" "%GH_MIRROR_2%%URL%"
call :check_size "%OUT%" %MINSZ%
if not errorlevel 1 goto :dl_ok
echo        镜像2也失败。
exit /b 1
:dl_ok
echo        下载完成: %OUT%
exit /b 0

:check_size
rem 用 PowerShell 比较文件大小：cmd 的 set /a 是 32 位有符号算术，对几十 MB 的文件会溢出。
rem 结果写成标记文件而不是靠 errorlevel：本函数会被括号块内的 call 调用，errorlevel 不可靠。
set "F=%~1"
set "MIN=%~2"
del "%TEMP%\tokisaki_size_ok" 2>nul
powershell -NoProfile -Command "if((Get-Item -LiteralPath '%F%' -ErrorAction SilentlyContinue).Length -ge [int64]%MIN%*1000000){New-Item -Path $env:TEMP\tokisaki_size_ok -ItemType File -Force | Out-Null}"
if exist "%TEMP%\tokisaki_size_ok" exit /b 0
if exist "%F%" del "%F%"
exit /b 1

rem ---------- clone_via_mirror: 镜像下载分支 tar.gz 并还原成 git 仓库 ----------
:clone_via_mirror
set "TAR=%DL_DIR%\branch.tar.gz"
call :download_file "https://github.com/tokisakijsq1/OnmyojiAutoScript/archive/refs/heads/%BRANCH%.tar.gz" "%TAR%" 1
if errorlevel 1 exit /b 1
rem 校验 gzip 完整性（下载被截断时文件大小仍可能通过下限检查）
"%PYTHON%" -c "import gzip,sys; gzip.open(sys.argv[1],'rb').read()" "%TAR%" >nul 2>&1
if errorlevel 1 (
    echo        下载的压缩包不完整（可能是下载中断），请重新运行本脚本。
    del "%TAR%"
    exit /b 1
)
if exist "%DL_DIR%\branch_unpack" rmdir /s /q "%DL_DIR%\branch_unpack"
mkdir "%DL_DIR%\branch_unpack"
rem 注: Windows 自带 bsdtar 在中文系统（GBK 代码页）下解压含中文文件名的 tar.gz 会失败，
rem     所以优先用 toolkit 自带的 Python 解压（按 UTF-8 处理文件名，稳定可靠）。
"%PYTHON%" -c "import tarfile; tarfile.open(r'%TAR%').extractall(r'%DL_DIR%\branch_unpack')"
if errorlevel 1 (
    echo        Python 解压失败，回退 tar...
    tar -xzf "%TAR%" -C "%DL_DIR%\branch_unpack" 2>nul
    if errorlevel 1 (
        echo        镜像包解压失败。
        exit /b 1
    )
)
set "SRC="
for /d %%D in ("%DL_DIR%\branch_unpack\*") do set "SRC=%%D"
if not defined SRC (
    echo        解压内容为空。
    exit /b 1
)
mkdir "%ROOT%" 2>nul
robocopy "%SRC%" "%ROOT%" /E /NFL /NDL /NJH /NJS /NP > "%TEMP%\tokisaki_robocopy.log"
if errorlevel 8 exit /b 1
rem 把快照还原成 git 仓库（保留完整历史，方便后续更新/rebase）
"%GIT%" -C "%ROOT%" init -q
"%GIT%" -C "%ROOT%" remote add fork "%FORK%"
"%GIT%" -C "%ROOT%" remote add origin "%OFFICIAL%"
rem 代理下一次拉 50 个提交容易被中断（early EOF），先浅拉再逐步加深，并重试
"%GIT%" -C "%ROOT%" -c http.version=HTTP/1.1 fetch --depth=1 fork %BRANCH%
if errorlevel 1 "%GIT%" -C "%ROOT%" -c http.version=HTTP/1.1 fetch --depth=1 fork %BRANCH%
if errorlevel 1 exit /b 1
"%GIT%" -C "%ROOT%" -c http.version=HTTP/1.1 fetch --deepen=50 fork %BRANCH%
rem checkout 会因工作区已有解压文件而拒绝覆盖，所以先把 HEAD 指到目标分支名，
rem 再用 reset --hard 对齐内容（内容就是这个提交的快照，不会丢失任何东西）
"%GIT%" -C "%ROOT%" symbolic-ref HEAD refs/heads/%BRANCH%
if errorlevel 1 (
    echo        无法创建分支 %BRANCH%。
    exit /b 1
)
"%GIT%" -C "%ROOT%" reset --hard FETCH_HEAD
if errorlevel 1 (
    echo        git 仓库还原失败。
    exit /b 1
)
exit /b 0

rem ---------- unrar file outdir ----------
rem 尝试常见位置的 WinRAR/7-Zip 解压 easy.rar（RAR5 需要 UnRAR 5+）
:unrar
set "UNRAR="
for %%P in (
    "D:\WinRAR\UnRAR.exe"
    "C:\Program Files\WinRAR\UnRAR.exe"
    "C:\Program Files (x86)\WinRAR\UnRAR.exe"
    "C:\Program Files\7-Zip\7z.exe"
    "C:\Program Files (x86)\7-Zip\7z.exe"
) do (
    if exist %%P if not defined UNRAR set "UNRAR=%%~P"
)
if defined UNRAR goto :unrar_found
echo [错误] 卡在解压步骤：本机没有找到 WinRAR/7-Zip。
echo        请安装 WinRAR 或 7-Zip 后重新运行本脚本（已下载的 easy.rar 会复用）。
exit /b 1
:unrar_found
echo        使用解压工具: !UNRAR!
if "!UNRAR!"=="C:\Program Files\7-Zip\7z.exe" goto :unrar_7z
if "!UNRAR!"=="C:\Program Files (x86)\7-Zip\7z.exe" goto :unrar_7z
"!UNRAR!" x -y "%~1" "OnmyojiAutoScript-easy-install\toolkit\*.*" "OnmyojiAutoScript-easy-install\config\*.*" "%~2\" >nul
if errorlevel 1 echo [错误] 解压失败（!UNRAR!）。 & exit /b 1
exit /b 0
:unrar_7z
"!UNRAR!" x -y -o"%~2" "%~1" "OnmyojiAutoScript-easy-install\toolkit\*" "OnmyojiAutoScript-easy-install\config\*" >nul
if errorlevel 1 echo [错误] 解压失败（!UNRAR!）。 & exit /b 1
exit /b 0

rem ---------- write_deploy_template outfile ----------
rem 用户选择“用 master 默认配置”时写出最小 deploy.yaml，之后需用户自行修改。
rem 关键项与官方模板一致：官方仓库、master、关闭自动更新、使用自带 git。
:write_deploy_template
> "%~1" echo Deploy:
>> "%~1" echo   Git:
>> "%~1" echo     Repository: https://e.coding.net/onmyojiautoscript/oas/OnmyojiAutoScript.git
>> "%~1" echo     Branch: master
>> "%~1" echo     GitExecutable: ./toolkit/Git/mingw64/bin/git.exe
>> "%~1" echo     GitProxy: null
>> "%~1" echo     SSLVerify: true
>> "%~1" echo     AutoUpdate: false
>> "%~1" echo   Python:
>> "%~1" echo     PythonExecutable: ./toolkit/python.exe
>> "%~1" echo     PypiMirror: https://pypi.tuna.tsinghua.edu.cn/simple
>> "%~1" echo     RequirementsFile: requirements.txt
>> "%~1" echo   Adb:
>> "%~1" echo     AdbExecutable: ./toolkit/Lib/site-packages/adbutils/binaries/adb.exe
>> "%~1" echo     AdbConnect: null
>> "%~1" echo     Device: null
>> "%~1" echo     ScreenshotMethod: ADB
>> "%~1" echo     ControlMethod: ADB
>> "%~1" echo   OCR:
>> "%~1" echo     OcrClient: null
>> "%~1" echo   Update:
>> "%~1" echo     GitExecutable: ./toolkit/Git/mingw64/bin/git.exe
exit /b 0
