from django.db import models
from django.conf import settings


class Prenotazioni(models.Model):
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="prenotazioni",
    )
    inizio = models.DateTimeField()
    fine = models.DateTimeField()
    stato_caparra = models.CharField(
        max_length=20,
        choices=[
            ("DA_PAGARE", "Da pagare"),
            ("DA_RESTITUIRE", "Da restituire"),
            ("COMPLETATO", "Completato")
        ],
        default="DA_PAGARE"
    )
    creato_il = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()

    class Meta:
        unique_together = [("cliente", "inizio", "fine")]

    def __str__(self):
        return f"{self.inizio.strftime('%d/%m/%Y')} - {self.fine.strftime('%d/%m/%Y')}"


class GalleryImage(models.Model):
    image = models.ImageField(upload_to="gallery/")
    objects = models.Manager()

    def __str__(self):
        return f"Foto {self.id}"


class Recensioni(models.Model):
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="recensioni",
    )
    prenotazione = models.OneToOneField(
        Prenotazioni,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    valutazione = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    titolo = models.CharField(max_length=255)
    testo = models.TextField()
    approvata = models.BooleanField(default=False)
    creata_il = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()

    @property
    def nome_recensore(self):
        return self.cliente.nome_completo if self.cliente else "Ospite"

    def __str__(self):
        return f"{self.titolo}"

class TokenPrenotazione(models.Model):
    token     = models.CharField(max_length=64, unique=True, db_index=True)
    objects=models.Manager()

    class Meta:
        db_table = "token_prenotazione"