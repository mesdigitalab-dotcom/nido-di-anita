# Nido di Anita — deploy in produzione

Progetto Django containerizzato con Docker, pronto per essere ospitato fuori da Replit.

## ⚠️ Prima di tutto: ruota le credenziali

Il vecchio `settings.py` conteneva in chiaro la password del database Neon, la
password SMTP di Gmail e una `SECRET_KEY` di Django. Anche se ora sono state
spostate in variabili d'ambiente, **quei valori vecchi vanno considerati compromessi**
(sono stati per mesi dentro il codice sorgente, probabilmente anche su Replit/git):

1. Neon → cambia la password del ruolo `neondb_owner` (dashboard Neon → Roles).
2. Gmail → revoca la vecchia "App Password" e creane una nuova (Account Google →
   Sicurezza → Password per le app).
3. Django `SECRET_KEY` → generane una nuova, ad esempio:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

## Cosa è cambiato rispetto alla versione Replit

- Tutti i segreti (SECRET_KEY, DB, email, URL iCal) ora arrivano da variabili
  d'ambiente / file `.env`, non dal codice.
- `DEBUG` di default è `False` (prima era sempre `True`, pericoloso in produzione).
- Rimosso il middleware/le ALLOWED_HOSTS specifici di Replit.
- Aggiunto **whitenoise** per servire i file statici da dentro il container
  (niente bisogno di nginx separato per un progetto di queste dimensioni).
- Aggiunte le tipiche impostazioni di sicurezza Django per la produzione
  (HSTS, cookie sicuri, redirect HTTPS) attive automaticamente quando `DEBUG=False`.
- `manage.py` ora sta nella root del progetto, insieme a `Dockerfile`,
  `docker-compose.yml`, `entrypoint.sh`, `requirements.txt`.

## Struttura

```
.
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── .env.example        ← copialo in .env e compila i valori veri
├── django_project/      (settings, urls, wsgi)
├── app/                 (prenotazioni, calendario, ecc.)
├── accounts/             (utenti/autenticazione)
└── ics/cache/            (cache dei calendari esterni)
```

## Uso in locale con Docker

```bash
cp .env.example .env
# modifica .env con i tuoi valori reali (DB Neon, email, ecc.)

docker compose build
docker compose up
```

L'app sarà su http://localhost:8000. Al primo avvio l'entrypoint esegue da solo
le migrazioni e il collectstatic. Per creare un superuser:

```bash
docker compose exec web python manage.py createsuperuser
```

## Nota tecnica importante: un solo worker gunicorn

`app/apps.py` avvia, dentro al processo Django, uno scheduler in background
(APScheduler) che ogni 15 minuti scarica i calendari iCal esterni. Per questo
`entrypoint.sh` avvia gunicorn con **un solo worker** (`--workers 1 --threads 4`):
con più worker partirebbero più scheduler duplicati che scaricano più volte lo
stesso file. Per il traffico di un sito di prenotazioni B&B un worker con più
thread è più che sufficiente; se in futuro serve scalare, la soluzione corretta
è spostare lo scheduler in un processo separato (un worker/cron dedicato) invece
che aumentare i worker di gunicorn.

## Storage dei media (foto galleria, avatar) — Cloudflare R2

Il filesystem dei container su Render/host simili **non è persistente**: senza
uno storage esterno, ogni immagine caricata da admin/utenti sparirebbe al primo
deploy o riavvio. Il progetto è configurato per usare **Cloudflare R2** (storage
S3-compatibile, gratuito fino a 10GB, nessun costo di banda in uscita) quando le
variabili `R2_*` sono compilate in `.env`; se le lasci vuote si usa il filesystem
locale (comodo solo per lo sviluppo).

Passi per attivarlo:

1. Cloudflare dashboard → R2 → crea un bucket (es. `nido-di-anita-media`).
2. Nel bucket → Settings → abilita l'accesso pubblico (o collega un dominio
   custom) per ottenere il dominio pubblico (`pub-xxxx.r2.dev` o il tuo dominio).
3. R2 → "Manage API tokens" → crea un token con permessi di lettura/scrittura
   sul bucket → ottieni `Access Key ID` e `Secret Access Key`.
4. Compila in `.env`/nelle variabili d'ambiente di Render:
   `R2_BUCKET_NAME`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`,
   `R2_ENDPOINT_URL` (es. `https://<account_id>.r2.cloudflarestorage.com`),
   `R2_PUBLIC_DOMAIN`.
5. Se avevi già foto caricate in locale (`media/gallery/...`), caricale
   manualmente nel bucket (dashboard R2 o `aws s3 cp` puntato all'endpoint R2)
   prima di andare in produzione, altrimenti i link nel DB punterebbero a file
   non più esistenti sul filesystem.

## Dove ospitarlo gratis e in permanenza

Il database resta su Neon (già gratuito e già configurato), quindi serve solo un
posto dove far girare il container Docker.

**Opzione consigliata per iniziare — Render.com (piano Hobby/free)**
- Gratis, supporto nativo a Dockerfile, deploy automatico da GitHub.
- Limite reale: il servizio "si addormenta" dopo ~15 minuti di inattività e la
  richiesta successiva impiega 30-60 secondi a "svegliarlo" (cold start). Per un
  sito con traffico basso/medio (prenotazioni B&B) è quasi sempre accettabile.
- Passi: crea un account su render.com → "New Web Service" → collega il repo
  GitHub → Render riconosce il `Dockerfile` → aggiungi le variabili d'ambiente
  del tuo `.env` nella sezione "Environment" → deploy.

**Opzione per un servizio sempre attivo, senza sleep — Oracle Cloud "Always Free"**
- Una VM ARM gratuita per sempre (fino a 4 core / 24 GB RAM), su cui installi
  Docker e usi lo stesso `docker-compose.yml`. Nessun cold start, nessun limite
  di ore mensili.
- Più lavoro di gestione (aggiornamenti di sistema, firewall, certificato TLS
  con es. Caddy o Let's Encrypt) perché è una VM vera, non una piattaforma
  gestita. L'approvazione dell'account Oracle a volte richiede qualche giorno.

Entrambe le strade usano esattamente gli stessi file che ho creato (Dockerfile,
docker-compose.yml, .env) — cambia solo dove li fai girare.
