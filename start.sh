source env/bin/activate
VERBOSE=1 uvicorn app.main:app --host 0.0.0.0
