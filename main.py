from database import engine, SessionLocal
from models import Base, User, Song, Ratings
from fastapi import FastAPI, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

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
    result = db.execute(text("""
        SELECT * FROM User WHERE userID = :id """)
        , {"id": int(user_id)}).fetchone()
    
    return result
        

@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    result = db.execute(text("""
        SELECT 
            s.songID,
            s.songName,
            a.albumName,
            r.rating,
            r.comments,
            r.userID,
            u.username
        FROM Song s
        LEFT JOIN Album a ON s.albumID = a.albumID
        LEFT JOIN Ratings r ON s.songID = r.songID
        LEFT JOIN User u ON r.userID = u.userID
        ORDER BY s.songID
    """)).fetchall()

    #formatting to frontend
    songs_dict = {}
    for row in result:
        song_id = row.songID

        if song_id not in songs_dict:
            songs_dict[song_id] = {
                "songID": song_id,
                "songName": row.songName,
                "albumName": row.albumName,
                "ratings": []
            }
        if row.rating is not None:
            songs_dict[song_id]["ratings"].append({
                "userID": row.userID,
                "username": row.username,
                "rating": row.rating,
                "comments": row.comments
            })
    songs = list(songs_dict.values())

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
    db.execute(text("""
        INSERT INTO User (username, email, password)
        VALUES (:username, :email, :password)
    """), {
        "username": username,
        "email": email,
        "password": password
    })

    db.commit()

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

    db.execute(text("""
        INSERT INTO Ratings (userID, songID, rating, comments)
        VALUES (:user_id, :song_id, :rating, :comments)
        ON DUPLICATE KEY UPDATE
            rating = :rating,
            comments = :comments
    """), {
        "user_id": int(user_id),
        "song_id": song_id,
        "rating": rating,
        "comments": comments
    })

    db.commit()

    return RedirectResponse("/", status_code=303)

@app.post("/delete-review")
def delete_my_reviews(
    request: Request,
    song_id: int = Form(...),
    db: Session = Depends(get_db)
):
    user_id = request.cookies.get("user_id")
    
    if not user_id:
        return RedirectResponse("/login", status_code=303)
    
    db.execute(text("""
        DELETE FROM Ratings
        WHERE userID = :user_id AND songID = :song_id;
    """), {
        "user_id": int(user_id),
        "song_id": song_id
    })
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
    user = db.execute(text("""
        SELECT * FROM User
        WHERE username = :username AND password = :password
    """), {
        "username": username,
        "password": password
    }).fetchone()

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

@app.get("/friends")
def friends_page(request: Request, db:Session = Depends(get_db)):
    user = get_current_user(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)
    
    friends = db.execute(text ("""
        SELECT 
            u.userID,
            u.username,
            u.email
        FROM Friends f
        JOIN User u ON f.friendID = u.userID
        WHERE f.userID = :user_id
                               
        UNION
                               
        SELECT u.userID, u.username, u.email
        FROM Friends f
        JOIN User u ON f.userID = u.userID
        WHERE f.friendID = :user_id;
    """), {
        "user_id": user.userID
    }).fetchall()

    users = db.execute(text("""
        SELECT userID, username FROM User
        WHERE userID != :user_id
        """), {
            "user_id": user.userID
        }).fetchall()
    return templates.TemplateResponse(
        request,
        "friends.html",
        {
            "request": request,
            "friends": friends,
            "users": users,
            "user": user
        }
    )

@app.post("/add-friend")
def add_friend(
    request: Request,
    friend_id: int = Form(...),
    db: Session = Depends(get_db)
):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)
    
    db.execute(
    text("""
        INSERT INTO Friends (userID, friendID)
        VALUES (:user_id, :friend_id)
    """),
    {
        "user_id": int(user_id),
        "friend_id": friend_id
    }
)

    db.commit()

    return RedirectResponse("/friends", status_code=303)

@app.post("/remove-friend")
def remove_friend(
    request: Request,
    friend_id: int = Form(...),
    db: Session = Depends(get_db)
):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)
    
    db.execute(text("""
        DELETE FROM Friends
        WHERE (userID = :user_id AND friendID = :friend_id)
        OR (userID = :friend_id AND friendID = :user_id)
    """), {
        "user_id": int(user_id),
        "friend_id": friend_id
    })
    db.commit()
    return RedirectResponse("/friends", status_code=303)