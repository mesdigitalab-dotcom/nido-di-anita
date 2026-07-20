from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.template.response import TemplateResponse
from django.http import HttpResponseRedirect
from .models import Prenotazioni, GalleryImage, Recensioni


@admin.register(Prenotazioni)
class PrenotazioniAdmin(admin.ModelAdmin):
    list_display  = ("id", "cliente", "inizio", "fine", "stato_caparra")
    list_filter   = ("stato_caparra", "inizio", "fine", "creato_il")
    search_fields = ("cliente__email", "cliente__first_name", "cliente__last_name")
    list_editable = ("stato_caparra",)


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ("id", "preview")

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="80" style="border-radius:10px;">',
                obj.image.url,
            )
        return "-"

    change_list_template = "admin/galleryimage_change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("upload/", self.admin_site.admin_view(self.upload_view), name="gallery_upload"),
        ]
        return custom + urls

    def upload_view(self, request):
        if request.method == "POST":
            files = request.FILES.getlist("images")
            if files:
                for f in files:
                    GalleryImage.objects.create(image=f)
                self.message_user(
                    request,
                    f"{len(files)} immagin{'e caricata' if len(files)==1 else 'i caricate'} correttamente.",
                )
            else:
                self.message_user(request, "Nessuna immagine selezionata.", level="warning")
            return HttpResponseRedirect(reverse("admin:app_galleryimage_changelist"))

        context = self.admin_site.each_context(request)
        return TemplateResponse(request, "admin/gallery_upload.html", context)


@admin.register(Recensioni)
class RecensioniAdmin(admin.ModelAdmin):
    list_display = ("nome_recensore", "valutazione", "titolo", "approvata", "creata_il")
    list_filter = ("approvata", "valutazione", "creata_il")
    search_fields = ("cliente__email", "cliente__first_name", "titolo", "testo")
    list_editable = ("approvata",)
