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
    ratings = db.query(Ratings).all()

    return templates.TemplateResponse(
        request,               # FIRST
        "index.html",          # SECOND
        {
            "request": request,
            "ratings": ratings
        }
    )

@app.post("/users/")
def create_user(username: str, email: str, db: Session = Depends(get_db)):
    new_user = User(username=username, email=email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/users/")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()