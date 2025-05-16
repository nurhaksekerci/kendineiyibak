from django.urls import path
from . import views

app_name = 'forum'

urlpatterns = [
    # Ana forum sayfası
    path('', views.forum_main, name='forum_main'),
    
    # Tüm konuları listele
    path('tum-konular/', views.tum_konulari_goster, name='tum_konular'),
    
    # Kategori ve konu işlemleri
    path('kategori/<slug:kategori_slug>/', views.kategori_detay, name='kategori_detay'),
    path('kategori/<slug:kategori_slug>/konu/<slug:konu_slug>/', views.konu_detay, name='konu_detay'),
    path('yeni-konu/', views.yeni_konu, name='yeni_konu'),
    path('yeni-konu/<slug:kategori_slug>/', views.yeni_konu, name='yeni_konu_kategori'),
    path('konu-duzenle/<int:konu_id>/', views.konu_duzenle, name='konu_duzenle'),
    path('konu-sil/<int:konu_id>/', views.konu_sil, name='konu_sil'),
    
    # Kullanıcı konuları
    path('konularim/', views.kullanici_konular, name='kullanici_konular'),
    
    # Normal kullanıcılar için kategori listesi
    path('kategoriler/', views.kullanici_forum_kategori_listele, name='kullanici_forum_kategori_listele'),
    
    # Yorum işlemleri
    path('yorum-duzenle/<int:yorum_id>/', views.yorum_duzenle, name='yorum_duzenle'),
    path('yorum-sil/<int:yorum_id>/', views.yorum_sil, name='yorum_sil'),
    
    # Beğeni işlemleri
    path('begeni-ekle/', views.begeni_ekle, name='begeni_ekle'),
    
    # Arama
    path('arama/', views.forum_arama, name='forum_arama'),
    
    # Yönetim paneli URL'leri - Kategoriler
    path('yonetim/kategoriler/', views.forum_kategori_listele, name='forum_kategori_listele'),
    path('yonetim/kategori/ekle/', views.forum_kategori_ekle, name='forum_kategori_ekle'),
    path('yonetim/kategori/duzenle/<int:kategori_id>/', views.forum_kategori_duzenle, name='forum_kategori_duzenle'),
    path('yonetim/kategori/sil/<int:kategori_id>/', views.forum_kategori_sil, name='forum_kategori_sil'),
    
    # Yönetim paneli URL'leri - Konular
    path('yonetim/konular/', views.forum_konu_listele, name='forum_konu_listele'),
    path('yonetim/konu/ekle/', views.forum_konu_ekle, name='forum_konu_ekle'),
    path('yonetim/konu/duzenle/<int:konu_id>/', views.forum_konu_duzenle, name='forum_konu_duzenle'),
    path('yonetim/konu/sil/<int:konu_id>/', views.forum_konu_sil, name='forum_konu_sil'),
    
    # Yönetim paneli URL'leri - Yorumlar
    path('yonetim/yorumlar/', views.forum_yorum_listele, name='forum_yorum_listele'),
    path('yonetim/yorum/duzenle/<int:yorum_id>/', views.forum_yorum_duzenle, name='forum_yorum_duzenle'),
    path('yonetim/yorum/sil/<int:yorum_id>/', views.forum_yorum_sil, name='forum_yorum_sil'),
    
    # Konu Onay Sistemi URL'leri
    path('yonetim/onay-bekleyen-konular/', views.forum_konu_onay_listesi, name='forum_konu_onay_listesi'),
    path('yonetim/konu-onayla/<int:konu_id>/', views.forum_konu_onayla, name='forum_konu_onayla'),
    path('yonetim/konu-reddet/<int:konu_id>/', views.forum_konu_reddet, name='forum_konu_reddet'),
]
