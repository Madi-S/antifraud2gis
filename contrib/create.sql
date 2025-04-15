CREATE TABLE company (
    oid TEXT PRIMARY KEY,
    title TEXT,
    address TEXT,
    town TEXT,
    searchstr TEXT,
    rating_2gis REAL,
    trusted BOOLEAN,
    nreviews INTEGER,
    detections TEXT
);
