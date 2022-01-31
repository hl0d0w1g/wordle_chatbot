DROP DATABASE IF EXISTS wordle;
CREATE DATABASE wordle;
\c wordle;

DROP TABLE IF EXISTS words;
CREATE TABLE words (
	word_id serial PRIMARY KEY,
	word VARCHAR ( 50 ) UNIQUE NOT NULL,
	word_date DATE NOT NULL
);

DROP TABLE IF EXISTS users;
CREATE TABLE users (
	user_id serial PRIMARY KEY,
	user_phone VARCHAR ( 25 ) UNIQUE NOT NULL,
	signup_on TIMESTAMP NOT NULL,
    last_login TIMESTAMP 
);

DROP TABLE IF EXISTS sessions;
CREATE TABLE sessions (
	session_id serial PRIMARY KEY,
    session_date DATE,
    n_tries INT NOT NULL,
    completed BOOLEAN NOT NULL,
    user_id INT NOT NULL,
    FOREIGN KEY (user_id)
      REFERENCES users (user_id)
);

DROP TABLE IF EXISTS results;
CREATE TABLE results (
	result_id serial PRIMARY KEY,
	result_datetime TIMESTAMP NOT NULL,
	color_code VARCHAR ( 5 ) NOT NULL,
	tried_word VARCHAR ( 50 ) NOT NULL,
    session_id INT NOT NULL,
    FOREIGN KEY (session_id)
      REFERENCES sessions (session_id)
);