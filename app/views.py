from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from .apps import get_ical_manager
from .models import Prenotazioni, GalleryImage, Recensioni, TokenPrenotazione

import json
import secrets

User = get_user_model()


def invia_email(subject, template_name, context, to, from_email=None,
                 plain_text="Il tuo client email non supporta HTML."):
    """
    Punto unico di invio email. Usa qualunque EMAIL_BACKEND sia configurato in
    settings.py (attualmente anymail + Resend, quindi via HTTP e non SMTP:
    su Render il traffico SMTP in uscita è bloccato, l'API HTTP no).
    """
    if isinstance(to, str):
        to = [to]

    html_content = render_to_string(template_name, context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain_text,
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        to=to,
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /account/",
        "",
        "Sitemap: https://nido-di-anita.onrender.com/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def home(request):
    return render(request, 'home.html')

def prenota(request):
    slots = get_ical_manager().get_busy_slots()
    busy_ranges = [
        [s.strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d")]
        for s, e in slots
    ]
    return render(request, 'prenota.html', {"busyRanges": busy_ranges})

def casa(request):
    all_images = GalleryImage.objects.all()
    recensioni = Recensioni.objects.filter(approvata=True).order_by("-creata_il")
    totale = recensioni.count()
    avg = round(sum(r.valutazione for r in recensioni) / totale, 1) if totale else 0

    soggiorni_recensibili = []
    soggiorno_recensibile = None
    if request.user.is_authenticated:
        soggiorni_recensibili = list(Prenotazioni.objects.filter(
            cliente=request.user,
            fine__lt=timezone.now(),
        ).exclude(recensioni__isnull=False).order_by("-fine"))
        soggiorno_recensibile = soggiorni_recensibili[0] if soggiorni_recensibili else None

    return render(request, 'casa.html', {
        "gallery_images": all_images,
        "gallery_preview": all_images[:3],
        "recensioni": recensioni,
        "avg": avg,
        "soggiorni_recensibili": soggiorni_recensibili,
        "soggiorno_recensibile": soggiorno_recensibile,
    })


@login_required
def invia_recensione(request):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)
    data = json.loads(request.body)
    try:
        prenotazione = Prenotazioni.objects.get(
            id=data["prenotazione_id"],
            cliente=request.user,
            fine__lt=timezone.now(),
        )
    except Prenotazioni.DoesNotExist:
        return JsonResponse({"ok": False, "errore": "Prenotazione non valida"}, status=403)
    if Recensioni.objects.filter(prenotazione=prenotazione).exists():
        return JsonResponse({"ok": False, "errore": "Hai già recensito questo soggiorno"}, status=400)
    Recensioni.objects.create(
        cliente=request.user,
        prenotazione=prenotazione,
        valutazione=data["valutazione"],
        titolo=data["titolo"],
        testo=data["testo"],
    )
    return JsonResponse({"ok": True})

def dintorni(request):
    return render(request, 'dintorni.html')

@login_required
@csrf_exempt
def send_mail(request):
    if request.method != "GET":
        return JsonResponse({"errore": "Metodo non consentito"}, status=405)

    try:
        note        = request.GET.get("note", "").strip()
        persone     = request.GET.get("persone")
        data_inizio = request.GET.get("start-date")
        data_fine   = request.GET.get("end-date")
        user        = request.user

        token = secrets.token_urlsafe(32)
        TokenPrenotazione.objects.create(token=token)

        approva_url = request.build_absolute_uri(
            reverse("approva_prenotazione")
            + f"?start={data_inizio}&end={data_fine}&id={user.id}&token={token}"
        )
        rifiuta_url = request.build_absolute_uri(
            reverse("rifiuta_prenotazione")
            + f"?start={data_inizio}&end={data_fine}&id={user.id}&token={token}"
        )

        invia_email(
            subject="Nuova Prenotazione",
            template_name="email_templates/mail_prenotazione.html",
            context={
                "telefono":    user.numero,
                "email":       user.email,
                "nome":        user,
                "note":        note,
                "persone":     persone,
                "data_inizio": data_inizio,
                "data_fine":   data_fine,
                "id":          user.id,
                "approva_url": approva_url,
                "rifiuta_url": rifiuta_url,
                "logo":        "ciao",
            },
            to=["nidodianita@gmail.com"],
        )

        return redirect('home')

    except Exception as e:
        return JsonResponse({"errore": str(e)}, status=500)

def approva_prenotazione(request):
    try:
        token     = request.GET.get("token")
        start_str = request.GET.get("start")
        end_str   = request.GET.get("end")
        utente_id = request.GET.get("id")

        if not token or not start_str or not end_str:
            return HttpResponse(status=400)

        with transaction.atomic():
            obj = TokenPrenotazione.objects.filter(token=token).first()
            if not obj:
                return HttpResponse("""
                    <html><body>
                    <script>setTimeout(() => window.close(), 100);</script>
                    </body></html>
                """)
            obj.delete()

        start_dt = datetime.strptime(start_str, "%d/%m/%Y")
        end_dt   = datetime.strptime(end_str,   "%d/%m/%Y")
        utente   = User.objects.get(id=utente_id)

        Prenotazioni.objects.create(
            cliente=utente,
            inizio=start_dt,
            fine=end_dt,
        )

        invia_email(
            subject="Prenotazione confermata",
            template_name="email_templates/mail_conferma.html",
            context={
                "start": start_dt.strftime("%d/%m/%Y"),
                "end":   end_dt.strftime("%d/%m/%Y"),
                "nome":  utente.first_name or utente.email,
                "logo":  "ciao",
            },
            to=utente.email,
        )

        return HttpResponse("""
            <html><body>
            <script>setTimeout(() => window.close(), 100);</script>
            </body></html>
        """)

    except ValueError as e:
        return HttpResponse(f"Formato data non valido: {e}", status=400)
    except Exception as e:
        return HttpResponse(status=500)

def rifiuta_prenotazione(request):
    try:
        token     = request.GET.get("token")
        start_str = request.GET.get("start")
        end_str   = request.GET.get("end")
        utente_id = request.GET.get("id")

        if not token or not start_str or not end_str:
            return HttpResponse(status=400)

        with transaction.atomic():
            obj = TokenPrenotazione.objects.filter(token=token).first()
            if not obj:
                return HttpResponse("""
                    <html><body>
                    <script>setTimeout(() => window.close(), 100);</script>
                    </body></html>
                """)
            obj.delete()

        start_dt = datetime.strptime(start_str, "%d/%m/%Y")
        end_dt   = datetime.strptime(end_str,   "%d/%m/%Y")
        utente   = User.objects.get(id=utente_id)

        invia_email(
            subject="Prenotazione rifiutata",
            template_name="email_templates/mail_rifiuto.html",
            context={
                "start": start_dt.strftime("%d/%m/%Y"),
                "end":   end_dt.strftime("%d/%m/%Y"),
                "nome":  utente.first_name or utente.email,
                "sito":  request.build_absolute_uri(reverse("home")),
                "logo":  "ciao",
            },
            to=utente.email,
        )

        return HttpResponse("""
            <html><body>
            <script>setTimeout(() => window.close(), 100);</script>
            </body></html>
        """)

    except ValueError as e:
        return HttpResponse(f"Formato data non valido: {e}", status=400)
    except Exception as e:
        return HttpResponse(status=500)

def serve_calendario(request):
    content = get_ical_manager().serve_personal_ical()
    return HttpResponse(
        content,
        content_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="calendario.ics"',
            "Cache-Control": "no-cache, no-store",
        },
    )
