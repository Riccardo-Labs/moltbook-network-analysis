"""
config.py — Configurazione centralizzata del progetto

Contiene tutti i parametri globali: base URL, rate limiting,
paginazione e percorsi di file. È l'unico file da modificare per
adattare il crawler a nuove esigenze (es. cambiare delay, path DB).

NOTA: l'API di Moltbook è pubblica e non richiede autenticazione.
Header Access-Control-Allow-Origin: * confermato via DevTools (marzo 2026).
Nessun Bearer token o API key necessari.
"""

# ── API ───────────────────────────────────────────────────────────────────────
# IMPORTANTE: usare sempre il prefisso www — senza, il server risponde
# con un redirect che può causare comportamenti inattesi.
BASE_URL = "https://www.moltbook.com/api/v1"

# ── Rate limiting ─────────────────────────────────────────────────────────────
# Limite osservato: 200 richieste per finestra temporale (dimensione non nota).
# REQUEST_DELAY di 0.4s → ~150 req/min, abbondantemente sotto il limite.
REQUEST_DELAY = 0.4   # secondi di pausa tra una richiesta e l'altra
MAX_RETRIES   = 3     # quante volte riprovare in caso di errore di rete
RETRY_DELAY   = 5     # secondi di attesa prima di ogni retry

# ── Paginazione ───────────────────────────────────────────────────────────────
# 50 è il massimo consentito dall'API per la lista post
POSTS_PER_PAGE = 50

# Sort validi confermati via API: best, new, old ("controversial" restituisce 400)
# Richiedere tutti e 3 gli ordinamenti massimizza i commenti unici per post
COMMENT_SORT_ORDERS = ["best", "new", "old"]

# ── Percorsi file ─────────────────────────────────────────────────────────────
DB_PATH  = "data/moltbook.db"   # database SQLite (creato automaticamente)
LOG_PATH = "logs/crawler.log"   # log del crawler (creato automaticamente)
