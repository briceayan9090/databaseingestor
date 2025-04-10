CREATE DATABASE mydatabase;
\c mydatabase;

CREATE TABLE IF NOT EXISTS mytable (
    id SERIAL PRIMARY KEY,
    some_column VARCHAR(255)
);

INSERT INTO mytable (some_column) VALUES ('Initial Value 1');
INSERT INTO mytable (some_column) VALUES ('Initial Value 2');

-- You can add more table creations, user grants, etc., here