from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.db import models
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import (
    Kategori, Egitmen, Modul, Video, Soru, Secenek,
    KullaniciIlerleme, VideoIzleme, Mesaj,
    Gorusme, GorusmeKatilimci, KullaniciCevap,
    AktiviteOgesi, HaftalikAktivite, KullaniciAktiviteYaniti,
    DinamikTabloVerisi
)
from django.utils import timezone

# User Admin için ek alanları ekle
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'fullname', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    list_editable = ('is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'fullname')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Kişisel Bilgiler', {'fields': ('fullname', 'first_name', 'last_name', 'email', 'sorumlu_staff')}),
        ('Yetkiler', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'description': 'Kullanıcıya yönetim paneli erişimi vermek için "Staff statüsü" (is_staff) seçeneğini işaretleyin.'
        }),
        ('Önemli Tarihler', {'fields': ('last_login', 'date_joined', 'kayit_tarihi')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'fullname', 'first_name', 'last_name', 'email', 'password1', 'password2'),
        }),
        ('Yetkiler', {
            'classes': ('wide',),
            'fields': ('is_active', 'is_staff', 'is_superuser', 'sorumlu_staff'),
            'description': 'Kullanıcıya yönetim paneli erişimi vermek için "Staff statüsü" (is_staff) seçeneğini işaretleyin.'
        }),
    )
    
    def sorumlu_staff_display(self, obj):
        if obj.sorumlu_staff:
            first_name = obj.sorumlu_staff.first_name or ""
            last_name = obj.sorumlu_staff.last_name or ""
            full_name = f"{first_name} {last_name}".strip()
            return full_name if full_name else obj.sorumlu_staff.username
        return "-"
    sorumlu_staff_display.short_description = "Sorumlu Staff"
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Staff olmayan kullanıcılara sorumlu_staff olarak sadece staff kullanıcıları göster
        if db_field.name == "sorumlu_staff":
            kwargs["queryset"] = User.objects.filter(is_staff=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
        
    def save_model(self, request, obj, form, change):
        """Kullanıcı kaydedilirken kayıt tarihini bugün olarak ayarla (eğer belirtilmemişse)"""
        if not obj.pk and not hasattr(obj, 'kayit_tarihi'):
            obj.kayit_tarihi = timezone.now().date()
        super().save_model(request, obj, form, change)

# User Admin'i özelleştirilmiş versiyonla değiştir
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Admin panel kayıtları
@admin.register(Kategori)
class KategoriAdmin(admin.ModelAdmin):
    list_display = ('baslik', 'aktif', 'silindi', 'silinme_tarihi', 'olusturma_tarihi')
    search_fields = ('baslik', 'aciklama')
    list_filter = ('aktif', 'silindi')
    ordering = ['id']
    list_per_page = 20
    readonly_fields = ('silinme_tarihi', 'olusturma_tarihi')

@admin.register(Egitmen)
class EgitmenAdmin(admin.ModelAdmin):
    list_display = ('ad_soyad', 'unvan', 'email', 'aktif', 'silindi', 'silinme_tarihi')
    search_fields = ('ad_soyad', 'unvan', 'email', 'ozgecmis')
    list_filter = ('aktif', 'silindi')
    ordering = ['ad_soyad']
    list_per_page = 20
    readonly_fields = ('silinme_tarihi',)

class VideoInline(admin.TabularInline):
    model = Video
    extra = 0
    fields = ('baslik', 'sure', 'aktif')

@admin.register(Modul)
class ModulAdmin(admin.ModelAdmin):
    list_display = ('baslik', 'kategori', 'egitmen', 'video_sayisi', 'toplam_sure_formatli', 'aktif', 'hafta', 'silindi', 'silinme_tarihi', 'id')
    search_fields = ('baslik', 'aciklama', 'kategori__baslik', 'egitmen__ad_soyad', 'egitmen__unvan')
    list_filter = ('kategori', 'aktif', 'hafta', 'egitmen', 'silindi')
    inlines = [VideoInline]
    ordering = ['hafta', 'id']
    actions = ['aktif_yap', 'pasif_yap']
    list_per_page = 25
    readonly_fields = ('video_sayisi', 'toplam_sure', 'silinme_tarihi', 'olusturma_tarihi', 'guncelleme_tarihi')
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('baslik', 'aciklama', 'kategori', 'egitmen', 'resim')
        }),
        ('Erişim Ayarları', {
            'fields': ('hafta', 'aktif', 'one_cikan'),
            'description': ('Modüller, haftaları içinde ID sırasına göre kilitlenir. '
                           'Aynı haftadaki önceki modüller tamamlanmadan sonraki modül açılmaz. '
                           'Önceki haftadaki tüm modüller tamamlanmadan sonraki haftaya geçilemez.')
        }),
        ('İstatistikler', {
            'fields': ('video_sayisi', 'toplam_sure'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('video_sayisi', 'toplam_sure')
    
    def aktif_yap(self, request, queryset):
        updated = queryset.update(aktif=True)
        self.message_user(request, f'{updated} modül aktif hale getirildi.')
    aktif_yap.short_description = "Seçili modülleri aktif yap"
    
    def pasif_yap(self, request, queryset):
        updated = queryset.update(aktif=False)
        self.message_user(request, f'{updated} modül pasif hale getirildi.')
    pasif_yap.short_description = "Seçili modülleri pasif yap"

class SecenekInline(admin.TabularInline):
    model = Secenek
    extra = 1
    fields = ('secenek_metni', 'dogru_mu', 'aktif')

@admin.register(Soru)
class SoruAdmin(admin.ModelAdmin):
    list_display = ('id', 'video', 'soru_tipi', 'aktif', 'silindi', 'silinme_tarihi')
    search_fields = ('soru_metni', 'video__baslik', 'video__modul__baslik')
    list_filter = ('soru_tipi', 'aktif', 'silindi', 'video__modul')
    inlines = [SecenekInline]
    list_per_page = 20
    readonly_fields = ('silinme_tarihi', 'olusturma_tarihi', 'guncelleme_tarihi')

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('baslik', 'modul', 'sure_formatli', 'aktif', 'silindi', 'silinme_tarihi')
    search_fields = ('baslik', 'aciklama', 'modul__baslik', 'modul__kategori__baslik')
    list_filter = ('modul', 'aktif', 'silindi', 'modul__kategori')
    ordering = ['modul__hafta', 'modul', 'id']
    list_per_page = 20
    readonly_fields = ('silinme_tarihi', 'olusturma_tarihi')

@admin.register(Secenek)
class SecenekAdmin(admin.ModelAdmin):
    list_display = ('secenek_metni', 'soru', 'dogru_mu', 'aktif', 'silindi', 'silinme_tarihi')
    search_fields = ('secenek_metni', 'soru__soru_metni', 'soru__video__baslik')
    list_filter = ('dogru_mu', 'aktif', 'silindi', 'soru__soru_tipi')
    list_per_page = 20
    readonly_fields = ('silinme_tarihi', 'olusturma_tarihi', 'guncelleme_tarihi')

@admin.register(KullaniciIlerleme)
class KullaniciIlerlemeAdmin(admin.ModelAdmin):
    list_display = ('kullanici', 'modul', 'ilerleme_yuzdesi', 'tamamlandi', 'baslama_tarihi', 'silindi', 'silinme_tarihi')
    search_fields = ('kullanici__username', 'kullanici__fullname', 'modul__baslik')
    list_filter = ('tamamlandi', 'silindi')
    readonly_fields = ('silinme_tarihi',)

@admin.register(VideoIzleme)
class VideoIzlemeAdmin(admin.ModelAdmin):
    list_display = ('kullanici', 'video', 'tamamlandi', 'izleme_suresi', 'silindi', 'silinme_tarihi')
    search_fields = ('kullanici__username', 'kullanici__fullname', 'video__baslik')
    list_filter = ('tamamlandi', 'silindi')
    readonly_fields = ('silinme_tarihi',)

@admin.register(Mesaj)
class MesajAdmin(admin.ModelAdmin):
    list_display = ('konu', 'gonderen', 'alici', 'olusturma_tarihi', 'okundu', 'durum', 'silindi', 'silinme_tarihi')
    search_fields = ('konu', 'icerik', 'gonderen__username', 'gonderen__fullname', 'alici__username', 'alici__fullname')
    list_filter = ('okundu', 'durum', 'silindi')
    readonly_fields = ('silinme_tarihi',)

@admin.register(KullaniciCevap)
class KullaniciCevapAdmin(admin.ModelAdmin):
    list_display = ('kullanici', 'soru', 'secilen_secenek', 'dogru_mu', 'degerlendirildi', 'cevaplama_tarihi', 'degerlendirme_tarihi', 'metinsel_mi', 'degerlendir_butonu', 'silindi', 'silinme_tarihi')
    list_filter = ('dogru_mu', 'degerlendirildi', 'soru__soru_tipi', 'cevaplama_tarihi', 'degerlendirme_tarihi', 'silindi')
    search_fields = ('kullanici__username', 'kullanici__fullname', 'soru__soru_metni', 'secilen_secenek__secenek_metni')
    readonly_fields = ('kullanici', 'soru', 'secilen_secenek', 'cevaplama_tarihi', 'silinme_tarihi')
    fields = ('kullanici', 'soru', 'secilen_secenek', 'dogru_mu', 'degerlendirildi', 'cevaplama_tarihi', 'degerlendirme_tarihi', 'degerlendiren', 'silindi', 'silinme_tarihi')
    actions = ['degerlendir_dogru', 'degerlendir_yanlis']
    
    def metinsel_mi(self, obj):
        return obj.soru.is_metin()
    metinsel_mi.boolean = True
    metinsel_mi.short_description = "Metinsel Soru mu?"
    
    def degerlendir_butonu(self, obj):
        if obj.soru.is_metin() and not obj.degerlendirildi:
            return format_html(
                '<a class="button" href="{}">Değerlendir</a>',
                f"/admin/webui/kullanicicevap/{obj.id}/change/"
            )
        return "-"
    degerlendir_butonu.short_description = "Değerlendirme"
    
    def degerlendir_dogru(self, request, queryset):
        # Sadece değerlendirilmemiş metinsel soruları filtrele
        metinsel_cevaplar = [cevap for cevap in queryset if cevap.soru.is_metin() and not cevap.degerlendirildi]
        count = 0
        
        for cevap in metinsel_cevaplar:
            cevap.degerlendir(True, request.user)
            count += 1
            
            # Kullanıcıya değerlendirme mesajı gönder
            Mesaj.objects.create(
                gonderen=request.user,
                alici=cevap.kullanici,
                konu=f"Cevabınız Değerlendirildi: {cevap.soru.video.baslik}",
                icerik=f"'{cevap.soru.soru_metni}' sorusuna verdiğiniz '{cevap.secilen_secenek.secenek_metni}' cevabı değerlendirildi. Cevabınız doğru kabul edilmiştir."
            )
            
        self.message_user(request, f"{count} metin cevabı doğru olarak değerlendirildi ve kullanıcılara bildirim gönderildi.")
    degerlendir_dogru.short_description = "Seçili metinsel cevapları DOĞRU olarak değerlendir"
    
    def degerlendir_yanlis(self, request, queryset):
        # Sadece değerlendirilmemiş metinsel soruları filtrele
        metinsel_cevaplar = [cevap for cevap in queryset if cevap.soru.is_metin() and not cevap.degerlendirildi]
        count = 0
        
        for cevap in metinsel_cevaplar:
            cevap.degerlendir(False, request.user)
            count += 1
            
            # Kullanıcıya değerlendirme mesajı gönder
            Mesaj.objects.create(
                gonderen=request.user,
                alici=cevap.kullanici,
                konu=f"Cevabınız Değerlendirildi: {cevap.soru.video.baslik}",
                icerik=f"'{cevap.soru.soru_metni}' sorusuna verdiğiniz '{cevap.secilen_secenek.secenek_metni}' cevabınız değerlendirildi. Daha fazla çalışmanız önerilir."
            )
            
        self.message_user(request, f"{count} metin cevabı değerlendirildi ve kullanıcılara bildirim gönderildi.")
    degerlendir_yanlis.short_description = "Seçili metinsel cevapları YANLIŞ olarak değerlendir"
    
    def save_model(self, request, obj, form, change):
        """Admin panelinden kaydedildiğinde değerlendirme bilgilerini güncelle"""
        if change and obj.soru.is_metin() and 'dogru_mu' in form.changed_data:
            obj.degerlendirildi = True
            obj.degerlendirme_tarihi = timezone.now()
            obj.degerlendiren = request.user
            
            # Kullanıcıya mesaj gönder
            if obj.dogru_mu:
                mesaj_icerik = f"'{obj.soru.soru_metni}' sorusuna verdiğiniz '{obj.secilen_secenek.secenek_metni}' cevabınız değerlendirildi. Cevabınız doğru kabul edilmiştir."
            else:
                mesaj_icerik = f"'{obj.soru.soru_metni}' sorusuna verdiğiniz '{obj.secilen_secenek.secenek_metni}' cevabınız değerlendirildi. Daha fazla çalışmanız önerilir."
            
            Mesaj.objects.create(
                gonderen=request.user,
                alici=obj.kullanici,
                konu=f"Cevabınız Değerlendirildi: {obj.soru.video.baslik}",
                icerik=mesaj_icerik
            )
        
        super().save_model(request, obj, form, change)

@admin.register(Gorusme)
class GorusmeAdmin(admin.ModelAdmin):
    list_display = ('baslik', 'olusturan', 'baslangic_zamani', 'durum', 'silindi', 'silinme_tarihi')
    search_fields = ('baslik', 'aciklama', 'olusturan__username', 'olusturan__fullname')
    list_filter = ('durum', 'giris_izni', 'silindi')
    readonly_fields = ('silinme_tarihi', 'olusturma_tarihi', 'guncelleme_tarihi')

@admin.register(GorusmeKatilimci)
class GorusmeKatilimciAdmin(admin.ModelAdmin):
    list_display = ('gorusme', 'kullanici', 'davet_durumu', 'davet_zamani', 'silindi', 'silinme_tarihi')
    search_fields = ('kullanici__username', 'kullanici__fullname', 'gorusme__baslik')
    list_filter = ('davet_durumu', 'silindi')
    readonly_fields = ('silinme_tarihi',)

# Aktivite Sistemi Admin Kayıtları
class AktiviteOgesiInline(admin.TabularInline):
    model = AktiviteOgesi
    extra = 1
    fields = ('tip', 'sira', 'baslik', 'aciklama', 'zorunlu', 'aktif')

@admin.register(HaftalikAktivite)
class HaftalikAktiviteAdmin(admin.ModelAdmin):
    list_display = ['id', 'baslik', 'hafta', 'baslangic_tarihi', 'bitis_tarihi', 'tip', 'aktif', 'silindi', 'silinme_tarihi', 'olusturma_tarihi']
    list_filter = ['hafta', 'aktif', 'tip', 'silindi']
    search_fields = ['baslik', 'aciklama']
    ordering = ['hafta', 'id']
    list_editable = ['aktif']
    date_hierarchy = 'olusturma_tarihi'
    inlines = [AktiviteOgesiInline]
    actions = ['aktif_yap', 'pasif_yap']
    list_per_page = 25
    readonly_fields = ('silinme_tarihi', 'olusturma_tarihi', 'guncelleme_tarihi')
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('baslik', 'aciklama', 'hafta', 'baslangic_tarihi', 'bitis_tarihi', 'aktif', 'silindi')
        }),
        ('Erişim Ayarları', {
            'fields': ('tip',),
            'description': ('Aktiviteler, haftaları içinde ID sırasına göre kilitlenir. '
                           'Aynı haftadaki önceki aktiviteler tamamlanmadan sonraki aktivite açılmaz. '
                           'Önceki haftadaki tüm aktiviteler ve modüller tamamlanmadan sonraki haftaya geçilemez.')
        }),
        ('Diğer Bilgiler', {
            'fields': ('icerik_json', 'olusturan', 'olusturma_tarihi', 'guncelleme_tarihi'),
            'classes': ('collapse',),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.olusturan:
            obj.olusturan = request.user
        super().save_model(request, obj, form, change)
        
    def aktif_yap(self, request, queryset):
        updated = queryset.update(aktif=True)
        self.message_user(request, f'{updated} aktivite aktif hale getirildi.')
    aktif_yap.short_description = "Seçili aktiviteleri aktif yap"
    
    def pasif_yap(self, request, queryset):
        updated = queryset.update(aktif=False)
        self.message_user(request, f'{updated} aktivite pasif hale getirildi.')
    pasif_yap.short_description = "Seçili aktiviteleri pasif yap"

@admin.register(AktiviteOgesi)
class AktiviteOgesiAdmin(admin.ModelAdmin):
    list_display = ('baslik', 'aktivite', 'tip', 'sira', 'zorunlu', 'aktif', 'silindi', 'silinme_tarihi')
    list_filter = ('aktivite__hafta', 'tip', 'aktif', 'zorunlu', 'silindi')
    search_fields = ('baslik', 'aciklama', 'aktivite__baslik')
    ordering = ['aktivite__hafta', 'aktivite__id', 'sira']
    list_editable = ['sira', 'aktif', 'zorunlu']
    actions = ['aktif_yap', 'pasif_yap']
    list_per_page = 25
    readonly_fields = ('olusturma_tarihi', 'silinme_tarihi')
    
    fieldsets = (
        (None, {
            'fields': ('aktivite', 'tip', 'sira', 'baslik', 'aciklama', 'zorunlu', 'aktif', 'silindi', 'olusturma_tarihi')
        }),
        ('Tablo Yapılandırması', {
            'classes': ('collapse',),
            'fields': ('icerik_json',),
        }),
    )
    
    def aktif_yap(self, request, queryset):
        updated = queryset.update(aktif=True)
        self.message_user(request, f'{updated} aktivite öğesi aktif hale getirildi.')
    aktif_yap.short_description = "Seçili aktivite öğelerini aktif yap"
    
    def pasif_yap(self, request, queryset):
        updated = queryset.update(aktif=False)
        self.message_user(request, f'{updated} aktivite öğesi pasif hale getirildi.')
    pasif_yap.short_description = "Seçili aktivite öğelerini pasif yap"

@admin.register(KullaniciAktiviteYaniti)
class KullaniciAktiviteYanitiAdmin(admin.ModelAdmin):
    list_display = ('kullanici', 'aktivite', 'tamamlandi', 'olusturma_tarihi', 'guncelleme_tarihi', 'silindi', 'silinme_tarihi')
    list_filter = ('tamamlandi', 'aktivite__hafta', 'silindi')
    search_fields = ('kullanici__username', 'kullanici__fullname', 'aktivite__baslik')
    readonly_fields = ('kullanici', 'aktivite', 'olusturma_tarihi', 'silinme_tarihi')
    fieldsets = (
        (None, {
            'fields': ('kullanici', 'aktivite', 'tamamlandi', 'olusturma_tarihi', 'guncelleme_tarihi')
        }),
        ('Yanıt Detayları', {
            'classes': ('collapse',),
            'fields': ('yanitlar_json',),
        }),
    )

@admin.register(DinamikTabloVerisi)
class DinamikTabloVerisiAdmin(admin.ModelAdmin):
    list_display = ('tablo_adi', 'satir_id', 'sutun_id', 'kisa_deger', 'silindi', 'silinme_tarihi')
    list_filter = ('tablo_adi', 'silindi')
    search_fields = ('tablo_adi', 'deger')
    ordering = ['tablo_adi', 'satir_id', 'sutun_id']
    list_per_page = 30
    
    def kisa_deger(self, obj):
        """Değerin kısa versiyonunu göster"""
        if obj.deger and len(obj.deger) > 50:
            return obj.deger[:50] + '...'
        return obj.deger
    kisa_deger.short_description = 'Değer'
