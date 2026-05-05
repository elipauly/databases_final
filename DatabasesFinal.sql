CREATE SCHEMA IF NOT EXISTS myapp;
USE myapp;


-- CREATE TABLES

CREATE TABLE User (
    userID INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50),
    email VARCHAR(100),
    password VARCHAR(100)
);
ALTER TABLE User
MODIFY userID INT AUTO_INCREMENT;
ALTER TABLE User
ADD COLUMN isAdmin BOOLEAN DEFAULT FALSE;


CREATE TABLE Friends (
    userID INT,
    friendID INT,
    PRIMARY KEY (userID, friendID),
    FOREIGN KEY (userID) REFERENCES User(userID),
    FOREIGN KEY (friendID) REFERENCES User(userID)
);

CREATE TABLE Album (
    albumID INT PRIMARY KEY AUTO_INCREMENT,
    albumName VARCHAR(100)
);

CREATE TABLE Song (
    songID INT PRIMARY KEY AUTO_INCREMENT,
    songName VARCHAR(100),
    albumID INT,
    FOREIGN KEY (albumID) REFERENCES Album(albumID)
);

CREATE TABLE Artist (
    artistID INT PRIMARY KEY AUTO_INCREMENT,
    artistName VARCHAR(100)
);

CREATE TABLE Ratings (
    userID INT,
    songID INT,
    rating INT,
    comments VARCHAR(255),
    PRIMARY KEY (userID, songID),
    FOREIGN KEY (userID) REFERENCES User(userID),
    FOREIGN KEY (songID) REFERENCES Song(songID)
);

CREATE TABLE AlbumRatings (
	userID INT,
    albumID INT,
    rating INT,
    comments VARCHAR(255),
    PRIMARY KEY (userID, albumID),
    FOREIGN KEY (userID) REFERENCES User(userID),
    FOREIGN KEY (albumID) REFERENCES Album(albumID)
);

CREATE TABLE artistMakesSong (
    artistID INT,
    songID INT,
    PRIMARY KEY (artistID, songID),
    FOREIGN KEY (artistID) REFERENCES Artist(artistID),
    FOREIGN KEY (songID) REFERENCES Song(songID)
);

CREATE TABLE artistMakesAlbum (
    artistID INT,
    albumID INT,
    PRIMARY KEY (artistID, albumID),
    FOREIGN KEY (artistID) REFERENCES Artist(artistID),
    FOREIGN KEY (albumID) REFERENCES Album(albumID)
);


-- TRIGGERS

-- TRIGGER 1: Prevent duplicate friendships, not eligible
DELIMITER //

CREATE TRIGGER before_friend_insert
BEFORE INSERT ON Friends
FOR EACH ROW
BEGIN
	IF NEW.userID = NEW.friendID THEN
		SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'User may not add themselves as a friend';
	END IF;
    IF EXISTS (
        SELECT 1 FROM Friends
        WHERE userID = NEW.userID AND friendID = NEW.friendID
    ) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'This user already friended';
    END IF;
END//

DELIMITER ;


-- TRIGGER 3: Delete old rating before inserting new one NOT USED
DELIMITER //

CREATE TRIGGER before_rating_insert
BEFORE INSERT ON Ratings
FOR EACH ROW
BEGIN
    IF EXISTS (
        SELECT 1 FROM Ratings
        WHERE userID = NEW.userID AND songID = NEW.songID
    ) THEN
        DELETE FROM Ratings
        WHERE userID = NEW.userID AND songID = NEW.songID;
    END IF;
END//

DELIMITER ;

DROP TRIGGER IF EXISTS before_rating_insert;

-- TRIGGER 4: Clamp INSERT rating value between 1 and 5, WOKRING
DELIMITER //

CREATE TRIGGER before_song_rating_validate
BEFORE INSERT ON Ratings
FOR EACH ROW
BEGIN
    IF NEW.rating < 1 THEN
        SET NEW.rating = 1;
    END IF;
    IF NEW.rating > 5 THEN
        SET NEW.rating = 5;
    END IF;
END//

DELIMITER ;

-- TRIGGER 4.5: Clamp INSERT rating value between 1 and 5, WOKRING
DELIMITER //

CREATE TRIGGER before_album_rating_validate
BEFORE INSERT ON AlbumRatings
FOR EACH ROW
BEGIN
    IF NEW.rating < 1 THEN
        SET NEW.rating = 1;
    END IF;
    IF NEW.rating > 5 THEN
        SET NEW.rating = 5;
    END IF;
END//

DELIMITER ;

-- TRIGGER 5: Clamp UPDATE rating value between 1 and 5, WORKING
DELIMITER //

CREATE TRIGGER before_song_rating_update
BEFORE UPDATE ON Ratings
FOR EACH ROW
BEGIN
    IF NEW.rating < 1 THEN
        SET NEW.rating = 1;
    END IF;
    IF NEW.rating > 5 THEN
        SET NEW.rating = 5;
    END IF;
END//

DELIMITER ;

-- TRIGGER 5.5: Clamp UPDATE rating value between 1 and 5, WORKING
DELIMITER //

CREATE TRIGGER before_album_rating_update
BEFORE UPDATE ON AlbumRatings
FOR EACH ROW
BEGIN
    IF NEW.rating < 1 THEN
        SET NEW.rating = 1;
    END IF;
    IF NEW.rating > 5 THEN
        SET NEW.rating = 5;
    END IF;
END//

DELIMITER ;

-- TRIGGER 6: email must be lowercase

DELIMITER //

CREATE TRIGGER before_email_insert
BEFORE INSERT ON User
FOR EACH ROW
BEGIN
    SET NEW.email = LOWER(NEW.email);
END//

DELIMITER ;


-- VIEWS

-- VIEW 1: User View — Current Song List
CREATE VIEW v_CurrentSongs AS
SELECT 
    s.songID,
    s.songName,
    al.albumName,
    ar.artistName,
    ROUND(AVG(r.rating), 2) AS avgRating
FROM Song s
LEFT JOIN Album al ON s.albumID = al.albumID
LEFT JOIN artistMakesSong ams ON s.songID = ams.songID
LEFT JOIN Artist ar ON ams.artistID = ar.artistID
LEFT JOIN Ratings r ON s.songID = r.songID
GROUP BY s.songID, s.songName, al.albumName, ar.artistName;

-- VIEW 2: Admin View — Full Song + Rating Details
CREATE VIEW v_AdminSongDetails AS
SELECT
    s.songID,
    s.songName,
    al.albumName,
    ar.artistName,
    u.username,
    u.email,
    r.rating,
    r.comments
FROM Song s
LEFT JOIN Album al ON s.albumID = al.albumID
LEFT JOIN artistMakesSong ams ON s.songID = ams.songID
LEFT JOIN Artist ar ON ams.artistID = ar.artistID
LEFT JOIN Ratings r ON s.songID = r.songID
LEFT JOIN User u ON r.userID = u.userID;

-- FUNCTION: Calculate average rating for a given song
DELIMITER //

CREATE FUNCTION fn_AvgRating(p_songID INT)
RETURNS DECIMAL(4,2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE avg_rating DECIMAL(4,2);

    SELECT ROUND(AVG(rating), 2)
    INTO avg_rating
    FROM Ratings
    WHERE songID = p_songID;

    IF avg_rating IS NULL THEN
        RETURN 0.00;
    END IF;

    RETURN avg_rating;
END//

DELIMITER ;


-- FUNCTION 2: Calculate average rating for a given album

DELIMITER //

CREATE FUNCTION fn_AvgAlbumRating(p_albumID INT)
RETURNS DECIMAL(4,2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE avg_rating DECIMAL(4,2);

    SELECT ROUND(AVG(rating), 2)
    INTO avg_rating
    FROM AlbumRatings
    WHERE albumID = p_albumID;

    IF avg_rating IS NULL THEN
        RETURN 0.00;
    END IF;

    RETURN avg_rating;
END//

DELIMITER ;

-- PROCEDURE: Add a new user
DELIMITER //

CREATE PROCEDURE sp_AddUser(
    IN p_username VARCHAR(50),
    IN p_email    VARCHAR(100),
    IN p_password VARCHAR(100)
)
BEGIN
    INSERT INTO User (username, email, password)
    VALUES (p_username, p_email, p_password);
END//

DELIMITER ;

-- QUERIES
-- QUERY 1: Show a user's friend list
SELECT 
	u.userID, u.username, u.email FROM Friends f
JOIN User u ON f.friendID = u.userID WHERE f.userID = user_id
					   
UNION
					   
SELECT u.userID, u.username, u.email FROM Friends f
JOIN User u ON f.userID = u.userID WHERE f.friendID = user_id;

-- QUERY 2: Show all of a user's ratings
SELECT 
    v.songName,
    v.albumName,
    v.artistName,
    r.rating AS userRating,
    r.comments,
    fn_AvgRating(r.songID) AS overallAvgRating
FROM Ratings r
JOIN v_CurrentSongs v ON r.songID = v.songID
WHERE r.userID = 1;

SELECT * FROM Ratings;
-- QUERY 3: Artist's average rating
SELECT 
    ar.artistID,
    ar.artistName,
    ROUND(AVG(fn_AvgRating(ams.songID)), 2) AS avgRating
FROM Artist ar
JOIN artistMakesSong ams ON ar.artistID = ams.artistID
GROUP BY ar.artistID, ar.artistName
ORDER BY avgRating DESC;

-- QUERY 4: Total number of ratings on an album
SELECT 
    al.albumID,
    al.albumName,
    COUNT(r.rating) AS totalRatings,
    ROUND(AVG(fn_AvgRating(s.songID)), 2) AS avgRating
FROM Album al
JOIN Song s ON al.albumID = s.albumID
LEFT JOIN Ratings r ON s.songID = r.songID
GROUP BY al.albumID, al.albumName
ORDER BY totalRatings DESC;

-- QUERY 5: All albums a user has rated (subquery)
SELECT DISTINCT
    al.albumID,
    al.albumName
FROM Album al
JOIN Song s ON al.albumID = s.albumID
WHERE s.songID IN (
    SELECT songID
    FROM Ratings
    WHERE userID = 1
);


-- INSERT DATA

INSERT INTO User VALUES
(1, 'alice', 'alice@example.com', 'pass1'),
(2, 'bob', 'bob@example.com', 'pass2'),
(3, 'charlie', 'charlie@example.com', 'pass3'),
(4, 'david', 'david@example.com', 'pass4'),
(5, 'eve', 'eve@example.com', 'pass5');

INSERT INTO Friends VALUES
(1, 2),
(1, 3),
(2, 3),
(3, 4),
(4, 5);

INSERT INTO Album VALUES
(1, 'The Glow, pt. 2'),
(2, 'Blur'),
(3, '1000 Hurts'),
(4, 'The Lonesome Crowded West'),
(5, 'The Piper at the Gates of Dawn');

INSERT INTO Song VALUES
(1, 'I Want Wind to Blow', 1),
(2, 'Song 2', 2),
(3, 'Prayer to God', 3),
(4, 'Heart Cooks Brain', 4),
(5, 'Flaming', 5);

INSERT INTO Artist VALUES
(1, 'The Microphones'),
(2, 'Blur'),
(3, 'Shellac'),
(4, 'Modest Mouse'),
(5, 'Pink Floyd');

INSERT INTO Ratings VALUES
(1, 1, 5, 'Great song'),
(2, 2, 4, 'Nice'),
(3, 3, 3, 'Okay'),
(4, 4, 5, 'Loved it'),
(5, 5, 2, 'Not good');

INSERT INTO artistMakesSong VALUES
(1, 1),
(2, 2),
(3, 3),
(4, 4),
(5, 5);

INSERT INTO artistMakesAlbum VALUES
(1, 1),
(2, 2),
(3, 3),
(4, 4),
(5, 5);

SELECT * FROM Ratings;