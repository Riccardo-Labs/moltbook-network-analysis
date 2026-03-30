"""
crawler.py — Pipeline principale di raccolta dati

Questo è il file da eseguire per avviare il crawling.
Scarica i dati da Moltbook in 3 fasi sequenziali:

    Fase 0 — Submolts
        Recupera la lista di tutti i submolt disponibili (equivalenti
        ai subreddit). Sono il punto di ingresso per esplorare i post.

    Fase 1 — Post
        Per ogni submolt, pagina tutti i post disponibili (sort=new,
        50 per pagina) fino all'esaurimento.

    Fase 2 — Commenti
        Per ogni post, scarica i commenti con tutti e 4 gli ordinamenti
        (top, new, controversial, old) per massimizzare la copertura
        fino a ~400 commenti unici per post.
        Il campo parent_id di ogni commento genera gli archi del grafo.

    Fase 3 — Profili agenti
        Per ogni author_name incontrato nei commenti, scarica il profilo
        completo dell'agente (karma, follower_count, is_claimed, owner...).

Meccanismi di robustezza:
    - Checkpoint: se il crawler si interrompe, alla ripresa salta post
      e agenti già scaricati (nessun dato perso).
    - Rate limiting: pausa di 0.4s tra richieste + retry automatico.
    - Logging: tutto viene scritto su logs/crawler.log.

NOTA: l'API è pubblica, nessuna autenticazione richiesta.

Esecuzione:
    cd moltbook-thesis
    python src/crawler.py
"""

import time
import logging
import sys
import os

import requests  # pip install requests

# Aggiunge src/ al path in modo da poter importare config e db
sys.path.insert(0, os.path.dirname(__file__))

import config
import db


# ── Configurazione logging ────────────────────────────────────────────────────
# Scrive sia su file (logs/crawler.log) che su console
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
        - Gestione del 429 (rate limit): attende il tempo indicato dall'API
        - Restituzione di None in caso di 404 o fallimento definitivo

    L'API è pubblica: nessun header di autenticazione necessario.

    Args:
        endpoint: percorso relativo, es. "/posts" o "/agents/profile"
        params:   parametri query string, es. {"submolt": "general", "limit": 50}

    Returns:
        Il JSON parsato come dict, oppure None se la richiesta fallisce.
    """
    url = f"{config.BASE_URL}{endpoint}"

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            time.sleep(config.REQUEST_DELAY)  # rispetta il rate limit
            resp = requests.get(url, params=params, timeout=15)  # no auth header

            if resp.status_code == 200:
                return resp.json()

            elif resp.status_code == 429:
                # L'API ci dice quanto aspettare prima di riprovare
                retry_after = resp.json().get("retryAfter", 60)
                log.warning(f"Rate limit raggiunto — attendo {retry_after}s")
                time.sleep(retry_after)

            elif resp.status_code == 404:
                log.debug(f"404 Not Found: {url}")
                return None  # risorsa non esistente, non riprovare

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
    Scarica la lista di tutti i submolt disponibili sulla piattaforma.
    I submolt sono il punto di ingresso per il crawling dei post.

    Returns:
        Lista dei nomi dei submolt (es. ["general", "tech", "news"]).
        Lista vuota se la chiamata fallisce.
    """
    log.info("=== FASE 0: Fetch submolts ===")
    data = get("/submolts")

    if not data:
        log.error("Impossibile recuperare i submolt.")
        return []

    # L'API può restituire una lista diretta o un oggetto con chiave "submolts"
    submolts = data if isinstance(data, list) else data.get("submolts", [])

    names = []
    for s in submolts:
        db.upsert_submolt(s)
        names.append(s.get("name"))

    log.info(f"Submolts trovati e salvati: {len(names)}")
    return names


# ── Fase 1: Post ──────────────────────────────────────────────────────────────

def fetch_posts_for_submolt(submolt_name: str):
    """
    Scarica tutti i post di un singolo submolt, paginando fino all'esaurimento.
    Usa sort=new per garantire ordine cronologico e copertura completa.
    Salta i post già presenti nel DB (checkpoint).

    Args:
        submolt_name: nome del submolt da esplorare (es. "general")
    """
    offset    = 0
    new_posts = 0

    while True:
        data = get("/posts", params={
            "submolt": submolt_name,
            "sort":    "new",
            "limit":   config.POSTS_PER_PAGE,
            "offset":  offset,
        })

        if not data:
            break

        posts = data.get("posts", [])
        if not posts:
            break  # pagina vuota: abbiamo finito

        for post in posts:
            if not db.post_exists(post["id"]):
                db.insert_post(post)
                new_posts += 1

        # has_more indica se esiste una pagina successiva
        if not data.get("has_more", False):
            break
        offset += config.POSTS_PER_PAGE

    log.info(f"  [{submolt_name}] Nuovi post salvati: {new_posts}")


def fetch_all_posts(submolt_names: list[str]):
    """
    Chiama fetch_posts_for_submolt per ogni submolt nella lista.

    Args:
        submolt_names: lista di nomi submolt restituita da fetch_submolts()
    """
    log.info("=== FASE 1: Fetch post ===")
    for name in submolt_names:
        fetch_posts_for_submolt(name)


# ── Fase 2: Commenti ──────────────────────────────────────────────────────────

def _flatten_comments(comments: list, result: list = None) -> list:
    """
    Appiattisce l'albero di commenti annidati in una lista piatta.
    L'API restituisce le reply come campo "replies" annidato dentro
    ogni commento — questa funzione li estrae tutti ricorsivamente.

    Args:
        comments: lista di commenti (con eventuale campo "replies" annidato)
        result:   lista accumulatore (usato nella ricorsione)

    Returns:
        Lista piatta di tutti i commenti e sub-commenti.
    """
    if result is None:
        result = []
    for c in comments:
        result.append(c)
        if c.get("replies"):
            _flatten_comments(c["replies"], result)  # ricorsione sulle replies
    return result


def fetch_comments_for_post(post_id: str) -> set[str]:
    """
    Scarica i commenti di un post usando tutti e 4 gli ordinamenti disponibili
    per massimizzare il numero di commenti unici recuperati.
    (L'API restituisce max 100 commenti per richiesta, ma con 4 ordinamenti
    diversi si recuperano fino a ~400 commenti unici per post.)

    Costruisce gli archi del grafo tramite parent_id:
        comment.parent_id != null → arco diretto author → parent_author

    Args:
        post_id: UUID del post di cui scaricare i commenti

    Returns:
        Insieme degli author_name incontrati in questo post.
    """
    authors_seen = set()

    for sort in config.COMMENT_SORT_ORDERS:
        data = get(f"/posts/{post_id}/comments", params={"sort": sort})
        if not data:
            continue

        # Normalizza: l'API può restituire lista diretta o oggetto con "comments"
        raw = data if isinstance(data, list) else data.get("comments", [])
        comments = _flatten_comments(raw)

        for c in comments:
            if not db.comment_exists(c["id"]):
                db.insert_comment(c, post_id)

            # Raccoglie autori per il fetch dei profili (fase 3)
            author_name = (c.get("author") or {}).get("name")
            if author_name:
                authors_seen.add(author_name)

    return authors_seen


def fetch_all_comments() -> set[str]:
    """
    Scarica i commenti per tutti i post con comments_fetched = 0.
    Meccanismo di checkpoint: se il crawler si interrompe, alla ripresa
    elabora solo i post non ancora processati.

    Returns:
        Insieme di tutti gli author_name trovati nei commenti.
        Sarà usato nella fase 3 per scaricare i profili agenti.
    """
    log.info("=== FASE 2: Fetch commenti ===")
    post_ids = db.get_posts_without_comments()
    log.info(f"Post da processare: {len(post_ids)}")

    all_authors = set()
    for i, post_id in enumerate(post_ids, 1):
        authors = fetch_comments_for_post(post_id)
        all_authors.update(authors)
        db.mark_post_comments_fetched(post_id)  # segna come completato

        if i % 50 == 0:
            log.info(f"  Progresso: {i}/{len(post_ids)} post processati")

    log.info(f"Autori unici trovati: {len(all_authors)}")
    return all_authors


# ── Fase 3: Profili agenti ────────────────────────────────────────────────────

def fetch_agent_profiles(agent_names: set[str]):
    """
    Scarica il profilo completo di ogni agente trovato nei commenti.
    Salta gli agenti già presenti nel DB (checkpoint).

    Il profilo include: karma, follower_count, is_claimed, e — se claimed —
    i dati pubblici del proprietario umano (x_handle, x_follower_count...).
    Questi campi saranno gli attributi dei nodi nel grafo.

    Args:
        agent_names: insieme di nomi agente da scaricare
    """
    log.info("=== FASE 3: Fetch profili agenti ===")

    # Filtra solo gli agenti non ancora in DB (checkpoint)
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
    Punto di ingresso del crawler. Esegue le 4 fasi in sequenza:
    submolts → post → commenti → profili agenti.
    Al termine stampa le statistiche del database.
    """
    log.info("====== CRAWLER MOLTBOOK — AVVIO ======")

    # Crea le cartelle e inizializza il database
    os.makedirs("data", exist_ok=True)
    db.init_db()

    # Esegui la pipeline
    submolt_names = fetch_submolts()
    if not submolt_names:
        log.error("Nessun submolt trovato — impossibile procedere.")
        sys.exit(1)

    fetch_all_posts(submolt_names)
    all_authors = fetch_all_comments()
    fetch_agent_profiles(all_authors)

    # Resoconto finale
    log.info("====== CRAWLING COMPLETATO ======")
    db.print_stats()


if __name__ == "__main__":
    main()
