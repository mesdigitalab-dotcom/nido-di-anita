# nomeapp1/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        # metti qui i "name" delle tue path, non gli URL letterali
        return ["home", "casa", "dintorni", "prenota"]

    def location(self, item):
        return reverse(item)
