from database import engine, SessionLocal
from models import Base, User, Song, Ratings
from fastapi import FastAPI, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

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

    #song rating list
    song_result = db.execute(text("""
        SELECT 
            s.songID,
            s.songName,
            a.albumName,
            ur.rating AS userRating,
            ur.comments AS userComments,
            
            fn_AvgRating(s.songID) AS avgRating,
                
            r.rating,
            r.comments,
            r.userID,
            u.username,
                                  
            fr.rating as friendRating,
            fr.comments as friendComments,
            fu.username as friendUsername                
        FROM Song s
        LEFT JOIN Album a ON s.albumID = a.albumID
        LEFT JOIN Ratings ur ON s.songID = ur.songID AND ur.userID = :user_id
        LEFT JOIN Ratings r 
            ON s.songID = r.songID
            AND r.userID NOT IN (
                SELECT friendID FROM Friends WHERE userID = :user_id
            )
            AND r.userID != :user_id

        LEFT JOIN User u ON r.userID = u.userID
        LEFT JOIN Ratings fr 
            ON s.songID = fr.songID 
            AND fr.userID IN (
                SELECT friendID FROM Friends WHERE userID = :user_id
            )
        LEFT JOIN User fu ON fr.userID = fu.userID                        
        ORDER BY s.songID
    """), {
        "user_id": user.userID if user else -1
    }).fetchall()

    #formatting to frontend
    songs_dict = {}
    for row in song_result:
        song_id = row.songID

        if song_id not in songs_dict:
            songs_dict[song_id] = {
                "songID": song_id,
                "songName": row.songName,
                "albumName": row.albumName,
                "ratings": [],
                "friendRatings": [],
                "userRating": row.userRating,
                "userComments": row.userComments,
                "avgRating": row.avgRating
            }
        if row.rating is not None:
            songs_dict[song_id]["ratings"].append({
                "userID": row.userID,
                "username": row.username,
                "rating": row.rating,
                "comments": row.comments
            })

        if row.friendRating is not None:
            existing = songs_dict[song_id]["friendRatings"]
            if not any(fr["username"] == row.friendUsername for fr in existing):
                existing.append({
                    "username": row.friendUsername,
                    "rating": row.friendRating,
                    "comments": row.friendComments
                })
    songs = list(songs_dict.values())

    #album rating list
    album_result = db.execute(text("""
        SELECT 
            s.albumID,
            s.albumName,
            ar.artistName,
            ur.rating AS userRating,
            ur.comments AS userComments,
            
            fn_AvgAlbumRating(s.albumID) AS avgRating,
                
            r.rating,
            r.comments,
            r.userID,
            u.username,
                                  
            fr.rating as friendRating,
            fr.comments as friendComments,
            fu.username as friendUsername                
        FROM Album s
        LEFT JOIN artistMakesAlbum ama ON s.albumID = ama.albumID
        LEFT JOIN Artist ar ON ama.artistID = ar.artistID
        LEFT JOIN AlbumRatings ur ON s.albumID = ur.albumID AND ur.userID = :user_id
        LEFT JOIN AlbumRatings r 
            ON s.albumID = r.albumID
            AND r.userID NOT IN (
                SELECT friendID FROM Friends WHERE userID = :user_id
            )
            AND r.userID != :user_id

        LEFT JOIN User u ON r.userID = u.userID
        LEFT JOIN AlbumRatings fr 
            ON s.albumID = fr.albumID 
            AND fr.userID IN (
                SELECT friendID FROM Friends WHERE userID = :user_id
            )
        LEFT JOIN User fu ON fr.userID = fu.userID                        
        ORDER BY s.albumID                           
    """), {
        "user_id": user.userID if user else -1
    }).fetchall()

    albums_dict = {}
    for row in album_result:
        if row.albumID not in albums_dict:
            albums_dict[row.albumID] = {
                "albumID": row.albumID,
                "albumName": row.albumName,
                "artistName": row.artistName,
                "ratings": [],
                "friendRatings": [],
                "userRating": row.userRating,
                "userComments": row.userComments,
                "avgRating": row.avgRating
            }

        if row.friendRating is not None:
            existing = albums_dict[row.albumID]["friendRatings"]
            if not any(fr["username"] == row.friendUsername for fr in existing):
                existing.append({
                    "username": row.friendUsername,
                    "rating": row.friendRating,
                    "comments": row.friendComments
                })

        if row.rating is not None:
            existing = albums_dict[row.albumID]["ratings"]
            if not any(r["userID"] == row.userID for r in existing):
                existing.append({
                    "userID": row.userID,
                    "username": row.username,
                    "rating": row.rating,
                    "comments": row.comments
            })


    albums = list(albums_dict.values())

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "songs": songs,
            "albums": albums,
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
def users_page(request: Request, db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT userID, username, email
        FROM User
        ORDER BY userID
    """)).mappings().all()

    created_email = request.query_params.get("email")

    return templates.TemplateResponse(
        request,
        "users.html",
        {
            "request": request,
            "users": result,
            "created_email": created_email
        }
    )

@app.post("/users/add")
def add_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    db.execute(text("""
        CALL sp_AddUser(:username, :email, :password)
    """), {
        "username": username,
        "email": email,
        "password": password
    })

    db.commit()

    return RedirectResponse("/users?created=1&email=" + email, status_code=303)

#song ratings
@app.post("/ratings")
def add_rating(
    request: Request,
    song_id: int = Form(...),
    rating: int = Form(...),
    comments: str = Form(""),
    db: Session = Depends(get_db)
):
    user_id = request.cookies.get("user_id")
    user_id = int(user_id) if user_id else -1
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

#album ratings
@app.post("/album-ratings")
def add_album_rating(
    request: Request,
    album_id: int = Form(...),
    rating: int = Form(...),
    comments: str = Form(""),
    db: Session = Depends(get_db)
):
    user_id = request.cookies.get("user_id")

    if not user_id:
        return RedirectResponse("/login", status_code=303)

    db.execute(text("""
        INSERT INTO AlbumRatings (userID, albumID, rating, comments)
        VALUES (:user_id, :album_id, :rating, :comments)
        ON DUPLICATE KEY UPDATE
            rating = :rating,
            comments = :comments
    """), {
        "user_id": int(user_id),
        "album_id": album_id,
        "rating": rating,
        "comments": comments
    })

    db.commit()

    return RedirectResponse("/", status_code=303)

@app.post("/delete-album-review")
def delete_album_reviews(
    request: Request,
    album_id: int = Form(...),
    db: Session = Depends(get_db)
):
    user_id = request.cookies.get("user_id")
    
    if not user_id:
        return RedirectResponse("/login", status_code=303)
    
    db.execute(text("""
        DELETE FROM AlbumRatings
        WHERE userID = :user_id AND albumID = :album_id;
    """), {
        "user_id": int(user_id),
        "album_id": album_id
    })
    db.commit()
    return RedirectResponse("/", status_code=303)

#my ratings
@app.get("/my-ratings")
def my_ratings(request: Request, db: Session = Depends(get_db)):
    user_id=request.cookies.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)
    
    song_results = db.execute(text("""
        SELECT 
            v.songName,
            v.albumName,
            v.artistName,
            r.rating AS userRating,
            r.comments,
            fn_AvgRating(r.songID) AS overallAvgRating
        FROM Ratings r
        LEFT JOIN v_CurrentSongs v ON r.songID = v.songID
        WHERE r.userID = :user_id;                       
    """), {
        "user_id": user_id
    }).fetchall()
    album_results = db.execute(text("""
        SELECT 
                al.albumName,
                GROUP_CONCAT(ar.artistName SEPARATOR ', ') AS artistName,
                r.rating AS userRating,
                r.comments,
                fn_AvgAlbumRating(r.albumID) AS overallAvgRating
            FROM AlbumRatings r
            JOIN Album al ON r.albumID = al.albumID
            LEFT JOIN artistMakesAlbum ama ON al.albumID = ama.albumID
            LEFT JOIN Artist ar ON ama.artistID = ar.artistID
            WHERE r.userID = :user_id
            GROUP BY al.albumID, r.rating, r.comments;                                               
        """), {
            "user_id": user_id
    }).fetchall()                                
    return templates.TemplateResponse(
        request,
        "my_ratings.html",
        {
            "request":request,
            "song_ratings": song_results,
            "album_ratings": album_results
        }
    )


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
def friends_page(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")

    if not user_id:
        return RedirectResponse("/login", status_code=303)

    error = request.query_params.get("error")

    friends = db.execute(text("""
        SELECT u.userID, u.username
        FROM Friends f
        JOIN User u ON f.friendID = u.userID
        WHERE f.userID = :user_id
    """), {"user_id": int(user_id)}).mappings().all()

    available_users = db.execute(text("""
    SELECT userID, username, email
    FROM User
    WHERE userID != :user_id
    AND userID NOT IN (
        SELECT friendID FROM Friends WHERE userID = :user_id
    )
"""), {"user_id": int(user_id)}).mappings().all()
    

    error = request.query_params.get("error")
    return templates.TemplateResponse(
        request,
        "friends.html",
        {
            "request": request,
            "friends": friends,
            "available_users": available_users,
            "error": error
        }
    )

@app.post("/add-friend")
async def add_friend(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    user_id = int(request.cookies.get("user_id"))
    friend_id = int(form.get("friend_id"))

    try:
        db.execute(text("""
            INSERT INTO Friends (userID, friendID)
            VALUES (:user_id, :friend_id)
        """), {
            "user_id": user_id,
            "friend_id": friend_id
        })
        db.commit()

        return RedirectResponse("/friends", status_code=303)

    except OperationalError as e:
        db.rollback()

        error_msg = str(e.orig.args[1]) if e.orig.args else "Unknown error"

        return RedirectResponse(
            f"/friends?error={error_msg}",
            status_code=303
    )
    error = request.query_params.get("error")

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