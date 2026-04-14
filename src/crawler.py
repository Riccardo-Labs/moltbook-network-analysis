"""
crawler.py — Pipeline principale di raccolta dati

Questo è il file da eseguire per avviare il crawling.
Scarica i dati da Moltbook in 3 fasi sequenziali:

    Fase 0 — Submolts
        Recupera la lista di tutti i submolt disponibili.

    Fase 1 — Post (strategia: TUTTI i post per submolt)
        Per ogni submolt, scarica TUTTI i post paginando fino a
        has_more=False (sort=new → ordine cronologico inverso).
        Checkpoint: i post già in DB vengono saltati.
        'general' è escluso di default (1.4M post ≈ 3h solo di GET /posts);
        imposta INCLUDE_GENERAL = True per includerlo.

    Fase 2 — Commenti
        Per ogni post con almeno MIN_COMMENTS_FOR_CRAWL commenti,
        scarica i commenti con i 3 sort validi (best, new, old).
        Il campo parent_id di ogni commento genera gli archi del grafo:
            parent_id != null → arco diretto author → parent_author

    Fase 3 — Profili agenti
        Per ogni author_name incontrato nei commenti, scarica il profilo
        completo (karma, follower_count, is_claimed, owner...).
        Questi dati diventano gli attributi dei nodi nel grafo.

Meccanismi di robustezza:
    - Checkpoint: se il crawler si interrompe, alla ripresa salta post
      e agenti già scaricati (nessun dato perso).
    - Rate limiting: pausa di REQUEST_DELAY secondi tra richieste.
    - Backoff esponenziale: in caso di 429 o errore di rete il delay
      raddoppia ad ogni tentativo (REQUEST_DELAY × 2^attempt).
    - Logging: tutto viene scritto su logs/crawler.log.

NOTA: l'API è pubblica, nessuna autenticazione richiesta
(confermato via DevTools: Access-Control-Allow-Origin: *).

Esecuzione:
    cd moltbook-thesis
    python src/crawler.py
"""

import time
import logging
import sys
import os

import requests

sys.path.insert(0, os.path.dirname(__file__))
import config
import db


# ── Parametri strategia crawling ─────────────────────────────────────────────

# Includi il submolt 'general'?
# True = incluso con cap MAX_POSTS_PER_SUBMOLT["general"] (100k post).
INCLUDE_GENERAL = True

# Limite massimo di post per submolt (None = nessun limite).
# 'general' ha 1.56M post: limitiamo ai primi 100k (sort=new).
# Tutti gli altri submolt vengono paginati completamente.
MAX_POSTS_PER_SUBMOLT = {
    "general": 100_000,
}

# Scarica commenti per post con almeno N commenti.
# 5 = buon compromesso: cattura la coda lunga senza sprecare richieste
# su post quasi vuoti (1-4 commenti) che contribuiscono poco al grafo.
MIN_COMMENTS_FOR_CRAWL = 5


# ── Configurazione logging ────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── HTTP helper ───────────────────────────────────────────────────────────────

def get(endpoint: str, params: dict = None) -> dict | None:
    """
    Esegue una richiesta GET all'API Moltbook con:
        - Pausa automatica (rate limiting) prima di ogni chiamata
        - Backoff esponenziale in caso di errore di rete o 5xx:
          il delay raddoppia ad ogni tentativo (REQUEST_DELAY × 2^attempt)
        - Gestione del 429: attende il tempo indicato dall'API,
          poi applica backoff esponenziale aggiuntivo
        - Restituzione di None in caso di 404 o fallimento definitivo

    Args:
        endpoint: percorso relativo, es. "/posts" o "/agents/profile"
        params:   parametri query string, es. {"submolt": "agents", "limit": 50}

    Returns:
        Il JSON parsato come dict, oppure None se la richiesta fallisce.
    """
    url = f"{config.BASE_URL}{endpoint}"

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            time.sleep(config.REQUEST_DELAY)
            resp = requests.get(url, params=params, timeout=15)

            if resp.status_code == 200:
                return resp.json()

            elif resp.status_code == 429:
                # L'API indica esplicitamente quanto aspettare
                try:
                    retry_after = resp.json().get("retryAfter", 60)
                except Exception:
                    retry_after = 60
                backoff = retry_after * (2 ** (attempt - 1))
                log.warning(f"Rate limit (429) — attendo {backoff}s (tentativo {attempt}/{config.MAX_RETRIES})")
                time.sleep(backoff)

            elif resp.status_code == 404:
                log.debug(f"404 Not Found: {url}")
                return None

            else:
                backoff = config.RETRY_DELAY * (2 ** (attempt - 1))
                log.warning(
                    f"HTTP {resp.status_code} per {url} "
                    f"(tentativo {attempt}/{config.MAX_RETRIES}) — attendo {backoff}s"
                )
                time.sleep(backoff)

        except requests.RequestException as e:
            backoff = config.RETRY_DELAY * (2 ** (attempt - 1))
            log.error(f"Errore di rete: {e} (tentativo {attempt}/{config.MAX_RETRIES}) — attendo {backoff}s")
            time.sleep(backoff)

    log.error(f"Richiesta fallita definitivamente dopo {config.MAX_RETRIES} tentativi: {url}")
    return None


# ── Fase 0: Submolts ──────────────────────────────────────────────────────────

def fetch_submolts() -> list[str]:
    """
    Scarica la lista di tutti i submolt disponibili e li salva nel DB.
    Restituisce solo i nomi dei submolt da crawlare (rispettando INCLUDE_GENERAL).

    Returns:
        Lista filtrata di nomi submolt da processare.
    """
    log.info("=== FASE 0: Fetch submolts ===")
    data = get("/submolts")

    if not data:
        log.error("Impossibile recuperare i submolt.")
        return []

    submolts = data if isinstance(data, list) else data.get("submolts", [])

    names = []
    for s in submolts:
        db.upsert_submolt(s)
        name = s.get("name")
        if name == "general" and not INCLUDE_GENERAL:
            log.info(f"  Submolt 'general' escluso (INCLUDE_GENERAL=False).")
        else:
            names.append(name)

    excluded = len(submolts) - len(names)
    log.info(f"Submolts da crawlare: {len(names)} (esclusi: {excluded})")
    return names


# ── Fase 1: Post (tutti per submolt) ─────────────────────────────────────────

def fetch_all_posts_for_submolt(submolt_name: str):
    """
    Scarica i post di un submolt paginando fino a has_more=False.
    Usa sort=new (ordine cronologico inverso).

    Se il submolt è presente in MAX_POSTS_PER_SUBMOLT, si ferma al
    raggiungimento del cap (es. 100k per 'general').
    Per tutti gli altri submolt non c'è limite.

    Checkpoint: i post già in DB vengono conteggiati ma non re-inseriti.

    Args:
        submolt_name: nome del submolt da esplorare
    """
    max_posts     = MAX_POSTS_PER_SUBMOLT.get(submolt_name)  # None = nessun limite
    cursor        = None
    new_posts     = 0
    already_in_db = 0
    pages         = 0
    total_fetched = 0

    while True:
        # Rispetta il cap se definito
        if max_posts is not None and total_fetched >= max_posts:
            log.info(f"  [{submolt_name}] Cap di {max_posts:,} post raggiunto.")
            break

        remaining = (max_posts - total_fetched) if max_posts is not None else config.POSTS_PER_PAGE
        limit = min(config.POSTS_PER_PAGE, remaining)

        params = {
            "submolt": submolt_name,
            "sort":    "new",
            "limit":   limit,
        }
        if cursor:
            params["cursor"] = cursor

        data = get("/posts", params=params)
        if not data:
            break

        posts = data.get("posts", [])
        if not posts:
            break

        pages += 1
        for post in posts:
            if not db.post_exists(post["id"]):
                db.insert_post(post)
                new_posts += 1
            else:
                already_in_db += 1
            total_fetched += 1

        cursor = data.get("next_cursor")
        if not cursor or not data.get("has_more", False):
            break

        # Log di avanzamento ogni 20 pagine (= 1000 post)
        if pages % 20 == 0:
            log.info(
                f"  [{submolt_name}] Pagina {pages} — "
                f"nuovi: {new_posts}, già in DB: {already_in_db}"
            )

    total = new_posts + already_in_db
    log.info(
        f"  [{submolt_name}] Completato: {total} post visti, "
        f"{new_posts} nuovi, {already_in_db} già in DB ({pages} pagine)"
    )


def fetch_all_posts(submolt_names: list[str]):
    """
    Scarica tutti i post per ogni submolt nella lista.

    Args:
        submolt_names: lista di nomi submolt da processare
    """
    log.info(f"=== FASE 1: Fetch TUTTI i post per {len(submolt_names)} submolt ===")
    for name in submolt_names:
        fetch_all_posts_for_submolt(name)


# ── Fase 2: Commenti ──────────────────────────────────────────────────────────

def _flatten_comments(comments: list, result: list = None) -> list:
    """
    Appiattisce l'albero di commenti annidati in una lista piatta.
    L'API restituisce le reply nel campo "replies" annidato dentro ogni
    commento — questa funzione li estrae tutti ricorsivamente.

    Esempio struttura API:
        commento A (depth=0)
          └─ reply B (depth=1, parent_id=A) → arco B→A
               └─ reply C (depth=2, parent_id=B) → arco C→B

    Args:
        comments: lista di commenti top-level con eventuali "replies" annidate
        result:   lista accumulatore (usato nella ricorsione interna)

    Returns:
        Lista piatta di tutti i commenti incluse le replies a qualsiasi profondità.
    """
    if result is None:
        result = []
    for c in comments:
        result.append(c)
        if c.get("replies"):
            _flatten_comments(c["replies"], result)
    return result


def fetch_comments_for_post(post_id: str) -> set[str]:
    """
    Scarica i commenti di un post con i 3 sort validi (best, new, old)
    per massimizzare il numero di commenti unici recuperati per post.
    (L'API restituisce max 100 commenti top-level per richiesta, ma le
    replies annidate vengono incluse nel JSON — quindi si recuperano molti più.)

    Gli archi del grafo emergono qui:
        comment.parent_id != null → arco diretto author → parent_author

    Args:
        post_id: UUID del post

    Returns:
        Insieme degli author_name unici incontrati in questo post.
    """
    authors_seen = set()

    for sort in config.COMMENT_SORT_ORDERS:
        data = get(f"/posts/{post_id}/comments", params={"sort": sort})
        if not data:
            continue

        raw = data if isinstance(data, list) else data.get("comments", [])
        comments = _flatten_comments(raw)

        for c in comments:
            if not db.comment_exists(c["id"]):
                db.insert_comment(c, post_id)

            author_name = (c.get("author") or {}).get("name")
            if author_name:
                authors_seen.add(author_name)

    return authors_seen


def fetch_all_comments() -> set[str]:
    """
    Scarica i commenti per tutti i post con:
        - comments_fetched = 0 (non ancora processati)
        - comment_count >= MIN_COMMENTS_FOR_CRAWL (hanno archi utili)

    Il filtro su comment_count evita di sprecare richieste API su post
    senza commenti, che non genererebbero nessun arco nel grafo.

    Returns:
        Insieme di tutti gli author_name trovati, per il fetch dei profili.
    """
    log.info("=== FASE 2: Fetch commenti ===")

    post_ids = db.get_posts_without_comments(min_comments=MIN_COMMENTS_FOR_CRAWL)
    log.info(f"Post da processare (>= {MIN_COMMENTS_FOR_CRAWL} commenti): {len(post_ids)}")

    all_authors = set()
    for i, post_id in enumerate(post_ids, 1):
        authors = fetch_comments_for_post(post_id)
        all_authors.update(authors)
        db.mark_post_comments_fetched(post_id)

        if i % 50 == 0:
            log.info(
                f"  Progresso: {i}/{len(post_ids)} post processati "
                f"— autori unici finora: {len(all_authors)}"
            )

    log.info(f"Autori unici trovati: {len(all_authors)}")
    return all_authors


# ── Fase 3: Profili agenti ────────────────────────────────────────────────────

def fetch_agent_profiles(agent_names: set[str]):
    """
    Scarica il profilo completo di ogni agente trovato nei commenti.
    Salta gli agenti già in DB (checkpoint).

    I campi recuperati diventano gli attributi dei nodi nel grafo:
        - karma, follower_count, following_count → misure di influenza
        - is_claimed → indica se l'agente è controllato da un umano
        - owner.x_handle → identità del proprietario umano (se claimed)
        - created_at, last_active → dimensione temporale

    Args:
        agent_names: insieme di nomi agente da scaricare
    """
    log.info("=== FASE 3: Fetch profili agenti ===")

    to_fetch = [n for n in agent_names if not db.agent_exists(n)]
    log.info(f"Agenti da scaricare: {len(to_fetch)} (già in DB: {len(agent_names) - len(to_fetch)})")

    for i, name in enumerate(to_fetch, 1):
        data = get("/agents/profile", params={"name": name})
        if data:
            db.upsert_agent(data)

        if i % 200 == 0:
            pct = i / len(to_fetch) * 100
            log.info(f"  Progresso: {i}/{len(to_fetch)} agenti processati ({pct:.1f}%)")

    log.info("Fetch profili agenti completato.")


# ── Entrypoint ────────────────────────────────────────────────────────────────

def main():
    """
    Punto di ingresso del crawler.
    Esegue le 4 fasi in sequenza e stampa le statistiche finali.
    Il checkpoint garantisce che una ripresa dopo interruzione
    non perda dati e non rifaccia lavoro già fatto.
    """
    log.info("====== CRAWLER MOLTBOOK — AVVIO ======")
    log.info(f"Strategia: TUTTI i post per submolt — general={'incluso' if INCLUDE_GENERAL else 'escluso'}")

    os.makedirs("data", exist_ok=True)
    db.init_db()

    submolt_names = fetch_submolts()
    if not submolt_names:
        log.error("Nessun submolt trovato — impossibile procedere.")
        sys.exit(1)

    fetch_all_posts(submolt_names)
    session_authors = fetch_all_comments()

    # Unisce gli autori trovati in questa sessione con quelli già in DB
    # dai commenti di sessioni precedenti (robustezza al crash).
    all_authors = db.get_all_comment_authors()
    log.info(f"Autori totali da commenti in DB (incluse sessioni precedenti): {len(all_authors)}")

    fetch_agent_profiles(all_authors)

    log.info("====== CRAWLING COMPLETATO ======")
    db.print_stats()


if __name__ == "__main__":
    main()
