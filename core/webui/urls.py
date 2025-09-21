from django.urls import path
from .views import *

urlpatterns = [
    # Ana Sayfa
    path('', index, name='index'),
    
    # Kullanıcı işlemleri
    path('giris/', login, name='giris'),
    path('login/', login, name='login'),
    path('cikis/', logout_view, name='logout'),
    path('kayit/', register, name='kayit'),
    path('profil/', profil, name='profil'),
    path('reset-password/', reset_password_request, name='reset_password_request'),
    path('reset-password-confirm/<str:token>/', reset_password_confirm, name='reset_password_confirm'),
    
    # Eğitim sistemi
    path('courses/', courses, name='courses'),
    path('access-denied/', access_denied, name='access_denied'),
    path('modul/<int:modul_id>/', modul_detay, name='modul_detay'),
    path('video/<int:video_id>/', video_izle, name='video_izle'),
    path('video/<int:video_id>/sorular/', video_sorular, name='video_sorular'),
    path('video/<int:video_id>/tamamla/', video_tamamla, name='video_tamamla'),
    path('video/<int:video_id>/sure-guncelle/', video_sure_guncelle, name='video_sure_guncelle'),
    path('soru/<int:soru_id>/cevapla/', soru_cevapla, name='soru_cevapla'),
    
    # Mesajlaşma sistemi
    path('mesajlar/', mesaj_listesi, name='mesajlar'),
    path('mesajlar/yeni/', yeni_mesaj, name='yeni_mesaj'),
    path('mesajlar/<int:mesaj_id>/', mesaj_detay, name='mesaj_detay'),
    path('mesajlar/<int:mesaj_id>/cevapla/', mesaj_cevapla, name='mesaj_cevapla'),
    path('mesajlar/<int:mesaj_id>/sil/', mesaj_sil, name='mesaj_sil'),
    path('mesajlar/gelen-temizle/', mesajlar_gelen_temizle, name='mesajlar_gelen_temizle'),
    path('mesajlar/gonderilen-temizle/', mesajlar_gonderilen_temizle, name='mesajlar_gonderilen_temizle'),
    
    # Görüşme sistemi
    path('gorusmeler/', gorusme_listesi, name='gorusme_listesi'),
    path('gorusme/yeni/', yeni_gorusme, name='yeni_gorusme'),
    path('gorusme/<uuid:gorusme_id>/', gorusme_detay, name='gorusme_detay'),
    path('gorusme/<uuid:gorusme_id>/sonlandir/', gorusme_sonlandir, name='gorusme_sonlandir'),
    path('gorusme/<uuid:gorusme_id>/davet-gonder/', gorusme_davet_gonder, name='gorusme_davet_gonder'),
    
    # Yönetici paneli
    path('yonetim/', yonetim_paneli, name='yonetim_paneli'),
    
    # Yönetim - Kullanıcı işlemleri
    path('yonetim/kullanicilar/', kullanici_listesi, name='kullanici_listesi'),  
    path('yonetim/kullanicilar/', kullanici_listesi, name='yonetim_kullanici_listesi'),  
    path('yonetim/kullanici/<int:kullanici_id>/', kullanici_detay, name='yonetim_kullanici_detay'),
    path('yonetim/kullanici/<int:kullanici_id>/', kullanici_detay, name='kullanici_detay'),  
    
    # Yönetim - Kategori İşlemleri
    path('yonetim/kategori/ekle/', kategori_ekle, name='kategori_ekle'),  
    path('yonetim/kategori/ekle/', kategori_ekle, name='yonetim_kategori_ekle'),  
    path('yonetim/kategori/<int:kategori_id>/duzenle/', kategori_duzenle, name='kategori_duzenle'),  
    path('yonetim/kategori/<int:kategori_id>/duzenle/', kategori_duzenle, name='yonetim_kategori_duzenle'),  
    path('yonetim/kategori/<int:kategori_id>/sil/', kategori_sil, name='kategori_sil'),  
    path('yonetim/kategori/<int:kategori_id>/sil/', kategori_sil, name='yonetim_kategori_sil'),  
    path('yonetim/kategori/<int:kategori_id>/sira/<str:yon>/', kategori_sira_degistir, name='kategori_sira_degistir'),
    path('yonetim/kategoriler/tumunu-sirala/', tum_kategorileri_sirala, name='tum_kategorileri_sirala'),
    path('yonetim/kategoriler/toplu-sil/', kategoriler_toplu_sil, name='kategoriler_toplu_sil'),
    
    # Yönetim - Eğitmen İşlemleri
    path('yonetim/egitmen/ekle/', egitmen_ekle, name='egitmen_ekle'),
    path('yonetim/egitmen/<int:egitmen_id>/duzenle/', egitmen_duzenle, name='egitmen_duzenle'),
    path('yonetim/egitmen/<int:egitmen_id>/sil/', egitmen_sil, name='egitmen_sil'),
    path('yonetim/egitmenler/tumunu-sil/', tum_egitmenleri_sil, name='tum_egitmenleri_sil'),
    path('yonetim/egitmenler/toplu-sil/', egitmenler_toplu_sil, name='egitmenler_toplu_sil'),
    
    # Yönetim - Modül İşlemleri
    path('yonetim/modul/ekle/', modul_ekle, name='modul_ekle'),
    path('yonetim/modul/<int:modul_id>/duzenle/', modul_duzenle, name='modul_duzenle'),
    path('yonetim/modul/<int:modul_id>/sil/', modul_sil, name='modul_sil'),
    path('yonetim/modul/<int:modul_id>/videolar/', modul_videolari, name='modul_videolari'),
    path('yonetim/modul/<int:modul_id>/video/ekle/', video_ekle, name='modul_video_ekle'),
    path('yonetim/modul/<int:modul_id>/sira/<str:yon>/', modul_sira_degistir, name='modul_sira_degistir'),
    path('yonetim/moduller/tumunu-sirala/', tum_modulleri_sirala, name='tum_modulleri_sirala'),
    path('yonetim/moduller/toplu-sil/', moduller_toplu_sil, name='moduller_toplu_sil'),
    path('yonetim/videolar/toplu-sil/', videolar_toplu_sil, name='videolar_toplu_sil'),
    
    # Yönetim - Video ve Soru İşlemleri
    path('yonetim/video/<int:video_id>/duzenle/', video_duzenle, name='video_duzenle'),
    path('yonetim/video/<int:video_id>/sil/', video_sil, name='video_sil'),
    path('yonetim/video/<int:video_id>/sorular/', video_sorulari, name='video_sorulari'),
    path('yonetim/video/<int:video_id>/soru/ekle/', soru_ekle, name='soru_ekle'),
    path('yonetim/soru/<int:soru_id>/duzenle/', soru_duzenle, name='soru_duzenle'),
    path('yonetim/soru/<int:soru_id>/sil/', soru_sil, name='soru_sil'),
    
    # Haftalık Aktivite Sistemi
    path('aktiviteler/', aktivite_listesi, name='aktivite_listesi'),
    path('aktivite/<int:aktivite_id>/', aktivite_detay, name='aktivite_detay'),
    path('aktivite/<int:aktivite_id>/yanitla/', aktivite_yanitla, name='aktivite_yanitla'),
    
    # Yönetim - Aktivite İşlemleri
    path('yonetim/aktiviteler/', yonetim_aktivite_listesi, name='yonetim_aktivite_listesi'),
    path('yonetim/aktivite/ekle/', yonetim_aktivite_ekle, name='yonetim_aktivite_ekle'),
    path('yonetim/aktivite/<int:aktivite_id>/duzenle/', yonetim_aktivite_duzenle, name='yonetim_aktivite_duzenle'),
    path('yonetim/aktivite/<int:aktivite_id>/sil/', yonetim_aktivite_sil, name='yonetim_aktivite_sil'),
    path('yonetim/aktivite/<int:aktivite_id>/yanitlar/', yonetim_aktivite_yanitlar, name='yonetim_aktivite_yanitlar'),
    path('yonetim/aktivite-yanit/<int:yanit_id>/detay/', yonetim_aktivite_yanit_detay, name='yonetim_aktivite_yanit_detay'),
    
    # Aktivite öğeleri
    path('yonetim/aktivite/<int:aktivite_id>/oge-ekle/', yonetim_aktivite_oge_ekle, name='yonetim_aktivite_oge_ekle'),
    path('yonetim/aktivite/<int:aktivite_id>/oge-siralama/', aktivite_oge_sirala, name='aktivite_oge_sirala'),
    path('yonetim/aktivite-oge/<int:oge_id>/duzenle/', yonetim_aktivite_oge_duzenle, name='yonetim_aktivite_oge_duzenle'),
    path('yonetim/aktivite-oge/<int:oge_id>/detay/', yonetim_aktivite_oge_detay, name='yonetim_aktivite_oge_detay'),
    path('yonetim/aktivite-oge/<int:oge_id>/sil/', yonetim_aktivite_oge_sil, name='yonetim_aktivite_oge_sil'),
    path('yonetim/aktivite/<int:aktivite_id>/tumunu-temizle/', yonetim_aktivite_tumunu_temizle, name='yonetim_aktivite_tumunu_temizle'),
    
    # Metinsel sorular için URL'ler
    path('yonetim/metinsel-sorular/', metinsel_sorular, name='metinsel_sorular'),
    path('yonetim/metinsel-soru-degerlendir/<int:soru_id>/', metinsel_soru_degerlendir, name='metinsel_soru_degerlendir'),

    # Kilitleri Kaldır
    path('yonetim/kullanici/<int:kullanici_id>/kilitleri-kaldir/', lock_system, name='lock_system'),
]     
