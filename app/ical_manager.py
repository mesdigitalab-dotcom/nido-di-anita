"""
ICalManager — gestione calendari iCal.

Architettura:

  ┌─ Calendario INTERNO ──────────────────────────────────────────────────┐
  │  Generato al volo dal DB ad ogni GET /calendario.ics                  │
  │  (funz3 · serve_personal_ical — NON MODIFICATA)                       │
  └───────────────────────────────────────────────────────────────────────┘

  ┌─ Calendari ESTERNI ───────────────────────────────────────────────────┐
  │  Scaricati ogni 15 min dallo scheduler (AppConfig.ready).             │
  │  ETag/Last-Modified: skip automatico se il server risponde 304.       │
  │  Validazione prima della scrittura: se corrotto → mantieni vecchio.   │
  │  Scrittura atomica (tmp → rename).                                    │
  │  Risultato del parsing cachato in memoria per 15 min.                 │
  └───────────────────────────────────────────────────────────────────────┘

  ┌─ get_busy_slots() ────────────────────────────────────────────────────┐
  │  Unisce DB (query diretta) + iCal esterni (cache disco/memoria).      │
  └───────────────────────────────────────────────────────────────────────┘
"""

import os
import logging
import tempfile
import shutil
import threading
import time as _time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from icalendar import Calendar, Event

logger = logging.getLogger(__name__)


class ICalManager:
    """
    Tre funzioni pubbliche:

      funz1 · get_busy_slots()       → range occupati (DB + iCal esterni)
      funz2 · fetch_external_icals() → scarica/aggiorna cache iCal esterni
      funz3 · serve_personal_ical()  → genera .ics dal DB (NON MODIFICATA)
    """

    PRODID = "-//NidoDiAnita//Calendario Prenotazioni//IT"
    _EXT_CACHE_TTL = 900  # secondi — allineato al job ogni 15 min

    def __init__(
        self,
        external_urls: List[str],
        cache_dir: str = "/var/www/ics/cache",
        request_timeout: int = 10,
        max_workers: int = 4,
    ):
        self.external_urls = external_urls
        self.cache_dir = Path(cache_dir)
        self.request_timeout = request_timeout
        self.max_workers = max_workers

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache in-memory dei busy slots estratti dagli iCal esterni.
        self._ext_cache: Optional[List[Tuple[datetime, datetime]]] = None
        self._ext_cache_ts: float = 0.0
        self._ext_lock = threading.Lock()

    # ── helpers privati ────────────────────────────────────────────────────

    @staticmethod
    def _safe_load(content: bytes) -> Optional[Calendar]:
        """
        Carica un iCal da bytes. Compatibile con icalendar 4.x e 5.x.
        Ritorna None se il contenuto è corrotto o non è un iCal valido.
        """
        try:
            cals = list(Calendar.from_ical(content, multiple=True))
            return cals[0] if cals else None
        except TypeError:
            pass  # icalendar < 5.0: multiple=True non supportato
        try:
            return Calendar.from_ical(content)
        except Exception as e:
            logger.debug("Parsing iCal fallito: %s", e)
            return None

    def _cache_path(self, url: str) -> Path:
        """Mappa un URL a un filename sicuro nella cache."""
        safe = (
            url.replace("https://", "").replace("http://", "")
               .replace("/", "_").replace(":", "_").replace("?", "_")
        )
        return self.cache_dir / f"{safe[:120]}.ics"

    @staticmethod
    def _to_dt(value) -> datetime:
        """Normalizza date/datetime naive → datetime UTC-aware."""
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)

    # ── funz2 · fetch esterni ──────────────────────────────────────────────

    def _fetch_one(self, url: str) -> str:
        """
        Scarica un singolo iCal esterno con supporto ETag/Last-Modified
        (evita il re-download se il file non è cambiato sul server).

        Flusso:
          1. GET con headers condizionali (ETag/Last-Modified se disponibili)
          2. 304 → nessuna scrittura, cache in-memory rimane valida
          3. 200 → valida il contenuto PRIMA di scrivere su disco
          4. Se valido → scrittura atomica (tmp → rename) + aggiorna .meta
          5. Se corrotto → scarta, mantieni il vecchio file in cache intatto
        """
        cache_path = self._cache_path(url)
        meta_path = cache_path.with_suffix(".meta")

        # Costruisce headers condizionali da file .meta salvato in precedenza
        req_headers = {}
        if cache_path.exists() and meta_path.exists():
            for line in meta_path.read_text(encoding="utf-8").splitlines():
                k, _, v = line.partition(":")
                req_headers[k.strip()] = v.strip()

        try:
            resp = requests.get(url, headers=req_headers, timeout=self.request_timeout)

            if resp.status_code == 304:
                logger.debug("iCal invariato (304): %s", url)
                return "skipped"

            resp.raise_for_status()

            # ── Validazione PRIMA della scrittura ─────────────────────────
            # Se il contenuto è corrotto il file in cache rimane intatto.
            cal = self._safe_load(resp.content)
            if cal is None:
                logger.warning(
                    "iCal non valido o corrotto da %s — file in cache mantenuto.", url
                )
                return "invalid"

            # ── Scrittura atomica: tmp → rename ────────────────────────────
            tmp_fd, tmp_path = tempfile.mkstemp(dir=self.cache_dir, suffix=".ics")
            try:
                with os.fdopen(tmp_fd, "wb") as f:
                    f.write(resp.content)
                shutil.move(tmp_path, cache_path)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

            # Persiste ETag/Last-Modified per la prossima richiesta
            meta = {}
            if "ETag" in resp.headers:
                meta["If-None-Match"] = resp.headers["ETag"]
            if "Last-Modified" in resp.headers:
                meta["If-Modified-Since"] = resp.headers["Last-Modified"]
            if meta:
                meta_path.write_text(
                    "\n".join(f"{k}: {v}" for k, v in meta.items()),
                    encoding="utf-8",
                )

            logger.info("iCal aggiornato: %s → %s", url, cache_path.name)
            return "ok"

        except requests.RequestException as e:
            logger.warning("Fetch fallito (%s): %s", url, e)
            return "failed"
        except Exception as e:
            logger.error("Errore imprevisto fetch (%s): %s", url, e)
            return "error"

    def fetch_external_icals(self) -> dict:
        """
        funz2 — Scarica tutti gli iCal esterni in parallelo ogni 15 min.

        - Download paralleli (ThreadPoolExecutor) per ridurre la latenza.
        - ETag/Last-Modified: skip automatico se il server risponde 304.
        - Validazione prima della scrittura: contenuto corrotto → scartato,
          file in cache precedente mantenuto intatto.
        - Se almeno un file cambia, invalida la cache in-memory dei slots
          così la prossima get_busy_slots() rilegge i dati freschi.

        Returns:
            Dict {url: "ok" | "skipped" | "invalid" | "failed" | "error"}
        """
        if not self.external_urls:
            logger.debug("Nessun URL iCal esterno configurato.")
            return {}

        results = {}
        any_changed = False

        n_workers = min(self.max_workers, len(self.external_urls))
        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = {
                pool.submit(self._fetch_one, url): url
                for url in self.external_urls
            }
            for future in as_completed(futures):
                url = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = "error"
                    logger.error("Eccezione nel thread fetch (%s): %s", url, e)
                results[url] = result
                if result == "ok":
                    any_changed = True

        if any_changed:
            with self._ext_lock:
                self._ext_cache = None  # forza ricalcolo al prossimo accesso

        logger.info(
            "fetch_external_icals completato: %s",
            {url.split("/")[-1]: r for url, r in results.items()},
        )
        return results

    # ── funz1 · busy slots ─────────────────────────────────────────────────

    def _external_slots(self) -> List[Tuple[datetime, datetime]]:
        """
        Legge i file .ics in cache e ritorna i busy slots degli esterni.
        Cache in-memory per _EXT_CACHE_TTL sec: il parsing disco è la
        parte più lenta, farlo una volta ogni 15 min è sufficiente.
        """
        now = _time.monotonic()

        with self._ext_lock:
            if (
                self._ext_cache is not None
                and (now - self._ext_cache_ts) < self._EXT_CACHE_TTL
            ):
                return self._ext_cache

        # Parsing fuori dal lock (operazione lenta, non blocca altri thread)
        slots: List[Tuple[datetime, datetime]] = []
        for ics_path in self.cache_dir.glob("*.ics"):
            try:
                cal = self._safe_load(ics_path.read_bytes())
                if cal is None:
                    logger.warning(
                        "File in cache corrotto ignorato: %s", ics_path.name
                    )
                    continue
                for comp in cal.walk():
                    if comp.name != "VEVENT":
                        continue
                    ds = comp.get("dtstart")
                    de = comp.get("dtend")
                    if ds and de:
                        slots.append((self._to_dt(ds.dt), self._to_dt(de.dt)))
            except Exception as e:
                logger.warning(
                    "Lettura iCal esterno fallita (%s): %s", ics_path.name, e
                )

        with self._ext_lock:
            self._ext_cache = slots
            self._ext_cache_ts = _time.monotonic()

        return slots

    def get_busy_slots(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[Tuple[datetime, datetime]]:
        """
        funz1 — Ritorna tutti i range occupati come lista ordinata di tuple
        (inizio: datetime, fine: datetime).

        Fonti:
          1. DB Prenotazioni: query diretta con values_list — zero file I/O,
             sempre aggiornata, una sola query con 2 colonne.
          2. iCal esterni: parsing da cache disco con cache in-memory 15 min.

        Args:
            since: escludi eventi già terminati prima di questa data.
                   Default: datetime.now(UTC).
            until: escludi eventi che iniziano dopo questa data (opzionale).
        """
        if since is None:
            since = datetime.now(tz=timezone.utc)

        # ── 1. DB: query singola, 2 colonne, zero oggetti ORM ─────────────
        from .models import Prenotazioni

        db_qs = Prenotazioni.objects.filter(fine__gt=since)
        if until:
            db_qs = db_qs.filter(inizio__lt=until)

        db_slots: List[Tuple[datetime, datetime]] = [
            (
                s if s.tzinfo else s.replace(tzinfo=timezone.utc),
                e if e.tzinfo else e.replace(tzinfo=timezone.utc),
            )
            for s, e in db_qs.values_list("inizio", "fine")
        ]

        # ── 2. iCal esterni (skip se nessun URL configurato) ──────────────
        ext_slots: List[Tuple[datetime, datetime]] = []
        if self.external_urls:
            ext_slots = [
                (s, e) for s, e in self._external_slots()
                if e > since and (until is None or s < until)
            ]

        all_slots = db_slots + ext_slots
        all_slots.sort(key=lambda t: t[0])
        return all_slots

    # ── funz3 · serve iCal personale — NON MODIFICATA ─────────────────────

    def serve_personal_ical(self) -> bytes:
        """
        funz3 — Genera e ritorna il file .ics come bytes.

        Il calendario è costruito in real-time dal DB ad ogni chiamata:
        nessun file da mantenere sincronizzato, mirror 1:1 garantito
        per costruzione. Query singola con 3 colonne (id, inizio, fine).
        """
        from .models import Prenotazioni

        cal = Calendar()
        cal.add("prodid", self.PRODID)
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        cal.add("x-wr-calname", "Prenotazioni Nido di Anita")
        cal.add("x-wr-timezone", "Europe/Rome")
        cal.add("method", "PUBLISH")

        stamp = datetime.now(tz=timezone.utc)

        for pren_id, inizio, fine in Prenotazioni.objects.values_list("id", "inizio", "fine"):
            if inizio.tzinfo is None:
                inizio = inizio.replace(tzinfo=timezone.utc)
            if fine.tzinfo is None:
                fine = fine.replace(tzinfo=timezone.utc)

            evt = Event()
            evt.add("uid", f"{pren_id}@nidodianita")
            evt.add("dtstamp", stamp)
            evt.add("dtstart", inizio)
            evt.add("dtend", fine)
            evt.add("summary", "Occupato")
            evt.add("transp", "OPAQUE")
            cal.add_component(evt)

        return cal.to_ical()