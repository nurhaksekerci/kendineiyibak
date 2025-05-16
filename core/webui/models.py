from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils import timezone
import uuid
import json
from datetime import timedelta

# Bugünün tarihini döndüren fonksiyon
def get_today():
    return timezone.now().date()

# User modeline fullname alanı ekle
User.add_to_class('fullname', models.CharField(max_length=100, null=True, blank=True))

# User modeline sorumlu staff eklentisi
User.add_to_class('sorumlu_staff', models.ForeignKey(
    'self', 
    on_delete=models.SET_NULL, 
    null=True, 
    blank=True, 
    related_name='sorumlu_kullanicilar',
    verbose_name="Sorumlu Staff Üye"
))

# User modeline kayıt tarihi eklentisi
User.add_to_class('kayit_tarihi', models.DateField(default=get_today, verbose_name="Kayıt Tarihi"))

# Create your models here.

class Kategori(models.Model):
    """Eğitim kategorileri (Temel Bakım, İletişim Teknikleri, vb.)"""
    baslik = models.CharField(max_length=100)
    aciklama = models.TextField()
    aktif = models.BooleanField(default=True)
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    silindi = models.BooleanField(default=False)
    silinme_tarihi = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Kategori"
        verbose_name_plural = "Kategoriler"
        ordering = ['id']
    
    def __str__(self):
        return self.baslik
    
    def save(self, *args, **kwargs):
        # Direkt olarak kaydet, sıra numarası artık kullanılmıyor
        super().save(*args, **kwargs)

class Egitmen(models.Model):
    """Eğitim veren uzmanlar"""
    ad_soyad = models.CharField(max_length=100)
    unvan = models.CharField(max_length=100, blank=True)
    ozgecmis = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    profil_resmi = models.ImageField(upload_to='egitmenler/', blank=True, null=True)
    aktif = models.BooleanField(default=True)
    silindi = models.BooleanField(default=False)
    silinme_tarihi = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Eğitmen"
        verbose_name_plural = "Eğitmenler"
    
    def __str__(self):
        return f"{self.unvan} {self.ad_soyad}"

class Modul(models.Model):
    """Eğitim modülleri"""
    baslik = models.CharField(max_length=200, verbose_name="Başlık")
    aciklama = models.TextField(verbose_name="Açıklama")
    kategori = models.ForeignKey(Kategori, on_delete=models.CASCADE, related_name='moduller', verbose_name="Kategori")
    egitmen = models.ForeignKey(Egitmen, on_delete=models.SET_NULL, null=True, blank=True, related_name='moduller', verbose_name="Eğitmen")
    resim = models.ImageField(upload_to='modul_resimleri/', null=True, blank=True, help_text="Modül için kapak resmi")
    video_sayisi = models.PositiveSmallIntegerField(default=0)
    toplam_sure = models.PositiveIntegerField(help_text="Saniye cinsinden toplam süre", default=0)
    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    one_cikan = models.BooleanField(default=False, help_text="Öne çıkan modül olarak işaretlenirse, giriş yapmamış kullanıcılara gösterilir")
    hafta = models.PositiveSmallIntegerField(default=1, verbose_name="Hafta", help_text="Modülün hangi haftada erişilebilir olacağı")
    baslangic_tarihi = models.DateField(null=True, blank=True, verbose_name="Başlangıç Tarihi", help_text="Bu haftanın başlangıç tarihi (Artık kullanılmıyor, eski veriler için tutuldu)")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturma Tarihi")
    guncelleme_tarihi = models.DateTimeField(auto_now=True, verbose_name="Güncelleme Tarihi")
    silindi = models.BooleanField(default=False)
    silinme_tarihi = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Modül"
        verbose_name_plural = "Modüller"
        ordering = ['id']
    
    def __str__(self):
        return self.baslik
    
    @property
    def toplam_sure_formatli(self):
        """Toplam süreyi dakika ve saniye formatında döndürür."""
        toplam_saniye = self.toplam_sure
        dakika = toplam_saniye // 60
        saniye = toplam_saniye % 60
        if saniye > 0:
            return f"{dakika} dk {saniye} sn"
        return f"{dakika} dk"
        
    def guncelle_video_bilgileri(self):
        """Video sayısı ve toplam süreyi günceller"""
        # Aktif videoları filtrele
        aktif_videolar = self.videolar.filter(aktif=True)
        
        # Video sayısını güncelle
        self.video_sayisi = aktif_videolar.count()
        
        # Toplam süreyi güncelle (saniye cinsinden)
        toplam_sure = aktif_videolar.aggregate(toplam=Sum('sure'))['toplam'] or 0
        self.toplam_sure = toplam_sure
        
        # Değişiklikleri kaydet
        self.save(update_fields=['video_sayisi', 'toplam_sure'])
        
        # Kullanıcı ilerlemelerini güncelle
        self.guncelle_kullanici_ilerlemeleri()
        
    def guncelle_kullanici_ilerlemeleri(self):
        """Bu modüle ait tüm kullanıcı ilerlemelerini günceller"""
        from django.db.models import Count
        
        # Modüldeki aktif ve toplam video sayısını al
        toplam_video_sayisi = self.videolar.filter(aktif=True).count()
        
        # Eğer modülde hiç video yoksa işlem yapma
        if toplam_video_sayisi == 0:
            return
            
        # Bu modüle ait tüm kullanıcı ilerlemelerini al
        ilerlemeler = KullaniciIlerleme.objects.filter(modul=self)
        
        for ilerleme in ilerlemeler:
            # Kullanıcının bu modüldeki izlediği videoları say
            izlenen_video_sayisi = VideoIzleme.objects.filter(
                kullanici=ilerleme.kullanici,
                video__modul=self,
                tamamlandi=True
            ).count()
            
            # İlerleme yüzdesini hesapla
            yeni_ilerleme_yuzdesi = int((izlenen_video_sayisi / toplam_video_sayisi) * 100)
            
            # İlerleme durumunu güncelle
            ilerleme.ilerleme_yuzdesi = yeni_ilerleme_yuzdesi
            
            # Tamamlanma durumunu güncelle
            eski_tamamlandi = ilerleme.tamamlandi
            ilerleme.tamamlandi = yeni_ilerleme_yuzdesi == 100
            
            # Tamamlanma durumu değiştiyse, tamamlanma tarihini güncelle
            if not eski_tamamlandi and ilerleme.tamamlandi:
                ilerleme.tamamlanma_tarihi = timezone.now()
            elif eski_tamamlandi and not ilerleme.tamamlandi:
                ilerleme.tamamlanma_tarihi = None
                
            # Değişiklikleri kaydet
            ilerleme.save()
    
    def kullaniciya_acik_mi(self, kullanici):
        """
        Modülün kullanıcıya açık olup olmadığını kontrol eder.
        Kullanıcının kayıt tarihine göre hesaplama yapar.
        Hafta 1 her zaman erişilebilirdir.
        Ayrıca önceki hafta modülleri ve aktiviteleri tamamlanmışsa bir sonraki haftaya erişim izni verir.
        Aynı haftadaki modüller bu versiyon ile birlikte sırayla değil, toplu olarak erişime açılır.
        """
        # Admin ve superuser her zaman erişebilir
        if kullanici.is_superuser or kullanici.is_staff:
            return True
            
        # İlk hafta her zaman erişilebilir
        if self.hafta == 1:
            return True
            
        # Kullanıcının kayıt tarihini al
        kayit_tarihi = getattr(kullanici, 'kayit_tarihi', None) or kullanici.date_joined.date()
        
        # Bugünün tarihini al - timezone.now() yerine timezone.localtime() kullan
        bugun = timezone.localtime().date()
        
        # Modülün erişilebilir olduğu tarih (kayıt tarihine hafta sayısı * 7 gün ekle)
        erisim_tarihi = kayit_tarihi + timedelta(days=(self.hafta - 1) * 7)
        
        # Eğer bugün, erişim tarihinden sonra veya aynıysa erişim koşullarını kontrol et
        if bugun >= erisim_tarihi:
            # Önceki hafta modüllerinin tamamlanma durumunu kontrol et
            if self.hafta > 1:
                try:
                    onceki_hafta = self.hafta - 1
                    onceki_hafta_modulleri = Modul.objects.filter(
                        aktif=True,
                        silindi=False,
                        hafta=onceki_hafta
                    )
                    
                    # Önceki haftanın tüm modüllerinin tamamlanmış olması gerekiyor
                    for modul in onceki_hafta_modulleri:
                        ilerleme = KullaniciIlerleme.objects.filter(
                            kullanici=kullanici,
                            modul=modul
                        ).first()
                        
                        if not ilerleme or not (ilerleme.tamamlandi or ilerleme.ilerleme_yuzdesi == 100):
                            return False
                    
                    # Önceki hafta aktivitelerinin tamamlanma durumunu kontrol et
                    try:
                        from .models import HaftalikAktivite, KullaniciAktiviteYaniti
                        
                        onceki_hafta_aktiviteleri = HaftalikAktivite.objects.filter(
                            aktif=True,
                            silindi=False, 
                            hafta=onceki_hafta
                        )
                        
                        # Önceki haftanın tüm aktivitelerinin tamamlanmış olması gerekiyor
                        for aktivite in onceki_hafta_aktiviteleri:
                            yanit = KullaniciAktiviteYaniti.objects.filter(
                                kullanici=kullanici,
                                aktivite=aktivite
                            ).first()
                            
                            if not yanit or not yanit.tamamlandi:
                                return False
                    except Exception as e:
                        # HaftalikAktivite modeli henüz oluşturulmamış olabilir
                        pass
                except Exception as e:
                    # Hata durumunda, güvenli tarafta kalarak erişime izin verme
                    return False
            
            # Tüm kontroller geçildiyse erişime izin ver
            return True
        
        # Erişim tarihinden önce ise erişimi reddet
        return False
        
    def save(self, *args, **kwargs):
        # Sıra numarası artık kullanılmıyor
        # Doğrudan kaydet
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Eğer yeni oluşturulmuyorsa ve update_fields içinde video_sayisi veya toplam_sure yoksa
        # video bilgilerini güncelle
        if not is_new and (not kwargs.get('update_fields') or 
                          not all(field in kwargs.get('update_fields', []) 
                                 for field in ['video_sayisi', 'toplam_sure'])):
            self.guncelle_video_bilgileri()
            
    def delete(self, *args, **kwargs):
        """Modülü sil"""
        # Direkt olarak modülü sil, sıra numaralarıyla ilgili hiçbir işlem yapma
        super().delete(*args, **kwargs)

class Video(models.Model):
    """Eğitim videoları"""
    baslik = models.CharField(max_length=200)
    aciklama = models.TextField()
    modul = models.ForeignKey(Modul, on_delete=models.CASCADE, related_name='videolar')
    video_url = models.URLField(blank=True, null=True, help_text="YouTube veya diğer video platformu URL'i (opsiyonel)")
    dosya = models.FileField(upload_to='videolar/', null=True, blank=True, help_text="MP4, WebM veya diğer video formatında dosya yükleyebilirsiniz")
    thumbnail_image = models.ImageField(upload_to='thumbnails/', null=True, blank=True, help_text="Video için özel kapak görseli yükleyebilirsiniz")
    thumbnail_url = models.URLField(blank=True, null=True, help_text="Video için kapak görseli URL'i (opsiyonel)")
    sure = models.PositiveIntegerField(help_text="Saniye cinsinden video süresi")
    aktif = models.BooleanField(default=True)
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    silindi = models.BooleanField(default=False)
    silinme_tarihi = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Video"
        verbose_name_plural = "Videolar"
        ordering = ['id']
    
    def __str__(self):
        return f"{self.modul.baslik} - {self.baslik}"
    
    def sure_formatli(self):
        """Video süresini dakika:saniye formatında döndürür"""
        dakika = self.sure // 60
        saniye = self.sure % 60
        return f"{dakika}:{saniye:02d}"
    
    def dakika_formatli(self):
        """Video süresini dakika olarak döndürür (ondalıklı)"""
        return round(self.sure / 60, 1)
    
    def get_video_source(self):
        """Video kaynağını döndürür (URL veya dosya)"""
        if self.video_url:
            return self.video_url
        elif self.dosya:
            return self.dosya.url
        return None
    
    def get_thumbnail(self):
        """Video için thumbnail kaynağını döndürür (URL veya dosya)"""
        if self.thumbnail_image:
            return self.thumbnail_image.url
        elif self.thumbnail_url:
            return self.thumbnail_url
        return None
        
    def save(self, *args, **kwargs):
        # Önce videoyu kaydet
        super().save(*args, **kwargs)
        # Modül bilgilerini güncelle
        self.modul.guncelle_video_bilgileri()
        
    def delete(self, *args, **kwargs):
        # Modül referansını sakla
        modul = self.modul
        # Videoyu sil
        super().delete(*args, **kwargs)
        # Modül bilgilerini güncelle
        modul.guncelle_video_bilgileri()
        # Kullanıcı ilerlemelerini güncelle
        modul.guncelle_kullanici_ilerlemeleri()

class Soru(models.Model):
    """Video sonrası sorular"""
    SORU_TIPLERI = (
        ('coktan_secmeli', 'Çoktan Seçmeli'),
        ('dogru_yanlis', 'Doğru/Yanlış'),
        ('metin', 'Metin Cevaplı'),
    )
    
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='sorular')
    soru_metni = models.TextField()
    soru_tipi = models.CharField(max_length=20, choices=SORU_TIPLERI, default='coktan_secmeli')
    dogru_cevap_metni = models.TextField(blank=True, null=True, help_text="Metin tipi sorular için doğru cevap")
    aktif = models.BooleanField(default=True)
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    guncelleme_tarihi = models.DateTimeField(auto_now=True)
    silindi = models.BooleanField(default=False)
    silinme_tarihi = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Soru"
        verbose_name_plural = "Sorular"
        ordering = ['id']
    
    def __str__(self):
        return f"{self.video.baslik} - Soru {self.id}"
        
    def get_soru_tipi_display_name(self):
        return dict(self.SORU_TIPLERI).get(self.soru_tipi, "Bilinmeyen Tip")
        
    def is_coktan_secmeli(self):
        return self.soru_tipi == 'coktan_secmeli'
        
    def is_dogru_yanlis(self):
        return self.soru_tipi == 'dogru_yanlis'
        
    def is_metin(self):
        return self.soru_tipi == 'metin'

    def save(self, *args, **kwargs):
        # Direkt olarak kaydet, sıra numarası artık kullanılmıyor
        super().save(*args, **kwargs)

class Secenek(models.Model):
    """Soru seçenekleri"""
    soru = models.ForeignKey(Soru, on_delete=models.CASCADE, related_name='secenekler')
    secenek_metni = models.CharField(max_length=255)
    dogru_mu = models.BooleanField(default=False)
    aktif = models.BooleanField(default=True)
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    guncelleme_tarihi = models.DateTimeField(auto_now=True)
    silindi = models.BooleanField(default=False)
    silinme_tarihi = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Seçenek"
        verbose_name_plural = "Seçenekler"
        ordering = ['id']
    
    def __str__(self):
        return f"{self.soru} - {self.secenek_metni}"

    def save(self, *args, **kwargs):
        # Direkt olarak kaydet, sıra numarası artık kullanılmıyor
        super().save(*args, **kwargs)

class KullaniciIlerleme(models.Model):
    """Kullanıcının modül bazında ilerleme durumu"""
    kullanici = models.ForeignKey(User, on_delete=models.CASCADE)
    modul = models.ForeignKey('Modul', on_delete=models.CASCADE)
    ilerleme_yuzdesi = models.IntegerField(default=0)
    en_yuksek_ilerleme_yuzdesi = models.IntegerField(default=0)
    tamamlandi = models.BooleanField(default=False)
    baslama_tarihi = models.DateTimeField(auto_now_add=True)
    tamamlanma_tarihi = models.DateTimeField(null=True, blank=True)
    silindi = models.BooleanField(default=False)
    silinme_tarihi = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Kullanıcı İlerlemesi"
        verbose_name_plural = "Kullanıcı İlerlemeleri"
        unique_together = ('kullanici', 'modul')

    def __str__(self):
        return f"{self.kullanici.username} - {self.modul.baslik} - %{self.ilerleme_yuzdesi}"

    def save(self, *args, **kwargs):
        # İlk kez oluşturuluyorsa
        if not self.pk:
            self.en_yuksek_ilerleme_yuzdesi = self.ilerleme_yuzdesi
        else:
            # Mevcut en yüksek ilerleme yüzdesini kontrol et
            if self.ilerleme_yuzdesi > self.en_yuksek_ilerleme_yuzdesi:
                self.en_yuksek_ilerleme_yuzdesi = self.ilerleme_yuzdesi

        # Tamamlanma durumunu mevcut ilerleme yüzdesine göre güncelle
        eski_tamamlandi = self.tamamlandi
        self.tamamlandi = self.ilerleme_yuzdesi == 100

        # Tamamlanma tarihini güncelle
        if not eski_tamamlandi and self.tamamlandi:
            self.tamamlanma_tarihi = timezone.now()
        elif not self.tamamlandi:
            self.tamamlanma_tarihi = None

        super().save(*args, **kwargs)

class VideoIzleme(models.Model):
    """Kullanıcının video izleme kaydı"""
    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, related_name='izlemeler')
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    tamamlandi = models.BooleanField(default=False)
    izleme_suresi = models.PositiveIntegerField(default=0, help_text="Saniye cinsinden izleme süresi")
    son_izleme_tarihi = models.DateTimeField(auto_now=True)
    silindi = models.BooleanField(default=False)
    silinme_tarihi = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Video İzleme"
        verbose_name_plural = "Video İzlemeler"
        unique_together = ['kullanici', 'video']
    
    def __str__(self):
        return f"{self.kullanici.username} - {self.video.baslik}"

class Mesaj(models.Model):
    """Kullanıcı mesajları ve geri bildirimleri"""
    MESAJ_DURUMLARI = (
        ('bekliyor', 'Bekliyor'),
        ('cevaplandi', 'Cevaplandı'),
        ('kapatildi', 'Kapatıldı'),
    )
    
    gonderen = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gonderilen_mesajlar')
    alici = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alinan_mesajlar', null=True, blank=True)
    konu = models.CharField(max_length=255)
    icerik = models.TextField()
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    okundu = models.BooleanField(default=False)
    okunma_tarihi = models.DateTimeField(null=True, blank=True)
    durum = models.CharField(max_length=20, choices=MESAJ_DURUMLARI, default='bekliyor')
    cevap_mesaji = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='cevaplar')
    silindi = models.BooleanField(default=False)
    silinme_tarihi = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Mesaj"
        verbose_name_plural = "Mesajlar"
        ordering = ['-olusturma_tarihi']
    
    def __str__(self):
        return f"{self.gonderen.username} -> {self.konu}"
    
    def okundu_isaretle(self):
        """Mesajı okundu olarak işaretler"""
        self.okundu = True
        self.okunma_tarihi = timezone.now()
        self.save(update_fields=['okundu', 'okunma_tarihi'])
    
    def cevapla(self, cevap_icerik, cevaplayan_kullanici):
        """Mesaja cevap verir ve durumunu günceller"""
        cevap = Mesaj.objects.create(
            gonderen=cevaplayan_kullanici,
            alici=self.gonderen,
            konu=f"RE: {self.konu}",
            icerik=cevap_icerik,
            cevap_mesaji=self
        )
        
        self.durum = 'cevaplandi'
        self.save(update_fields=['durum'])
        
        return cevap

class Gorusme(models.Model):
    DURUM_CHOICES = (
        ('bekliyor', 'Bekliyor'),
        ('aktif', 'Aktif'),
        ('tamamlandi', 'Tamamlandı'),
        ('iptal', 'İptal Edildi'),
    )
    
    GIRIS_IZNI_CHOICES = (
        ('davetli', 'Sadece Davetliler'),
        ('herkes', 'Herkes (Link ile)'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    baslik = models.CharField(max_length=255, verbose_name="Görüşme Başlığı")
    aciklama = models.TextField(null=True, blank=True, verbose_name="Görüşme Açıklaması")
    olusturan = models.ForeignKey(User, on_delete=models.CASCADE, related_name="olusturulan_gorusmeler")
    baslangic_zamani = models.DateTimeField(verbose_name="Başlangıç Zamanı")
    bitis_zamani = models.DateTimeField(null=True, blank=True, verbose_name="Bitiş Zamanı")
    sure_dakika = models.PositiveIntegerField(null=True, blank=True, verbose_name="Süre (dakika)")
    durum = models.CharField(max_length=15, choices=DURUM_CHOICES, default='bekliyor', verbose_name="Durum")
    giris_izni = models.CharField(max_length=15, choices=GIRIS_IZNI_CHOICES, default='davetli', verbose_name="Giriş İzni")
    kayit_alsinmi = models.BooleanField(default=False, verbose_name="Kayıt Alınsın mı?")
    kayit_url = models.URLField(null=True, blank=True, verbose_name="Kayıt URL")
    jitsi_oda_adi = models.CharField(max_length=255, unique=True, verbose_name="Jitsi Oda Adı")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturma Tarihi")
    guncelleme_tarihi = models.DateTimeField(auto_now=True, verbose_name="Güncelleme Tarihi")
    silindi = models.BooleanField(default=False)
    silinme_tarihi = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Görüşme"
        verbose_name_plural = "Görüşmeler"
        ordering = ['-baslangic_zamani']
    
    def __str__(self):
        return self.baslik
    
    def katilimci_sayisi(self):
        return self.katilimcilar.count() + 1  # +1 for creator
    
    def oda_linki(self):
        return f"https://meet.jit.si/{self.jitsi_oda_adi}"
    
    def is_active(self):
        return self.durum == 'aktif'
    
    def can_join(self, user):
        if self.giris_izni == 'herkes':
            return True
        if self.olusturan == user:
            return True
        # Staff kullanıcılar her zaman katılabilir
        if user.is_staff:
            return True
        # Herhangi bir davet durumundaki kullanıcılar katılabilir (bekliyor, kabul, red)
        return self.katilimcilar.filter(kullanici=user).exists()
        
    def bildirim_gonder(self, bildirim_turu):
        """
        Görüşmeyle ilgili bildirimleri katılımcılara gönderir
        bildirim_turu: 'planlandi' veya 'aktif'
        """
        from django.db.models import Q
        from django.utils import timezone
        
        # Bildirim içeriğini hazırla
        tarih_formatli = self.baslangic_zamani.strftime('%d.%m.%Y %H:%M')
        if bildirim_turu == 'planlandi':
            konu = f"Toplantı Planlandı: {self.baslik}"
            icerik = f"Merhaba,\n\n{tarih_formatli} tarihinde '{self.baslik}' başlıklı toplantınız planlanmıştır. Belirtilen saatte katılım sağlayabilirsiniz.\n\nToplantı Linki: {self.oda_linki()}\n\nKendine İyi Bak Platformu"
        elif bildirim_turu == 'aktif':
            konu = f"Toplantı Başladı: {self.baslik}"
            icerik = f"Merhaba,\n\nŞu anda '{self.baslik}' başlıklı toplantınız aktif durumdadır. Toplantıya hemen katılabilirsiniz.\n\nToplantı Linki: {self.oda_linki()}\n\nKendine İyi Bak Platformu"
        else:
            return False
        
        # Katılımcı listesini al (kabul eden ve bekleyen)
        katilimcilar = self.katilimcilar.filter(
            Q(davet_durumu='kabul') | Q(davet_durumu='bekliyor')
        ).values_list('kullanici', flat=True)
        
        # Bildirim gönder
        bildirimler = []
        
        # Oluşturana bildirim
        Mesaj.objects.create(
            gonderen=self.olusturan,
            alici=self.olusturan,
            konu=konu,
            icerik=icerik,
            durum='bekliyor'
        )
        
        # Katılımcılara bildirim
        for katilimci_id in katilimcilar:
            try:
                katilimci = User.objects.get(id=katilimci_id)
                Mesaj.objects.create(
                    gonderen=self.olusturan,
                    alici=katilimci,
                    konu=konu,
                    icerik=icerik,
                    durum='bekliyor'
                )
            except User.DoesNotExist:
                continue
        
        return True

class GorusmeKatilimci(models.Model):
    gorusme = models.ForeignKey(Gorusme, on_delete=models.CASCADE, related_name="katilimcilar")
    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, related_name="gorusme_katilimlari")
    davet_zamani = models.DateTimeField(auto_now_add=True)
    davet_durumu = models.CharField(max_length=15, choices=(
        ('bekliyor', 'Bekliyor'),
        ('kabul', 'Kabul Edildi'),
        ('red', 'Reddedildi')
    ), default='bekliyor')
    katilim_zamani = models.DateTimeField(null=True, blank=True)
    ayrilma_zamani = models.DateTimeField(null=True, blank=True)
    silindi = models.BooleanField(default=False)
    silinme_tarihi = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Görüşme Katılımcısı"
        verbose_name_plural = "Görüşme Katılımcıları"
        unique_together = ('gorusme', 'kullanici')
    
    def __str__(self):
        return f"{self.kullanici.username} - {self.gorusme.baslik}"

class KullaniciCevap(models.Model):
    """Kullanıcının sorulara verdiği cevaplar"""
    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cevaplar')
    soru = models.ForeignKey(Soru, on_delete=models.CASCADE)
    secilen_secenek = models.ForeignKey(Secenek, on_delete=models.CASCADE)
    dogru_mu = models.BooleanField(default=False)
    cevaplama_tarihi = models.DateTimeField(auto_now_add=True)
    degerlendirildi = models.BooleanField(default=False, verbose_name="Değerlendirildi mi?")
    degerlendirme_tarihi = models.DateTimeField(null=True, blank=True, verbose_name="Değerlendirme Tarihi")
    degerlendiren = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                     related_name='degerlendirdigi_cevaplar', verbose_name="Değerlendiren Kişi")
    silindi = models.BooleanField(default=False)
    silinme_tarihi = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Kullanıcı Cevabı"
        verbose_name_plural = "Kullanıcı Cevapları"
        unique_together = ['kullanici', 'soru']
    
    def __str__(self):
        return f"{self.kullanici.username} - {self.soru}"
    
    def save(self, *args, **kwargs):
        # Metin tipi sorular için değerlendirme kontrolü yapma, diğer türler için otomatik değerlendir
        if not self.soru.is_metin():
            # Cevap doğru mu kontrolü
            self.dogru_mu = self.secilen_secenek.dogru_mu
            self.degerlendirildi = True
        else:
            # Eğer metin sorusu ve değerlendirildiyse ve değerlendirme tarihi boşsa
            if self.degerlendirildi and not self.degerlendirme_tarihi:
                self.degerlendirme_tarihi = timezone.now()
        
        super().save(*args, **kwargs)
        
    def degerlendir(self, dogru_mu, degerlendiren_user):
        """Metinsel soruyu değerlendirir"""
        self.dogru_mu = dogru_mu
        self.degerlendirildi = True
        self.degerlendirme_tarihi = timezone.now()
        self.degerlendiren = degerlendiren_user
        self.save()

class DinamikTabloVerisi(models.Model):
    """Dinamik tablo veri modeli"""
    tablo_adi = models.CharField(max_length=100)
    satir_id = models.PositiveIntegerField()
    sutun_id = models.PositiveIntegerField()
    deger = models.TextField(blank=True, null=True)
    silindi = models.BooleanField(default=False)
    silinme_tarihi = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Dinamik Tablo Verisi"
        verbose_name_plural = "Dinamik Tablo Verileri"
        unique_together = ('tablo_adi', 'satir_id', 'sutun_id')
    
    def __str__(self):
        return f"{self.tablo_adi} - Satır {self.satir_id}, Sütun {self.sutun_id}"

# Haftalık Aktivite Sistemi
class HaftalikAktivite(models.Model):
    """Haftaya özel aktiviteler"""
    AKTIVITE_TIPLERI = (
        ('checkbox', 'Onay Kutuları'),
        ('tablo', 'Tablo'),
        ('metin', 'Metin Alanı'),
        ('karma', 'Karma (Birden Fazla Tip)'),
    )
    
    baslik = models.CharField(max_length=255, verbose_name="Aktivite Başlığı")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Aktivite Açıklaması")
    hafta = models.PositiveSmallIntegerField(default=1, verbose_name="Hafta", 
                                           help_text="Aktivitenin hangi haftada görüntüleneceği")
    baslangic_tarihi = models.DateField(null=True, blank=True, verbose_name="Başlangıç Tarihi", 
                                      help_text="Bu aktivitenin erişilebilir olacağı başlangıç tarihi (Artık kullanılmıyor, eski veriler için tutuldu)")
    bitis_tarihi = models.DateField(null=True, blank=True, verbose_name="Bitiş Tarihi", 
                                  help_text="Bu aktivitenin erişilebilir olacağı son tarih (Artık kullanılmıyor, eski veriler için tutuldu)")
    tip = models.CharField(max_length=20, choices=AKTIVITE_TIPLERI, default='karma', verbose_name="Aktivite Tipi")
    aktif = models.BooleanField(default=True, verbose_name="Aktif mi?")
    icerik_json = models.TextField(null=True, blank=True, verbose_name="İçerik (JSON)", 
                                 help_text="Aktivitenin yapısını tanımlayan JSON verisi")
    olusturan = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name="olusturdugu_aktiviteler", verbose_name="Oluşturan")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturma Tarihi")
    guncelleme_tarihi = models.DateTimeField(auto_now=True, verbose_name="Güncelleme Tarihi")
    silindi = models.BooleanField(default=False, verbose_name="Silindi mi?")
    silinme_tarihi = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Haftalık Aktivite"
        verbose_name_plural = "Haftalık Aktiviteler"
        ordering = ['hafta', '-olusturma_tarihi']
    
    def __str__(self):
        return f"{self.hafta}. Hafta - {self.baslik}"
    
    def ogeleri_getir(self):
        """Aktiviteye ait öğeleri döndürür"""
        return self.ogeler.filter(aktif=True, silindi=False).order_by('sira')
    
    def kullanici_yaniti_varmi(self, kullanici):
        """Kullanıcının bu aktiviteye yanıt verip vermediğini kontrol eder"""
        return KullaniciAktiviteYaniti.objects.filter(aktivite=self, kullanici=kullanici).exists()
        
    def kullanici_yaniti_getir(self, kullanici):
        """Kullanıcının bu aktiviteye verdiği yanıtı döndürür"""
        try:
            return KullaniciAktiviteYaniti.objects.get(aktivite=self, kullanici=kullanici)
        except KullaniciAktiviteYaniti.DoesNotExist:
            return None
            
    def kullaniciya_acik_mi(self, kullanici):
        """
        Aktivitenin kullanıcıya açık olup olmadığını kontrol eder.
        Kullanıcının kayıt tarihine göre hesaplama yapar.
        Hafta 1 her zaman erişilebilirdir.
        Önceki hafta modülleri ve aktiviteleri tamamlanmışsa bir sonraki haftaya erişim izni verir.
        Aynı haftadaki aktiviteler bu versiyon ile birlikte sırayla değil, toplu olarak erişime açılır.
        """
        # Admin ve superuser her zaman erişebilir
        if kullanici.is_superuser or kullanici.is_staff:
            return True
            
        # İlk hafta her zaman erişilebilir
        if self.hafta == 1:
            return True
            
        # Kullanıcının kayıt tarihini al
        kayit_tarihi = getattr(kullanici, 'kayit_tarihi', None) or kullanici.date_joined.date()
        
        # Bugünün tarihini al - timezone.now() yerine timezone.localtime() kullan
        bugun = timezone.localtime().date()
        
        # Aktivitenin erişilebilir olduğu tarih (kayıt tarihine hafta sayısı * 7 gün ekle)
        erisim_tarihi = kayit_tarihi + timedelta(days=(self.hafta - 1) * 7)
        
        # Eğer bugün, erişim tarihinden sonra veya aynıysa erişim koşullarını kontrol et
        if bugun >= erisim_tarihi:
            # Önceki hafta modüllerinin tamamlanma durumunu kontrol et
            if self.hafta > 1:
                try:
                    onceki_hafta = self.hafta - 1
                    
                    # Önceki hafta aktivitelerinin tamamlanma durumunu kontrol et
                    onceki_hafta_aktiviteleri = HaftalikAktivite.objects.filter(
                        aktif=True,
                        silindi=False, 
                        hafta=onceki_hafta
                    )
                    
                    # Önceki haftanın tüm aktivitelerinin tamamlanmış olması gerekiyor
                    for aktivite in onceki_hafta_aktiviteleri:
                        yanit = KullaniciAktiviteYaniti.objects.filter(
                            kullanici=kullanici,
                            aktivite=aktivite
                        ).first()
                        
                        if not yanit or not yanit.tamamlandi:
                            return False
                            
                    # Önceki hafta modülleri tamamlanmış mı kontrolü
                    from .models import Modul, KullaniciIlerleme
                    
                    onceki_hafta_modulleri = Modul.objects.filter(
                        aktif=True,
                        silindi=False,
                        hafta=onceki_hafta
                    )
                    
                    # Önceki haftanın tüm modüllerinin tamamlanmış olması gerekiyor
                    for modul in onceki_hafta_modulleri:
                        ilerleme = KullaniciIlerleme.objects.filter(
                            kullanici=kullanici,
                            modul=modul
                        ).first()
                        
                        if not ilerleme or not (ilerleme.tamamlandi or ilerleme.ilerleme_yuzdesi == 100):
                            return False
                except Exception as e:
                    # Hata durumunda, güvenli tarafta kalarak erişime izin verme
                    return False
            
            # Tüm kontroller geçildiyse erişime izin ver
            return True
        
        # Erişim tarihinden önce ise erişimi reddet
        return False

class AktiviteOgesi(models.Model):
    """Aktivite içerisindeki öğeler (checkbox, tablo satırı, metin alanı vb.)"""
    OGE_TIPLERI = (
        ('checkbox', 'Onay Kutusu'),
        ('tablo', 'Tablo'),
        ('metin', 'Metin Alanı'),
        ('baslik', 'Başlık/Bölüm'),
        ('aciklama', 'Açıklama Metni'),
    )
    
    aktivite = models.ForeignKey(HaftalikAktivite, on_delete=models.CASCADE, related_name='ogeler', 
                                verbose_name="Bağlı Olduğu Aktivite")
    tip = models.CharField(max_length=20, choices=OGE_TIPLERI, verbose_name="Öğe Tipi")
    sira = models.PositiveSmallIntegerField(default=0, verbose_name="Sıra Numarası")
    baslik = models.CharField(max_length=255, blank=True, null=True, verbose_name="Öğe Başlığı/Etiketi")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    zorunlu = models.BooleanField(default=False, verbose_name="Zorunlu mu?")
    icerik_json = models.TextField(null=True, blank=True, verbose_name="İçerik (JSON)",
                                 help_text="Öğe için ek yapılandırma (tablo boyutu, seçenekler vb.)")
    aktif = models.BooleanField(default=True, verbose_name="Aktif mi?")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    silindi = models.BooleanField(default=False)
    silinme_tarihi = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Aktivite Öğesi"
        verbose_name_plural = "Aktivite Öğeleri"
        ordering = ['aktivite', 'sira']
    
    def __str__(self):
        return f"{self.aktivite.baslik} - {self.get_tip_display()} - {self.baslik or self.id}"
    
    def tablo_satir_sayisi(self):
        """Tablo tipi için satır sayısı"""
        if self.tip != 'tablo' or not self.icerik_json:
            return 0
        try:
            icerik = json.loads(self.icerik_json)
            return icerik.get('satir_sayisi', 0)
        except json.JSONDecodeError:
            return 0
    
    def tablo_sutun_sayisi(self):
        """Tablo tipi için sütun sayısı"""
        if self.tip != 'tablo' or not self.icerik_json:
            return 0
        try:
            icerik = json.loads(self.icerik_json)
            return icerik.get('sutun_sayisi', 0)
        except json.JSONDecodeError:
            return 0
    
    def tablo_basliklar(self):
        """Tablo sütun başlıkları"""
        if self.tip != 'tablo' or not self.icerik_json:
            return []
        try:
            icerik = json.loads(self.icerik_json)
            return icerik.get('sutun_basliklar', [])
        except json.JSONDecodeError:
            return []
    
    def tablo_satir_basliklar(self):
        """Tablo satır başlıkları"""
        if self.tip != 'tablo' or not self.icerik_json:
            return []
        try:
            icerik = json.loads(self.icerik_json)
            return icerik.get('satir_basliklar', [])
        except json.JSONDecodeError:
            return []

class KullaniciAktiviteYaniti(models.Model):
    """Kullanıcıların aktivitelere verdikleri yanıtlar"""
    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, related_name='aktivite_yanitlari',
                                 verbose_name="Kullanıcı")
    aktivite = models.ForeignKey(HaftalikAktivite, on_delete=models.CASCADE, related_name='kullanici_yanitlari',
                                verbose_name="Aktivite")
    yanitlar_json = models.TextField(verbose_name="Yanıtlar (JSON)")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturma Tarihi")
    guncelleme_tarihi = models.DateTimeField(auto_now=True, verbose_name="Güncelleme Tarihi")
    tamamlandi = models.BooleanField(default=False, verbose_name="Tamamlandı mı?")
    silindi = models.BooleanField(default=False)
    silinme_tarihi = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Kullanıcı Aktivite Yanıtı"
        verbose_name_plural = "Kullanıcı Aktivite Yanıtları"
        unique_together = ('kullanici', 'aktivite')
    
    def __str__(self):
        return f"{self.kullanici.username} - {self.aktivite.baslik}"
    
    def yanit_getir(self, oge_id):
        """Belirli bir öğeye verilen yanıtı döndürür"""
        if not self.yanitlar_json:
            return None
        try:
            yanitlar = json.loads(self.yanitlar_json)
            return yanitlar.get(str(oge_id))
        except json.JSONDecodeError:
            print(f"JSON çözümlenirken hata: {self.yanitlar_json}")
            return None
    
    def checkbox_durumu(self, oge_id):
        """Checkbox durumunu döndürür"""
        yanit = self.yanit_getir(oge_id)
        if yanit is None:
            return False
        try:
            return bool(yanit.get('deger', False))
        except (AttributeError, TypeError):
            return False
    
    def metin_yaniti(self, oge_id):
        """Metin yanıtını döndürür"""
        yanit = self.yanit_getir(oge_id)
        if yanit is None:
            return ""
        try:
            return str(yanit.get('metin', ""))
        except (AttributeError, TypeError):
            return ""
    
    def tablo_verisi(self, oge_id):
        """Tablo verisini döndürür"""
        yanit = self.yanit_getir(oge_id)
        if yanit is None:
            return {}
        try:
            return yanit.get('tablo_veri', {}) or {}
        except (AttributeError, TypeError):
            return {}
            
    def tablo_verisi_hucre(self, oge_id, satir, sutun):
        """Tablodaki belirli bir hücreyi döndürür"""
        tablo_veri = self.tablo_verisi(oge_id)
        if not tablo_veri:
            return ""
        try:
            hucre_key = f"satir{satir}_sutun{sutun}"
            return tablo_veri.get(hucre_key, "")
        except (TypeError, KeyError):
            return ""
