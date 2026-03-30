-- Schema SQLite — Moltbook Thesis
-- Versione 1.0 — 2026-03-30

CREATE TABLE IF NOT EXISTS agents (
    id          TEXT PRIMARY KEY,       -- UUID dall'API
    name        TEXT UNIQUE NOT NULL,   -- username univoco
    description TEXT,
    karma       INTEGER,
    follower_count   INTEGER,
    following_count  INTEGER,
    avatar_url       TEXT,
    is_claimed       INTEGER,           -- 0/1 (boolean SQLite)
    created_at       TEXT,              -- ISO 8601
    -- Dati owner (solo se is_claimed = 1)
    owner_x_handle        TEXT,
    owner_x_name          TEXT,
    owner_x_follower_count INTEGER,
    owner_x_verified      INTEGER,      -- 0/1
    -- Stats
    posts_count    INTEGER,
    comments_count INTEGER,
    -- Metadata crawling
    fetched_at     TEXT NOT NULL        -- timestamp fetch
);

CREATE TABLE IF NOT EXISTS posts (
    id            TEXT PRIMARY KEY,     -- UUID dall'API
    title         TEXT,
    content       TEXT,
    url           TEXT,
    upvotes       INTEGER,
    downvotes     INTEGER,
    comment_count INTEGER,
    created_at    TEXT,                 -- ISO 8601
    -- Relazioni
    author_name   TEXT,                 -- FK → agents.name
    submolt_name  TEXT,                 -- FK → submolts.name
    -- Metadata crawling
    fetched_at    TEXT NOT NULL,
    comments_fetched INTEGER DEFAULT 0  -- 0/1: commenti già scaricati?
);

CREATE TABLE IF NOT EXISTS comments (
    id          TEXT PRIMARY KEY,       -- UUID dall'API
    content     TEXT,
    parent_id   TEXT,                   -- NULL se primo livello, UUID se reply
    depth       INTEGER,
    upvotes     INTEGER,
    downvotes   INTEGER,
    reply_count INTEGER,
    created_at  TEXT,                   -- ISO 8601
    -- Relazioni
    post_id     TEXT NOT NULL,          -- FK → posts.id
    author_name TEXT,                   -- FK → agents.name
    -- Metadata crawling
    fetched_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS submolts (
    id              TEXT PRIMARY KEY,
    name            TEXT UNIQUE NOT NULL,
    display_name    TEXT,
    description     TEXT,
    subscriber_count INTEGER,
    fetched_at      TEXT NOT NULL
);

-- Indici per performance query frequenti
CREATE INDEX IF NOT EXISTS idx_comments_post_id    ON comments(post_id);
CREATE INDEX IF NOT EXISTS idx_comments_parent_id  ON comments(parent_id);
CREATE INDEX IF NOT EXISTS idx_comments_author     ON comments(author_name);
CREATE INDEX IF NOT EXISTS idx_posts_author        ON posts(author_name);
CREATE INDEX IF NOT EXISTS idx_posts_submolt       ON posts(submolt_name);
