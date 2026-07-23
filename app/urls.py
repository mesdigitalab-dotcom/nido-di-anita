from django.urls import path
from . import views

urlpatterns = [
    # Pagine pubbliche
    path('', views.home, name='home'),
    path('prenota/', views.prenota, name='prenota'),
    path('dintorni/', views.dintorni, name='dintorni'),
    path('casa/', views.casa, name='casa'),
    
    # Form prenotazione / email
    path('send_mail/', views.test, name="send_mail"),
    #path('send_mail/', views.send_mail, name="send_mail"),
    path('prenotazione/approva/', views.approva_prenotazione, name="approva_prenotazione"),
    path('prenotazione/rifiuta/', views.rifiuta_prenotazione, name="rifiuta_prenotazione"),

    path("recensione/invia/", views.invia_recensione, name="invia_recensione"),

    path('calendario.ics', views.serve_calendario, name="serve_calendario"),
]
