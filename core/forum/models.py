from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify

# Create your models here.

class ForumKategori(models.Model):
    """Forum kategorileri"""
    baslik = models.CharField(max_length=100, verbose_name="Başlık")
    aciklama = models.TextField(verbose_name="Açıklama")
    slug = models.SlugField(unique=True, max_length=150, blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome ikon adı (örn: fa-comments)")
    sira = models.PositiveSmallIntegerField(default=0, verbose_name="Sıra")
    ust_kategori = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='alt_kategoriler')
    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturma Tarihi")
    
    
    class Meta:
        verbose_name = "Forum Kategorisi"
        verbose_name_plural = "Forum Kategorileri"
        ordering = ['sira', 'baslik']
    
    def __str__(self):
        return self.baslik
    
    def konu_sayisi(self):
        """Kategori altındaki konu sayısını döndürür"""
        return self.konular.filter(aktif=True, onay_durumu='onaylanmis').count()
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.baslik)
        super().save(*args, **kwargs)


class ForumKonu(models.Model):
    """Forum konuları"""
    ONAY_DURUMLARI = (
        ('onaylanmis', 'Onaylanmış'),
        ('beklemede', 'Onay Bekliyor'),
        ('reddedilmis', 'Reddedilmiş'),
    )
    
    baslik = models.CharField(max_length=200, verbose_name="Başlık")
    icerik = models.TextField(verbose_name="İçerik")
    kategori = models.ForeignKey(ForumKategori, on_delete=models.CASCADE, related_name='konular', verbose_name="Kategori")
    yazar = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_konulari', verbose_name="Yazar")
    slug = models.SlugField(unique=True, max_length=250, blank=True)
    goruntulenme = models.PositiveIntegerField(default=0, verbose_name="Görüntülenme Sayısı")
    sabit = models.BooleanField(default=False, verbose_name="Sabit Konu")
    kapali = models.BooleanField(default=False, verbose_name="Kapalı (Yoruma Kapalı)")
    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    onay_durumu = models.CharField(max_length=20, choices=ONAY_DURUMLARI, default='onaylanmis', verbose_name="Onay Durumu")
    onaylayan = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='onayladigi_konular', verbose_name="Onaylayan Kullanıcı")
    onay_tarihi = models.DateTimeField(null=True, blank=True, verbose_name="Onay Tarihi")
    red_sebebi = models.TextField(blank=True, null=True, verbose_name="Red Sebebi")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturma Tarihi")
    guncelleme_tarihi = models.DateTimeField(auto_now=True, verbose_name="Güncelleme Tarihi")
    silinme_tarihi = models.DateTimeField(null=True, blank=True, verbose_name="Silinme Tarihi")
    
    class Meta:
        verbose_name = "Forum Konusu"
        verbose_name_plural = "Forum Konuları"
        ordering = ['-sabit', '-olusturma_tarihi']
    
    def __str__(self):
        return self.baslik
    
    def yorum_sayisi(self):
        """Konu altındaki yorum sayısını döndürür"""
        return self.yorumlar.filter(aktif=True).count()
    
    def goruntulenme_artir(self):
        """Görüntülenme sayısını bir artırır"""
        self.goruntulenme += 1
        self.save(update_fields=['goruntulenme'])
    
    @classmethod
    def aktif_konu_sayisi(cls):
        """Aktif ve onaylanmış konu sayısını döndürür (reddedilenler hariç)"""
        return cls.objects.filter(aktif=True).exclude(onay_durumu='reddedilmis').count()
    
    @classmethod
    def bugun_acilan_konu_sayisi(cls):
        """Bugün açılan aktif ve onaylanmış konu sayısını döndürür (reddedilenler hariç)"""
        from django.utils import timezone
        bugun = timezone.now().date()
        return cls.objects.filter(
            olusturma_tarihi__date=bugun,
            aktif=True
        ).exclude(onay_durumu='reddedilmis').count()
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.baslik)
            slug = base_slug
            counter = 1
            
            # Benzersiz slug oluştur
            while ForumKonu.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
                
            self.slug = slug
        super().save(*args, **kwargs)


class ForumYorum(models.Model):
    """Forum yorumları"""
    konu = models.ForeignKey(ForumKonu, on_delete=models.CASCADE, related_name='yorumlar', verbose_name="Konu")
    yazar = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_yorumlari', verbose_name="Yazar")
    icerik = models.TextField(verbose_name="İçerik")
    ust_yorum = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='alt_yorumlar', verbose_name="Üst Yorum")
    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturma Tarihi")
    guncelleme_tarihi = models.DateTimeField(auto_now=True, verbose_name="Güncelleme Tarihi")
    silinme_tarihi = models.DateTimeField(null=True, blank=True, verbose_name="Silinme Tarihi")
    
    class Meta:
        verbose_name = "Forum Yorumu"
        verbose_name_plural = "Forum Yorumları"
        ordering = ['olusturma_tarihi']
    
    def __str__(self):
        return f"{self.yazar.username} - {self.konu.baslik[:30]}"


class ForumBegeni(models.Model):
    """Forum beğenileri"""
    BEGENI_TURLERI = (
        ('like', 'Beğeni'),
        ('dislike', 'Beğenmeme'),
    )
    
    konu = models.ForeignKey(ForumKonu, on_delete=models.CASCADE, null=True, blank=True, related_name='begeniler', verbose_name="Konu")
    yorum = models.ForeignKey(ForumYorum, on_delete=models.CASCADE, null=True, blank=True, related_name='begeniler', verbose_name="Yorum")
    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_begenileri', verbose_name="Kullanıcı")
    tur = models.CharField(max_length=10, choices=BEGENI_TURLERI, default='like', verbose_name="Tür")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturma Tarihi")
    
    class Meta:
        verbose_name = "Forum Beğeni"
        verbose_name_plural = "Forum Beğenileri"
        unique_together = [['kullanici', 'konu'], ['kullanici', 'yorum']]
    
    def __str__(self):
        return f"{self.kullanici.username} - {self.get_tur_display()} - {self.konu or self.yorum}"


class ForumGoruntulenme(models.Model):
    """Konuların kim tarafından görüntülendiğini takip eden model"""
    konu = models.ForeignKey(ForumKonu, on_delete=models.CASCADE, related_name='goruntulenme_kayitlari', verbose_name="Konu")
    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goruntulenme_kayitlari', verbose_name="Kullanıcı")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Görüntülenme Tarihi")
    
    class Meta:
        verbose_name = "Forum Görüntülenme"
        verbose_name_plural = "Forum Görüntülenmeleri"
        unique_together = [['kullanici', 'konu']]
    
    def __str__(self):
        return f"{self.kullanici.username} - {self.konu.baslik[:30]}"
