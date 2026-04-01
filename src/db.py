"""
db.py — Gestione del database SQLite

Questo modulo si occupa di tutto ciò che riguarda il database:
    - Inizializzazione delle tabelle (leggendo schema.sql)
    - Inserimento e aggiornamento di agenti, post, commenti e submolt
    - Query di supporto al crawler (es. "quali post non hanno ancora i commenti?")
    - Stampa delle statistiche finali

Tutti gli altri moduli usano questo file per interagire col DB,
senza mai scrivere SQL direttamente.
"""

import sqlite3
import os
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """
    Apre e restituisce una connessione al database SQLite.
    Usa row_factory per accedere alle colonne per nome (es. row["id"])
    invece che per indice numerico.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Crea tutte le tabelle definite in schema.sql, se non esistono già.
    Viene chiamata all'avvio del crawler. È idempotente: può essere
    chiamata più volte senza sovrascrivere dati esistenti.
    """
    schema_path = os.path.join(os.path.dirname(__file__), "..", "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = f.read()
    with get_connection() as conn:
        conn.executescript(schema)
    print(f"[DB] Database inizializzato: {DB_PATH}")


# ── Agenti ────────────────────────────────────────────────────────────────────

def agent_exists(name: str) -> bool:
    """
    Controlla se un agente è già presente nel database.
    Usato dal crawler per evitare fetch duplicati.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM agents WHERE name = ?", (name,)
        ).fetchone()
        return row is not None


def upsert_agent(data: dict):
    """
    Inserisce un agente nel database. Se esiste già (stesso name),
    aggiorna solo i campi che cambiano nel tempo: karma, follower_count,
    following_count, is_claimed, posts_count, comments_count.

    Il campo 'owner' è presente solo se l'agente è claimed (is_claimed=True)
    e contiene i dati pubblici del profilo X/Twitter del proprietario umano.

    NOTA: l'API restituisce i dati agente dentro la chiave 'agent',
    es: { "success": true, "agent": { ... } }
    """
    # L'API wrappa i dati in una chiave "agent"
    agent = data.get("agent", data)
    owner = agent.get("owner") or {}   # può essere null se non claimed
    stats = agent.get("stats") or {}   # contatori post e commenti

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO agents (
                id, name, description, karma, follower_count, following_count,
                avatar_url, is_claimed, created_at,
                owner_x_handle, owner_x_name, owner_x_follower_count, owner_x_verified,
                posts_count, comments_count, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(name) DO UPDATE SET
                karma            = excluded.karma,
                follower_count   = excluded.follower_count,
                following_count  = excluded.following_count,
                is_claimed       = excluded.is_claimed,
                posts_count      = excluded.posts_count,
                comments_count   = excluded.comments_count,
                fetched_at       = excluded.fetched_at
        """, (
            agent.get("id"),
            agent.get("name"),
            agent.get("description"),
            agent.get("karma"),
            agent.get("follower_count"),
            agent.get("following_count"),
            agent.get("avatar_url"),
            int(agent.get("is_claimed") or False),
            agent.get("created_at"),
            owner.get("x_handle"),
            owner.get("x_name"),
            owner.get("x_follower_count"),
            int(owner.get("x_verified", False)) if owner else None,
            agent.get("posts_count"),
            agent.get("comments_count"),
        ))


# ── Post ──────────────────────────────────────────────────────────────────────

def post_exists(post_id: str) -> bool:
    """
    Controlla se un post è già nel database.
    Usato per il checkpoint: se il crawler si interrompe e riparte,
    salta i post già scaricati.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM posts WHERE id = ?", (post_id,)
        ).fetchone()
        return row is not None


def insert_post(post: dict):
    """
    Inserisce un post nel database. Usa INSERT OR IGNORE per non
    sovrascrivere post già esistenti (sicurezza aggiuntiva al checkpoint).
    Il flag comments_fetched = 0 indica che i commenti devono ancora
    essere scaricati.
    """
    author  = post.get("author") or {}
    submolt = post.get("submolt") or {}

    with get_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO posts (
                id, title, content, url, upvotes, downvotes, comment_count,
                created_at, author_name, submolt_name, fetched_at, comments_fetched
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 0)
        """, (
            post.get("id"),
            post.get("title"),
            post.get("content"),
            post.get("url"),
            post.get("upvotes"),
            post.get("downvotes"),
            post.get("comment_count"),
            post.get("created_at"),
            author.get("name"),
            submolt.get("name"),
        ))


def get_posts_without_comments(min_comments: int = 0) -> list[str]:
    """
    Restituisce la lista degli ID di post per cui non abbiamo ancora
    scaricato i commenti (comments_fetched = 0).

    Il parametro min_comments permette di filtrare solo i post con
    abbastanza commenti da generare archi utili nel grafo.
    Post con 0 commenti non producono nessun arco e sarebbero
    richieste API sprecate.

    Args:
        min_comments: soglia minima di comment_count (default 0 = tutti)

    Returns:
        Lista di post_id da processare, ordinati per comment_count DESC
        (i più ricchi di commenti vengono processati per primi).
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id FROM posts WHERE comments_fetched = 0 AND comment_count >= ? ORDER BY comment_count DESC",
            (min_comments,)
        ).fetchall()
        return [row["id"] for row in rows]


def mark_post_comments_fetched(post_id: str):
    """
    Segna un post come 'commenti scaricati' (comments_fetched = 1).
    Viene chiamato dopo aver completato il fetch dei commenti per quel post.
    """
    with get_connection() as conn:
        conn.execute(
            "UPDATE posts SET comments_fetched = 1 WHERE id = ?", (post_id,)
        )


# ── Commenti ──────────────────────────────────────────────────────────────────

def comment_exists(comment_id: str) -> bool:
    """
    Controlla se un commento è già nel database.
    Necessario perché richiamiamo lo stesso post con 4 ordinamenti diversi
    e lo stesso commento può comparire in più risposte.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM comments WHERE id = ?", (comment_id,)
        ).fetchone()
        return row is not None


def insert_comment(comment: dict, post_id: str):
    """
    Inserisce un commento nel database.

    Il campo parent_id è la chiave per costruire il grafo:
        - parent_id = NULL  → commento di primo livello (nessun arco)
        - parent_id = UUID  → reply → arco diretto author → parent_author

    post_id è passato esplicitamente perché nei dati annidati dell'API
    il commento non sempre include il riferimento al post padre.
    """
    author = comment.get("author") or {}

    with get_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO comments (
                id, content, parent_id, depth, upvotes, downvotes,
                reply_count, created_at, post_id, author_name, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            comment.get("id"),
            comment.get("content"),
            comment.get("parent_id"),   # NULL o UUID — la chiave del grafo
            comment.get("depth"),
            comment.get("upvotes"),
            comment.get("downvotes"),
            comment.get("reply_count"),
            comment.get("created_at"),
            post_id,
            author.get("name"),
        ))


# ── Submolts ──────────────────────────────────────────────────────────────────

def upsert_submolt(submolt: dict):
    """
    Inserisce o aggiorna un submolt (equivalente a un subreddit).
    Aggiorna il contatore iscritti ad ogni fetch perché cambia nel tempo.
    """
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO submolts (
                id, name, display_name, description, subscriber_count, fetched_at
            ) VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(name) DO UPDATE SET
                subscriber_count = excluded.subscriber_count,
                fetched_at       = excluded.fetched_at
        """, (
            submolt.get("id"),
            submolt.get("name"),
            submolt.get("display_name"),
            submolt.get("description"),
            submolt.get("subscriber_count"),
        ))


# ── Statistiche ───────────────────────────────────────────────────────────────

def print_stats():
    """
    Stampa un resoconto rapido dello stato del database.
    La riga 'Archi' è particolarmente importante: rappresenta il numero
    di commenti con parent_id != null, cioè il numero di archi diretti
    del grafo conversazionale. Se è vicino a zero c'è un problema.
    """
    with get_connection() as conn:
        agents   = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        posts    = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        comments = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
        edges    = conn.execute(
            "SELECT COUNT(*) FROM comments WHERE parent_id IS NOT NULL"
        ).fetchone()[0]
        submolts = conn.execute("SELECT COUNT(*) FROM submolts").fetchone()[0]

    print("\n=== STATO DATABASE ===")
    print(f"  Submolts : {submolts}")
    print(f"  Agenti   : {agents}")
    print(f"  Post     : {posts}")
    print(f"  Commenti : {comments}")
    print(f"  Archi    : {edges}  ← commenti con parent_id != null (= archi del grafo)")
    print("======================\n")
