@echo off
:: Production startup script for AI Email Agent for Salesforce (Windows version)

echo Starting AI Email Agent for Salesforce in production mode

:: Set default values if not provided in environment
if "%PORT%"=="" set PORT=8000
if "%WORKERS%"=="" set WORKERS=4
if "%LOG_LEVEL%"=="" set LOG_LEVEL=INFO

echo Port: %PORT%, Workers: %WORKERS%, Log Level: %LOG_LEVEL%

:: Run with Uvicorn for production
uvicorn main:app --host 0.0.0.0 --port %PORT% --workers %WORKERS% --log-level %LOG_LEVEL% --proxy-headers --forwarded-allow-ips *

pause
