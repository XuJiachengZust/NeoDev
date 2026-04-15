@echo off
REM NeoDev Docker 容器更新脚本（Windows 批处理版本）
REM 用途：重新构建并启动所有 Docker 容器

echo ==========================================
echo   NeoDev Docker 容器更新
echo ==========================================
echo.

REM 1. 停止现有容器
echo ^>^>^> 停止现有容器...
docker compose down

REM 2. 重新构建镜像（强制不使用缓存）
echo.
echo ^>^>^> 重新构建镜像...
docker compose build --no-cache

REM 3. 启动容器
echo.
echo ^>^>^> 启动容器...
docker compose up -d

REM 4. 等待服务健康检查
echo.
echo ^>^>^> 等待服务启动...
timeout /t 5 /nobreak >nul

REM 5. 显示容器状态
echo.
echo ^>^>^> 容器状态：
docker compose ps

REM 6. 显示日志（最后 20 行）
echo.
echo ^>^>^> 最近日志：
docker compose logs --tail=20

echo.
echo ==========================================
echo   更新完成！
echo ==========================================
echo.
echo 访问地址：
echo   - 前端: http://localhost:80
echo   - API: http://localhost:80/api
echo   - Neo4j: http://localhost:7474
echo.
echo 查看日志: docker compose logs -f
echo 停止服务: docker compose down
echo.
pause
