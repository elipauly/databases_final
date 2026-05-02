# databases final, deliverable 5 team 10

instructions to build a local instance

in database.py change DATABASE_URL = "mysql+pymysql://root:password@localhost/myapp"

where root=username, password=password, and myapp=database name
```
pip install fastapi uvicorn sqalchemy pymysql cryptography jinja2 python-multipart
uvicorn main:app --reload
```

Example user log in to start:
Username: Alice
Password: pass1