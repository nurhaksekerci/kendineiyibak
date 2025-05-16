from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.contrib.admin import SimpleListFilter
from .models import ForumKategori, ForumKonu, ForumYorum, ForumBegeni, ForumGoruntulenme

# Özel Filtre - Silinen Öğeleri Göster/Gizle
class SilinenlerFilter(SimpleListFilter):
    title = 'Silinen Öğeler'
    parameter_name = 'silinenler'
    
    def lookups(self, request, model_admin):
        return (
            ('all', 'Tümünü Göster'),
            ('active', 'Sadece Aktif Öğeleri Göster'),
            ('deleted', 'Sadece Silinenleri Göster'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(aktif=True)
        elif self.value() == 'deleted':
            return queryset.filter(aktif=False)
        return queryset  # Tümünü göster

# Register your models here.

@admin.register(ForumKategori)
class ForumKategoriAdmin(admin.ModelAdmin):
    list_display = ('baslik', 'aciklama', 'slug', 'sira', 'ust_kategori', 'aktif', 'olusturma_tarihi')
    list_filter = (SilinenlerFilter, 'ust_kategori', 'aktif')
    search_fields = ('baslik', 'aciklama', 'slug')
    prepopulated_fields = {'slug': ('baslik',)}
    list_editable = ('sira', 'aktif')
    list_per_page = 20
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Bu düzenleme modu
            return ['olusturma_tarihi']
        return []  # Bu oluşturma modu

    def get_queryset(self, request):
        # Varsayılan olarak aktif kategorileri göster (admin arayüzünün sağ tarafındaki filtreler bunu değiştirebilir)
        qs = super().get_queryset(request)
        
        # URL'de silinenler=all veya silinenler=deleted varsa, tüm kayıtları veya silinenleri göster
        if 'silinenler' in request.GET and request.GET['silinenler'] in ['all', 'deleted']:
            return qs
        
        # Varsayılan olarak sadece aktif öğeleri göster
        return qs.filter(aktif=True)


@admin.register(ForumKonu)
class ForumKonuAdmin(admin.ModelAdmin):
    list_display = ('baslik', 'kategori', 'yazar', 'onay_durumu', 'goruntulenme', 'yorum_sayisi_admin', 'sabit', 'kapali', 'aktif', 'olusturma_tarihi', 'silinme_tarihi_goster')
    list_filter = (SilinenlerFilter, 'onay_durumu', 'kategori', 'sabit', 'kapali')
    search_fields = ('baslik', 'icerik', 'yazar__username', 'yazar__fullname', 'yazar__first_name', 'yazar__last_name')
    prepopulated_fields = {'slug': ('baslik',)}
    list_editable = ('sabit', 'kapali', 'aktif', 'onay_durumu')
    readonly_fields = ('goruntulenme', 'olusturma_tarihi', 'guncelleme_tarihi', 'silinme_tarihi')
    list_per_page = 20
    actions = ['konulari_onayla', 'konulari_reddet']
    
    def yorum_sayisi_admin(self, obj):
        return obj.yorumlar.filter(aktif=True).count()
    yorum_sayisi_admin.short_description = 'Yorum Sayısı'
    
    def silinme_tarihi_goster(self, obj):
        if obj.silinme_tarihi:
            return obj.silinme_tarihi.strftime('%d.%m.%Y %H:%M')
        return '-'
    silinme_tarihi_goster.short_description = 'Silinme Tarihi'
    
    def konulari_onayla(self, request, queryset):
        queryset.update(onay_durumu='onaylanmis', onaylayan=request.user, onay_tarihi=timezone.now())
        self.message_user(request, f"{queryset.count()} konu başarıyla onaylandı.")
    konulari_onayla.short_description = "Seçili konuları onayla"
    
    def konulari_reddet(self, request, queryset):
        queryset.update(onay_durumu='reddedilmis', onaylayan=request.user, onay_tarihi=timezone.now())
        self.message_user(request, f"{queryset.count()} konu başarıyla reddedildi.")
    konulari_reddet.short_description = "Seçili konuları reddet"

    def get_queryset(self, request):
        # Varsayılan olarak aktif konuları göster (admin arayüzünün sağ tarafındaki filtreler bunu değiştirebilir)
        qs = super().get_queryset(request)
        
        # URL'de silinenler=all veya silinenler=deleted varsa, tüm kayıtları veya silinenleri göster
        if 'silinenler' in request.GET and request.GET['silinenler'] in ['all', 'deleted']:
            return qs
        
        # Varsayılan olarak sadece aktif öğeleri göster
        return qs.filter(aktif=True)


@admin.register(ForumYorum)
class ForumYorumAdmin(admin.ModelAdmin):
    list_display = ('kisa_icerik', 'konu_link', 'yazar', 'ust_yorum', 'aktif', 'olusturma_tarihi', 'silinme_tarihi_goster')
    list_filter = (SilinenlerFilter, 'konu__kategori', 'aktif')
    search_fields = ('icerik', 'yazar__username', 'yazar__fullname', 'yazar__first_name', 'yazar__last_name', 'konu__baslik')
    list_editable = ('aktif',)
    readonly_fields = ('olusturma_tarihi', 'guncelleme_tarihi', 'silinme_tarihi')
    list_per_page = 20
    
    def kisa_icerik(self, obj):
        return obj.icerik[:50] + '...' if len(obj.icerik) > 50 else obj.icerik
    kisa_icerik.short_description = 'İçerik'
    
    def silinme_tarihi_goster(self, obj):
        if obj.silinme_tarihi:
            return obj.silinme_tarihi.strftime('%d.%m.%Y %H:%M')
        return '-'
    silinme_tarihi_goster.short_description = 'Silinme Tarihi'
    
    def konu_link(self, obj):
        return format_html('<a href="{}">{}</a>', 
                          f'/admin/forum/forumkonu/{obj.konu.id}/change/', 
                          obj.konu.baslik)
    konu_link.short_description = 'Konu'

    def get_queryset(self, request):
        # Varsayılan olarak aktif yorumları göster (admin arayüzünün sağ tarafındaki filtreler bunu değiştirebilir)
        qs = super().get_queryset(request)
        
        # URL'de silinenler=all veya silinenler=deleted varsa, tüm kayıtları veya silinenleri göster
        if 'silinenler' in request.GET and request.GET['silinenler'] in ['all', 'deleted']:
            return qs
        
        # Varsayılan olarak sadece aktif öğeleri göster
        return qs.filter(aktif=True)


@admin.register(ForumBegeni)
class ForumBegeniAdmin(admin.ModelAdmin):
    list_display = ('kullanici', 'konu_referans', 'yorum_referans', 'tur', 'olusturma_tarihi')
    list_filter = ('tur', 'olusturma_tarihi')
    search_fields = ('kullanici__username', 'kullanici__fullname', 'kullanici__first_name', 'kullanici__last_name', 'konu__baslik', 'yorum__icerik')
    readonly_fields = ('olusturma_tarihi',)
    list_per_page = 20
    
    def konu_referans(self, obj):
        if obj.konu:
            return format_html('<a href="{}">{}</a>', 
                              f'/admin/forum/forumkonu/{obj.konu.id}/change/', 
                              obj.konu.baslik)
        return '-'
    konu_referans.short_description = 'Konu'
    
    def yorum_referans(self, obj):
        if obj.yorum:
            return format_html('<a href="{}">{}</a>', 
                              f'/admin/forum/forumyorum/{obj.yorum.id}/change/', 
                              obj.yorum.icerik[:30] + '...' if len(obj.yorum.icerik) > 30 else obj.yorum.icerik)
        return '-'
    yorum_referans.short_description = 'Yorum'


@admin.register(ForumGoruntulenme)
class ForumGoruntulenmeAdmin(admin.ModelAdmin):
    list_display = ('kullanici', 'konu', 'olusturma_tarihi')
    list_filter = ('olusturma_tarihi',)
    search_fields = ('kullanici__username', 'kullanici__fullname', 'kullanici__first_name', 'kullanici__last_name', 'konu__baslik')
    readonly_fields = ('olusturma_tarihi',)
    list_per_page = 20
