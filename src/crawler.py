"""
crawler.py — Pipeline principale di raccolta dati

Questo è il file da eseguire per avviare il crawling.
Scarica i dati da Moltbook in 3 fasi sequenziali:

    Fase 0 — Submolts
        Recupera la lista di tutti i submolt disponibili.

    Fase 1 — Post (strategia: top post per submolt)
        Per ogni submolt, scarica i TOP_POSTS_PER_SUBMOLT post ordinati
        per commenti (sort=top). Scelta deliberata: i post più discussi
        hanno più reply e quindi più archi nel grafo conversazionale.
        'general' è escluso perché ha 1,4M post e distorcerebbe il campione.

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
    - Rate limiting: pausa di 0.4s tra richieste + retry automatico.
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

# Submolt da escludere: general ha 1,4M post, distorce il campione
SUBMOLTS_DA_ESCLUDERE = {"general"}

# Quanti post top prendere per ogni submolt
TOP_POSTS_PER_SUBMOLT = 200

# Scarica commenti solo per post con almeno N commenti
# (post con 0 commenti non generano archi nel grafo)
MIN_COMMENTS_FOR_CRAWL = 10


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
        - Retry automatico in caso di errore di rete o 5xx
        - Gestione del 429: attende il tempo indicato dall'API
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
                retry_after = resp.json().get("retryAfter", 60)
                log.warning(f"Rate limit raggiunto — attendo {retry_after}s")
                time.sleep(retry_after)

            elif resp.status_code == 404:
                log.debug(f"404 Not Found: {url}")
                return None

            else:
                log.warning(f"HTTP {resp.status_code} per {url} (tentativo {attempt}/{config.MAX_RETRIES})")
                time.sleep(config.RETRY_DELAY)

        except requests.RequestException as e:
            log.error(f"Errore di rete: {e} (tentativo {attempt}/{config.MAX_RETRIES})")
            time.sleep(config.RETRY_DELAY)

    log.error(f"Richiesta fallita definitivamente dopo {config.MAX_RETRIES} tentativi: {url}")
    return None


# ── Fase 0: Submolts ──────────────────────────────────────────────────────────

def fetch_submolts() -> list[str]:
    """
    Scarica la lista di tutti i submolt disponibili e li salva nel DB.
    Restituisce solo i nomi dei submolt da crawlare (esclusi quelli in
    SUBMOLTS_DA_ESCLUDERE).

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
        if name not in SUBMOLTS_DA_ESCLUDERE:
            names.append(name)
        else:
            log.info(f"  Submolt '{name}' escluso dalla strategia di crawling.")

    log.info(f"Submolts da crawlare: {len(names)} (esclusi: {len(submolts) - len(names)})")
    return names


# ── Fase 1: Post (top per submolt) ───────────────────────────────────────────

def fetch_top_posts_for_submolt(submolt_name: str):
    """
    Scarica i TOP_POSTS_PER_SUBMOLT post più discussi di un submolt
    usando sort=top. Strategia scelta per massimizzare gli archi del grafo:
    i post più commentati hanno più reply e quindi più parent_id valorizzati.

    Salta i post già presenti nel DB (checkpoint per ripresa).

    Args:
        submolt_name: nome del submolt da esplorare
    """
    cursor    = None
    new_posts = 0
    total_fetched = 0

    while total_fetched < TOP_POSTS_PER_SUBMOLT:
        # Quanto manca al limite? Prendi al massimo quello che serve
        remaining = TOP_POSTS_PER_SUBMOLT - total_fetched
        limit = min(config.POSTS_PER_PAGE, remaining)

        params = {
            "submolt": submolt_name,
            "sort":    "top",     # ordina per engagement, non per data
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

        for post in posts:
            if not db.post_exists(post["id"]):
                db.insert_post(post)
                new_posts += 1
            total_fetched += 1

        cursor = data.get("next_cursor")
        if not cursor or not data.get("has_more", False):
            break

    log.info(f"  [{submolt_name}] Post scaricati: {total_fetched}, nuovi salvati: {new_posts}")


def fetch_all_posts(submolt_names: list[str]):
    """
    Scarica i top post per ogni submolt nella lista.

    Args:
        submolt_names: lista di nomi submolt da processare
    """
    log.info(f"=== FASE 1: Fetch top {TOP_POSTS_PER_SUBMOLT} post per {len(submolt_names)} submolt ===")
    for name in submolt_names:
        fetch_top_posts_for_submolt(name)


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

    # Prendi solo post con abbastanza commenti da generare archi
    post_ids = db.get_posts_without_comments(min_comments=MIN_COMMENTS_FOR_CRAWL)
    log.info(f"Post da processare (>= {MIN_COMMENTS_FOR_CRAWL} commenti): {len(post_ids)}")

    all_authors = set()
    for i, post_id in enumerate(post_ids, 1):
        authors = fetch_comments_for_post(post_id)
        all_authors.update(authors)
        db.mark_post_comments_fetched(post_id)

        if i % 50 == 0:
            log.info(f"  Progresso: {i}/{len(post_ids)} post processati — autori unici finora: {len(all_authors)}")

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

        if i % 100 == 0:
            log.info(f"  Progresso: {i}/{len(to_fetch)} agenti processati")

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
    log.info(f"Strategia: top {TOP_POSTS_PER_SUBMOLT} post per submolt, esclusi: {SUBMOLTS_DA_ESCLUDERE}")

    os.makedirs("data", exist_ok=True)
    db.init_db()

    submolt_names = fetch_submolts()
    if not submolt_names:
        log.error("Nessun submolt trovato — impossibile procedere.")
        sys.exit(1)

    fetch_all_posts(submolt_names)
    all_authors = fetch_all_comments()
    fetch_agent_profiles(all_authors)

    log.info("====== CRAWLING COMPLETATO ======")
    db.print_stats()


if __name__ == "__main__":
    main()
