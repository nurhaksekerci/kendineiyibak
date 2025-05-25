from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse, Http404, HttpResponseRedirect
from django.utils import timezone
from django.db.models import Count, Sum, Q, Min, Case, When, IntegerField, Max, F
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import models
from functools import wraps
from .models import (
    Kategori, Egitmen, LockSystem, Modul, Video, Soru, Secenek,
    KullaniciIlerleme, VideoIzleme, KullaniciCevap, Mesaj, Gorusme, GorusmeKatilimci,
    get_today, DinamikTabloVerisi,
    HaftalikAktivite, KullaniciAktiviteYaniti, AktiviteOgesi
)
# Forum modellerini import edelim
from forum.models import ForumKategori, ForumKonu, ForumYorum, ForumBegeni, ForumGoruntulenme
import json
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
import logging
import difflib
import re
import os
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
import uuid
import os
import difflib
from datetime import datetime, timedelta
from functools import wraps
from django.utils import timezone
from django.db.models import Sum, Count
import string
import random
import urllib.parse
from itertools import groupby
from collections import defaultdict
from django.utils.text import slugify
from django.urls import reverse
from django.conf import settings
from .utils import youtube_embed_converter
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_date

# YouTube URL'lerini format dönüştürme fonksiyonu
def format_youtube_url(url):
    """
    YouTube URL'lerini embed formatına dönüştürür.
    Normal video URL'leri: https://www.youtube.com/watch?v=VIDEO_ID
    Kısa URL'ler: https://youtu.be/VIDEO_ID
    Embed formatı: https://www.youtube.com/embed/VIDEO_ID
    """
    return youtube_embed_converter(url)

# Özel login_required dekoratörü
def custom_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Kullanıcı giriş yapmamışsa access_denied.html sayfasını göster
        if not request.user.is_authenticated:
            response = render(request, 'access_denied.html')
            # Tarayıcı önbelleğini devre dışı bırak
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response
        # Kullanıcı giriş yapmışsa normal görünümü göster
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Erişim engellendi sayfası
def access_denied(request):
    response = render(request, 'access_denied.html')
    # Tarayıcı önbelleğini devre dışı bırak
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

# Create your views here.
def index(request):
    return render(request, 'index.html')

@custom_login_required
def courses(request):
    """Eğitim modüllerini listeler"""
    from django.utils import timezone
    from django.db.models import Q, Count, Max
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    # Bugünün tarihini al
    today = timezone.now().date()
    
    # Kullanıcının kayıt tarihini al
    kayit_tarihi = getattr(request.user, 'kayit_tarihi', None) or request.user.date_joined.date()
    
    # LockSystem kontrolü - Eğer kullanıcı LockSystem'de varsa tüm erişimleri aç
    lock_system_kullanicisi = LockSystem.objects.filter(users=request.user).exists()
    
    # Tüm aktif modülleri getir
    moduller = Modul.objects.filter(
        aktif=True,
        silindi=False
    ).select_related('kategori', 'egitmen').order_by('hafta', 'id')
    
    # Kullanıcının ilerleme durumlarını getir
    ilerleme_dict = {}
    tamamlanan_moduller = set()
    
    kullanici_ilerlemeleri = KullaniciIlerleme.objects.filter(
        kullanici=request.user
    )
    
    for ilerleme in kullanici_ilerlemeleri:
        ilerleme_dict[ilerleme.modul_id] = ilerleme.ilerleme_yuzdesi
        if ilerleme.ilerleme_yuzdesi == 100:
            tamamlanan_moduller.add(ilerleme.modul_id)
    
    # Erişim izni olan modülleri, devam eden modülleri ve başlanmamış modülleri belirle
    erisim_izni_olan_moduller = set()
    devam_eden_moduller = set()
    baslanmamis_moduller = set()
    
    # LockSystem kullanıcısı ise tüm modüllere erişim ver
    if lock_system_kullanicisi:
        for modul in moduller:
            erisim_izni_olan_moduller.add(modul.id)
    else:
        # Normal erişim kontrolü
        # İlk hafta modüllerini belirle
        ilk_hafta_modulleri = [m for m in moduller if m.hafta == 1]
        ilk_hafta_moduller_ids = [m.id for m in ilk_hafta_modulleri]
        
        # İlk modül her zaman erişilebilir
        if ilk_hafta_modulleri:
            erisim_izni_olan_moduller.add(ilk_hafta_modulleri[0].id)
        
        # Her hafta içindeki modüller için erişim belirle
        hafta_gruplu_moduller = {}
        for modul in moduller:
            if modul.hafta not in hafta_gruplu_moduller:
                hafta_gruplu_moduller[modul.hafta] = []
            hafta_gruplu_moduller[modul.hafta].append(modul)
        
        # Hafta bazında tüm modülleri sırasıyla kontrol et
        for hafta, hafta_modulleri in sorted(hafta_gruplu_moduller.items()):
            # Haftadaki modülleri ID sırasına göre sırala
            hafta_modulleri.sort(key=lambda m: m.id)
            
            # Eğer ilk hafta ise ilk modül erişilebilir
            if hafta == 1:
                # İlk modül erişilebilir
                if hafta_modulleri:
                    erisim_izni_olan_moduller.add(hafta_modulleri[0].id)
                    
                    # Aynı haftadaki diğer modüller için sıralı erişim kontrolü
                    for i, modul in enumerate(hafta_modulleri[1:], 1):
                        onceki_modul = hafta_modulleri[i-1]
                        if onceki_modul.id in tamamlanan_moduller:
                            erisim_izni_olan_moduller.add(modul.id)
            else:
                # Diğer haftalar için tarih ve önceki hafta kontrolleri
                # Kullanıcının kayıt tarihine göre hafta erişimi kontrolü
                from datetime import timedelta
                erisim_tarihi = kayit_tarihi + timedelta(days=(hafta - 1) * 7)
                
                if today >= erisim_tarihi:
                    # Önceki haftadaki TÜM modüller tamamlanmış mı kontrol et
                    onceki_hafta = hafta - 1
                    onceki_hafta_modulleri = hafta_gruplu_moduller.get(onceki_hafta, [])
                    onceki_hafta_tamamlandi = True
                    
                    for onceki_modul in onceki_hafta_modulleri:
                        if onceki_modul.id not in tamamlanan_moduller:
                            onceki_hafta_tamamlandi = False
                            break
                    
                    # Eğer önceki hafta tamamlandıysa, bu haftanın ilk modülüne erişim izni ver
                    if onceki_hafta_tamamlandi and hafta_modulleri:
                        erisim_izni_olan_moduller.add(hafta_modulleri[0].id)
                        
                        # Aynı haftadaki diğer modüller için sıralı erişim kontrolü
                        for i, modul in enumerate(hafta_modulleri[1:], 1):
                            onceki_modul = hafta_modulleri[i-1]
                            if onceki_modul.id in tamamlanan_moduller:
                                erisim_izni_olan_moduller.add(modul.id)
    
    # Modülleri erişim durumuna göre sınıflandır
    for modul in moduller:
        modul.erisim_var = modul.id in erisim_izni_olan_moduller
        
        if modul.id in erisim_izni_olan_moduller:
            ilerleme_yuzdesi = ilerleme_dict.get(modul.id, 0)
            if ilerleme_yuzdesi == 100:
                pass  # Zaten tamamlanan_moduller içinde
            elif ilerleme_yuzdesi > 0:
                devam_eden_moduller.add(modul.id)
            else:
                baslanmamis_moduller.add(modul.id)
    
    # Haftalık ilerleme durumlarını hesapla
    haftalik_ilerleme = {}
    hafta_tamamlanan_moduller = {}
    
    # Hafta gruplu modülleri yeniden hesapla (LockSystem kullanıcısı için)
    hafta_gruplu_moduller = {}
    for modul in moduller:
        if modul.hafta not in hafta_gruplu_moduller:
            hafta_gruplu_moduller[modul.hafta] = []
        hafta_gruplu_moduller[modul.hafta].append(modul)
    
    for hafta, hafta_modulleri in hafta_gruplu_moduller.items():
        toplam_modul = len(hafta_modulleri)
        tamamlanan_modul = sum(1 for m in hafta_modulleri if m.id in tamamlanan_moduller)
        
        # Bu haftadaki tüm modüller tamamlandı mı?
        hafta_tamamlanan_moduller[hafta] = (tamamlanan_modul == toplam_modul and toplam_modul > 0)
        
        if toplam_modul > 0:
            ilerleme_yuzdesi = int((tamamlanan_modul / toplam_modul) * 100)
        else:
            ilerleme_yuzdesi = 0
            
        haftalik_ilerleme[hafta] = ilerleme_yuzdesi
    
    # Erişim izni olan haftaları belirle
    erisim_izni_olan_haftalar = set()
    
    if lock_system_kullanicisi:
        # LockSystem kullanıcısı tüm haftalara erişebilir
        erisim_izni_olan_haftalar = set(hafta_gruplu_moduller.keys())
    else:
        # Normal erişim kontrolü
        for hafta in sorted(hafta_gruplu_moduller.keys()):
            # İlk hafta her zaman erişilebilir
            if hafta == 1:
                erisim_izni_olan_haftalar.add(hafta)
                continue
                
            # Diğer haftalar için kullanıcının kayıt tarihinden itibaren 7*hafta gün geçmiş mi kontrol et
            from datetime import timedelta
            erisim_tarihi = kayit_tarihi + timedelta(days=(hafta - 1) * 7)
            if today >= erisim_tarihi:
                # Önceki haftadaki tüm modüller tamamlanmış mı kontrol et
                onceki_hafta = hafta - 1
                onceki_hafta_modulleri = hafta_gruplu_moduller.get(onceki_hafta, [])
                onceki_hafta_tamamlandi = True
                
                for onceki_modul in onceki_hafta_modulleri:
                    if onceki_modul.id not in tamamlanan_moduller:
                        onceki_hafta_tamamlandi = False
                        break
                
                if onceki_hafta_tamamlandi:
                    erisim_izni_olan_haftalar.add(hafta)
    
    # Her hafta için erişim izni olan aktiviteleri getir
    try:
        aktiviteler = HaftalikAktivite.objects.filter(
            aktif=True,
            silindi=False
        ).order_by('hafta', '-olusturma_tarihi')
        
        # Her aktivite için kullanıcının yanıt durumunu kontrol et
        for aktivite in aktiviteler:
            # LockSystem kullanıcısı ise tüm aktivitelere erişim ver
            if lock_system_kullanicisi:
                aktivite.erisim_var = True
            else:
                # Aktivitenin kullanıcıya açık olup olmadığını kontrol et
                aktivite.erisim_var = aktivite.kullaniciya_acik_mi(request.user)
            
            aktivite.kullanici_yaniti_var = aktivite.kullanici_yaniti_varmi(request.user)
            if aktivite.kullanici_yaniti_var:
                yanit = aktivite.kullanici_yaniti_getir(request.user)
                aktivite.tamamlandi = yanit.tamamlandi if yanit else False
    except Exception as e:
        # HaftalikAktivite modeli henüz oluşturulmamış olabilir
        aktiviteler = []
    
    # Sayfalama
    paginator = Paginator(moduller, 9)
    sayfa = request.GET.get('sayfa', 1)
    
    try:
        moduller = paginator.page(sayfa)
    except PageNotAnInteger:
        moduller = paginator.page(1)
    except EmptyPage:
        moduller = paginator.page(paginator.num_pages)
    
    context = {
        'moduller': moduller,
        'erisim_izni_olan_moduller': erisim_izni_olan_moduller,
        'devam_eden_moduller': devam_eden_moduller,
        'baslanmamis_moduller': baslanmamis_moduller,
        'today': today,
        'ilerleme_dict': ilerleme_dict,
        'haftalik_ilerleme': haftalik_ilerleme,
        'aktiviteler': aktiviteler,
        'erisim_izni_olan_haftalar': erisim_izni_olan_haftalar,
        'tamamlanan_moduller': list(tamamlanan_moduller),
        'hafta_tamamlanan_moduller': hafta_tamamlanan_moduller,
        'lock_system_kullanicisi': lock_system_kullanicisi,  # Template'te kullanmak için
    }
    
    return render(request, 'courses.html', context)

def instructors(request):
    egitmenler = Egitmen.objects.filter(aktif=True)
    return render(request, 'instructors.html', {'egitmenler': egitmenler})


def login(request):
    # Kullanıcı zaten giriş yapmışsa ana sayfaya yönlendir
    if request.user.is_authenticated:
        return redirect('index')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Standart kullanıcı adı (telefon) ile giriş denemesi
        user = authenticate(request, username=username, password=password)
        
        # Eğer kullanıcı bulunamadıysa ve girilen değer email formatındaysa email ile giriş dene
        if user is None and '@' in username:
            try:
                # Email'e göre kullanıcıyı bul
                user_obj = User.objects.get(email=username)
                # Kullanıcı adı ve şifre ile kimlik doğrula
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        
        if user is not None:
            auth_login(request, user)
            messages.success(request, f'Hoş geldiniz, {user.fullname}! Başarıyla giriş yaptınız.')
            # Yönlendirme URL'ini al, yoksa ana sayfaya yönlendir
            next_url = request.GET.get('next', 'index')
            return redirect(next_url)
        else:
            messages.error(request, 'Kullanıcı adı veya şifre hatalı.')
    
    return render(request, 'login.html')

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        fullname = request.POST.get('fullname', '').strip()  # Fullname alanını al
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '').strip()
        password2 = request.POST.get('password2', '').strip()
        privacy_policy = request.POST.get('privacy-policy')
        
        # Gizlilik politikası kontrolü - serverside kontrol
        if not privacy_policy:
            messages.error(request, 'Kullanıcı sözleşmesini kabul etmelisiniz.')
            return render(request, 'register.html')
        
        # Boş alan kontrolü
        if not username:
            messages.error(request, 'Telefon numarası boş bırakılamaz.')
            return render(request, 'register.html')
        
        # Ad Soyad kontrolü
        if not fullname:
            messages.error(request, 'Ad Soyad alanı boş bırakılamaz.')
            return render(request, 'register.html')
            
        # E-posta artık isteğe bağlı, boş bırakılabilir
        # if not email:
        #     messages.error(request, 'E-posta adresi boş bırakılamaz.')
        #     return render(request, 'register.html')
            
        if not password1 or not password2:
            messages.error(request, 'Şifre alanları boş bırakılamaz.')
            return render(request, 'register.html')
        
        # Telefon numarası format kontrolü
        import re
        # Telefon numarasından boşlukları ve özel karakterleri temizle
        temiz_telefon = re.sub(r'[\s\-\(\)]', '', username)
        
        # Başında 0 yoksa ve 5 ile başlıyorsa, başına 0 ekle
        if len(temiz_telefon) == 10 and temiz_telefon.startswith('5'):
            temiz_telefon = '0' + temiz_telefon
        
        telefon_pattern = re.compile(r'^(05\d{9}|5\d{9}|\+905\d{9})$')
        if not telefon_pattern.match(temiz_telefon):
            messages.error(request, 'Geçerli bir telefon numarası giriniz. Örnek: 05XXXXXXXXX')
            return render(request, 'register.html')
        
        # Kullanıcı adı olarak temizlenmiş telefon numarasını kullan
        username = temiz_telefon
            
        # Şifre uzunluk kontrolü
        if len(password1) < 6:
            messages.error(request, 'Şifre en az 6 karakter olmalıdır.')
            return render(request, 'register.html')
        
        # Şifre kontrolü
        if password1 != password2:
            messages.error(request, 'Şifreler eşleşmiyor.')
            return render(request, 'register.html')
        
        # Kullanıcı adı kontrolü
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Bu telefon numarası zaten kullanılıyor.')
            return render(request, 'register.html')
        
        # E-posta kontrolü - eğer e-posta girilmişse
        if email and User.objects.filter(email=email).exists():
            messages.error(request, 'Bu e-posta adresi zaten kullanılıyor.')
            return render(request, 'register.html')
        
        try:
            # Kullanıcı oluştur
            user = User.objects.create_user(username=username, email=email, password=password1)
            
            # Fullname alanını ekle
            user.fullname = fullname
            user.save()
            
            # Otomatik giriş yap
            auth_login(request, user)
            
            # Başarılı kayıt bildirimi
            messages.success(request, f'Hoş geldiniz, {user.fullname}! Hesabınız başarıyla oluşturuldu.')
            
            return redirect('index')
        except Exception as e:
            messages.error(request, 'Kayıt sırasında bir hata oluştu. Lütfen tekrar deneyin.')
    
    return render(request, 'register.html')

# Çıkış yapma fonksiyonu
def logout_view(request):
    messages.info(request, 'Başarıyla çıkış yaptınız.')
    logout(request)
    return redirect('index')

# Kullanıcı profil sayfası
@custom_login_required
def profil(request):
    # Önce mevcut ve aktif modülleri al
    mevcut_moduller = Modul.objects.filter(aktif=True, silindi=False).values_list('id', flat=True)
    
    # Kullanıcının ilerleme durumlarını getir (sadece mevcut modüllere ait olanlar)
    ilerlemeler = KullaniciIlerleme.objects.filter(
        kullanici=request.user,
        modul_id__in=mevcut_moduller
    ).select_related('modul')
    
    # Tamamlanan modüller
    tamamlanan_moduller = ilerlemeler.filter(tamamlandi=True)
    
    # Devam eden modüller (ilerlemesi > 0 olan ve tamamlanmamış)
    devam_eden_moduller = ilerlemeler.filter(tamamlandi=False, ilerleme_yuzdesi__gt=0)
    
    # Başlanmamış modüller (ilerlemesi = 0 olan ve tamamlanmamış)
    baslanmamis_moduller = ilerlemeler.filter(tamamlandi=False, ilerleme_yuzdesi=0)
    
    # İzlenen videolar (sadece aktif modüllerin videoları)
    izlenen_videolar = VideoIzleme.objects.filter(
        kullanici=request.user,
        tamamlandi=True,
        video__modul__aktif=True,
        video__modul__silindi=False,
        video__aktif=True,
        video__silindi=False
    ).select_related('video', 'video__modul').order_by('-son_izleme_tarihi')[:5]
    
    # Cevaplanan sorular
    cevaplanan_sorular = KullaniciCevap.objects.filter(
        kullanici=request.user
    ).select_related('soru', 'secilen_secenek')
    
    # Doğru cevaplanan soru sayısı
    dogru_cevap_sayisi = cevaplanan_sorular.filter(dogru_mu=True).count()
    
    context = {
        'ilerlemeler': ilerlemeler,
        'tamamlanan_moduller': tamamlanan_moduller,
        'devam_eden_moduller': devam_eden_moduller,
        'baslanmamis_moduller': baslanmamis_moduller,
        'izlenen_videolar': izlenen_videolar,
        'dogru_cevap_sayisi': dogru_cevap_sayisi
    }
    
    return render(request, 'profil.html', context)

# Modül erişim kontrolü
def modul_erisim_kontrolu(request, modul_id):
    """
    Kullanıcının modüle erişim iznini kontrol eder.
    Haftalık sisteme göre, kullanıcının kayıt tarihine ve önceki modüllerin tamamlanma durumuna göre kontrol yapar.
    Return: (erisim_izni, hata_mesaji)
    """
    try:
        modul = Modul.objects.get(id=modul_id, aktif=True, silindi=False)
        
        # Admin ve staff kullanıcılar her zaman erişebilir
        if request.user.is_superuser or request.user.is_staff:
            return True, None
        
        # LockSystem kontrolü - Eğer kullanıcı LockSystem'de varsa tüm modüllere erişim ver
        if LockSystem.objects.filter(users=request.user).exists():
            return True, None
        
        # Tüm aktif modülleri haftaya göre grupla ve ilerleme bilgilerini al
        moduller = Modul.objects.filter(
            aktif=True,
            silindi=False
        ).order_by('hafta', 'id')
        
        # Tamamlanan modülleri bul
        tamamlanan_moduller = set()
        kullanici_ilerlemeleri = KullaniciIlerleme.objects.filter(
            kullanici=request.user
        )
        
        for ilerleme in kullanici_ilerlemeleri:
            if ilerleme.ilerleme_yuzdesi == 100:
                tamamlanan_moduller.add(ilerleme.modul_id)
        
        # Hafta gruplu modüller
        hafta_gruplu_moduller = {}
        for m in moduller:
            if m.hafta not in hafta_gruplu_moduller:
                hafta_gruplu_moduller[m.hafta] = []
            hafta_gruplu_moduller[m.hafta].append(m)
            
        # Her hafta için modülleri ID'ye göre sırala
        for hafta in hafta_gruplu_moduller:
            hafta_gruplu_moduller[hafta].sort(key=lambda m: m.id)
        
        # İlk hafta kontrolü
        if modul.hafta == 1:
            # İlk modül
            if modul.id == hafta_gruplu_moduller[1][0].id:
                return True, None
                
            # İlk haftadaki sıralı modüller
            modul_index = next((i for i, m in enumerate(hafta_gruplu_moduller[1]) if m.id == modul.id), -1)
            if modul_index > 0:
                onceki_modul = hafta_gruplu_moduller[1][modul_index - 1]
                if onceki_modul.id not in tamamlanan_moduller:
                    return False, f"Bu modüle erişmek için önce '{onceki_modul.baslik}' modülünü tamamlamalısınız."
                else:
                    return True, None
        else:
            # Kullanıcının kayıt tarihini al
            kayit_tarihi = getattr(request.user, 'kayit_tarihi', None) or request.user.date_joined.date()
            
            # Bugünün tarihini al
            from django.utils import timezone
            bugun = timezone.localtime().date()
            
            # Modülün erişilebilir olduğu tarih
            from datetime import timedelta
            erisim_tarihi = kayit_tarihi + timedelta(days=(modul.hafta - 1) * 7)
            
            # Erişim tarihi kontrolü
            if bugun < erisim_tarihi:
                return False, f"Bu modül {erisim_tarihi.strftime('%d.%m.%Y')} tarihinde erişime açılacaktır."
            
            # Önceki hafta kontrolleri
            onceki_hafta = modul.hafta - 1
            onceki_hafta_modulleri = hafta_gruplu_moduller.get(onceki_hafta, [])
            
            # Önceki hafta tüm modülleri tamamlanmış mı?
            for onceki_modul in onceki_hafta_modulleri:
                if onceki_modul.id not in tamamlanan_moduller:
                    return False, f"Bu modüle erişmek için önce '{onceki_modul.baslik}' modülünü tamamlamalısınız."
            
            # Aynı haftadaki modüller için sıralı kontrol
            modul_index = next((i for i, m in enumerate(hafta_gruplu_moduller[modul.hafta]) if m.id == modul.id), -1)
            if modul_index > 0:
                onceki_modul = hafta_gruplu_moduller[modul.hafta][modul_index - 1]
                if onceki_modul.id not in tamamlanan_moduller:
                    return False, f"Bu modüle erişmek için önce '{onceki_modul.baslik}' modülünü tamamlamalısınız."
            
        # Tüm kontroller geçildi
        return True, None
        
    except Modul.DoesNotExist:
        return False, "Modül bulunamadı."

# Modül detay sayfası
@custom_login_required
def modul_detay(request, modul_id):
    # Modül erişim kontrolü
    erisim_izni, hata_mesaji = modul_erisim_kontrolu(request, modul_id)
    if not erisim_izni:
        messages.warning(request, hata_mesaji)
        return redirect('courses')
    
    modul = get_object_or_404(Modul, id=modul_id, aktif=True)
    videolar = Video.objects.filter(modul=modul, aktif=True).order_by('id')
    
    # Kullanıcının ilerleme durumunu kontrol et
    ilerleme, created = KullaniciIlerleme.objects.get_or_create(
        kullanici=request.user,
        modul=modul,
        defaults={'ilerleme_yuzdesi': 0, 'tamamlandi': False}
    )
    
    # Kullanıcının izlediği videoları bul
    izlenen_videolar = VideoIzleme.objects.filter(
        kullanici=request.user,
        video__modul=modul,
        tamamlandi=True
    ).values_list('video_id', flat=True)
    
    # Kullanıcının erişebileceği videoları belirle
    erisim_izni_olan_videolar = []
    
    # İlk video her zaman erişilebilir
    ilk_video = videolar.first()
    if ilk_video:
        erisim_izni_olan_videolar.append(ilk_video.id)
    
    # İzlenen videoların ardından gelen videolara erişim izni ver
    for video in videolar:
        # Önceki videoyu bul
        onceki_video = videolar.filter(id__lt=video.id).order_by('-id').first()
        
        # Eğer önceki video izlenmişse veya önceki video yoksa erişim izni ver
        if (onceki_video and onceki_video.id in izlenen_videolar) or not onceki_video:
            erisim_izni_olan_videolar.append(video.id)
    
    # AJAX isteği ise JSON yanıt döndür
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        from django.http import JsonResponse
        
        # JSON yanıtı için veri hazırla
        data = {
            'modul_id': modul.id,
            'baslik': modul.baslik,
            'ilerleme_yuzdesi': ilerleme.ilerleme_yuzdesi,
            'tamamlandi': ilerleme.tamamlandi,
            'video_sayisi': modul.video_sayisi,
            'toplam_sure': modul.toplam_sure,
            'toplam_sure_formatli': modul.toplam_sure_formatli,
            'izlenen_videolar': list(izlenen_videolar),
            'erisim_izni_olan_videolar': erisim_izni_olan_videolar,
        }
        
        # Tarayıcı önbelleğini devre dışı bırak
        response = JsonResponse(data)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    
    context = {
        'modul': modul,
        'videolar': videolar,
        'ilerleme': ilerleme,
        'izlenen_videolar': list(izlenen_videolar),
        'erisim_izni_olan_videolar': erisim_izni_olan_videolar,
    }
    
    return render(request, 'modul_detay.html', context)

# Video erişim kontrolü
def video_erisim_kontrolu(request, video_id):
    """
    Kullanıcının videoya erişim izni olup olmadığını kontrol eder.
    Erişim izni yoksa False döndürür ve hata mesajı gösterir.
    Ayrıca modül bilgisini de döndürür.
    """
    video = get_object_or_404(Video, id=video_id, aktif=True)
    modul = video.modul
    
    # Admin ve staff kullanıcılar her zaman erişebilir
    if request.user.is_superuser or request.user.is_staff:
        return True, modul
    
    # LockSystem kontrolü - Eğer kullanıcı LockSystem'de varsa tüm videolara erişim ver
    if LockSystem.objects.filter(users=request.user).exists():
        return True, modul
    
    # Önce modül erişim kontrolü yap
    erisim_izni, hata_mesaji = modul_erisim_kontrolu(request, modul.id)
    if not erisim_izni:
        messages.warning(request, hata_mesaji)
        return False, modul
    
    # Tüm videoları sıralı olarak getir
    videolar = Video.objects.filter(
        modul=modul,
        aktif=True
    ).order_by('id')
    
    # Kullanıcının izlediği videoları bul
    izlenen_videolar = VideoIzleme.objects.filter(
        kullanici=request.user,
        video__modul=modul,
        tamamlandi=True
    ).values_list('video_id', flat=True)
    
    # Eğer bu video modüldeki ilk videoysa, erişime izin ver
    if video.id == videolar.first().id:
        return True, modul
    
    # Önceki videoyu bul
    onceki_video = videolar.filter(id__lt=video.id).order_by('-id').first()
    
    # Önceki video yoksa veya izlenmişse erişime izin ver
    if not onceki_video or onceki_video.id in izlenen_videolar:
        return True, modul
    
    # Erişim izni yoksa hata mesajı göster
    messages.error(request, f'Bu videoyu izlemek için önce "{onceki_video.baslik}" videosunu izlemelisiniz.')
    return False, modul

# Video izleme sayfası
@custom_login_required
def video_izle(request, video_id):
    # Video erişim kontrolü
    erisim_izni, modul = video_erisim_kontrolu(request, video_id)
    if not erisim_izni:
        return redirect('modul_detay', modul_id=modul.id)
    
    video = get_object_or_404(Video, id=video_id, aktif=True)
    
    # Video izleme kaydı oluştur veya güncelle
    izleme, created = VideoIzleme.objects.get_or_create(
        kullanici=request.user,
        video=video,
        defaults={'tamamlandi': False, 'izleme_suresi': 0}
    )
    
    # Sorular
    sorular = Soru.objects.filter(video=video, aktif=True).order_by('id')
    
    # Cevaplanan soruları bul
    cevaplanan_sorular = KullaniciCevap.objects.filter(
        kullanici=request.user,
        soru__video=video
    ).values_list('soru_id', flat=True)
    
    # Kullanıcının izlediği videoları bul
    izlenen_videolar = VideoIzleme.objects.filter(
        kullanici=request.user,
        video__modul=modul,
        tamamlandi=True
    ).values_list('video_id', flat=True)
    
    # Kullanıcının erişebileceği videoları belirle
    erisim_izni_olan_videolar = []
    
    # Modüldeki tüm videoları getir
    modul_videolari = Video.objects.filter(modul=modul, aktif=True).order_by('id')
    
    # İlk video her zaman erişilebilir
    ilk_video = modul_videolari.first()
    if ilk_video:
        erisim_izni_olan_videolar.append(ilk_video.id)
    
    # İzlenen videoların ardından gelen videolara erişim izni ver
    for v in modul_videolari:
        # Önceki videoyu bul
        onceki_video = modul_videolari.filter(id__lt=v.id).order_by('-id').first()
        
        # Eğer önceki video izlenmişse veya önceki video yoksa erişim izni ver
        if (onceki_video and onceki_video.id in izlenen_videolar) or not onceki_video:
            erisim_izni_olan_videolar.append(v.id)
    
    # Kullanıcının ilerleme durumunu kontrol et
    ilerleme, created = KullaniciIlerleme.objects.get_or_create(
        kullanici=request.user,
        modul=modul,
        defaults={'ilerleme_yuzdesi': 0, 'tamamlandi': False}
    )
    
    context = {
        'video': video,
        'modul': modul,
        'sorular': sorular,
        'cevaplanan_sorular': list(cevaplanan_sorular),
        'erisim_izni': erisim_izni,
        'izleme': izleme,
        'ilerleme': ilerleme,
        'izlenen_videolar': list(izlenen_videolar),
        'erisim_izni_olan_videolar': erisim_izni_olan_videolar,
    }
    
    return render(request, 'video_izle.html', context)

# Video sorularını JSON olarak döndüren görünüm
@custom_login_required
def video_sorular(request, video_id):
    # Video erişim kontrolü
    erisim_izni, modul = video_erisim_kontrolu(request, video_id)
    
    if not erisim_izni:
        from django.http import JsonResponse
        return JsonResponse({'error': 'Bu videoya erişim izniniz yok.'}, status=403)
    
    video = get_object_or_404(Video, id=video_id, aktif=True)
    
    # Sorular
    sorular = Soru.objects.filter(video=video, aktif=True).order_by('id')
    
    # Cevaplanan soruları bul
    cevaplanan_sorular = KullaniciCevap.objects.filter(
        kullanici=request.user,
        soru__video=video
    ).values_list('soru_id', flat=True)
    
    # JSON yanıtı için veri hazırla
    from django.http import JsonResponse
    
    sorular_data = []
    for soru in sorular:
        secenekler = []
        for secenek in soru.secenekler.all():
            secenekler.append({
                'id': secenek.id,
                'secenek_metni': secenek.secenek_metni,
            })
        
        sorular_data.append({
            'id': soru.id,
            'soru_metni': soru.soru_metni,
            'secenekler': secenekler,
            'cevaplandi': soru.id in cevaplanan_sorular,
        })
    
    data = {
        'video_id': video.id,
        'baslik': video.baslik,
        'sorular': sorular_data,
        'cevaplanan_sorular': list(cevaplanan_sorular),
    }
    
    # Tarayıcı önbelleğini devre dışı bırak
    response = JsonResponse(data)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

# Video tamamlama işlemi
@custom_login_required
def video_tamamla(request, video_id):
    if request.method == 'POST':
        video = get_object_or_404(Video, id=video_id, aktif=True)
        modul = video.modul
        
        # Video izleme kaydını güncelle
        izleme, created = VideoIzleme.objects.get_or_create(
            kullanici=request.user,
            video=video,
            defaults={'tamamlandi': True, 'izleme_suresi': video.sure}
        )
        
        if not izleme.tamamlandi:
            izleme.tamamlandi = True
            izleme.izleme_suresi = video.sure
            izleme.save()
        
        # Modül ilerleme durumunu güncelle
        ilerleme, created = KullaniciIlerleme.objects.get_or_create(
            kullanici=request.user,
            modul=modul,
            defaults={'ilerleme_yuzdesi': 0, 'tamamlandi': False}
        )
        
        # Modüldeki toplam video sayısı
        toplam_video_sayisi = Video.objects.filter(modul=modul, aktif=True).count()
        
        # Kullanıcının izlediği video sayısı
        izlenen_video_sayisi = VideoIzleme.objects.filter(
            kullanici=request.user,
            video__modul=modul,
            tamamlandi=True
        ).count()
        
        # İlerleme yüzdesini hesapla
        ilerleme_yuzdesi = int((izlenen_video_sayisi / toplam_video_sayisi) * 100) if toplam_video_sayisi > 0 else 0
        
        # İlerleme durumunu güncelle
        ilerleme.ilerleme_yuzdesi = ilerleme_yuzdesi
        
        # Eğer ilerleme %100'e ulaştıysa
        if ilerleme_yuzdesi == 100:
            ilerleme.tamamlandi = True
            if not ilerleme.tamamlanma_tarihi:
                ilerleme.tamamlanma_tarihi = timezone.now()
            
            # Tamamlandı mesajı (AJAX değilse)
            if request.content_type != 'application/json':
                messages.success(request, f'Tebrikler! "{modul.baslik}" modülünü başarıyla tamamladınız.')
        else:
            # İlerleme %100 değilse, tamamlanmadı olarak işaretle
            ilerleme.tamamlandi = False
            ilerleme.tamamlanma_tarihi = None
        
        # En yüksek ilerleme yüzdesini güncelle
        if ilerleme_yuzdesi > ilerleme.en_yuksek_ilerleme_yuzdesi:
            ilerleme.en_yuksek_ilerleme_yuzdesi = ilerleme_yuzdesi
        
        ilerleme.save()
        
        # Başarı mesajı (tamamlanmadıysa)
        if not ilerleme.tamamlandi and request.content_type != 'application/json':
            messages.success(request, f'"{video.baslik}" videosu başarıyla tamamlandı. Modül ilerlemeniz: %{ilerleme_yuzdesi}')
        
        # AJAX isteği ise başarılı yanıt döndür
        if request.content_type == 'application/json':
            # İlerleme bilgisini de döndür
            data = {
                'success': True,
                'ilerleme_yuzdesi': ilerleme_yuzdesi,
                'tamamlandi': ilerleme.tamamlandi
            }
            response = JsonResponse(data)
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response
        
        # Sonraki videoyu bul
        sonraki_video = Video.objects.filter(
            modul=modul,
            aktif=True,
            id__gt=video.id
        ).order_by('id').first()
        
        # Eğer sonraki video varsa ve erişim izni varsa, sonraki videoya yönlendir
        if sonraki_video and video_erisim_kontrolu(request, sonraki_video.id)[0]:
            return redirect('video_izle', video_id=sonraki_video.id)
        
        # Sonraki video yoksa veya erişim izni yoksa, modül sayfasına yönlendir
        return redirect('modul_detay', modul_id=modul.id)
    
    # POST isteği değilse, hata mesajı göster
    if request.content_type == 'application/json':
        return HttpResponse(status=400)
    
    messages.error(request, 'Geçersiz istek.')
    return redirect('index')

# YouTube video süresini güncellemek için API endpoint
@login_required
@csrf_exempt
def video_sure_guncelle(request, video_id):
    """
    YouTube videosunun süresini güncellemek için API endpoint.
    """
    if request.method == 'POST':
        try:
            # JSON verisini al
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                return JsonResponse({'error': 'Content type application/json olmalıdır.'}, status=400)
            
            sure = data.get('sure')
            if not sure:
                return JsonResponse({'error': 'Süre parametresi gereklidir.'}, status=400)
            
            # Video nesnesini bul
            video = get_object_or_404(Video, id=video_id)
            
            # Süreyi güncelle
            video.sure = int(sure)
            video.save()
            
            # Modülün toplam süresini de güncelle
            modul = video.modul
            modul_videolari = Video.objects.filter(modul=modul, aktif=True)
            toplam_sure = modul_videolari.aggregate(models.Sum('sure'))['sure__sum'] or 0
            modul.toplam_sure = toplam_sure
            modul.save()
            
            return JsonResponse({
                'success': True,
                'sure': video.sure,
                'sure_formatli': video.sure_formatli
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Geçersiz JSON verisi.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Sadece POST metodu desteklenmektedir.'}, status=405)

# Soru cevaplama işlemi
@login_required
@csrf_exempt
def soru_cevapla(request, soru_id):
    """Soru cevaplama işlemi"""
    soru = get_object_or_404(Soru, id=soru_id, aktif=True)
    
    # Kullanıcı daha önce bu soruyu cevaplamış mı kontrol et
    if KullaniciCevap.objects.filter(kullanici=request.user, soru=soru).exists():
        return JsonResponse({'hata': 'Bu soruyu zaten cevapladınız.'}, status=400)
    
    # Video tamamlanmış mı kontrol et
    video = soru.video
    video_tamamlandi = VideoIzleme.objects.filter(
        kullanici=request.user,
        video=video,
        tamamlandi=True
    ).exists()
    
    # Video tamamlanmadıysa soruları cevaplamaya izin verme
    if not video_tamamlandi:
        return JsonResponse({'hata': 'Bu soruyu cevaplayabilmek için önce videoyu tamamlamalısınız.'}, status=403)
    
    if request.method == 'POST':
        try:
            # JSON veya form verisi olabilir
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
            
            # Soru tipine göre işlem yap
            if soru.soru_tipi == 'coktan_secmeli' or soru.soru_tipi == 'dogru_yanlis':
                secenek_id = data.get('secenek_id')
                
                if not secenek_id:
                    return JsonResponse({'hata': 'Seçenek ID\'si gereklidir.'}, status=400)
                
                try:
                    secenek = get_object_or_404(Secenek, id=secenek_id, soru=soru)
                    
                    # Kullanıcı cevabını kaydet
                    cevap = KullaniciCevap.objects.create(
                        kullanici=request.user,
                        soru=soru,
                        secilen_secenek=secenek,
                        dogru_mu=secenek.dogru_mu
                    )
                    
                    return JsonResponse({
                        'dogru': secenek.dogru_mu,
                        'mesaj': 'Doğru cevap!' if secenek.dogru_mu else 'Yanlış cevap.'
                    })
                except Exception as e:
                    return JsonResponse({'hata': f'Seçenek işlenirken hata oluştu: {str(e)}'}, status=500)
                
            elif soru.soru_tipi == 'metin':
                kullanici_cevabi = data.get('metin_cevap', '').strip()
                
                # Metin cevabı işle
                if not kullanici_cevabi:
                    return JsonResponse({'hata': 'Cevap metni gereklidir.'}, status=400)
                
                try:
                    # Geçici bir seçenek oluştur (veritabanı kısıtlaması için)
                    temp_secenek = Secenek.objects.create(
                        soru=soru,
                        secenek_metni=kullanici_cevabi,
                        dogru_mu=False  # Değerlendirme yapılana kadar False
                    )
                    
                    # Kullanıcı cevabını kaydet (değerlendirilmedi olarak)
                    cevap = KullaniciCevap.objects.create(
                        kullanici=request.user,
                        soru=soru,
                        secilen_secenek=temp_secenek,
                        dogru_mu=False,  # Değerlendirme yapılana kadar False
                        degerlendirildi=False  # Henüz değerlendirilmedi
                    )
                    
                    # Staff kullanıcılara bildirim gönder
                    staff_kullanicilar = User.objects.filter(is_staff=True)
                    for staff in staff_kullanicilar:
                        Mesaj.objects.create(
                            gonderen=request.user,
                            alici=staff,
                            konu=f"Metinsel Soru Değerlendirme: {soru.video.baslik}",
                            icerik=f"Kullanıcı {request.user.username} tarafından '{soru.soru_metni}' sorusuna verilen '{kullanici_cevabi}' cevabını değerlendirmeniz gerekiyor. Lütfen yönetim panelinden değerlendirme işlemini gerçekleştirin."
                        )
                    
                    # Metin sorusu için mesaj - sadece metin sorularında gösterilecek
                    return JsonResponse({
                        'mesaj': 'Cevabınız alınmıştır. En kısa zamanda değerlendirilecektir.'
                    })
                except Exception as e:
                    return JsonResponse({'hata': f'Metin cevabı işlenirken hata oluştu: {str(e)}'}, status=500)
                
            else:
                return JsonResponse({'hata': 'Geçersiz soru tipi.'}, status=400)
                
        except json.JSONDecodeError as e:
            return JsonResponse({'hata': f'Geçersiz JSON verisi: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'hata': 'Geçersiz istek.'}, status=400)

# Yetkili kullanıcı kontrolü
def is_yetkili(user):
    """
    Kullanıcının yetkili olup olmadığını kontrol eder.
    Yetkili kullanıcılar, is_staff veya is_superuser özelliğine sahip olanlardır.
    """
    return user.is_authenticated and (user.is_staff or user.is_superuser)

# Yetkili kullanıcı kontrolü için dekoratör
def yetkili_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_yetkili(request.user):
            messages.error(request, 'Bu sayfaya erişim yetkiniz bulunmamaktadır.')
            return redirect('index')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Yönetim Paneli Sayfaları
@login_required
@yetkili_required
def yonetim_paneli(request):
    """Yönetim paneli ana sayfası"""
    # Temel veri modelleri
    moduller = Modul.objects.filter(silindi=False).order_by('id')
    kategoriler = Kategori.objects.filter(silindi=False).order_by('id')
    egitmenler = Egitmen.objects.filter(silindi=False).order_by('id')
    
    # İstatistik bilgileri
    kullanici_sayisi = User.objects.count()
    modul_sayisi = Modul.objects.filter(silindi=False).count()
    video_sayisi = Video.objects.filter(silindi=False).count()
    soru_sayisi = Soru.objects.filter(silindi=False).count()
    aktif_modul_sayisi = Modul.objects.filter(aktif=True, silindi=False).count()
    egitmen_sayisi = Egitmen.objects.filter(silindi=False).count()
    
    # Ek istatistikler
    son_hafta = timezone.now() - timezone.timedelta(days=7)
    son_hafta_kullanici_sayisi = User.objects.filter(date_joined__gte=son_hafta).count()
    aktif_kullanici_sayisi = User.objects.filter(last_login__gte=son_hafta).count()
    
    # Video istatistikleri
    toplam_izlenme = VideoIzleme.objects.filter(tamamlandi=True).count()
    
    # Toplam video süresi
    toplam_sure_saniye = Video.objects.aggregate(Sum('sure'))['sure__sum'] or 0
    saat = toplam_sure_saniye // 3600
    dakika = (toplam_sure_saniye % 3600) // 60
    toplam_video_suresi = f"{saat} saat {dakika} dakika"
    
    # Soru tipleri istatistikleri
    coktan_secmeli_soru_sayisi = Soru.objects.filter(soru_tipi='coktan_secmeli').count()
    dogru_yanlis_soru_sayisi = Soru.objects.filter(soru_tipi='dogru_yanlis').count()
    metin_soru_sayisi = Soru.objects.filter(soru_tipi='metin').count()
    
    # Eğitmen istatistikleri
    egitmen_video_sayisi = Video.objects.filter(modul__egitmen__isnull=False).count()
    
    # Kategori istatistikleri
    aktif_kategori_sayisi = Kategori.objects.filter(aktif=True, silindi=False).count()
    
    # Tamamlanan içerik istatistikleri
    tamamlanan_video = VideoIzleme.objects.filter(tamamlandi=True).values('kullanici').annotate(toplam=Count('id')).count()
    tamamlanan_modul = KullaniciIlerleme.objects.filter(tamamlandi=True).count()
    tamamlanan_toplam = tamamlanan_video + tamamlanan_modul
    
    # Forum istatistikleri
    forum_kategori_sayisi = ForumKategori.objects.filter(aktif=True).count()
    forum_konu_sayisi = ForumKonu.objects.filter(aktif=True).count()
    forum_yorum_sayisi = ForumYorum.objects.filter(aktif=True).count()
    
    # Son hafta içindeki forum aktivitesi
    son_hafta_forum_konu_sayisi = ForumKonu.objects.filter(olusturma_tarihi__gte=son_hafta, aktif=True).count()
    son_hafta_forum_yorum_sayisi = ForumYorum.objects.filter(olusturma_tarihi__gte=son_hafta, aktif=True).count()
    son_hafta_forum_aktivite = son_hafta_forum_konu_sayisi + son_hafta_forum_yorum_sayisi
    
    # Değerlendirilmeyi bekleyen metinsel sorular
    degerlendirilmeyen_metinsel_sorular = KullaniciCevap.objects.filter(
        soru__soru_tipi='metin',
        degerlendirildi=False
    ).select_related('kullanici', 'soru', 'secilen_secenek')
    
    # Son güncelleme tarihi (en son güncellenen modül veya video)
    son_modul_guncelleme = Modul.objects.order_by('-guncelleme_tarihi').first()
    son_video_ekleme = Video.objects.order_by('-olusturma_tarihi').first()
    
    son_guncelleme = None
    if son_modul_guncelleme and son_video_ekleme:
        son_guncelleme = max(son_modul_guncelleme.guncelleme_tarihi, son_video_ekleme.olusturma_tarihi)
    elif son_modul_guncelleme:
        son_guncelleme = son_modul_guncelleme.guncelleme_tarihi
    elif son_video_ekleme:
        son_guncelleme = son_video_ekleme.olusturma_tarihi
    
    if son_guncelleme:
        son_guncelleme = son_guncelleme.strftime('%d.%m.%Y %H:%M')
    else:
        son_guncelleme = 'Bilgi yok'
    
    context = {
        'moduller': moduller,
        'kategoriler': kategoriler,
        'egitmenler': egitmenler,
        'kullanici_sayisi': kullanici_sayisi,
        'modul_sayisi': modul_sayisi,
        'video_sayisi': video_sayisi,
        'soru_sayisi': soru_sayisi,
        'aktif_modul_sayisi': aktif_modul_sayisi,
        'egitmen_sayisi': egitmen_sayisi,
        'son_guncelleme': son_guncelleme,
        'son_hafta_kullanici_sayisi': son_hafta_kullanici_sayisi,
        'aktif_kullanici_sayisi': aktif_kullanici_sayisi,
        'toplam_izlenme': toplam_izlenme,
        'toplam_video_suresi': toplam_video_suresi,
        'coktan_secmeli_soru_sayisi': coktan_secmeli_soru_sayisi,
        'dogru_yanlis_soru_sayisi': dogru_yanlis_soru_sayisi,
        'metin_soru_sayisi': metin_soru_sayisi,
        'egitmen_video_sayisi': egitmen_video_sayisi,
        'aktif_kategori_sayisi': aktif_kategori_sayisi,
        'tamamlanan_video': tamamlanan_video,
        'tamamlanan_modul': tamamlanan_modul,
        'tamamlanan_toplam': tamamlanan_toplam,
        'degerlendirilmeyen_metinsel_sorular': degerlendirilmeyen_metinsel_sorular,
        # Forum istatistiklerini ekleyelim
        'forum_kategori_sayisi': forum_kategori_sayisi,
        'forum_konu_sayisi': forum_konu_sayisi,
        'forum_yorum_sayisi': forum_yorum_sayisi,
        'son_hafta_forum_konu_sayisi': son_hafta_forum_konu_sayisi,
        'son_hafta_forum_yorum_sayisi': son_hafta_forum_yorum_sayisi,
        'son_hafta_forum_aktivite': son_hafta_forum_aktivite,
    }
    
    return render(request, 'yonetim/panel.html', context)

@login_required
@yetkili_required
def modul_ekle(request):
    """Yeni modül ekleme sayfası"""
    # Kategorileri getir - Sadece aktif ve silinmemiş kategorileri listele
    kategoriler = Kategori.objects.filter(aktif=True, silindi=False).order_by('id')
    egitmenler = Egitmen.objects.filter(aktif=True).order_by('ad_soyad')
    
    if request.method == 'POST':
        baslik = request.POST.get('baslik', '').strip()
        aciklama = request.POST.get('aciklama', '').strip()
        kategori_id = request.POST.get('kategori', '')
        egitmen_id = request.POST.get('egitmen', '')
        hafta = request.POST.get('hafta', 1)
        aktif = request.POST.get('aktif') == 'on'
        
        # Boş alan kontrolü
        if not baslik:
            messages.error(request, 'Modül başlığı boş bırakılamaz.')
            return render(request, 'yonetim/modul_ekle.html', {'kategoriler': kategoriler, 'egitmenler': egitmenler})
            
        # Kategori kontrolü
        if not kategori_id:
            messages.error(request, 'Lütfen bir kategori seçin. Kategori seçimi zorunludur.')
            return render(request, 'yonetim/modul_ekle.html', {'kategoriler': kategoriler, 'egitmenler': egitmenler})
        
        # Kategorinin hala aktif ve silinmemiş olduğunu kontrol et
        kategori = Kategori.objects.filter(id=kategori_id, aktif=True, silindi=False).first()
        if not kategori:
            messages.error(request, 'Seçilen kategori artık mevcut değil veya silinmiş. Lütfen başka bir kategori seçin.')
            return render(request, 'yonetim/modul_ekle.html', {'kategoriler': kategoriler, 'egitmenler': egitmenler})
            
        try:
            # Modülü oluştur
            modul = Modul(
                baslik=baslik,
                aciklama=aciklama,
                kategori_id=kategori_id,
                hafta=hafta,
                aktif=aktif,
            )
            
            # Eğitmen kontrolü
            if egitmen_id:
                modul.egitmen_id = egitmen_id
                
            # Resim kontrolü
            if 'resim' in request.FILES:
                modul.resim = request.FILES['resim']
                
            # Kaydet
            modul.save()
            
            messages.success(request, 'Modül başarıyla eklendi.')
            return redirect('yonetim_paneli')
            
        except Exception as e:
            messages.error(request, f'Modül eklenirken bir hata oluştu: {str(e)}')
            
    # Yeni modül formu
    context = {
        'kategoriler': kategoriler,
        'egitmenler': egitmenler,
        'yeni_sistem_aciklamasi': 'Yeni sistemde modülün erişilebilirliği, kullanıcının kayıt tarihi + (hafta-1) x 7 gün formülü ile hesaplanır.'
    }
    return render(request, 'yonetim/modul_ekle.html', context)

@login_required
@yetkili_required
def modul_duzenle(request, modul_id):
    """Modül düzenleme sayfası"""
    modul = get_object_or_404(Modul, id=modul_id)
    kategoriler = Kategori.objects.filter(aktif=True, silindi=False).order_by('id')
    egitmenler = Egitmen.objects.filter(aktif=True).order_by('ad_soyad')
    
    if request.method == 'POST':
        baslik = request.POST.get('baslik', '').strip()
        aciklama = request.POST.get('aciklama', '').strip()
        kategori_id = request.POST.get('kategori', '')
        egitmen_id = request.POST.get('egitmen', '')
        hafta = request.POST.get('hafta', 1)
        aktif = request.POST.get('aktif') == 'on'
        
        # Boş alan kontrolü
        if not baslik:
            messages.error(request, 'Modül başlığı boş bırakılamaz.')
            context = {
                'modul': modul,
                'kategoriler': kategoriler,
                'egitmenler': egitmenler
            }
            return render(request, 'yonetim/modul_duzenle.html', context)
            
        # Kategori kontrolü
        if not kategori_id:
            messages.error(request, 'Lütfen bir kategori seçin. Kategori seçimi zorunludur.')
            context = {
                'modul': modul,
                'kategoriler': kategoriler,
                'egitmenler': egitmenler
            }
            return render(request, 'yonetim/modul_duzenle.html', context)
            
        # Kategorinin hala aktif ve silinmemiş olduğunu kontrol et
        kategori = Kategori.objects.filter(id=kategori_id, aktif=True, silindi=False).first()
        if not kategori:
            messages.error(request, 'Seçilen kategori artık mevcut değil veya silinmiş. Lütfen başka bir kategori seçin.')
            context = {
                'modul': modul,
                'kategoriler': kategoriler,
                'egitmenler': egitmenler
            }
            return render(request, 'yonetim/modul_duzenle.html', context)
            
        try:
            # Modülü güncelle
            modul.baslik = baslik
            modul.aciklama = aciklama
            modul.kategori_id = kategori_id
            modul.hafta = hafta
            modul.aktif = aktif
            
            # Eğitmen kontrolü
            if egitmen_id:
                modul.egitmen_id = egitmen_id
            else:
                modul.egitmen = None
                
            # Resim kontrolü
            if 'resim' in request.FILES:
                modul.resim = request.FILES['resim']
            elif request.POST.get('resim_sil') == 'on':
                modul.resim = None
                
            # Kaydet
            modul.save()
            
            messages.success(request, 'Modül başarıyla güncellendi.')
            return redirect('yonetim_paneli')
            
        except Exception as e:
            messages.error(request, f'Modül güncellenirken bir hata oluştu: {str(e)}')
    
    # Düzenleme formu
    context = {
        'modul': modul,
        'kategoriler': kategoriler,
        'egitmenler': egitmenler,
        'yeni_sistem_aciklamasi': 'Yeni sistemde modülün erişilebilirliği, kullanıcının kayıt tarihi + (hafta-1) x 7 gün formülü ile hesaplanır.'
    }
    return render(request, 'yonetim/modul_duzenle.html', context)

@login_required
@yetkili_required
def modul_sil(request, modul_id):
    """Modül silme işlemi"""
    modul = get_object_or_404(Modul, id=modul_id)
    
    if request.method == 'POST':
        try:
            baslik = modul.baslik
            
            # Soft delete işlemi
            modul.silindi = True
            modul.silinme_tarihi = timezone.now()
            modul.save()
            
            messages.success(request, f'"{baslik}" modülü başarıyla silindi.')
        except Exception as e:
            messages.error(request, f'Modül silinirken bir hata oluştu: {str(e)}')
    
    return redirect('yonetim_paneli')

@login_required
@yetkili_required
def video_ekle(request, modul_id):
    """Yeni video ekleme sayfası"""
    modul = get_object_or_404(Modul, id=modul_id)
    
    if request.method == 'POST':
        baslik = request.POST.get('baslik', '').strip()
        aciklama = request.POST.get('aciklama', '').strip()
        video_url = request.POST.get('video_url', '').strip()
        sure_saat = request.POST.get('sure_saat', 0)
        sure_dakika = request.POST.get('sure_dakika', 0)
        sure_saniye = request.POST.get('sure_saniye', 0)
        aktif = request.POST.get('aktif') == 'on'
        
        # Resim dosyası
        resim = request.FILES.get('resim')
        
        # Boş alan kontrolü
        if not baslik:
            messages.error(request, 'Video başlığı boş bırakılamaz.')
            return render(request, 'yonetim/video_ekle.html', {'modul': modul})
        
        # Video dosyası
        video_dosya = request.FILES.get('video_dosya')
        
        # URL veya dosya kontrolü
        if not video_url and not video_dosya:
            messages.error(request, 'Video URL veya video dosyası eklenmelidir.')
            return render(request, 'yonetim/video_ekle.html', {'modul': modul})
        
        try:
            # YouTube URL'lerini embed formatına dönüştür
            if video_url:
                video_url = format_youtube_url(video_url)
                
            # Süre kontrolü - saat, dakika ve saniyeyi toplam saniyeye çevir
            try:
                sure_saat = int(sure_saat)
                sure_dakika = int(sure_dakika)
                sure_saniye = int(sure_saniye)
                toplam_sure = (sure_saat * 3600) + (sure_dakika * 60) + sure_saniye
            except ValueError:
                toplam_sure = 0
            
            # Video oluştur
            video = Video.objects.create(
                modul=modul,
                baslik=baslik,
                aciklama=aciklama,
                video_url=video_url if video_url else None,
                dosya=video_dosya,
                thumbnail_image=resim,
                sure=toplam_sure,
                aktif=aktif
            )
            
            messages.success(request, f'"{video.baslik}" videosu başarıyla oluşturuldu.')
            return redirect('modul_videolari', modul_id=modul.id)
            
        except Exception as e:
            messages.error(request, f'Video oluşturulurken bir hata oluştu: {str(e)}')
    
    return render(request, 'yonetim/video_ekle.html', {'modul': modul})

@login_required
@yetkili_required
def modul_videolari(request, modul_id):
    """Modüle ait videoları listeler"""
    modul = get_object_or_404(Modul, id=modul_id)
    
    # Video sıralama işlemi POST metodu ile yapılıyorsa, şimdi devre dışı bırakalım
    if request.method == 'POST':
        messages.info(request, "Otomatik ID sıralaması kullanıldığından manuel sıralama artık desteklenmiyor.")
    
    videolar = Video.objects.filter(modul=modul).order_by('id')
    return render(request, 'yonetim/modul_videolari.html', {'modul': modul, 'videolar': videolar})

@login_required
@yetkili_required
def video_duzenle(request, video_id):
    """Video düzenleme sayfası"""
    video = get_object_or_404(Video, id=video_id)
    modul = video.modul
    
    if request.method == 'POST':
        baslik = request.POST.get('baslik', '').strip()
        aciklama = request.POST.get('aciklama', '').strip()
        video_url = request.POST.get('video_url', '').strip()
        sure_saat = request.POST.get('sure_saat', 0)
        sure_dakika = request.POST.get('sure_dakika', 0)
        sure_saniye = request.POST.get('sure_saniye', 0)
        aktif = request.POST.get('aktif') == 'on'
        
        # Resim dosyası
        resim = request.FILES.get('resim')
        
        # Boş alan kontrolü
        if not baslik:
            messages.error(request, 'Video başlığı boş bırakılamaz.')
            return render(request, 'yonetim/video_duzenle.html', {'video': video})
        
        # Video dosyası
        video_dosya = request.FILES.get('video_dosya')
        
        # URL veya dosya kontrolü - düzenleme sırasında mevcut bir video varsa kontrol etme
        if not video_url and not video_dosya and not video.dosya:
            messages.error(request, 'Video URL veya video dosyası eklenmelidir.')
            return render(request, 'yonetim/video_duzenle.html', {'video': video})
        
        try:
            # YouTube URL'lerini embed formatına dönüştür
            if video_url:
                video_url = format_youtube_url(video_url)
                
            # Süre kontrolü - saat, dakika ve saniyeyi toplam saniyeye çevir
            try:
                sure_saat = int(sure_saat)
                sure_dakika = int(sure_dakika)
                sure_saniye = int(sure_saniye)
                video.sure = (sure_saat * 3600) + (sure_dakika * 60) + sure_saniye
            except ValueError:
                video.sure = 0
            
            # Diğer alanları güncelle
            video.baslik = baslik
            video.aciklama = aciklama
            video.video_url = video_url if video_url else None
            video.aktif = aktif
            
            # Dosya varsa güncelle
            if video_dosya:
                video.dosya = video_dosya
            
            # Resim varsa güncelle
            if resim:
                video.thumbnail_image = resim
            
            video.save()
            
            messages.success(request, f'"{video.baslik}" videosu başarıyla güncellendi.')
            return redirect('modul_videolari', modul_id=modul.id)
            
        except Exception as e:
            messages.error(request, f'Video güncellenirken bir hata oluştu: {str(e)}')
    
    # Saat, dakika ve saniye değerlerini hesapla
    saat = video.sure // 3600
    dakika = (video.sure % 3600) // 60
    saniye = video.sure % 60
    
    context = {
        'video': video,
        'saat': saat,
        'dakika': dakika,
        'saniye': saniye
    }
    
    return render(request, 'yonetim/video_duzenle.html', context)

@login_required
@yetkili_required
def video_sil(request, video_id):
    """Video silme işlemi"""
    video = get_object_or_404(Video, id=video_id)
    modul = video.modul
    
    if request.method == 'POST':
        try:
            baslik = video.baslik
            video.delete()
            messages.success(request, f'"{baslik}" videosu başarıyla silindi.')
        except Exception as e:
            messages.error(request, f'Video silinirken bir hata oluştu: {str(e)}')
    
    return redirect('modul_videolari', modul_id=modul.id)

@login_required
@yetkili_required
def soru_ekle(request, video_id):
    """Yeni soru ekleme sayfası"""
    video = get_object_or_404(Video, id=video_id)
    
    if request.method == 'POST':
        metin = request.POST.get('metin', '').strip()
        aktif = request.POST.get('aktif') == 'on'
        soru_tipi = request.POST.get('soru_tipi', 'coktan_secmeli')
        
        # Boş alan kontrolü
        if not metin:
            messages.error(request, 'Soru metni boş bırakılamaz.')
            return render(request, 'yonetim/soru_ekle.html', {'video': video})
        
        try:
            # Soru oluştur
            soru = Soru.objects.create(
                video=video,
                soru_metni=metin,
                soru_tipi=soru_tipi,
                aktif=aktif
            )
            
            # Soru tipine göre işlem yap
            if soru_tipi == 'coktan_secmeli':
                # Seçenekler
                secenek_metinleri = request.POST.getlist('secenek_metin')
                dogru_secenek = request.POST.get('dogru_secenek')
                
                if not secenek_metinleri or len(secenek_metinleri) < 2:
                    soru.delete()
                    messages.error(request, 'Çoktan seçmeli sorular için en az 2 seçenek eklemelisiniz.')
                    return render(request, 'yonetim/soru_ekle.html', {'video': video})
                
                if not dogru_secenek or int(dogru_secenek) >= len(secenek_metinleri):
                    soru.delete()
                    messages.error(request, 'Geçerli bir doğru seçenek seçmelisiniz.')
                    return render(request, 'yonetim/soru_ekle.html', {'video': video})
                
                # Seçenekleri oluştur
                for i, secenek_metin in enumerate(secenek_metinleri):
                    if secenek_metin.strip():  # Boş seçenekleri atla
                        Secenek.objects.create(
                            soru=soru,
                            secenek_metni=secenek_metin.strip(),
                            dogru_mu=(i == int(dogru_secenek))
                        )
            
            elif soru_tipi == 'dogru_yanlis':
                # Doğru/Yanlış için iki seçenek oluştur
                dogru_yanlis_cevap = request.POST.get('dogru_yanlis_cevap', 'dogru')
                dogru_mu = dogru_yanlis_cevap == 'dogru'
                
                # Doğru seçeneği oluştur
                Secenek.objects.create(
                    soru=soru,
                    secenek_metni="Doğru",
                    dogru_mu=dogru_mu
                )
                
                # Yanlış seçeneği oluştur
                Secenek.objects.create(
                    soru=soru,
                    secenek_metni="Yanlış",
                    dogru_mu=not dogru_mu
                )
            
            elif soru_tipi == 'metin':
                # Metin cevaplı soru için doğru cevabı kaydet
                dogru_cevap = request.POST.get('dogru_cevap_metni', '').strip()
                if not dogru_cevap:
                    soru.delete()
                    messages.error(request, 'Metin cevaplı sorular için doğru cevap girmelisiniz.')
                    return render(request, 'yonetim/soru_ekle.html', {'video': video})
                
                soru.dogru_cevap_metni = dogru_cevap
                soru.save()
            
            messages.success(request, 'Soru başarıyla oluşturuldu.')
            return redirect('video_sorulari', video_id=video.id)
            
        except Exception as e:
            messages.error(request, f'Soru oluşturulurken bir hata oluştu: {str(e)}')
    
    return render(request, 'yonetim/soru_ekle.html', {'video': video})

@login_required
@yetkili_required
def video_sorulari(request, video_id):
    """Videoya ait soruları listeler"""
    video = get_object_or_404(Video, id=video_id)
    
    # Soru sıralama işlemi POST metodu ile yapılıyorsa, şimdi devre dışı bırakalım
    if request.method == 'POST':
        messages.info(request, "Otomatik ID sıralaması kullanıldığından manuel sıralama artık desteklenmiyor.")
    
    sorular = Soru.objects.filter(video=video).order_by('id')
    return render(request, 'yonetim/video_sorulari.html', {'video': video, 'sorular': sorular})

@yetkili_required
def soru_duzenle(request, soru_id):
    """Soru düzenleme sayfası"""
    soru = get_object_or_404(Soru, id=soru_id)
    video = soru.video
    secenekler = Secenek.objects.filter(soru=soru)
    
    if request.method == 'POST':
        metin = request.POST.get('metin', '').strip()
        aktif = request.POST.get('aktif') == 'on'
        soru_tipi = request.POST.get('soru_tipi', soru.soru_tipi)
        
        # Boş alan kontrolü
        if not metin:
            messages.error(request, 'Soru metni boş bırakılamaz.')
            return render(request, 'yonetim/soru_duzenle.html', {'soru': soru, 'secenekler': secenekler})
        
        try:
            # Soru güncelle
            soru.soru_metni = metin
            soru.aktif = aktif
            
            # Soru tipi değiştiyse, eski seçenekleri sil
            if soru_tipi != soru.soru_tipi:
                secenekler.delete()
                soru.soru_tipi = soru_tipi
                soru.dogru_cevap_metni = None  # Metin cevabı sıfırla
            
            # Soru tipine göre işlem yap
            if soru_tipi == 'coktan_secmeli':
                # Seçenekler
                secenek_metinleri = request.POST.getlist('secenek_metin')
                secenek_idleri = request.POST.getlist('secenek_id')
                dogru_secenek = request.POST.get('dogru_secenek')
                
                # Seçenek sayısı kontrolü
                if not secenek_metinleri:
                    messages.error(request, 'Seçenek bulunamadı. Lütfen en az 2 seçenek ekleyin.')
                    return render(request, 'yonetim/soru_duzenle.html', {'soru': soru, 'secenekler': secenekler})
                
                # Boş seçenekleri filtrele
                gecerli_secenekler = [s for s in secenek_metinleri if s.strip()]
                if len(gecerli_secenekler) < 2:
                    messages.error(request, 'Çoktan seçmeli sorular için en az 2 geçerli seçenek eklemelisiniz.')
                    return render(request, 'yonetim/soru_duzenle.html', {'soru': soru, 'secenekler': secenekler})
                
                # Doğru seçenek kontrolü
                if not dogru_secenek:
                    messages.error(request, 'Bir seçeneği doğru cevap olarak işaretlemelisiniz.')
                    return render(request, 'yonetim/soru_duzenle.html', {'soru': soru, 'secenekler': secenekler})
                
                try:
                    dogru_secenek_index = int(dogru_secenek)
                    if dogru_secenek_index < 0 or dogru_secenek_index >= len(secenek_metinleri):
                        messages.error(request, 'Geçersiz doğru seçenek. Lütfen var olan bir seçeneği işaretleyin.')
                        return render(request, 'yonetim/soru_duzenle.html', {'soru': soru, 'secenekler': secenekler})
                    
                    if not secenek_metinleri[dogru_secenek_index].strip():
                        messages.error(request, 'Doğru olarak işaretlediğiniz seçenek boş olamaz.')
                        return render(request, 'yonetim/soru_duzenle.html', {'soru': soru, 'secenekler': secenekler})
                except (ValueError, IndexError):
                    messages.error(request, 'Geçersiz doğru seçenek. Lütfen var olan bir seçeneği işaretleyin.')
                    return render(request, 'yonetim/soru_duzenle.html', {'soru': soru, 'secenekler': secenekler})
                
                # Mevcut seçenekleri güncelle veya yenilerini oluştur
                mevcut_secenekler = list(secenekler)
                yeni_secenekler = []
                
                for i, secenek_metin in enumerate(secenek_metinleri):
                    secenek_metin = secenek_metin.strip()
                    if secenek_metin:  # Boş seçenekleri atla
                        secenek_id = secenek_idleri[i] if i < len(secenek_idleri) else None
                        
                        if secenek_id and secenek_id.isdigit():
                            # Mevcut seçeneği güncelle
                            try:
                                secenek_obj = Secenek.objects.get(id=int(secenek_id), soru=soru)
                                secenek_obj.secenek_metni = secenek_metin
                                secenek_obj.dogru_mu = (i == dogru_secenek_index)
                                secenek_obj.save()
                                yeni_secenekler.append(secenek_obj)
                            except Secenek.DoesNotExist:
                                # Seçenek bulunamadıysa yeni oluştur
                                yeni_secenek = Secenek.objects.create(
                                    soru=soru,
                                    secenek_metni=secenek_metin,
                                    dogru_mu=(i == dogru_secenek_index)
                                )
                                yeni_secenekler.append(yeni_secenek)
                        else:
                            # Yeni seçenek oluştur
                            yeni_secenek = Secenek.objects.create(
                                soru=soru,
                                secenek_metni=secenek_metin,
                                dogru_mu=(i == dogru_secenek_index)
                            )
                            yeni_secenekler.append(yeni_secenek)
                
                # Kullanılmayan seçenekleri sil
                for s in mevcut_secenekler:
                    if s not in yeni_secenekler:
                        s.delete()
            
            elif soru_tipi == 'dogru_yanlis':
                # Doğru/Yanlış için iki seçenek oluştur veya güncelle
                dogru_yanlis_cevap = request.POST.get('dogru_yanlis_cevap', 'dogru')
                dogru_mu = dogru_yanlis_cevap == 'dogru'
                
                # Mevcut seçenekleri sil
                secenekler.delete()
                
                # Yeni seçenekler oluştur
                Secenek.objects.create(
                    soru=soru,
                    secenek_metni="Doğru",
                    dogru_mu=dogru_mu
                )
                
                Secenek.objects.create(
                    soru=soru,
                    secenek_metni="Yanlış",
                    dogru_mu=not dogru_mu
                )
            
            elif soru_tipi == 'metin':
                # Metin cevaplı soru için doğru cevabı güncelle
                dogru_cevap = request.POST.get('dogru_cevap_metni', '').strip()
                if not dogru_cevap:
                    messages.error(request, 'Metin cevaplı sorular için doğru cevap girmelisiniz.')
                    return render(request, 'yonetim/soru_duzenle.html', {'soru': soru, 'secenekler': secenekler})
                
                # Doğru cevabı kaydet
                soru.dogru_cevap_metni = dogru_cevap
                
                # Mevcut seçenekleri sil
                secenekler.delete()
            
            # Değişiklikleri kaydet ve loglama yap
            try:
                soru.save()
                logging.info(f"Soru başarıyla güncellendi: {soru.id} - {soru.soru_metni[:50]}")
                
                messages.success(request, 'Soru başarıyla güncellendi.')
                return redirect('video_sorulari', video_id=video.id)
            except Exception as e:
                logging.error(f"Soru güncellenirken hata: {str(e)}")
                messages.error(request, f'Soru güncellenirken bir hata oluştu: {str(e)}')
        
        except Exception as e:
            logging.error(f"Soru düzenlerken beklenmeyen hata: {str(e)}")
            messages.error(request, f'Soru güncellenirken bir hata oluştu: {str(e)}')
    
    return render(request, 'yonetim/soru_duzenle.html', {'soru': soru, 'secenekler': secenekler})

@login_required
@yetkili_required
def soru_sil(request, soru_id):
    """Soru silme işlemi"""
    soru = get_object_or_404(Soru, id=soru_id)
    video = soru.video
    
    if request.method == 'POST':
        try:
            soru.delete()
            messages.success(request, 'Soru başarıyla silindi.')
        except Exception as e:
            messages.error(request, f'Soru silinirken bir hata oluştu: {str(e)}')
    
    return redirect('video_sorulari', video_id=video.id)

@login_required
@yetkili_required
def kategori_ekle(request):
    """Yeni kategori ekleme sayfası"""
    if request.method == 'POST':
        baslik = request.POST.get('baslik', '').strip()
        aciklama = request.POST.get('aciklama', '').strip()
        aktif = request.POST.get('aktif') == 'on'
        
        # Boş alan kontrolü
        if not baslik:
            messages.error(request, 'Kategori başlığı boş bırakılamaz.')
            return render(request, 'yonetim/kategori_ekle.html')
            
        try:
            # Kategoriyi oluştur
            kategori = Kategori.objects.create(
                baslik=baslik,
                aciklama=aciklama,
                aktif=aktif
            )
            
            messages.success(request, f'"{kategori.baslik}" kategorisi başarıyla oluşturuldu.')
            return redirect('yonetim_paneli')
            
        except Exception as e:
            messages.error(request, f'Kategori oluşturulurken bir hata oluştu: {str(e)}')
    
    return render(request, 'yonetim/kategori_ekle.html')

@login_required
@yetkili_required
def kategori_duzenle(request, kategori_id):
    """Kategori düzenleme sayfası"""
    kategori = get_object_or_404(Kategori, id=kategori_id)
    
    if request.method == 'POST':
        baslik = request.POST.get('baslik', '').strip()
        aciklama = request.POST.get('aciklama', '').strip()
        aktif = request.POST.get('aktif') == 'on'
        
        # Boş alan kontrolü
        if not baslik:
            messages.error(request, 'Kategori başlığı boş bırakılamaz.')
            return render(request, 'yonetim/kategori_duzenle.html', {'kategori': kategori})
            
        try:
            # Diğer alanları güncelle
            kategori.baslik = baslik
            kategori.aciklama = aciklama
            kategori.aktif = aktif
            kategori.save()
            
            messages.success(request, f'"{kategori.baslik}" kategorisi başarıyla güncellendi.')
            return redirect('yonetim_paneli')
            
        except Exception as e:
            messages.error(request, f'Kategori güncellenirken bir hata oluştu: {str(e)}')
    
    return render(request, 'yonetim/kategori_duzenle.html', {'kategori': kategori})

@login_required
@yetkili_required
def kategori_sil(request, kategori_id):
    """Kategori silme işlemi"""
    kategori = get_object_or_404(Kategori, id=kategori_id)
    
    if request.method == 'POST':
        try:
            baslik = kategori.baslik
            
            # Soft delete işlemi
            kategori.silindi = True
            kategori.silinme_tarihi = timezone.now()
            kategori.save()
            
            messages.success(request, f'"{baslik}" kategorisi başarıyla silindi.')
        except Exception as e:
            messages.error(request, f'Kategori silinirken bir hata oluştu: {str(e)}')
    
    return redirect('yonetim_paneli')

@login_required
@yetkili_required
def modul_sira_degistir(request, modul_id, yon):
    """Modülün sıra numarasını bir yukarı veya aşağı taşır"""
    # Sıra alanı kaldırıldığından, otomatik ID sıralaması kullanılacak
    messages.info(request, "Otomatik ID sıralaması kullanıldığından manuel sıralama artık desteklenmiyor.")
    return redirect('yonetim_paneli')

@login_required
@yetkili_required
def tum_modulleri_sirala(request):
    """Tüm modülleri sıralama veya toplu silme işlemi"""
    if request.method == 'POST':
        islem = request.POST.get('islem', '')
        
        if islem == 'sil':
            # Toplu silme işlemi
            secili_moduller = request.POST.getlist('seciliModuller')
            if secili_moduller:
                try:
                    silinecek_moduller = Modul.objects.filter(id__in=secili_moduller)
                    silinecek_sayisi = silinecek_moduller.count()
                    
                    # Silme işlemi için soft delete işlemi
                    for modul in silinecek_moduller:
                        modul.silindi = True
                        modul.silinme_tarihi = timezone.now()
                        modul.save()
                    
                    messages.success(request, f'{silinecek_sayisi} modül başarıyla silindi.')
                except Exception as e:
                    messages.error(request, f'Modüller silinirken bir hata oluştu: {str(e)}')
            else:
                messages.warning(request, 'Silinecek modül seçilmedi.')
                
        else:
            # Normal sıralama işlemi (eğer varsa)
            pass
    
    return redirect('yonetim_paneli')

@login_required
@yetkili_required
def kategori_sira_degistir(request, kategori_id, yon):
    """Kategorinin sıra numarasını bir yukarı veya aşağı taşır"""
    # Sıra alanı kaldırıldığından, otomatik ID sıralaması kullanılacak
    messages.info(request, "Otomatik ID sıralaması kullanıldığından manuel sıralama artık desteklenmiyor.")
    return redirect('yonetim_paneli')

@login_required
@yetkili_required
def tum_kategorileri_sirala(request):
    """Tüm kategorileri sıralama veya toplu silme işlemi"""
    if request.method == 'POST':
        islem = request.POST.get('islem', '')
        
        if islem == 'sil':
            # Toplu silme işlemi
            secili_kategoriler = request.POST.getlist('seciliKategoriler')
            if secili_kategoriler:
                try:
                    silinecek_kategoriler = Kategori.objects.filter(id__in=secili_kategoriler)
                    silinecek_sayisi = silinecek_kategoriler.count()
                    
                    # Silme işlemi için soft delete işlemi
                    for kategori in silinecek_kategoriler:
                        kategori.silindi = True
                        kategori.silinme_tarihi = timezone.now()
                        kategori.save()
                    
                    messages.success(request, f'{silinecek_sayisi} kategori başarıyla silindi.')
                except Exception as e:
                    messages.error(request, f'Kategoriler silinirken bir hata oluştu: {str(e)}')
            else:
                messages.warning(request, 'Silinecek kategori seçilmedi.')
                
        else:
            # Normal sıralama işlemi (eğer varsa)
            pass
    
    return redirect('yonetim_paneli')

# Eğitmen Yönetimi
@login_required
@yetkili_required
def egitmen_ekle(request):
    """Yeni eğitmen ekleme sayfası"""
    if request.method == 'POST':
        ad_soyad = request.POST.get('ad_soyad', '').strip()
        unvan = request.POST.get('unvan', '').strip()
        email = request.POST.get('email', '').strip() or None
        ozgecmis = request.POST.get('ozgecmis', '').strip() or None
        aktif = request.POST.get('aktif') == 'on'
        profil_resmi = request.FILES.get('profil_resmi')
        
        # Boş alan kontrolü
        if not ad_soyad:
            messages.error(request, 'Ad soyad alanı boş bırakılamaz.')
            return render(request, 'yonetim/egitmen_ekle.html')
            
        try:
            # Eğitmeni oluştur
            egitmen = Egitmen.objects.create(
                ad_soyad=ad_soyad,
                unvan=unvan,
                email=email,
                ozgecmis=ozgecmis,
                aktif=aktif,
                profil_resmi=profil_resmi
            )
            
            messages.success(request, f'"{egitmen.unvan} {egitmen.ad_soyad}" eğitmeni başarıyla oluşturuldu.')
            return redirect('yonetim_paneli')
            
        except Exception as e:
            messages.error(request, f'Eğitmen oluşturulurken bir hata oluştu: {str(e)}')
    
    return render(request, 'yonetim/egitmen_ekle.html')

@login_required
@yetkili_required
def egitmen_duzenle(request, egitmen_id):
    """Eğitmen düzenleme sayfası"""
    egitmen = get_object_or_404(Egitmen, id=egitmen_id)
    
    if request.method == 'POST':
        ad_soyad = request.POST.get('ad_soyad', '').strip()
        unvan = request.POST.get('unvan', '').strip()
        email = request.POST.get('email', '').strip() or None
        ozgecmis = request.POST.get('ozgecmis', '').strip() or None
        aktif = request.POST.get('aktif') == 'on'
        profil_resmi = request.FILES.get('profil_resmi')
        
        # Boş alan kontrolü
        if not ad_soyad:
            messages.error(request, 'Ad soyad alanı boş bırakılamaz.')
            return render(request, 'yonetim/egitmen_duzenle.html', {'egitmen': egitmen})
            
        try:
            # Bilgileri güncelle
            egitmen.ad_soyad = ad_soyad
            egitmen.unvan = unvan
            egitmen.email = email
            egitmen.ozgecmis = ozgecmis
            egitmen.aktif = aktif
            
            # Eğer yeni bir profil resmi yüklendiyse güncelle
            if profil_resmi:
                egitmen.profil_resmi = profil_resmi
            
            egitmen.save()
            
            messages.success(request, f'"{egitmen.unvan} {egitmen.ad_soyad}" eğitmeni başarıyla güncellendi.')
            return redirect('yonetim_paneli')
            
        except Exception as e:
            messages.error(request, f'Eğitmen güncellenirken bir hata oluştu: {str(e)}')
    
    return render(request, 'yonetim/egitmen_duzenle.html', {'egitmen': egitmen})

@login_required
@yetkili_required
def egitmen_sil(request, egitmen_id):
    """Eğitmen silme işlemi"""
    egitmen = get_object_or_404(Egitmen, id=egitmen_id)
    
    if request.method == 'POST':
        try:
            ad_soyad = egitmen.ad_soyad  # Silme öncesi adını sakla
            
            # Soft delete işlemi
            egitmen.silindi = True
            egitmen.silinme_tarihi = timezone.now()
            egitmen.save()
            
            messages.success(request, f'"{ad_soyad}" eğitmeni başarıyla silindi.')
            
            # JavaScript bildirimini önlemek için is_ajax kontrolü
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success'})
                
        except Exception as e:
            messages.error(request, f'Eğitmen silinirken bir hata oluştu: {str(e)}')
    
    return redirect('yonetim_paneli')

@login_required
@yetkili_required
def tum_egitmenleri_sil(request):
    """Tüm eğitmenleri silme işlemi"""
    if request.method == 'POST':
        try:
            secili_egitmenler = request.POST.getlist('seciliEgitmenler')
            if secili_egitmenler:
                silinecek_egitmenler = Egitmen.objects.filter(id__in=secili_egitmenler)
                silinecek_sayisi = silinecek_egitmenler.count()
                
                # Silme işlemi için soft delete işlemi
                for egitmen in silinecek_egitmenler:
                    egitmen.silindi = True
                    egitmen.silinme_tarihi = timezone.now()
                    egitmen.save()
                
                
                messages.success(request, f'{silinecek_sayisi} eğitmen başarıyla silindi.')
            else:
                messages.warning(request, 'Silinecek eğitmen seçilmedi.')
        except Exception as e:
            messages.error(request, f'Eğitmenler silinirken bir hata oluştu: {str(e)}')
    
    return redirect('yonetim_paneli')

# Kullanıcı Yönetimi
@login_required
@yetkili_required
def kullanici_listesi(request):
    """Kullanıcı listesi sayfası"""
    arama = request.GET.get('arama', '')
    siralama = request.GET.get('siralama', 'id')  # Varsayılan olarak ID'ye göre sıralama
    
    # Kullanıcı listesini al
    kullanicilar = User.objects.all()
    
    # Arama sorgusu varsa filtrele
    if arama:
        kullanicilar = kullanicilar.filter(
            Q(username__icontains=arama) | 
            Q(email__icontains=arama) | 
            Q(first_name__icontains=arama) | 
            Q(last_name__icontains=arama) |
            Q(fullname__icontains=arama)  # fullname alanını arama filtrelerine ekle
        )
    
    # Sıralama alanını belirle
    sira = siralama
    if siralama == 'kayit_tarihi_eski':
        sira = 'date_joined'
    elif siralama == 'kayit_tarihi_yeni':
        sira = '-date_joined'
    elif siralama == 'son_giris_eski':
        sira = 'last_login'
    elif siralama == 'son_giris_yeni':
        sira = '-last_login'
    elif siralama == 'isim':
        sira = 'fullname'  # isim sıralamasını fullname alanına göre yap
    elif siralama == 'isim_desc':
        sira = '-fullname'  # tersten sıralama için fullname alanını kullan
    elif siralama == 'id':
        sira = 'id'
    elif siralama == 'id_desc':
        sira = '-id'
    
    # Sıralamaya göre kullanıcıları getir
    kullanicilar = kullanicilar.order_by(sira)
    
    # Sayfalama - her sayfada 10 kullanıcı göster
    paginator = Paginator(kullanicilar, 10)
    sayfa = request.GET.get('sayfa', 1)
    
    try:
        kullanicilar = paginator.page(sayfa)
    except PageNotAnInteger:
        # Eğer sayfa bir tamsayı değilse, ilk sayfayı göster
        kullanicilar = paginator.page(1)
    except EmptyPage:
        # Eğer sayfa aralık dışındaysa, son sayfayı göster
        kullanicilar = paginator.page(paginator.num_pages)
    
    context = {
        'kullanicilar': kullanicilar,
        'arama': arama,
        'siralama': siralama,
        'toplam_kullanici': User.objects.count()
    }
    
    return render(request, 'yonetim/kullanici_listesi.html', context)

@login_required
@yetkili_required
def kullanici_detay(request, kullanici_id):
    """Kullanıcı detay sayfası"""
    kullanici = get_object_or_404(User, id=kullanici_id)
    
    # Mevcut ve aktif modülleri al
    mevcut_moduller = Modul.objects.filter(aktif=True, silindi=False).values_list('id', flat=True)
    
    # Kullanıcının izlediği modüller (sadece mevcut modüllere ait olanlar)
    kullanici_ilerlemeler = KullaniciIlerleme.objects.filter(
        kullanici=kullanici,
        modul_id__in=mevcut_moduller
    ).select_related('modul')
    
    # Tamamlanan, devam eden ve başlanmamış modüller
    tamamlanan_moduller = kullanici_ilerlemeler.filter(tamamlandi=True).order_by('-tamamlanma_tarihi')
    devam_eden_moduller = kullanici_ilerlemeler.filter(tamamlandi=False, ilerleme_yuzdesi__gt=0).order_by('-baslama_tarihi')
    
    # Kullanıcının izlediği videolar (sadece aktif modüllerin videoları)
    video_izlemeler = VideoIzleme.objects.filter(
        kullanici=kullanici,
        video__modul__aktif=True,
        video__modul__silindi=False,
        video__aktif=True,
        video__silindi=False
    ).order_by('-son_izleme_tarihi')
    
    # Kullanıcının cevapladığı sorular
    kullanici_cevaplar = KullaniciCevap.objects.filter(kullanici=kullanici).order_by('-cevaplama_tarihi')
    
    # Doğru ve yanlış cevaplar
    dogru_cevaplar = kullanici_cevaplar.filter(dogru_mu=True)
    yanlis_cevaplar = kullanici_cevaplar.filter(dogru_mu=False)
    
    # İlerleme ve başarı istatistikleri
    toplam_modul_sayisi = Modul.objects.filter(aktif=True, silindi=False).count()
    tamamlanan_modul_sayisi = tamamlanan_moduller.count()
    
    toplam_soru_sayisi = kullanici_cevaplar.count()
    dogru_cevap_sayisi = dogru_cevaplar.count()
    
    modul_tamamlama_yuzdesi = (tamamlanan_modul_sayisi / toplam_modul_sayisi * 100) if toplam_modul_sayisi > 0 else 0
    dogru_cevap_yuzdesi = (dogru_cevap_sayisi / toplam_soru_sayisi * 100) if toplam_soru_sayisi > 0 else 0
    
    if LockSystem.objects.filter(users=kullanici).exists():
        lock_system_kullanicisi = True
    else:
        lock_system_kullanicisi = False

    context = {
        'kullanici': kullanici,
        'tamamlanan_moduller': tamamlanan_moduller,
        'devam_eden_moduller': devam_eden_moduller,
        'video_izlemeler': video_izlemeler,
        'kullanici_cevaplar': kullanici_cevaplar,
        'dogru_cevaplar': dogru_cevaplar,
        'yanlis_cevaplar': yanlis_cevaplar,
        'modul_tamamlama_yuzdesi': int(modul_tamamlama_yuzdesi),
        'dogru_cevap_yuzdesi': int(dogru_cevap_yuzdesi),
        'toplam_modul_sayisi': toplam_modul_sayisi,
        'tamamlanan_modul_sayisi': tamamlanan_modul_sayisi,
        'toplam_soru_sayisi': toplam_soru_sayisi,
        'dogru_cevap_sayisi': dogru_cevap_sayisi,
        'lock_system_kullanicisi': lock_system_kullanicisi,
    }
    
    return render(request, 'yonetim/kullanici_detay.html', context)

# Mesaj Sistemi
@login_required
def mesaj_listesi(request):
    """Kullanıcının mesaj listesini gösterir"""
    # Kullanıcının gelen ve gönderilen mesajlarını al
    if request.user.is_staff:
        # Staff kullanıcılar için tüm mesajları göster
        gelen_mesajlar = Mesaj.objects.filter(alici=request.user).order_by('-olusturma_tarihi')
        gonderilen_mesajlar = Mesaj.objects.filter(gonderen=request.user).order_by('-olusturma_tarihi')
    else:
        # Normal kullanıcılar için metinsel soru mesajlarını gizle
        gelen_mesajlar = Mesaj.objects.filter(alici=request.user).exclude(
            konu__contains="Metinsel Soru Değerlendirme"
        ).order_by('-olusturma_tarihi')
        
        gonderilen_mesajlar = Mesaj.objects.filter(gonderen=request.user).exclude(
            konu__contains="Metinsel Soru Değerlendirme"
        ).order_by('-olusturma_tarihi')
    
    # Okunmayan mesaj sayısını hesapla
    if request.user.is_staff:
        okunmayan_mesaj_sayisi = gelen_mesajlar.filter(okundu=False).count()
    else:
        okunmayan_mesaj_sayisi = gelen_mesajlar.filter(okundu=False).exclude(
            konu__contains="Metinsel Soru Değerlendirme"
        ).count()
    
    # Sayfalama
    gelen_sayfa_basina = 15  # Her sayfada 15 mesaj
    gonderilen_sayfa_basina = 15
    
    gelen_paginator = Paginator(gelen_mesajlar, gelen_sayfa_basina)
    gonderilen_paginator = Paginator(gonderilen_mesajlar, gonderilen_sayfa_basina)
    
    gelen_sayfa = request.GET.get('gelen_sayfa', 1)
    gonderilen_sayfa = request.GET.get('gonderilen_sayfa', 1)
    
    try:
        gelen_mesajlar_sayfa = gelen_paginator.get_page(gelen_sayfa)
    except PageNotAnInteger:
        # Sayfa numarası tam sayı değilse ilk sayfayı göster
        gelen_mesajlar_sayfa = gelen_paginator.page(1)
    except EmptyPage:
        # Sayfa numarası aralık dışındaysa son sayfayı göster
        gelen_mesajlar_sayfa = gelen_paginator.page(gelen_paginator.num_pages)
    
    try:
        gonderilen_mesajlar_sayfa = gonderilen_paginator.get_page(gonderilen_sayfa)
    except PageNotAnInteger:
        gonderilen_mesajlar_sayfa = gonderilen_paginator.page(1)
    except EmptyPage:
        gonderilen_mesajlar_sayfa = gonderilen_paginator.page(gonderilen_paginator.num_pages)
    
    context = {
        'gelen_mesajlar': gelen_mesajlar_sayfa,
        'gonderilen_mesajlar': gonderilen_mesajlar_sayfa,
        'okunmayan_mesaj_sayisi': okunmayan_mesaj_sayisi,
        'toplam_gelen_mesaj': gelen_mesajlar.count(),
        'toplam_gonderilen_mesaj': gonderilen_mesajlar.count()
    }
    
    return render(request, 'mesajlar/mesaj_listesi.html', context)

@login_required
def mesaj_detay(request, mesaj_id):
    """Mesaj detayını gösterir"""
    # Mesajı al (kullanıcının erişebileceği mesajlardan)
    mesaj = get_object_or_404(
        Mesaj.objects.filter(
            Q(alici=request.user) | Q(gonderen=request.user),
            id=mesaj_id
        )
    )
    
    # Eğer kullanıcı alıcıysa ve mesaj okunmamışsa, okundu olarak işaretle
    if mesaj.alici == request.user and not mesaj.okundu:
        mesaj.okundu = True
        mesaj.okunma_tarihi = timezone.now()
        
        # Durumu bekliyor ise cevaplandı olarak güncelle
        # İleride "okundu" şeklinde bir durum eklenebilir
        if mesaj.durum == 'bekliyor' and mesaj.cevap_mesaji is None:
            mesaj.durum = 'cevaplandi'
        
        mesaj.save(update_fields=['okundu', 'okunma_tarihi', 'durum'])
    
    # Mesaja verilen cevapları al
    cevaplar = Mesaj.objects.filter(cevap_mesaji=mesaj).order_by('olusturma_tarihi')
    
    context = {
        'mesaj': mesaj,
        'cevaplar': cevaplar
    }
    
    return render(request, 'mesajlar/mesaj_detay.html', context)

@login_required
def yeni_mesaj(request):
    """Yeni mesaj gönderme formu"""
    # Staff olmayan kullanıcılar sadece kendilerine atanmış sorumlu staff'a mesaj gönderebilir
    if not request.user.is_staff:
        if hasattr(request.user, 'sorumlu_staff') and request.user.sorumlu_staff:
            staff_kullanicilar = User.objects.filter(id=request.user.sorumlu_staff.id, is_active=True)
        else:
            # Sorumlu staff atanmamış kullanıcılar tüm staff'lara mesaj gönderebilir (admin/süper kullanıcılar hariç)
            staff_kullanicilar = User.objects.filter(is_staff=True, is_active=True, is_superuser=False)
    else:
        # Staff kullanıcılar tüm kullanıcılara mesaj gönderebilir (kendisi hariç)
        staff_kullanicilar = User.objects.filter(is_active=True).exclude(id=request.user.id)
        
        # Staff kullanıcılar da admin/süper kullanıcılara mesaj gönderemesin (eğer kendileri süper kullanıcı değilse)
        if not request.user.is_superuser:
            staff_kullanicilar = staff_kullanicilar.exclude(is_superuser=True)
    
    if request.method == 'POST':
        alici_id = request.POST.get('alici')
        konu = request.POST.get('konu')
        icerik = request.POST.get('icerik')
        
        # Form doğrulama
        if not alici_id or not konu or not icerik:
            messages.error(request, 'Lütfen tüm alanları doldurun.')
            return redirect('yeni_mesaj')
        
        try:
            alici = User.objects.get(id=alici_id)
            
            # Admin/süper kullanıcılara mesaj gönderilmesini engelle (eğer gönderen süper kullanıcı değilse)
            if alici.is_superuser and not request.user.is_superuser:
                messages.error(request, 'Bu kullanıcıya mesaj gönderemezsiniz.')
                return redirect('yeni_mesaj')
            
            # Staff olmayan kullanıcılar sadece kendilerine atanmış staff'a mesaj gönderebilir
            if not request.user.is_staff and not alici.is_staff:
                messages.error(request, 'Bu kullanıcıya mesaj gönderemezsiniz.')
                return redirect('yeni_mesaj')
            
            # Staff olmayan kullanıcı, sorumlu staff'ı dışındaki staff'a mesaj gönderemez
            if not request.user.is_staff and hasattr(request.user, 'sorumlu_staff') and request.user.sorumlu_staff and alici.id != request.user.sorumlu_staff.id:
                messages.error(request, 'Sadece size atanmış sorumlu personele mesaj gönderebilirsiniz.')
                return redirect('yeni_mesaj')
            
            # Mesajı oluştur
            mesaj = Mesaj.objects.create(
                gonderen=request.user,
                alici=alici,
                konu=konu,
                icerik=icerik
            )
            
            messages.success(request, 'Mesajınız başarıyla gönderildi.')
            return redirect('mesajlar')
            
        except User.DoesNotExist:
            messages.error(request, 'Alıcı bulunamadı.')
            return redirect('yeni_mesaj')
    
    context = {
        'staff_kullanicilar': staff_kullanicilar
    }
    
    return render(request, 'mesajlar/yeni_mesaj.html', context)

@login_required
def mesaj_cevapla(request, mesaj_id):
    """Mesaja cevap verme"""
    # Mesajı al (kullanıcının erişebileceği mesajlardan)
    mesaj = get_object_or_404(
        Mesaj.objects.filter(
            Q(alici=request.user) | Q(gonderen=request.user),
            id=mesaj_id
        )
    )
    
    if request.method == 'POST':
        icerik = request.POST.get('icerik')
        
        if not icerik:
            messages.error(request, 'Mesaj içeriği boş olamaz.')
            return redirect('mesaj_detay', mesaj_id=mesaj.id)
        
        # Cevap mesajını oluştur
        if mesaj.alici == request.user:
            alici = mesaj.gonderen
        else:
            alici = mesaj.alici
        
        cevap = Mesaj.objects.create(
            gonderen=request.user,
            alici=alici,
            konu=f"RE: {mesaj.konu}",
            icerik=icerik,
            cevap_mesaji=mesaj
        )
        
        # Cevaplanan mesajın durumunu güncelle
        if mesaj.gonderen == request.user:
            mesaj.durum = 'cevaplandi'
            mesaj.save(update_fields=['durum'])
        
        messages.success(request, 'Cevabınız başarıyla gönderildi.')
        return redirect('mesaj_detay', mesaj_id=mesaj.id)
    
    context = {
        'mesaj': mesaj
    }
    
    return render(request, 'mesajlar/mesaj_cevapla.html', context)

@login_required
def mesajlar_gelen_temizle(request):
    """Gelen kutusundaki tüm mesajları temizler"""
    # Normal kullanıcılar için metinsel soru değerlendirme mesajlarını dahil etmeme
    if request.user.is_staff:
        Mesaj.objects.filter(alici=request.user).delete()
    else:
        Mesaj.objects.filter(alici=request.user).exclude(
            konu__contains="Metinsel Soru Değerlendirme"
        ).delete()
    
    messages.success(request, 'Gelen kutunuz başarıyla temizlendi.')
    return redirect('mesajlar')

@login_required
def mesajlar_gonderilen_temizle(request):
    """Gönderilen tüm mesajları temizler"""
    # Normal kullanıcılar için metinsel soru değerlendirme mesajlarını dahil etmeme
    if request.user.is_staff:
        Mesaj.objects.filter(gonderen=request.user).delete()
    else:
        Mesaj.objects.filter(gonderen=request.user).exclude(
            konu__contains="Metinsel Soru Değerlendirme"
        ).delete()
    
    messages.success(request, 'Gönderilen mesajlarınız başarıyla temizlendi.')
    return redirect('mesajlar')

# Görüntülü Görüşme Sistemi
@login_required
def gorusme_listesi(request):
    # Kullanıcının erişebileceği görüşmeleri getir
    if not request.user.is_authenticated:
        return redirect('login')
    
    now = timezone.now()
    
    # Önce tüm görüşmelerin durumlarını kontrol et ve güncelle
    # Bekleyen ve başlangıç zamanı gelmiş görüşmeleri aktif olarak işaretle
    bekleyen_gorusmeler = Gorusme.objects.filter(
        durum='bekliyor',
        baslangic_zamani__lte=now
    )
    for gorusme in bekleyen_gorusmeler:
        gorusme.durum = 'aktif'
        gorusme.save(update_fields=['durum'])
    
    # Aktif görüşmeler (şu anda devam eden)
    aktif_gorusmeler = Gorusme.objects.filter(
        durum='aktif'
    ).filter(
        models.Q(olusturan=request.user) |
        models.Q(katilimcilar__kullanici=request.user) |  # Davet durumuna bakılmaksızın tüm katılımcılar
        models.Q(giris_izni='herkes')
    ).distinct()
    
    # Yaklaşan görüşmeler (gelecekteki)
    yaklasan_gorusmeler = Gorusme.objects.filter(
        durum='bekliyor',
        baslangic_zamani__gt=now
    ).filter(
        models.Q(olusturan=request.user) |
        models.Q(katilimcilar__kullanici=request.user)
    ).distinct()
    
    # Geçmiş görüşmeler
    gecmis_gorusmeler = Gorusme.objects.filter(
        durum='tamamlandi'
    ).filter(
        models.Q(olusturan=request.user) |
        models.Q(katilimcilar__kullanici=request.user)
    ).distinct()[:10]  # Son 10 tane
    
    context = {
        'aktif_gorusmeler': aktif_gorusmeler,
        'yaklasan_gorusmeler': yaklasan_gorusmeler,
        'gecmis_gorusmeler': gecmis_gorusmeler
    }
    
    return render(request, 'gorusme/gorusme_listesi.html', context)

@login_required
def yeni_gorusme(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Staff kontrolünü kaldırdım - tüm kullanıcılar görüşme oluşturabilir
    
    context = {}
    
    if request.method == 'POST':
        # Form verilerini işle
        baslik = request.POST.get('baslik', '').strip()
        aciklama = request.POST.get('aciklama', '')
        gorusme_turu = request.POST.get('gorusme_turu', '')
        giris_izni = request.POST.get('giris_izni', 'davetli')
        kayit_alsinmi = request.POST.get('kayit_alsinmi', '') == 'on'
        
        # Temel veri doğrulama
        hata_var = False
        
        if not baslik:
            messages.error(request, 'Lütfen görüşme başlığını girin.')
            hata_var = True
            
        if not gorusme_turu:
            messages.error(request, 'Lütfen görüşme türünü seçin.')
            hata_var = True
        
        if hata_var:
            # Hata varsa, kullanıcı listesini ekle ve formu tekrar göster
            context['kullanicilar'] = User.objects.filter(is_staff=True).exclude(id=request.user.id).order_by('first_name', 'last_name')
            return render(request, 'gorusme/yeni_gorusme.html', context)
            
        # Başlangıç zamanını ayarla
        now = timezone.now()
        
        if gorusme_turu == 'planlanan':
            baslangic_tarihi = request.POST.get('baslangic_tarihi', '')
            baslangic_saati = request.POST.get('baslangic_saati', '')
            
            if not baslangic_tarihi or not baslangic_saati:
                messages.error(request, 'Planlanan görüşmeler için başlangıç tarihi ve saati gereklidir.')
                context['kullanicilar'] = User.objects.filter(is_staff=True).exclude(id=request.user.id).order_by('first_name', 'last_name')
                return render(request, 'gorusme/yeni_gorusme.html', context)
            
            try:
                print(f"Debug: Tarih={baslangic_tarihi}, Saat={baslangic_saati}")
                baslangic_zamani = datetime.strptime(f'{baslangic_tarihi} {baslangic_saati}', '%Y-%m-%d %H:%M')
                baslangic_zamani = timezone.make_aware(baslangic_zamani)
                
                if baslangic_zamani < now:
                    messages.error(request, 'Başlangıç zamanı geçmiş bir tarih olamaz.')
                    context['kullanicilar'] = User.objects.filter(is_staff=True).exclude(id=request.user.id).order_by('first_name', 'last_name')
                    return render(request, 'gorusme/yeni_gorusme.html', context)
                
                durum = 'bekliyor'
            except ValueError as e:
                print(f"Debug: Hata - {str(e)}")
                messages.error(request, f'Geçersiz tarih veya saat formatı. Saat için HH:MM formatını kullanın ve tarih için geçerli bir tarih seçin. Hata: {str(e)}')
                context['kullanicilar'] = User.objects.filter(is_staff=True).exclude(id=request.user.id).order_by('first_name', 'last_name')
                return render(request, 'gorusme/yeni_gorusme.html', context)
            except Exception as e:
                print(f"Debug: Beklenmeyen hata - {str(e)}")
                messages.error(request, f'Tarih/saat işlenirken bir hata oluştu: {str(e)}')
                context['kullanicilar'] = User.objects.filter(is_staff=True).exclude(id=request.user.id).order_by('first_name', 'last_name')
                return render(request, 'gorusme/yeni_gorusme.html', context)
        else:
            # Anlık görüşme
            baslangic_zamani = now
            durum = 'aktif'
        
        # Jitsi oda adı oluştur (benzersiz bir string)
        jitsi_oda_adi = f"kib_{uuid.uuid4().hex[:10]}"
        
        # Görüşme oluştur
        gorusme = Gorusme.objects.create(
            baslik=baslik,
            aciklama=aciklama,
            olusturan=request.user,
            baslangic_zamani=baslangic_zamani,
            durum=durum,
            giris_izni=giris_izni,
            kayit_alsinmi=kayit_alsinmi,
            jitsi_oda_adi=jitsi_oda_adi
        )
        
        # Katılımcıları ekle (sadece davetliler modunda)
        if giris_izni == 'davetli':
            for key, value in request.POST.items():
                if key.startswith('katilimci_') and value:
                    try:
                        kullanici_id = int(value)
                        kullanici = User.objects.get(id=kullanici_id)
                        
                        # Kendini katılımcı olarak eklememeli
                        if kullanici != request.user:
                            GorusmeKatilimci.objects.create(
                                gorusme=gorusme,
                                kullanici=kullanici,
                                davet_durumu='bekliyor'
                            )
                    except (User.DoesNotExist, ValueError):
                        continue
        
        # Toplantı planlandığına dair bildirim gönder
        if durum == 'bekliyor':
            gorusme.bildirim_gonder('planlandi')
        elif durum == 'aktif':
            gorusme.bildirim_gonder('aktif')
            
        messages.success(request, 'Görüşme başarıyla oluşturuldu.')
        
        if durum == 'aktif':
            # Anlık görüşmeler için doğrudan görüşme sayfasına yönlendir
            return redirect('gorusme_detay', gorusme_id=gorusme.id)
        else:
            # Planlanan görüşmeler için görüşme listesine yönlendir
            return redirect('gorusme_listesi')
    
    # Kullanıcı listesini getir (katılımcı eklemek için) - sadece staff kullanıcıları göster
    if request.user.is_staff or request.user.is_superuser:
        # Staff kullanıcılar tüm kullanıcıları görebilir
        kullanicilar = User.objects.exclude(id=request.user.id).order_by('first_name', 'last_name')
    else:
        # Normal kullanıcılar sadece staff kullanıcıları görebilir
        kullanicilar = User.objects.filter(is_staff=True).exclude(id=request.user.id).order_by('first_name', 'last_name')
    
    # Kullanıcılar için display_name ekle
    for kullanici in kullanicilar:
        if kullanici.first_name and kullanici.last_name:
            kullanici.display_name = f"{kullanici.first_name} {kullanici.last_name}"
        else:
            kullanici.display_name = kullanici.username
    
    context['kullanicilar'] = kullanicilar
    
    return render(request, 'gorusme/yeni_gorusme.html', context)

@login_required
def gorusme_detay(request, gorusme_id):
    if not request.user.is_authenticated:
        return redirect('login')
    
    try:
        gorusme = Gorusme.objects.get(id=gorusme_id)
    except Gorusme.DoesNotExist:
        messages.error(request, 'Görüşme bulunamadı.')
        return redirect('gorusme_listesi')
    
    # Kullanıcının bu görüşmeye katılma izni var mı kontrol et
    # Görüşme sahibi, davet edilmiş herhangi bir kullanıcı veya herkes modunda ise katılabilir
    katilim_izni = (
        gorusme.olusturan == request.user or
        GorusmeKatilimci.objects.filter(gorusme=gorusme, kullanici=request.user).exists() or
        gorusme.giris_izni == 'herkes' or
        request.user.is_staff  # Staff kullanıcılar her zaman katılabilir
    )
    
    if not katilim_izni:
        messages.error(request, 'Bu görüşmeye katılma izniniz yok.')
        return redirect('gorusme_listesi')
    
    # Eğer görüşme bekliyor durumundaysa ve başlangıç zamanı geldiyse, aktif yap
    now = timezone.now()
    if gorusme.durum == 'bekliyor' and gorusme.baslangic_zamani <= now:
        eski_durum = gorusme.durum
        gorusme.durum = 'aktif'
        gorusme.save(update_fields=['durum'])
        
        # Durum değiştiyse bildirim gönder
        if eski_durum != 'aktif':
            gorusme.bildirim_gonder('aktif')
    
    # Kullanıcı görüşmeye katıldı olarak işaretle
    if gorusme.durum == 'aktif' and not gorusme.olusturan == request.user:
        katilimci, created = GorusmeKatilimci.objects.get_or_create(
            gorusme=gorusme,
            kullanici=request.user,
            defaults={'davet_durumu': 'kabul'}
        )
        
        if not katilimci.katilim_zamani:
            katilimci.katilim_zamani = now
            katilimci.davet_durumu = 'kabul'
            katilimci.save(update_fields=['katilim_zamani', 'davet_durumu'])
    
    # Görüşme URL'si
    gorusme_url = gorusme.oda_linki()
    
    # Kullanıcı yetkisine göre filtreleme yap
    # Staff kullanıcılar tüm kullanıcıları görebilir
    # Normal kullanıcılar sadece staff kullanıcıları görebilir
    if request.user.is_staff or request.user.is_superuser:
        # Staff kullanıcılar tüm kullanıcıları görebilir
        kullanicilar = User.objects.exclude(id=request.user.id).order_by('first_name', 'last_name')
    else:
        # Normal kullanıcılar sadece staff kullanıcıları görebilir
        kullanicilar = User.objects.filter(is_staff=True).exclude(id=request.user.id).order_by('first_name', 'last_name')
    
    # Kullanıcılar için display_name ekle
    for kullanici in kullanicilar:
        if kullanici.first_name and kullanici.last_name:
            kullanici.display_name = f"{kullanici.first_name} {kullanici.last_name}"
        else:
            kullanici.display_name = kullanici.username
    
    # Katılımcıları getir
    katilimcilar = GorusmeKatilimci.objects.filter(gorusme=gorusme)
    
    # Katılımcılar için display_name ekle
    for katilimci in katilimcilar:
        kullanici = katilimci.kullanici
        if kullanici.first_name and kullanici.last_name:
            kullanici.display_name = f"{kullanici.first_name} {kullanici.last_name}"
        else:
            kullanici.display_name = kullanici.username
    
    # Görüşmeyi oluşturan için display_name ekle
    if gorusme.olusturan.first_name and gorusme.olusturan.last_name:
        gorusme.olusturan.display_name = f"{gorusme.olusturan.first_name} {gorusme.olusturan.last_name}"
    else:
        gorusme.olusturan.display_name = gorusme.olusturan.username
    
    context = {
        'gorusme': gorusme,
        'gorusme_id': str(gorusme.id),  # UUID string olarak gönder
        'meeting_link': gorusme_url,
        'kullanicilar': kullanicilar,
        'katilimcilar': katilimcilar,
        'users': kullanicilar  # template'deki değişken adıyla uyumlu olması için
    }
    
    return render(request, 'gorusme/gorusme.html', context)

@login_required
@csrf_exempt
def gorusme_sonlandir(request, gorusme_id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Giriş yapmanız gerekiyor.'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Geçersiz istek yöntemi. POST gerekli.'})
    
    try:
        gorusme = Gorusme.objects.get(id=gorusme_id)
    except Gorusme.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Görüşme bulunamadı.'})
    
    # Sadece görüşmeyi oluşturan kişi sonlandırabilir
    if gorusme.olusturan != request.user:
        return JsonResponse({'success': False, 'message': 'Bu işlem için yetkiniz yok.'})
    
    now = timezone.now()
    baslangic = gorusme.baslangic_zamani
    eski_durum = gorusme.durum
    
    # Görüşmeyi sonlandır
    gorusme.durum = 'tamamlandi'
    gorusme.bitis_zamani = now
    
    # Süreyi hesapla
    if baslangic:
        sure_dakika = int((now - baslangic).total_seconds() / 60)
        gorusme.sure_dakika = sure_dakika
    
    gorusme.save()
    
    # Tüm katılımcıların ayrılma zamanını güncelle
    GorusmeKatilimci.objects.filter(
        gorusme=gorusme, 
        katilim_zamani__isnull=False, 
        ayrilma_zamani__isnull=True
    ).update(ayrilma_zamani=now)
    
    # Formdan gelen yönlendirme URL'ini al, yoksa varsayılan olarak anasayfaya yönlendir
    redirect_url = request.POST.get('redirect_url', '/')
    
    # JSON yanıtı döndürmek yerine sayfaya yönlendir
    return redirect(redirect_url)

@login_required
@csrf_exempt
def gorusme_davet_gonder(request, gorusme_id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Giriş yapmanız gerekiyor.'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Geçersiz istek.'})
    
    try:
        gorusme = Gorusme.objects.get(id=gorusme_id)
    except Gorusme.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Görüşme bulunamadı.'})
    
    # Sadece görüşme sahibi davet gönderebilir
    if gorusme.olusturan != request.user and not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Bu işlem için yetkiniz yok.'})
    
    # JSON veya form verilerini kontrol et
    if request.content_type == 'application/json':
        import json
        try:
            data = json.loads(request.body)
            kullanici_id = data.get('kullanici_id')
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Geçersiz JSON formatı.'})
    else:
        kullanici_id = request.POST.get('kullanici_id')
    
    if not kullanici_id:
        return JsonResponse({'success': False, 'message': 'Kullanıcı seçilmedi.'})
    
    try:
        kullanici = User.objects.get(id=kullanici_id)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Kullanıcı bulunamadı.'})
    
    # Kullanıcı kendisini davet edemez
    if kullanici == request.user:
        return JsonResponse({'success': False, 'message': 'Kendinizi davet edemezsiniz.'})
    
    # Kullanıcı zaten davet edilmiş mi kontrol et
    katilimci, created = GorusmeKatilimci.objects.get_or_create(
        gorusme=gorusme,
        kullanici=kullanici,
        defaults={'davet_durumu': 'bekliyor'}
    )
    
    if not created and katilimci.davet_durumu == 'bekliyor':
        return JsonResponse({'success': False, 'message': 'Bu kullanıcı zaten davet edilmiş.'})
    
    # Davet durumunu güncelle
    katilimci.davet_durumu = 'bekliyor'
    katilimci.save()
    
    # Davet edilen kullanıcıya bildirim mesajı gönder
    tarih_formatli = gorusme.baslangic_zamani.strftime('%d.%m.%Y %H:%M')
    konu = f"Görüşme Daveti: {gorusme.baslik}"
    icerik = f"Merhaba,\n\n{request.user.get_full_name() or request.user.username} tarafından '{gorusme.baslik}' başlıklı görüşmeye davet edildiniz.\nGörüşme Tarihi: {tarih_formatli}\n\nGörüşme Linki: {gorusme.oda_linki()}\n\nKendine İyi Bak Platformu"
    
    Mesaj.objects.create(
        gonderen=request.user,
        alici=kullanici,
        konu=konu,
        icerik=icerik,
        durum='bekliyor'
    )
    
    return JsonResponse({
        'success': True, 
        'message': f'{kullanici.get_full_name() if hasattr(kullanici, "get_full_name") else kullanici.username} başarıyla davet edildi.'
    })

# Haftalık Aktivite Sistemi
@login_required
def aktivite_listesi(request):
    """Kullanıcı için erişilebilir aktiviteleri listeler"""
    from django.utils import timezone
    from .models import HaftalikAktivite, KullaniciAktiviteYaniti
    
    # Bugünün tarihini al
    today = timezone.now().date()
    
    # Tüm aktif aktiviteleri getir - olusturma_tarihi yerine id kullanarak doğru sıralama yap
    aktiviteler = HaftalikAktivite.objects.filter(
        aktif=True,
        silindi=False
    ).order_by('hafta', 'id')
    
    # Erişim izni olan haftaları belirle
    erisim_izni_olan_haftalar = set()
    onceki_hafta_tamamlandi = True
    
    # Her hafta için kontrol et
    mevcut_haftalar = sorted(set(aktiviteler.values_list('hafta', flat=True)))
    
    for hafta in mevcut_haftalar:
        if hafta > 1 and not onceki_hafta_tamamlandi:
            continue
        
        # Bu haftanın aktivitelerini getir
        hafta_aktiviteleri = aktiviteler.filter(hafta=hafta)
        
        # Bu haftanın tamamlanma durumunu kontrol et
        hafta_tamamlandi = True
        for aktivite in hafta_aktiviteleri:
            try:
                yanit = KullaniciAktiviteYaniti.objects.get(
                    kullanici=request.user,
                    aktivite=aktivite
                )
                if not yanit.tamamlandi:
                    hafta_tamamlandi = False
                    break
            except KullaniciAktiviteYaniti.DoesNotExist:
                hafta_tamamlandi = False
                break
        
        # Bu hafta erişilebilir
        erisim_izni_olan_haftalar.add(hafta)
        
        # Sonraki hafta için tamamlanma durumunu güncelle
        onceki_hafta_tamamlandi = hafta_tamamlandi
    
    # Her aktivite için kullanıcının yanıt durumunu ve erişim durumunu kontrol et
    for aktivite in aktiviteler:
        aktivite.kullanici_yaniti_var = False
        aktivite.tamamlandi = False
        
        try:
            yanit = KullaniciAktiviteYaniti.objects.get(
                kullanici=request.user,
                aktivite=aktivite
            )
            aktivite.kullanici_yaniti_var = True
            aktivite.tamamlandi = yanit.tamamlandi
        except KullaniciAktiviteYaniti.DoesNotExist:
            pass
        
        # Erişim durumunu belirle
        aktivite.erisim_var = True
        
        # Hafta erişim kontrolü
        if aktivite.hafta > 1 and aktivite.hafta not in erisim_izni_olan_haftalar:
            aktivite.erisim_var = False
        
        # Başlangıç tarihi kontrolü
        elif aktivite.baslangic_tarihi and aktivite.baslangic_tarihi > today:
            aktivite.erisim_var = False
        
        # Bitiş tarihi kontrolü
        elif aktivite.bitis_tarihi and aktivite.bitis_tarihi < today:
            aktivite.erisim_var = False
    
    # Aktiviteleri haftalara göre grupla
    aktivite_gruplari = {}
    hafta_tamamlanan_aktivite_sayilari = {}
    hafta_toplam_aktivite_sayilari = {}
    
    for aktivite in aktiviteler:
        hafta = aktivite.hafta
        
        if hafta not in aktivite_gruplari:
            aktivite_gruplari[hafta] = []
            hafta_tamamlanan_aktivite_sayilari[hafta] = 0
            hafta_toplam_aktivite_sayilari[hafta] = 0
        
        aktivite_gruplari[hafta].append(aktivite)
        hafta_toplam_aktivite_sayilari[hafta] += 1
        
        if aktivite.tamamlandi:
            hafta_tamamlanan_aktivite_sayilari[hafta] += 1
    
    # Grupları sıralı listeye dönüştür ve her gruptaki aktiviteleri id'ye göre sırala
    aktivite_gruplari_sirali = []
    for hafta, aktiviteler_listesi in sorted(aktivite_gruplari.items()):
        # Her haftanın aktivitelerini id'ye göre sırala
        sirali_aktiviteler = sorted(aktiviteler_listesi, key=lambda x: x.id)
        aktivite_gruplari_sirali.append((hafta, sirali_aktiviteler))
    
    context = {
        'aktivite_gruplari': aktivite_gruplari_sirali,
        'erisim_izni_olan_haftalar': erisim_izni_olan_haftalar,
        'hafta_tamamlanan_aktivite_sayilari': hafta_tamamlanan_aktivite_sayilari,
        'hafta_toplam_aktivite_sayilari': hafta_toplam_aktivite_sayilari,
        'today': today,
    }
    
    return render(request, 'aktiviteler/aktivite_listesi.html', context)

@login_required
def aktivite_hafta_erisim_kontrolu(request, hafta):
    """
    Belirli bir haftanın aktivitelerine erişim kontrolü yapar.
    İlk hafta her zaman erişilebilirdir. Diğer haftalar için kullanıcının
    kayıt tarihine göre erişim sağlanır ve önceki haftaların tamamlanma durumu kontrol edilir.
    
    Return:
        None: Erişim izni varsa
        HttpResponseRedirect: Erişim izni yoksa yönlendirme
    """
    from .models import HaftalikAktivite, KullaniciAktiviteYaniti, Modul, KullaniciIlerleme
    from django.utils import timezone
    
    # Admin veya staff her zaman erişebilir
    if request.user.is_superuser or request.user.is_staff:
        return None
    
    # LockSystem kontrolü - Eğer kullanıcı LockSystem'de varsa tüm haftalara erişim ver
    if LockSystem.objects.filter(users=request.user).exists():
        return None
    
    # İlk hafta her zaman erişilebilir
    if hafta == 1:
        return None
        
    # Kullanıcının kayıt tarihini al
    kayit_tarihi = getattr(request.user, 'kayit_tarihi', None) or request.user.date_joined.date()
    
    # Bugünün tarihini al - timezone.now() yerine timezone.localtime() kullan 
    bugun = timezone.localtime().date()
    
    # Debug amaçlı yazdır
    print(f"DEBUG aktivite_hafta_erisim_kontrolu: Kullanıcı={request.user.username}, Kayıt={kayit_tarihi}, Bugün={bugun}, Erişilen Hafta={hafta}")
    
    # Aktivitenin erişilebilir olduğu tarih (kayıt tarihine hafta sayısı * 7 gün ekle)
    from datetime import timedelta
    erisim_tarihi = kayit_tarihi + timedelta(days=(hafta - 1) * 7)
    
    print(f"DEBUG: Hafta Erişim Tarihi={erisim_tarihi}")
    
    # Eğer bugün, erişim tarihinden önce ise erişimi reddet
    if bugun < erisim_tarihi:
        messages.warning(
            request, 
            f"{hafta}. hafta aktiviteleri {erisim_tarihi.strftime('%d.%m.%Y')} tarihinde erişime açılacaktır."
        )
        return redirect('courses')
    
    # Önceki hafta aktivitelerinin tamamlanma durumunu kontrol et
    if hafta > 1:
        onceki_hafta = hafta - 1
        onceki_hafta_aktiviteleri = HaftalikAktivite.objects.filter(
            aktif=True, 
            silindi=False,
            hafta=onceki_hafta
        )
        
        if onceki_hafta_aktiviteleri.exists():
            # Önceki haftanın tüm aktivitelerini kontrol et
            for aktivite in onceki_hafta_aktiviteleri:
                try:
                    yanit = KullaniciAktiviteYaniti.objects.get(
                        kullanici=request.user,
                        aktivite=aktivite
                    )
                    if not yanit.tamamlandi:
                        messages.warning(
                            request, 
                            f"{hafta}. hafta aktivitelerine erişmek için önce {onceki_hafta}. haftadaki '{aktivite.baslik}' aktivitesini tamamlamanız gerekiyor."
                        )
                        return redirect('courses')
                except KullaniciAktiviteYaniti.DoesNotExist:
                    messages.warning(
                        request, 
                        f"{hafta}. hafta aktivitelerine erişmek için önce {onceki_hafta}. haftadaki '{aktivite.baslik}' aktivitesini tamamlamanız gerekiyor."
                    )
                    return redirect('courses')
        
        # Önceki hafta modüllerinin tamamlanma durumunu kontrol et
        onceki_hafta_modulleri = Modul.objects.filter(
            aktif=True,
            silindi=False,
            hafta=onceki_hafta
        )
        
        if onceki_hafta_modulleri.exists():
            # Önceki haftanın tüm modüllerini kontrol et
            for modul in onceki_hafta_modulleri:
                try:
                    ilerleme = KullaniciIlerleme.objects.get(
                        kullanici=request.user,
                        modul=modul
                    )
                    if not ilerleme.tamamlandi:
                        messages.warning(
                            request, 
                            f"{hafta}. hafta aktivitelerine erişmek için önce {onceki_hafta}. haftadaki '{modul.baslik}' modülünü tamamlamanız gerekiyor."
                        )
                        return redirect('courses')
                except KullaniciIlerleme.DoesNotExist:
                    messages.warning(
                        request, 
                        f"{hafta}. hafta aktivitelerine erişmek için önce {onceki_hafta}. haftadaki '{modul.baslik}' modülünü tamamlamanız gerekiyor."
                    )
                    return redirect('courses')
    
    # Aynı haftadaki aktiviteler artık sırayla tamamlanmayı gerektirmiyor
    # Hepsi aynı anda erişilebilir
    
    return None

@login_required
def aktivite_detay(request, aktivite_id):
    """Aktivite detaylarını gösterir"""
    from .models import HaftalikAktivite, KullaniciAktiviteYaniti
    from django.http import HttpResponseRedirect
    
    # Aktiviteyi getir
    aktivite = get_object_or_404(HaftalikAktivite, id=aktivite_id, aktif=True, silindi=False)
    
    # LockSystem kontrolü - Eğer kullanıcı LockSystem'de varsa aktiviteye erişim ver
    lock_system_kullanicisi = LockSystem.objects.filter(users=request.user).exists()
    
    # Aktivitenin kullanıcıya açık olup olmadığını kontrol et (LockSystem kullanıcısı değilse)
    if not lock_system_kullanicisi and not aktivite.kullaniciya_acik_mi(request.user):
        # Kullanıcının kayıt tarihini al
        kayit_tarihi = getattr(request.user, 'kayit_tarihi', None) or request.user.date_joined.date()
        # Aktivitenin erişilebilir olacağı tarihi hesapla
        from datetime import timedelta
        erisim_tarihi = kayit_tarihi + timedelta(days=(aktivite.hafta - 1) * 7)
        messages.warning(
            request, 
            f"Bu aktivite {erisim_tarihi.strftime('%d.%m.%Y')} tarihinde erişime açılacaktır."
        )
        return redirect('courses')
    
    # Aktivitenin haftasına erişim kontrolü (LockSystem kullanıcısı değilse)
    if not lock_system_kullanicisi:
        erisim_kontrolu = aktivite_hafta_erisim_kontrolu(request, aktivite.hafta)
        if isinstance(erisim_kontrolu, HttpResponseRedirect):
            return erisim_kontrolu
    
    # Kullanıcının bu aktiviteye yanıtı var mı?
    try:
        kullanici_yaniti = KullaniciAktiviteYaniti.objects.get(
            kullanici=request.user,
            aktivite=aktivite
        )
    except KullaniciAktiviteYaniti.DoesNotExist:
        kullanici_yaniti = None
    
    # Aktivitenin öğelerini getir
    ogeler = aktivite.ogeleri_getir()
    
    context = {
        'aktivite': aktivite,
        'ogeler': ogeler,
        'kullanici_yaniti': kullanici_yaniti,
        'tamamlandi': kullanici_yaniti.tamamlandi if kullanici_yaniti else False,
        'lock_system_kullanicisi': lock_system_kullanicisi,  # Template'te kullanmak için
    }
    
    return render(request, 'aktiviteler/aktivite_detay.html', context)

@login_required
@csrf_exempt
def aktivite_yanitla(request, aktivite_id):
    """Aktivite yanıtlarını kaydet"""
    from .models import HaftalikAktivite, KullaniciAktiviteYaniti
    import json
    from django.urls import reverse
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Sadece POST istekleri kabul edilir'})
    
    try:
        aktivite = get_object_or_404(HaftalikAktivite, id=aktivite_id)
        
        # JSON verisini al
        data = json.loads(request.body)
        yanitlar = data.get('yanitlar', {})
        tamamlandi = data.get('tamamlandi', False)
        
        # Debug için
        print("Alınan form verileri:", data)
        print("Yanıtlar:", yanitlar)
        
        # Yanıtları düzenle
        duzenlenmis_yanitlar = {}
        for oge_id, yanit in yanitlar.items():
            # oge_id'den "oge_" önekini kaldır
            temiz_oge_id = oge_id.replace('oge_', '')
            duzenlenmis_yanitlar[temiz_oge_id] = yanit
            
            # Tablo tipi için özel işlem
            if yanit.get('tip') == 'tablo':
                print(f"Tablo tipi yanıt - Öğe ID: {temiz_oge_id}")
                print(f"Tablo verisi: {yanit.get('tablo_veri', {})}")
        
        # Yanıt nesnesini al veya oluştur
        yanit, created = KullaniciAktiviteYaniti.objects.get_or_create(
            kullanici=request.user,
            aktivite=aktivite,
            defaults={
                'yanitlar_json': json.dumps(duzenlenmis_yanitlar),
                'tamamlandi': tamamlandi
            }
        )
        
        if not created:
            # Mevcut yanıtı güncelle
            yanit.yanitlar_json = json.dumps(duzenlenmis_yanitlar)
            yanit.tamamlandi = tamamlandi
            yanit.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Yanıtlarınız başarıyla kaydedildi.',
            'tamamlandi': tamamlandi,
            'redirect_url': reverse('courses')  # Yönlendirme URL'sini ekle
        })
        
    except HaftalikAktivite.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Aktivite bulunamadı.'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Geçersiz JSON verisi.'
        })
    except Exception as e:
        print(f"Hata oluştu: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Bir hata oluştu: {str(e)}'
        })

@login_required
@yetkili_required
def yonetim_aktivite_listesi(request):
    """Yönetim paneli - aktivite listesi"""
    from .models import HaftalikAktivite
    
    aktiviteler = HaftalikAktivite.objects.filter(silindi=False).order_by('hafta', '-olusturma_tarihi')
    
    # Her aktivite için kullanıcı yanıt sayısını hesapla
    for aktivite in aktiviteler:
        aktivite.yanit_sayisi = aktivite.kullanici_yanitlari.count()
    
    context = {
        'aktiviteler': aktiviteler,
        'aktif_menu': 'aktiviteler',
    }
    
    return render(request, 'yonetim/aktiviteler/aktivite_listesi.html', context)

@login_required
@yetkili_required
def yonetim_aktivite_ekle(request):
    """Yönetim paneli - yeni aktivite ekleme"""
    from .models import HaftalikAktivite, AktiviteOgesi
    import json
    
    if request.method == 'POST':
        baslik = request.POST.get('baslik')
        aciklama = request.POST.get('aciklama')
        hafta = request.POST.get('hafta', 1)
        aktif = 'aktif' in request.POST
        icerik_json = request.POST.get('icerik_json', '{}')
        
        # Tip parametresi her zaman "karma" olarak ayarlandı
        tip = "karma"
        
        # Form doğrulama
        if not baslik or not hafta:
            messages.error(request, 'Lütfen tüm zorunlu alanları doldurun.')
            return redirect('yonetim_aktivite_ekle')
        
        try:
            # Debug log - icerik_json içeriğini göster
            print("icerik_json içeriği:", icerik_json)
            
            # Aktiviteyi oluştur
            aktivite = HaftalikAktivite.objects.create(
                baslik=baslik,
                aciklama=aciklama,
                hafta=int(hafta),
                tip=tip,
                aktif=aktif,
                icerik_json=icerik_json,
                olusturan=request.user
            )
            
            # icerik_json verisini parse ederek öğeleri oluştur
            try:
                ogeler = json.loads(icerik_json)
                for index, oge_data in enumerate(ogeler):
                    # Öğe tipini kontrol et
                    tip = oge_data.get('tip')
                    if not tip:
                        continue
                    
                    # Temel öğe bilgileri
                    baslik = oge_data.get('baslik', '')
                    aciklama = oge_data.get('aciklama', '')
                    zorunlu = oge_data.get('zorunlu', False)
                    icerik = {}
                    
                    # Eğer tablo tipiyse, satır ve sütun bilgilerini ekle
                    if tip == 'tablo':
                        icerik = {
                            'satir_sayisi': oge_data.get('satir_sayisi', 5),
                            'sutun_sayisi': oge_data.get('sutun_sayisi', 4),
                            'sutun_basliklar': oge_data.get('sutun_basliklar', []),
                            'satir_basliklar': oge_data.get('satir_basliklar', [])
                        }
                        print(f"Tablo öğesi {index} - satır başlıkları: {icerik['satir_basliklar']}")
                        print(f"Tablo öğesi {index} - sütun başlıkları: {icerik['sutun_basliklar']}")
                    
                    # Öğeyi oluştur
                    AktiviteOgesi.objects.create(
                        aktivite=aktivite,
                        tip=tip,
                        sira=index,
                        baslik=baslik,
                        aciklama=aciklama,
                        zorunlu=zorunlu,
                        icerik_json=json.dumps(icerik) if icerik else '{}'
                    )
            except json.JSONDecodeError:
                messages.warning(request, 'İçerik JSON verisi parse edilemedi, öğeler oluşturulamadı.')
            
            messages.success(request, f'"{aktivite.baslik}" aktivitesi başarıyla oluşturuldu.')
            return redirect('yonetim_aktivite_listesi')
            
        except Exception as e:
            messages.error(request, f'Aktivite oluşturulurken bir hata oluştu: {str(e)}')
            
    context = {
        'aktif_menu': 'aktivite_ekle',
        'yeni_sistem_aciklamasi': 'Yeni sistemde aktivitenin erişilebilirliği, kullanıcının kayıt tarihi + (hafta-1) x 7 gün formülü ile hesaplanır.'
    }
    return render(request, 'yonetim/aktiviteler/aktivite_ekle.html', context)

@login_required
@yetkili_required
def yonetim_aktivite_duzenle(request, aktivite_id):
    """Yönetim paneli - aktivite düzenleme"""
    from .models import HaftalikAktivite, AktiviteOgesi
    import json
    
    aktivite = get_object_or_404(HaftalikAktivite, id=aktivite_id)
    
    if request.method == 'POST':
        baslik = request.POST.get('baslik')
        aciklama = request.POST.get('aciklama')
        hafta = request.POST.get('hafta', 1)
        aktif = 'aktif' in request.POST
        icerik_json = request.POST.get('icerik_json', '{}')
        
        # Form doğrulama
        if not baslik or not hafta:
            messages.error(request, 'Lütfen tüm zorunlu alanları doldurun.')
            return redirect('yonetim_aktivite_duzenle', aktivite_id=aktivite_id)
        
        try:
            # Aktiviteyi güncelle
            aktivite.baslik = baslik
            aktivite.aciklama = aciklama
            aktivite.hafta = int(hafta)
            aktivite.aktif = aktif
            aktivite.icerik_json = icerik_json
            aktivite.save()
            
            messages.success(request, f'"{aktivite.baslik}" aktivitesi başarıyla güncellendi.')
            
            # Öğeler düzenlendiği için kullanıcı yanıtlarını temizle
            if 'reset_responses' in request.POST:
                from .models import KullaniciAktiviteYaniti
                KullaniciAktiviteYaniti.objects.filter(aktivite=aktivite).delete()
                messages.info(request, 'Kullanıcı yanıtları temizlendi.')
                
            return redirect('yonetim_aktivite_listesi')
            
        except Exception as e:
            messages.error(request, f'Aktivite güncellenirken bir hata oluştu: {str(e)}')
    
    # Aktivite öğelerini al
    ogeler = aktivite.ogeleri_getir()
    
    context = {
        'aktivite': aktivite,
        'ogeler': ogeler,
        'aktif_menu': 'aktiviteler',
        'yeni_sistem_aciklamasi': 'Yeni sistemde aktivitenin erişilebilirliği, kullanıcının kayıt tarihi + (hafta-1) x 7 gün formülü ile hesaplanır.'
    }
    return render(request, 'yonetim/aktiviteler/aktivite_duzenle.html', context)

@login_required
@yetkili_required
def yonetim_aktivite_sil(request, aktivite_id):
    """Yönetim paneli - aktivite silme"""
    from .models import HaftalikAktivite
    
    aktivite = get_object_or_404(HaftalikAktivite, id=aktivite_id)
        
    context = {
        'aktivite': aktivite,
        'aktif_menu': 'aktiviteler',
    }
    
    if request.method == 'POST':
        # Aktiviteyi sil (soft delete)
        aktivite.silindi = True
        aktivite.silinme_tarihi = timezone.now()
        aktivite.save()
        
        messages.success(request, f'"{aktivite.baslik}" aktivitesi başarıyla silindi.')
        return redirect('yonetim_aktivite_listesi')
    
    return render(request, 'yonetim/aktiviteler/aktivite_sil.html', context)

@login_required
@yetkili_required
def yonetim_aktivite_oge_ekle(request, aktivite_id):
    """Yönetim paneli - aktiviteye öğe ekleme"""
    from .models import HaftalikAktivite, AktiviteOgesi
    import json
    
    aktivite = get_object_or_404(HaftalikAktivite, id=aktivite_id)
    
    if request.method == 'POST':
        # AJAX isteği mi kontrol et
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            # JSON formatında veri geldi mi kontrol et
            if is_ajax and request.headers.get('Content-Type') == 'application/json':
                # JSON verilerini parse et
                data = json.loads(request.body)
                tip = data.get('tip')
                baslik = data.get('baslik')
                aciklama = data.get('aciklama', '')
                zorunlu = data.get('zorunlu', False)
                aktif = data.get('aktif', True)
                satir_sayisi = data.get('satir_sayisi', 0)
                sutun_sayisi = data.get('sutun_sayisi', 0)
                sutun_basliklar = data.get('sutun_basliklar', [])
                satir_basliklar = data.get('satir_basliklar', [])
            else:
                # Form verilerini al
                tip = request.POST.get('tip')
                baslik = request.POST.get('baslik')
                aciklama = request.POST.get('aciklama', '')
                zorunlu = 'zorunlu' in request.POST
                aktif = 'aktif' in request.POST
                satir_sayisi = int(request.POST.get('satir_sayisi', 3))
                sutun_sayisi = int(request.POST.get('sutun_sayisi', 3))
                sutun_basliklar = request.POST.get('sutun_basliklar', '').split(',')
                sutun_basliklar = [baslik.strip() for baslik in sutun_basliklar if baslik.strip()]
                
                # Satır başlıklarını al
                satir_basliklar = request.POST.get('satir_basliklar', '').split(',')
                satir_basliklar = [baslik.strip() for baslik in satir_basliklar if baslik.strip()]
            
            # Öğenin sıra numarasını belirle
            son_sira = aktivite.ogeler.filter(silindi=False).aggregate(models.Max('sira'))['sira__max'] or 0
            yeni_sira = son_sira + 1
            
            # Tablo tipi için JSON yapısını hazırla
            icerik_json = None
            if tip == 'tablo':
                # JSON isteklerinde zaten liste olarak geliyor olabilir, kontrolü yap
                if isinstance(sutun_basliklar, str):
                    sutun_basliklar = sutun_basliklar.split(',')
                    sutun_basliklar = [baslik.strip() for baslik in sutun_basliklar if baslik.strip()]
                
                # Satır başlıklarını al (AJAX istek için if-else kullanılacak)
                if is_ajax and request.headers.get('Content-Type') == 'application/json':
                    # Veri zaten JSON'dan alındı, hazır liste olabilir
                    if isinstance(satir_basliklar, str):
                        satir_basliklar = satir_basliklar.split(',')
                        satir_basliklar = [baslik.strip() for baslik in satir_basliklar if baslik.strip()]
                else:
                    # Form verisi 
                    satir_basliklar = request.POST.get('satir_basliklar', '').split(',')
                    satir_basliklar = [baslik.strip() for baslik in satir_basliklar if baslik.strip()]
                
                if not sutun_basliklar or len(sutun_basliklar) < sutun_sayisi:
                    sutun_basliklar = [f"Sütun {i+1}" for i in range(sutun_sayisi)]
                
                # Satır başlıklarını kontrol et
                if not satir_basliklar or len(satir_basliklar) < satir_sayisi:
                    satir_basliklar = [f"Satır {i+1}" for i in range(satir_sayisi)]
                
                yeni_icerik = {
                    'satir_sayisi': satir_sayisi,
                    'sutun_sayisi': sutun_sayisi,
                    'sutun_basliklar': sutun_basliklar[:sutun_sayisi],
                    'satir_basliklar': satir_basliklar[:satir_sayisi],
                    'tablo_veri': {}
                }
                
                for i in range(satir_sayisi):
                    for j in range(sutun_sayisi):
                        hucre_key = f"satir{i+1}_sutun{j+1}"
                        yeni_icerik['tablo_veri'][hucre_key] = ""
                
                icerik_json = json.dumps(yeni_icerik)
            
            # Öğeyi oluştur
            yeni_oge = AktiviteOgesi.objects.create(
                aktivite=aktivite,
                tip=tip,
                sira=yeni_sira,
                baslik=baslik,
                aciklama=aciklama,
                zorunlu=zorunlu,
                aktif=aktif,
                icerik_json=icerik_json
            )
            
            if is_ajax:
                # AJAX isteği için JSON yanıtı döndür
                return JsonResponse({
                    'success': True, 
                    'message': 'Öğe başarıyla eklendi.',
                    'oge_id': yeni_oge.id,
                    'oge_tip': yeni_oge.tip,
                    'oge_baslik': yeni_oge.baslik
                })
            else:
                messages.success(request, 'Öğe başarıyla eklendi.')
            
        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'Öğe eklenirken hata oluştu: {str(e)}'
                })
            else:
                messages.error(request, f'Öğe eklenirken hata oluştu: {str(e)}')
        
        if not is_ajax:
            return redirect('yonetim_aktivite_duzenle', aktivite_id=aktivite.id)
    
    # GET isteği için form sayfasını göster
    context = {
        'aktivite': aktivite,
        'oge_tipleri': AktiviteOgesi.OGE_TIPLERI,
        'aktif_menu': 'aktiviteler',
    }
    
    return render(request, 'yonetim/aktiviteler/aktivite_oge_ekle.html', context)

@login_required
@yetkili_required
@csrf_exempt
def aktivite_oge_sirala(request, aktivite_id):
    """AJAX - Aktivite öğelerini yeniden sıralama"""
    from .models import HaftalikAktivite, AktiviteOgesi
    import json
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Geçersiz istek metodu.'})
    
    aktivite = get_object_or_404(HaftalikAktivite, id=aktivite_id)
    
    try:
        # POST verilerinden yeni sıralamayı al
        data = json.loads(request.body)
        oge_siralamasi = data.get('oge_siralamasi', [])
        
        # Her öğe için yeni sıra numarasını güncelle
        for sira, oge_id in enumerate(oge_siralamasi):
            AktiviteOgesi.objects.filter(id=oge_id, aktivite=aktivite).update(sira=sira)
        
        return JsonResponse({
            'success': True, 
            'message': 'Öğeler başarıyla yeniden sıralandı.'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Öğeler sıralanırken hata oluştu: {str(e)}'
        })

@login_required
@yetkili_required
def yonetim_aktivite_oge_duzenle(request, oge_id):
    """Aktivite öğesi düzenleme"""
    try:
        oge = AktiviteOgesi.objects.get(id=oge_id)
        aktivite = oge.aktivite
    except AktiviteOgesi.DoesNotExist:
        messages.error(request, 'Düzenlenecek öğe bulunamadı!')
        return redirect('yonetim_aktivite_listesi')
    
    # POST isteği kontrolü
    if request.method == 'POST' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
        baslik = request.POST.get('baslik')
        aciklama = request.POST.get('aciklama', '')
        zorunlu = 'zorunlu' in request.POST
        aktif = 'aktif' in request.POST
        
        # Tablo tipi için özel alanlar
        if oge.tip == 'tablo':
            import json
            # Tablo boyutları
            satir_sayisi = int(request.POST.get('satir_sayisi', 3))
            sutun_sayisi = int(request.POST.get('sutun_sayisi', 3))
            
            # Başlıklar için JSON alanları
            try:
                # JSON verilerini parse et ve boş değerleri filtrele
                sutun_basliklar_json = request.POST.get('sutun_basliklar_json', '[]')
                satir_basliklar_json = request.POST.get('satir_basliklar_json', '[]')
                
                print("Alınan JSON verisi:", sutun_basliklar_json, satir_basliklar_json)
                
                sutun_basliklar = json.loads(sutun_basliklar_json)
                satir_basliklar = json.loads(satir_basliklar_json)
                
                # Dizi uzunluklarını boyutlara göre ayarla
                while len(sutun_basliklar) < sutun_sayisi:
                    sutun_basliklar.append(f"Sütun {len(sutun_basliklar)+1}")
                    
                while len(satir_basliklar) < satir_sayisi:
                    satir_basliklar.append(f"Satır {len(satir_basliklar)+1}")
                
                # İçerik JSON'ı oluştur
                icerik_json = json.dumps({
                    'satir_sayisi': satir_sayisi,
                    'sutun_sayisi': sutun_sayisi, 
                    'sutun_basliklar': sutun_basliklar[:sutun_sayisi],
                    'satir_basliklar': satir_basliklar[:satir_sayisi]
                })
                
            except Exception as e:
                print("Tablo JSON hatası:", e)
                # Varsayılan değerlerle devam et
                icerik_json = json.dumps({
                    'satir_sayisi': satir_sayisi,
                    'sutun_sayisi': sutun_sayisi,
                    'sutun_basliklar': [f"Sütun {i+1}" for i in range(sutun_sayisi)],
                    'satir_basliklar': [f"Satır {i+1}" for i in range(satir_sayisi)]
                })
                
            # Öğeyi güncelle
            oge.baslik = baslik
            oge.aciklama = aciklama
            oge.zorunlu = zorunlu
            oge.aktif = aktif
            oge.icerik_json = icerik_json
            oge.save()
        else:
            # Tablo olmayan tipler için normal güncelleme
            oge.baslik = baslik
            oge.aciklama = aciklama
            oge.zorunlu = zorunlu
            oge.aktif = aktif
            oge.save()
        
        # AJAX yanıtı
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Öğe başarıyla güncellendi'
            })
        
        # Normal form yanıtı
        messages.success(request, 'Öğe başarıyla güncellendi')
        return redirect('yonetim_aktivite_duzenle', aktivite_id=aktivite.id)
    
    # GET isteği için form görünümü (bu kısım kullanılmıyor, AJAX işlemi yapılıyor)
    context = {
        'oge': oge,
        'aktivite': aktivite
    }
    
    return render(request, 'yonetim/aktiviteler/aktivite_oge_duzenle.html', context)

@login_required
@yetkili_required
def yonetim_aktivite_oge_sil(request, oge_id):
    """Yönetim paneli - aktivite öğesi silme"""
    from .models import AktiviteOgesi
    
    oge = get_object_or_404(AktiviteOgesi, id=oge_id)
    aktivite = oge.aktivite
    
    # AJAX isteği mi kontrol et
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if request.method == 'POST':
        try:
            # Öğeyi soft-delete yap
            oge.silindi = True
            oge.save()
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'Öğe başarıyla silindi.'
                })
            else:
                messages.success(request, 'Öğe başarıyla silindi.')
                return redirect('yonetim_aktivite_duzenle', aktivite_id=aktivite.id)
        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False, 
                    'message': f'Öğe silinirken bir hata oluştu: {str(e)}'
                })
            else:
                messages.error(request, f'Öğe silinirken bir hata oluştu: {str(e)}')
                return redirect('yonetim_aktivite_duzenle', aktivite_id=aktivite.id)
    
    # GET isteği için onay sayfası göster
    context = {
        'oge': oge,
        'aktivite': aktivite,
        'aktif_menu': 'aktiviteler',
    }
    
    return render(request, 'yonetim/aktiviteler/aktivite_oge_sil.html', context)

@login_required
@yetkili_required
def yonetim_aktivite_yanitlar(request, aktivite_id):
    """Yönetim paneli - aktivite yanıtlarını listele"""
    from .models import HaftalikAktivite, KullaniciAktiviteYaniti
    
    aktivite = get_object_or_404(HaftalikAktivite, id=aktivite_id)
    
    # Kullanıcıların yanıtlarını getir
    yanitlar = KullaniciAktiviteYaniti.objects.filter(aktivite=aktivite).order_by('-guncelleme_tarihi')
    
    context = {
        'aktivite': aktivite,
        'yanitlar': yanitlar,
        'aktif_menu': 'aktiviteler',
    }
    
    return render(request, 'yonetim/aktiviteler/aktivite_yanitlar.html', context)

@login_required
@yetkili_required
def yonetim_aktivite_yanit_detay(request, yanit_id):
    """Yönetim paneli - aktivite yanıt detayı"""
    from .models import KullaniciAktiviteYaniti
    
    yanit = get_object_or_404(KullaniciAktiviteYaniti, id=yanit_id)
    aktivite = yanit.aktivite
    
    # Aktivitenin öğelerini getir
    ogeler = aktivite.ogeleri_getir()
    
    context = {
        'yanit': yanit,
        'aktivite': aktivite,
        'ogeler': ogeler,
        'aktif_menu': 'aktiviteler',
    }
    
    return render(request, 'yonetim/aktiviteler/aktivite_yanit_detay.html', context)

@login_required
@yetkili_required
def yonetim_aktivite_tumunu_temizle(request, aktivite_id):
    """Yönetim paneli - aktivitedeki tüm öğeleri temizle"""
    from .models import HaftalikAktivite, AktiviteOgesi
    
    aktivite = get_object_or_404(HaftalikAktivite, id=aktivite_id)
    
    # AJAX isteği mi kontrol et
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if request.method == 'POST':
        try:
            # Aktivitenin tüm öğelerini silindi olarak işaretle
            AktiviteOgesi.objects.filter(aktivite=aktivite).update(silindi=True)
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'Tüm aktivite öğeleri başarıyla silindi.'
                })
            else:
                messages.success(request, "Tüm aktivite öğeleri başarıyla silindi.")
                return redirect('yonetim_aktivite_duzenle', aktivite_id=aktivite.id)
        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'Öğeler temizlenirken bir hata oluştu: {str(e)}'
                })
            else:
                messages.error(request, f'Öğeler temizlenirken bir hata oluştu: {str(e)}')
                return redirect('yonetim_aktivite_duzenle', aktivite_id=aktivite.id)
    
    # GET isteği için onay sayfası göster
    context = {
        'aktivite': aktivite,
        'aktif_menu': 'aktiviteler',
    }
    
    return render(request, 'yonetim/aktiviteler/aktivite_tumunu_temizle.html', context)

# Metinsel sorular için view fonksiyonları
@login_required
@staff_member_required
def metinsel_sorular(request):
    """
    Metinsel soruları listeleyen view fonksiyonu
    """
    # Arama parametresini alma
    search_query = request.GET.get('q', '')
    
    # Baz filtreleme kriteri
    filter_criteria = {'soru__soru_tipi': 'metin', 'degerlendirildi': False}
    
    # Arama sorgusu varsa filtreleme kriterlerine ekle
    if search_query:
        from django.db.models import Q
        degerlendirilmeyen_sorular = KullaniciCevap.objects.filter(
            Q(soru__soru_tipi='metin'),
            Q(degerlendirildi=False),
            Q(kullanici__username__icontains=search_query) | 
            Q(kullanici__first_name__icontains=search_query) | 
            Q(kullanici__last_name__icontains=search_query) | 
            Q(soru__soru_metni__icontains=search_query) | 
            Q(secilen_secenek__secenek_metni__icontains=search_query)
        ).select_related('kullanici', 'soru', 'secilen_secenek')
    else:
        # Değerlendirilmemiş soruları al
        degerlendirilmeyen_sorular = KullaniciCevap.objects.filter(
            **filter_criteria
        ).select_related('kullanici', 'soru', 'secilen_secenek')
    
    # Sayfalama işlemi
    from django.core.paginator import Paginator
    paginator = Paginator(degerlendirilmeyen_sorular, 10)  # Her sayfada 10 soru
    page_number = request.GET.get('page', 1)
    degerlendirilmeyen_sorular_page = paginator.get_page(page_number)
    
    # Değerlendirilmiş soruları al
    degerlendirilmis_sorular = KullaniciCevap.objects.filter(
        soru__soru_tipi='metin',
        degerlendirildi=True
    ).select_related('kullanici', 'soru', 'secilen_secenek', 'degerlendiren').order_by('-degerlendirme_tarihi')[:20]
    
    context = {
        'degerlendirilmeyen_metinsel_sorular': degerlendirilmeyen_sorular_page,
        'degerlendirilmis_metinsel_sorular': degerlendirilmis_sorular,
        'page_title': 'Metinsel Sorular',
        'search_query': search_query,
    }
    
    return render(request, 'yonetim/metinsel_sorular.html', context)

@login_required
@staff_member_required
def metinsel_soru_degerlendir(request, soru_id):
    """
    Metinsel soruyu değerlendiren view fonksiyonu
    """
    # Kullanıcı cevabını id'ye göre getir
    kullanici_cevap = get_object_or_404(KullaniciCevap, id=soru_id, soru__soru_tipi='metin')
    
    if request.method == 'POST':
        # Değerlendirme işlemi
        degerlendirme = request.POST.get('degerlendirme', None)
        
        if degerlendirme == 'dogru' or degerlendirme == 'yanlis':
            dogru_mu = (degerlendirme == 'dogru')
            
            # Cevabı değerlendir
            kullanici_cevap.dogru_mu = dogru_mu
            kullanici_cevap.degerlendirildi = True
            kullanici_cevap.degerlendirme_tarihi = timezone.now()
            kullanici_cevap.degerlendiren = request.user
            kullanici_cevap.save()
            
            # Kullanıcıya mesaj gönder
            if dogru_mu:
                mesaj_icerik = f"'{kullanici_cevap.soru.soru_metni}' sorusuna verdiğiniz '{kullanici_cevap.secilen_secenek.secenek_metni}' cevabınız değerlendirildi. Cevabınız doğru kabul edilmiştir."
            else:
                mesaj_icerik = f"'{kullanici_cevap.soru.soru_metni}' sorusuna verdiğiniz '{kullanici_cevap.secilen_secenek.secenek_metni}' cevabınız değerlendirildi. Daha fazla çalışmanız önerilir."
            
            Mesaj.objects.create(
                gonderen=request.user,
                alici=kullanici_cevap.kullanici,
                konu=f"Cevabınız Değerlendirildi: {kullanici_cevap.soru.video.baslik}",
                icerik=mesaj_icerik
            )
            
            messages.success(request, "Cevap başarıyla değerlendirildi ve kullanıcıya bildirim gönderildi.")
            return redirect('metinsel_sorular')
        else:
            messages.error(request, "Geçersiz değerlendirme seçeneği! Lütfen doğru ya da yanlış olarak değerlendirin.")
    
    context = {
        'kullanici_cevap': kullanici_cevap,
        'page_title': 'Metinsel Soru Değerlendirme',
    }
    
    return render(request, 'yonetim/metinsel_soru_degerlendir.html', context)

@login_required
@staff_member_required
def tum_kategorileri_sirala(request):
    """
    Tüm kategorileri sıralamak için admin işlevi
    """
    if request.method == 'POST':
        kategoriler = request.POST.getlist('selected_categories')
        if not kategoriler:
            messages.warning(request, "Kategori seçilmedi!")
            return redirect('yonetim_paneli')
        
        # Kategorileri sırala
        for index, kategori_id in enumerate(kategoriler):
            try:
                kategori = Kategori.objects.get(id=kategori_id)
                kategori.sira = index + 1
                kategori.save()
            except Kategori.DoesNotExist:
                continue
        
        messages.success(request, f"{len(kategoriler)} kategori başarıyla sıralandı.")
        return redirect('yonetim_paneli')
    else:
        return redirect('yonetim_paneli')

@login_required
@staff_member_required
def kategoriler_toplu_sil(request):
    """
    Seçili kategorileri toplu olarak silen admin işlevi
    """
    if request.method == 'POST':
        # Gönderilen kategori ID'lerini al
        secili_kategoriler = request.POST.getlist('seciliKategoriler') or request.POST.get('ids', '').split(',')
        
        if not secili_kategoriler:
            messages.warning(request, "Silmek için kategori seçilmedi!")
            return redirect('yonetim_paneli')
        
        silinen_kategori_sayisi = 0
        # Seçili kategorileri yumuşak sil
        for kategori_id in secili_kategoriler:
            try:
                kategori = Kategori.objects.get(id=kategori_id)
                kategori.silindi = True
                kategori.silinme_tarihi = timezone.now()
                kategori.save()
                silinen_kategori_sayisi += 1
            except Kategori.DoesNotExist:
                continue
        
        messages.success(request, f"{silinen_kategori_sayisi} kategori başarıyla silindi.")
        return redirect('yonetim_paneli')
    else:
        return redirect('yonetim_paneli')

@login_required
@staff_member_required
def egitmen_ekle(request):
    """
    Yeni bir eğitmen eklemek için admin view'i
    """
    if request.method == 'POST':
        ad_soyad = request.POST.get('ad_soyad', '').strip()
        unvan = request.POST.get('unvan', '').strip()
        email = request.POST.get('email', '').strip() or None
        ozgecmis = request.POST.get('ozgecmis', '').strip() or None
        aktif = request.POST.get('aktif') == 'on'
        profil_resmi = request.FILES.get('profil_resmi')
        
        # Boş alan kontrolü
        if not ad_soyad:
            messages.error(request, 'Ad soyad alanı boş bırakılamaz.')
            return render(request, 'yonetim/egitmen_ekle.html')
            
        try:
            # Eğitmeni oluştur
            egitmen = Egitmen.objects.create(
                ad_soyad=ad_soyad,
                unvan=unvan,
                email=email,
                ozgecmis=ozgecmis,
                aktif=aktif,
                profil_resmi=profil_resmi
            )
            
            messages.success(request, f'"{egitmen.unvan} {egitmen.ad_soyad}" eğitmeni başarıyla oluşturuldu.')
            return redirect('yonetim_paneli')
            
        except Exception as e:
            messages.error(request, f'Eğitmen oluşturulurken bir hata oluştu: {str(e)}')
    
    return render(request, 'yonetim/egitmen_ekle.html')

@login_required
@staff_member_required
def moduller_toplu_sil(request):
    """
    Seçili modülleri toplu olarak silen admin işlevi
    """
    if request.method == 'POST':
        # Gönderilen modül ID'lerini al
        secili_moduller = request.POST.getlist('seciliModuller') or request.POST.get('ids', '').split(',')
        
        if not secili_moduller:
            messages.warning(request, "Silmek için modül seçilmedi!")
            return redirect('yonetim_paneli')
        
        silinen_modul_sayisi = 0
        # Seçili modülleri yumuşak sil
        for modul_id in secili_moduller:
            try:
                modul = Modul.objects.get(id=modul_id)
                modul.silindi = True
                modul.silinme_tarihi = timezone.now()
                modul.save()
                silinen_modul_sayisi += 1
            except Modul.DoesNotExist:
                continue
        
        messages.success(request, f"{silinen_modul_sayisi} modül başarıyla silindi.")
        return redirect('yonetim_paneli')
    else:
        return redirect('yonetim_paneli')

@login_required
@staff_member_required
def egitmenler_toplu_sil(request):
    """
    Seçili eğitmenleri toplu olarak silen admin işlevi
    """
    if request.method == 'POST':
        # Gönderilen eğitmen ID'lerini al
        secili_egitmenler = request.POST.getlist('seciliEgitmenler') or request.POST.get('ids', '').split(',')
        
        if not secili_egitmenler:
            messages.warning(request, "Silmek için eğitmen seçilmedi!")
            return redirect('yonetim_paneli')
        
        silinen_egitmen_sayisi = 0
        # Seçili eğitmenleri yumuşak sil
        for egitmen_id in secili_egitmenler:
            try:
                egitmen = Egitmen.objects.get(id=egitmen_id)
                egitmen.silindi = True
                egitmen.silinme_tarihi = timezone.now()
                egitmen.save()
                silinen_egitmen_sayisi += 1
            except Egitmen.DoesNotExist:
                continue
        
        messages.success(request, f"{silinen_egitmen_sayisi} eğitmen başarıyla silindi.")
        return redirect('yonetim_paneli')
    else:
        return redirect('yonetim_paneli')

@login_required
@yetkili_required
def videolar_toplu_sil(request):
    """Seçilen videoları toplu olarak silme işlemi"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'Bu işlemi yapmaya yetkiniz bulunmamaktadır.')
        return redirect('yonetim_paneli')
    
    if request.method == 'POST':
        secilen_videolar = request.POST.getlist('seciliVideolar')
        silinen_adet = 0
        
        if secilen_videolar:
            for video_id in secilen_videolar:
                try:
                    video = Video.objects.get(id=video_id)
                    modul = video.modul  # Modül referansını sakla
                    
                    # Soft delete işlemi yap
                    video.silindi = True
                    video.silinme_tarihi = timezone.now()
                    video.save()
                    
                    # Modül bilgilerini güncelle
                    modul.guncelle_video_bilgileri()
                    # Kullanıcı ilerlemelerini güncelle
                    modul.guncelle_kullanici_ilerlemeleri()
                    
                    silinen_adet += 1
                except Video.DoesNotExist:
                    continue
                except Exception as e:
                    messages.error(request, f'Video silme işlemi sırasında bir hata oluştu: {str(e)}')
            
            if silinen_adet > 0:
                messages.success(request, f'Toplam {silinen_adet} video başarıyla silindi.')
            else:
                messages.warning(request, 'Hiçbir video silinemedi.')
        else:
            messages.warning(request, 'Silinecek video seçilmedi.')
    
    # Yönetim paneline yönlendir
    return redirect('yonetim_paneli')

@login_required
def mesaj_sil(request, mesaj_id):
    """Tek bir mesajı siler"""
    # Mesajı al (kullanıcının erişebileceği mesajlardan)
    mesaj = get_object_or_404(
        Mesaj.objects.filter(
            Q(alici=request.user) | Q(gonderen=request.user),
            id=mesaj_id
        )
    )
    
    # Mesajı sil
    mesaj.delete()
    
    messages.success(request, 'Mesaj başarıyla silindi.')
    return redirect('mesajlar')

@login_required
@yetkili_required
def yonetim_aktivite_oge_detay(request, oge_id):
    """AJAX ile aktivite öğesi detaylarını döndür"""
    try:
        oge = AktiviteOgesi.objects.get(id=oge_id)
        
        # Tablo için özel alanlar
        sutun_basliklar = []
        satir_basliklar = []
        satir_sayisi = 0
        sutun_sayisi = 0
        
        if oge.tip == 'tablo' and oge.icerik_json:
            try:
                import json
                icerik = json.loads(oge.icerik_json)
                satir_sayisi = icerik.get('satir_sayisi', 0)
                sutun_sayisi = icerik.get('sutun_sayisi', 0)
                sutun_basliklar = icerik.get('sutun_basliklar', [])
                satir_basliklar = icerik.get('satir_basliklar', [])
            except:
                pass
        
        # Öğe verisini hazırla
        oge_data = {
            'id': oge.id,
            'tip': oge.tip,
            'baslik': oge.baslik,
            'aciklama': oge.aciklama,
            'zorunlu': oge.zorunlu,
            'aktif': oge.aktif,
            'sira': oge.sira,
            'satir_sayisi': satir_sayisi,
            'sutun_sayisi': sutun_sayisi,
            'sutun_basliklar': sutun_basliklar,
            'satir_basliklar': satir_basliklar
        }
        
        return JsonResponse({
            'success': True,
            'oge': oge_data
        })
    except AktiviteOgesi.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Öğe bulunamadı'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@login_required
@yetkili_required
def yonetim_aktivite_oge_sil(request, oge_id):
    # ... existing code ...
    try:
        oge = AktiviteOgesi.objects.get(id=oge_id)
        aktivite = oge.aktivite
        oge.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Öğe başarıyla silindi'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


def lock_system(request, kullanici_id):
    kullanici = get_object_or_404(User, id=kullanici_id)
    if LockSystem.objects.all().first():
        lock_system = LockSystem.objects.all().first()
        lock_system.users.add(kullanici)
        lock_system.save()
    else:
        lock_system = LockSystem.objects.create()
        lock_system.users.add(kullanici)
        lock_system.save()

    messages.success(request, f'{kullanici.username} kullanıcısının kilitleri başarıyla kaldırıldı.')

    # Query string'den next_url'i al
    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    else:
        return redirect('yonetim_paneli')
