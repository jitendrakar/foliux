@echo off
cd /d "G:\My Drive\NETPROFIT\FOLIUX"
echo [%date% %time%] Starting Stock News Sync... >> stock_news_sync.log
python -u manage.py process_stock_news --fetch-only --days 3 >> stock_news_sync.log 2>&1
echo [%date% %time%] Completed with exit code %ERRORLEVEL% >> stock_news_sync.log
