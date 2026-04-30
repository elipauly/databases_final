from database import engine
from models import Base, User, Song, Ratings
from fastapi import FastAPI, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User

Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).all()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "users": users
    })

@app.post("/users/")
def create_user(name: str, email: str, db: Session = Depends(get_db)):
    User = User(name=name, email=email)
    db.add(User)
    db.commit()
    db.refresh(User)
    return User

@app.get("/users/")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()