@echo off
chcp 65001 >nul
REM NeoDev Docker 容器交互式更新脚本
REM 支持选择性更新服务

:MENU
cls
echo ==========================================
echo   NeoDev Docker 容器管理
echo ==========================================
echo.
echo 请选择操作：
echo.
echo   1. 完整更新（停止 + 重新构建 + 启动）
echo   2. 仅重新构建镜像（不停止容器）
echo   3. 仅重启容器（不重新构建）
echo   4. 停止所有容器
echo   5. 启动所有容器
echo   6. 查看容器状态
echo   7. 查看实时日志
echo   8. 清理并重置（删除数据卷）
echo   0. 退出
echo.
set /p choice="请输入选项 (0-8): "

if "%choice%"=="1" goto FULL_UPDATE
if "%choice%"=="2" goto BUILD_ONLY
if "%choice%"=="3" goto RESTART_ONLY
if "%choice%"=="4" goto STOP
if "%choice%"=="5" goto START
if "%choice%"=="6" goto STATUS
if "%choice%"=="7" goto LOGS
if "%choice%"=="8" goto CLEAN
if "%choice%"=="0" goto EXIT
echo 无效选项，请重新选择
timeout /t 2 >nul
goto MENU

:FULL_UPDATE
echo.
echo ========================================
echo   执行完整更新
echo ========================================
echo.
echo [1/3] 停止现有容器...
docker compose down
echo.
echo [2/3] 重新构建镜像（不使用缓存）...
docker compose build --no-cache
if errorlevel 1 (
    echo.
    echo 构建失败！
    pause
    goto MENU
)
echo.
echo [3/3] 启动容器...
docker compose up -d
echo.
echo 等待服务启动...
timeout /t 5 /nobreak >nul
echo.
echo 容器状态：
docker compose ps
echo.
echo ========================================
echo   更新完成！
echo ========================================
echo.
echo 访问地址：
echo   - 前端: http://localhost:80
echo   - API: http://localhost:80/api
echo   - Neo4j: http://localhost:7474
echo.
pause
goto MENU

:BUILD_ONLY
echo.
echo ========================================
echo   仅重新构建镜像
echo ========================================
echo.
docker compose build --no-cache
if errorlevel 1 (
    echo.
    echo 构建失败！
    pause
    goto MENU
)
echo.
echo 构建完成！使用选项 3 重启容器以应用更新。
pause
goto MENU

:RESTART_ONLY
echo.
echo ========================================
echo   重启容器
echo ========================================
echo.
docker compose restart
echo.
echo 容器状态：
docker compose ps
echo.
pause
goto MENU

:STOP
echo.
echo ========================================
echo   停止所有容器
echo ========================================
echo.
docker compose down
echo.
echo 所有容器已停止
pause
goto MENU

:START
echo.
echo ========================================
echo   启动所有容器
echo ========================================
echo.
docker compose up -d
echo.
echo 等待服务启动...
timeout /t 5 /nobreak >nul
echo.
echo 容器状态：
docker compose ps
echo.
pause
goto MENU

:STATUS
echo.
echo ========================================
echo   容器状态
echo ========================================
echo.
docker compose ps
echo.
echo 最近日志（最后 20 行）：
docker compose logs --tail=20
echo.
pause
goto MENU

:LOGS
echo.
echo ========================================
echo   实时日志（按 Ctrl+C 退出）
echo ========================================
echo.
docker compose logs -f
goto MENU

:CLEAN
echo.
echo ========================================
echo   清理并重置
echo ========================================
echo.
echo 警告：此操作将删除所有数据卷（数据库数据、仓库数据等）！
echo.
set /p confirm="确认删除所有数据？(yes/no): "
if not "%confirm%"=="yes" (
    echo 已取消
    pause
    goto MENU
)
echo.
echo 停止并删除容器和数据卷...
docker compose down -v
echo.
echo 清理完成！
pause
goto MENU

:EXIT
echo.
echo 再见！
exit /b 0
