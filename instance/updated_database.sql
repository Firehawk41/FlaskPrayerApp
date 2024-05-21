CREATE TABLE "user" (
    id SERIAL PRIMARY KEY,
    firstname VARCHAR(100) NOT NULL,
    lastname VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(128) NOT NULL
);

CREATE TABLE tag (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE prayer (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    answered BOOLEAN,
    archived BOOLEAN,
    created_at TIMESTAMP,
    last_modified TIMESTAMP,
    answered_at TIMESTAMP,
    tag_id INTEGER NOT NULL,
    FOREIGN KEY(user_id) REFERENCES "user" (id),
    FOREIGN KEY(tag_id) REFERENCES tag (id)
);

CREATE TABLE prayer_history (
    id SERIAL PRIMARY KEY,
    prayer_id INTEGER NOT NULL,
    date_prayed TIMESTAMP,
    FOREIGN KEY(prayer_id) REFERENCES prayer (id)
);

INSERT INTO "user" (id, firstname, lastname, email, password)
VALUES
(1, 'Jamie', 'Thomson', 'jamiemrt@gmail.com', '243262243132245a4b59493157356163666a49725479667a72464c5a4f334343376f6934684e75535451726347446c6c74364e4f6f476e67574e4653'),
(2, 'Rubi', 'Thomson', 'rubi.thomson@email.com', '243262243132244a513957497747536d4e746e374764312f64683334753177506b4d61506a466b5130635a4e7479305453423167736a4a3172667257'),
(3, 'Olivia', 'Thomson', 'olivia.thomson@email.com', '243262243132242f4c6c7630446c523966696a5330383544534438512e504f74756a62464f68427631644172564766704b667252506145626e555057');

INSERT INTO tag (id, name)
VALUES
(1, 'Petition'),
(2, 'Protection'),
(3, 'Thanksgiving'),
(4, 'Healing');

INSERT INTO prayer (id, user_id, title, description, answered, archived, created_at, last_modified, answered_at, tag_id)
VALUES
(2, 1, 'Safe travels', 'Lord, please guide me safely to my destination today.', FALSE, FALSE, '2024-04-16 20:57:14.604112', '2024-04-18 13:23:23.964762', '2024-04-18 13:23:23.964762', 1),
(3, 1, 'Bodie''s health', 'Lord, please heal Bodie and comfort his family.', TRUE, FALSE, '2024-04-16 20:57:14.604112', '2024-04-19 22:42:32.587796', '2024-04-19 22:42:32.587796', 4),
(4, 2, 'friends and toys', 'thankyou for friends and we get to play together. and thankyou for my toys.', FALSE, FALSE, '2024-04-19 22:42:32.587796', '2024-04-19 22:42:32.587796', NULL, 3);

INSERT INTO prayer_history (id, prayer_id, date_prayed)
VALUES
(2, 2, '2024-04-16 20:57:14.604112'),
(3, 3, '2024-04-17 16:50:18.487607'),
(4, 3, '2024-04-19 14:53:03.235701'),
(5, 2, '2024-04-19 14:53:03.235701');

