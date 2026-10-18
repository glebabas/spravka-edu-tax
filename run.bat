@echo off
chcp 65001 >nul
title SpravkaEduTax — Генератор справок КНД 1151158

echo =====================================================================
echo  Запуск Генератора справок об оплате образовательных услуг (КНД 1151158)
echo =====================================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден! Установите Python 3.10+ с сайта python.org
    pause
    exit /b 1
)

echo [1/2] Проверка зависимостей...
pip install -r requirements.txt --quiet

echo [2/2] Запуск веб-приложения...
echo.
python app.py

pause
