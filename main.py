from fastapi.responses import RedirectResponse

from database import engine
from models import Base, User, Song, Ratings
from fastapi import FastAPI, Depends, Request, Form
from fastapi import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
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

def get_current_user(request: Request, db: Session):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.userID == int(user_id)).first()

@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    songs = db.query(Song).options(
        joinedload(Song.ratings).joinedload(Ratings.user),
        joinedload(Song.album)
    ).all()

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "songs": songs,
            "user": user
        }
    )

@app.post("/users/")
def create_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    new_user = User(
        username=username,
        email=email,
        password=password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return RedirectResponse("/login", status_code=303)

@app.get("/users/")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@app.post("/ratings")
def add_rating(
    request: Request,
    song_id: int = Form(...),
    rating: int = Form(...),
    comments: str = Form(""),
    db: Session = Depends(get_db)
):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    new_rating = Ratings(
        userID=int(user_id),
        songID=song_id,
        rating=rating,
        comments=comments
    )

    db.add(new_rating)
    db.commit()

    return RedirectResponse("/", status_code=303)

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html", {"request": request}
    )

@app.post("/login")
def login(
    username: str = Form(...), password:str = Form(...), db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.username == username,
        User.password == password
    ).first()

    if not user:
        return RedirectResponse("/login", status_code=303)
    
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(key="user_id", value=str(user.userID))

    return response

@app.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("user_id")
    return response