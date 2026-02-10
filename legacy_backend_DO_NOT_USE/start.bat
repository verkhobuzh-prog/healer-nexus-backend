@echo off
set PYTHONPATH=.
set GEMINI_API_KEY=???_????_???
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
