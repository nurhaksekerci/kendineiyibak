from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponseForbidden
from django.utils.text import slugify
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
from functools import wraps
from webui.views import custom_login_required

from .models import ForumKategori, ForumKonu, ForumYorum, ForumBegeni, ForumGoruntulenme

# Yetkili kontrolü için decorator
def yetkili_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "Bu sayfaya erişim yetkiniz bulunmamaktadır.")
            return redirect('forum:forum_main')
        return view_func(request, *args, **kwargs)
    return wrapper

# Create your views here.

@custom_login_required
def forum_main(request):
    """
    Ana forum sayfasını görüntüler.
    Arama yapıldığında arama sonuçlarını gösterir.
    """
    # Arama parametresini al
    q = request.GET.get('q', '')
    
    if q:
        # Arama sonuçlarını getir
        arama_konular = ForumKonu.objects.filter(
            Q(baslik__icontains=q) | Q(icerik__icontains=q),
            aktif=True
        )
        
        # Staff olmayan kullanıcılar için onaylanmış konuları filtrele
        if not request.user.is_staff:
            arama_konular = arama_konular.filter(onay_durumu='onaylanmis')
        else:
            # Staff kullanıcılar için de reddedilen konuları gizle
            arama_konular = arama_konular.exclude(onay_durumu='reddedilmis')
        
        # Sonuçları sınırla (limit'i en son uygula)
        arama_konular_limited = arama_konular[:20]  # İlk 20 konu
        
        # Kategorilerde de arama yap
        arama_kategoriler = ForumKategori.objects.filter(
            Q(baslik__icontains=q) | Q(aciklama__icontains=q),
            aktif=True
        )
        
        # Sonuçları sınırla
        arama_kategoriler_limited = arama_kategoriler[:10]  # İlk 10 kategori
        
        toplam_sonuc = arama_konular.count() + arama_kategoriler.count()
        
        context = {
            'q': q,
            'arama_konular': arama_konular_limited,
            'arama_kategoriler': arama_kategoriler_limited,
            'toplam_sonuc': toplam_sonuc,
        }
        
        # Staff kullanıcıları için bekleyen konu sayısını ekle
        if request.user.is_authenticated and request.user.is_staff:
            context['bekleyen_konu_sayisi'] = ForumKonu.objects.filter(onay_durumu='beklemede', aktif=True).count()
    else:
        # Normal forum içeriğini getir
        tum_kategoriler = ForumKategori.objects.filter(aktif=True, ust_kategori=None)
        
        # Kategori sayfalaması için
        paginator = Paginator(tum_kategoriler, 5)  # Sayfa başına 5 kategori
        sayfa = request.GET.get('sayfa', 1)
        
        try:
            kategoriler = paginator.page(sayfa)
        except PageNotAnInteger:
            kategoriler = paginator.page(1)
        except EmptyPage:
            kategoriler = paginator.page(paginator.num_pages)
        
        # Tüm filtreleri önce uygula, sonra dilimleme yap
        son_konular_query = ForumKonu.objects.filter(aktif=True)
        if not request.user.is_staff:
            son_konular_query = son_konular_query.filter(onay_durumu='onaylanmis')
        else:
            # Staff kullanıcılar için de reddedilen konuları gizle
            son_konular_query = son_konular_query.exclude(onay_durumu='reddedilmis')
        son_konular = son_konular_query.order_by('-olusturma_tarihi')[:5]
        
        # Popüler konuları getir - önce tüm filtreleri uygula
        populer_konular_query = ForumKonu.objects.filter(aktif=True)
        if not request.user.is_staff:
            populer_konular_query = populer_konular_query.filter(onay_durumu='onaylanmis')
        else:
            # Staff kullanıcılar için de reddedilen konuları gizle
            populer_konular_query = populer_konular_query.exclude(onay_durumu='reddedilmis')
        populer_konular = populer_konular_query.order_by('-goruntulenme')[:5]
        
        # Kullanıcının konularını getir (giriş yapmış kullanıcılar için)
        kullanici_konulari = None
        if request.user.is_authenticated:
            kullanici_konulari_query = ForumKonu.objects.filter(yazar=request.user, aktif=True)
            if not request.user.is_staff:
                # Sadece onaylanmış konuları göster, beklemede olanları gösterme
                kullanici_konulari_query = kullanici_konulari_query.filter(onay_durumu='onaylanmis')
            # Ana sayfada sadece son 4 konuyu göster (kullanici_konular sayfasında tümü gösterilecek)
            kullanici_konulari = kullanici_konulari_query.order_by('-olusturma_tarihi')[:4]
        
        istatistikler = {
            'toplam_konu': ForumKonu.aktif_konu_sayisi(),
            'toplam_yorum': ForumYorum.objects.filter(aktif=True, konu__onay_durumu='onaylanmis').count(),
            'toplam_uye': User.objects.filter(is_active=True).count(),
            'bugun_konu': ForumKonu.bugun_acilan_konu_sayisi(),
            'bugun_yorum': ForumYorum.objects.filter(
                olusturma_tarihi__date=timezone.now().date(), 
                aktif=True,
                konu__onay_durumu='onaylanmis'
            ).count(),
        }
        
        context = {
            'kategoriler': kategoriler,
            'toplam_kategori_sayisi': tum_kategoriler.count(),
            'son_konular': son_konular,
            'populer_konular': populer_konular,
            'kullanici_konulari': kullanici_konulari,
            'istatistikler': istatistikler,
        }
        
        # Staff kullanıcıları için bekleyen konu sayısını ekle
        if request.user.is_authenticated and request.user.is_staff:
            context['bekleyen_konu_sayisi'] = ForumKonu.objects.filter(onay_durumu='beklemede', aktif=True).count()
    
    return render(request, 'forum/forum.html', context)


@custom_login_required
def kategori_detay(request, kategori_slug):
    """
    Kategori detay sayfasını görüntüler.
    """
    kategori = get_object_or_404(ForumKategori, slug=kategori_slug, aktif=True)
    
    # Alt kategorileri al
    alt_kategoriler = ForumKategori.objects.filter(ust_kategori=kategori, aktif=True)
    
    # Konuları al
    konular = ForumKonu.objects.filter(kategori=kategori, aktif=True)
    
    # Staff olmayan kullanıcılar için onaylanmış konuları filtrele
    if not request.user.is_staff:
        konular = konular.filter(onay_durumu='onaylanmis')
    else:
        # Staff kullanıcılar için de reddedilen konuları gizle
        konular = konular.exclude(onay_durumu='reddedilmis')
    
    # Sıralama parametresi
    siralama = request.GET.get('sirala', '-olusturma_tarihi')
    konular = konular.order_by(siralama)
    
    # Sayfalama
    paginator = Paginator(konular, 5)  # Sayfa başına 5 konu
    sayfa = request.GET.get('sayfa', 1)
    
    try:
        konular_sayfa = paginator.page(sayfa)
    except PageNotAnInteger:
        konular_sayfa = paginator.page(1)
    except EmptyPage:
        konular_sayfa = paginator.page(paginator.num_pages)
    
    context = {
        'kategori': kategori,
        'alt_kategoriler': alt_kategoriler,
        'konular': konular_sayfa,
        'siralama': siralama,
    }
    
    return render(request, 'forum/kategori_detay.html', context)


@custom_login_required
def konu_detay(request, kategori_slug, konu_slug):
    """
    Konu detay sayfasını görüntüler.
    """
    kategori = get_object_or_404(ForumKategori, slug=kategori_slug, aktif=True)
    
    # Staff olmayan kullanıcılar sadece onaylanmış konuları görebilir
    # Staff kullanıcılar ise onaylanmış ve bekleyen konuları görebilir (reddedilenler hariç)
    if request.user.is_staff:
        konu = get_object_or_404(
            ForumKonu, 
            slug=konu_slug, 
            kategori=kategori, 
            aktif=True
        )
        # Reddedilen konuları yöneticilere de gösterme
        if konu.onay_durumu == 'reddedilmis':
            messages.error(request, "Bu konu reddedilmiş, görüntülenemez.")
            return redirect('forum:kategori_detay', kategori_slug=kategori.slug)
    else:
        konu = get_object_or_404(
            ForumKonu, 
            slug=konu_slug, 
            kategori=kategori, 
            aktif=True, 
            onay_durumu='onaylanmis'
        )
    
    # Kullanıcı giriş yapmışsa görüntülenme sayısını artır
    if request.user.is_authenticated:
        # Kullanıcı daha önce bu konuyu görüntülememiş mi kontrol et
        goruntulenme, created = ForumGoruntulenme.objects.get_or_create(
            konu=konu,
            kullanici=request.user
        )
        
        # Eğer yeni bir görüntülenme kaydı oluşturulduysa sayacı artır
        if created:
            konu.goruntulenme_artir()
    else:
        # Giriş yapmamış kullanıcılar için her zaman artır
        # (Bu kısım tercihe bağlı, session ile de takip edilebilir)
        konu.goruntulenme_artir()
    
    # Yorumları al
    yorumlar = ForumYorum.objects.filter(konu=konu, ust_yorum=None, aktif=True)
    
    # Kullanıcının beğenilerini al
    kullanici_begenileri = {}
    if request.user.is_authenticated:
        # Konuya ait beğeni
        konu_begeni = ForumBegeni.objects.filter(
            konu=konu,
            kullanici=request.user
        ).first()
        
        if konu_begeni:
            kullanici_begenileri['konu'] = konu_begeni.tur
        
        # Yorumlara ait beğeniler
        yorum_begenileri = ForumBegeni.objects.filter(
            yorum__konu=konu,
            kullanici=request.user
        )
        
        for begeni in yorum_begenileri:
            kullanici_begenileri[f'yorum_{begeni.yorum.id}'] = begeni.tur
    
    # Yorum formunu işle
    if request.method == 'POST' and request.user.is_authenticated:
        yorum_icerik = request.POST.get('yorum_icerik')
        ust_yorum_id = request.POST.get('ust_yorum_id')
        
        if yorum_icerik:
            if ust_yorum_id:
                ust_yorum = get_object_or_404(ForumYorum, id=ust_yorum_id, konu=konu)
                yeni_yorum = ForumYorum.objects.create(
                    konu=konu,
                    yazar=request.user,
                    icerik=yorum_icerik,
                    ust_yorum=ust_yorum
                )
            else:
                yeni_yorum = ForumYorum.objects.create(
                    konu=konu,
                    yazar=request.user,
                    icerik=yorum_icerik
                )
            
            messages.success(request, 'Yorumunuz başarıyla eklendi.')
            return redirect('forum:konu_detay', kategori_slug=kategori_slug, konu_slug=konu_slug)
    
    context = {
        'kategori': kategori,
        'konu': konu,
        'yorumlar': yorumlar,
        'kullanici_begenileri': kullanici_begenileri,
    }
    
    return render(request, 'forum/konu_detay.html', context)


@login_required
def yeni_konu(request, kategori_slug=None):
    """
    Yeni konu ekleme sayfasını görüntüler ve yeni konu ekler.
    """
    # Kategori parametresi varsa al, yoksa ilk varsayılanı kullan
    if kategori_slug:
        kategori = get_object_or_404(ForumKategori, slug=kategori_slug, aktif=True)
    else:
        kategori = None
    
    kategoriler = ForumKategori.objects.filter(aktif=True)
    
    if request.method == 'POST':
        baslik = request.POST.get('baslik')
        icerik = request.POST.get('icerik')
        kategori_id = request.POST.get('kategori')
        
        # Sabit konu ve kapalı değerlerini al
        sabit = request.POST.get('sabit') == 'on'
        kapali = request.POST.get('kapali') == 'on'
        
        # Eğer kullanıcı staff değilse sabit konu oluşturamaz
        if sabit and not request.user.is_staff:
            sabit = False
        
        if baslik and icerik and kategori_id:
            kategori = get_object_or_404(ForumKategori, id=kategori_id, aktif=True)
            
            # Kullanıcı staff ise direkt onaylı olarak ekle, değilse onay bekliyor olarak işaretle
            onay_durumu = 'onaylanmis' if request.user.is_staff else 'beklemede'
            
            yeni_konu = ForumKonu.objects.create(
                baslik=baslik,
                icerik=icerik,
                kategori=kategori,
                yazar=request.user,
                sabit=sabit,
                kapali=kapali,
                onay_durumu=onay_durumu
            )
            
            # Staff ise kendisi onaylamış olarak işaretle
            if request.user.is_staff:
                yeni_konu.onaylayan = request.user
                yeni_konu.onay_tarihi = timezone.now()
                yeni_konu.save()
                
                messages.success(request, 'Konu başarıyla oluşturuldu.')
            else:
                messages.success(request, 'Konunuz başarıyla oluşturuldu ve onay için bekliyor. Onaylandıktan sonra görünür olacaktır.')
            
            if onay_durumu == 'onaylanmis':
                return redirect('forum:konu_detay', kategori_slug=kategori.slug, konu_slug=yeni_konu.slug)
            else:
                return redirect('forum:kategori_detay', kategori_slug=kategori.slug)
        else:
            messages.error(request, 'Lütfen tüm alanları doldurun.')
    
    context = {
        'kategoriler': kategoriler,
        'secili_kategori': kategori,
    }
    
    return render(request, 'forum/yeni_konu.html', context)


@login_required
def konu_duzenle(request, konu_id):
    """
    Konu düzenleme sayfasını görüntüler ve konu bilgilerini günceller.
    """
    konu = get_object_or_404(ForumKonu, id=konu_id, aktif=True)
    
    # Sadece yazar veya personel düzenleyebilir
    if not (request.user == konu.yazar or request.user.is_staff):
        return HttpResponseForbidden("Bu konuyu düzenleme yetkiniz yok.")
    
    kategoriler = ForumKategori.objects.filter(aktif=True)
    
    if request.method == 'POST':
        baslik = request.POST.get('baslik')
        icerik = request.POST.get('icerik')
        kategori_id = request.POST.get('kategori')
        
        if baslik and icerik and kategori_id:
            kategori = get_object_or_404(ForumKategori, id=kategori_id, aktif=True)
            
            # Konu bilgilerini güncelle
            konu.baslik = baslik
            konu.icerik = icerik
            konu.kategori = kategori
            konu.save()
            
            messages.success(request, 'Konu başarıyla güncellendi.')
            return redirect('forum:konu_detay', kategori_slug=kategori.slug, konu_slug=konu.slug)
        else:
            messages.error(request, 'Lütfen tüm alanları doldurun.')
    
    context = {
        'konu': konu,
        'kategoriler': kategoriler,
    }
    
    return render(request, 'forum/konu_duzenle.html', context)


@login_required
def yorum_duzenle(request, yorum_id):
    """
    Yorum düzenleme işlemini yapar.
    """
    yorum = get_object_or_404(ForumYorum, id=yorum_id, aktif=True)
    
    # Sadece yazar veya personel düzenleyebilir
    if not (request.user == yorum.yazar or request.user.is_staff):
        return HttpResponseForbidden("Bu yorumu düzenleme yetkiniz yok.")
    
    if request.method == 'POST':
        icerik = request.POST.get('icerik')
        
        if icerik:
            yorum.icerik = icerik
            yorum.save()
            
            messages.success(request, 'Yorum başarıyla güncellendi.')
            return redirect('forum:konu_detay', kategori_slug=yorum.konu.kategori.slug, konu_slug=yorum.konu.slug)
        else:
            messages.error(request, 'Yorum içeriği boş olamaz.')
    
    context = {
        'yorum': yorum,
    }
    
    return render(request, 'forum/yorum_duzenle.html', context)


@login_required
def begeni_ekle(request):
    """
    Ajax ile beğeni/beğenmeme ekleme/kaldırma işlemi yapar.
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        konu_id = request.POST.get('konu_id')
        yorum_id = request.POST.get('yorum_id')
        begeni_turu = request.POST.get('tur', 'like')  # Varsayılan olarak beğeni
        
        # Beğeni türünü kontrol et
        if begeni_turu not in ['like', 'dislike']:
            begeni_turu = 'like'  # Geçersiz değer için varsayılan
        
        if konu_id:
            konu = get_object_or_404(ForumKonu, id=konu_id, aktif=True)
            
            # Mevcut beğeni varsa bul
            mevcut_begeni = ForumBegeni.objects.filter(
                kullanici=request.user,
                konu=konu
            ).first()
            
            if mevcut_begeni:
                # Aynı tür beğeni yapılmışsa sil (toggle)
                if mevcut_begeni.tur == begeni_turu:
                    mevcut_begeni.delete()
                    return JsonResponse({
                        'status': 'removed',
                        'tur': begeni_turu,
                        'like_count': ForumBegeni.objects.filter(konu=konu, tur='like').count(),
                        'dislike_count': ForumBegeni.objects.filter(konu=konu, tur='dislike').count()
                    })
                else:
                    # Farklı tür beğeni yapılmışsa güncelle
                    mevcut_begeni.tur = begeni_turu
                    mevcut_begeni.save()
                    return JsonResponse({
                        'status': 'changed',
                        'tur': begeni_turu,
                        'like_count': ForumBegeni.objects.filter(konu=konu, tur='like').count(),
                        'dislike_count': ForumBegeni.objects.filter(konu=konu, tur='dislike').count()
                    })
            else:
                # Yeni beğeni oluştur
                ForumBegeni.objects.create(
                    kullanici=request.user,
                    konu=konu,
                    tur=begeni_turu,
                    yorum=None
                )
                return JsonResponse({
                    'status': 'added',
                    'tur': begeni_turu,
                    'like_count': ForumBegeni.objects.filter(konu=konu, tur='like').count(),
                    'dislike_count': ForumBegeni.objects.filter(konu=konu, tur='dislike').count()
                })
                
        elif yorum_id:
            yorum = get_object_or_404(ForumYorum, id=yorum_id, aktif=True)
            
            # Mevcut beğeni varsa bul
            mevcut_begeni = ForumBegeni.objects.filter(
                kullanici=request.user,
                yorum=yorum
            ).first()
            
            if mevcut_begeni:
                # Aynı tür beğeni yapılmışsa sil (toggle)
                if mevcut_begeni.tur == begeni_turu:
                    mevcut_begeni.delete()
                    return JsonResponse({
                        'status': 'removed',
                        'tur': begeni_turu,
                        'like_count': ForumBegeni.objects.filter(yorum=yorum, tur='like').count(),
                        'dislike_count': ForumBegeni.objects.filter(yorum=yorum, tur='dislike').count()
                    })
                else:
                    # Farklı tür beğeni yapılmışsa güncelle
                    mevcut_begeni.tur = begeni_turu
                    mevcut_begeni.save()
                    return JsonResponse({
                        'status': 'changed',
                        'tur': begeni_turu,
                        'like_count': ForumBegeni.objects.filter(yorum=yorum, tur='like').count(),
                        'dislike_count': ForumBegeni.objects.filter(yorum=yorum, tur='dislike').count()
                    })
            else:
                # Yeni beğeni oluştur
                ForumBegeni.objects.create(
                    kullanici=request.user,
                    yorum=yorum,
                    tur=begeni_turu,
                    konu=None
                )
                return JsonResponse({
                    'status': 'added',
                    'tur': begeni_turu,
                    'like_count': ForumBegeni.objects.filter(yorum=yorum, tur='like').count(),
                    'dislike_count': ForumBegeni.objects.filter(yorum=yorum, tur='dislike').count()
                })
        
    return JsonResponse({'status': 'error'}, status=400)


@custom_login_required
def forum_arama(request):
    """
    Forum içerisinde arama yapar.
    """
    q = request.GET.get('q', '')
    return redirect('forum:forum_main') if not q else redirect(f"{reverse('forum:forum_main')}?q={q}")


@login_required
@yetkili_required
def forum_kategori_listele(request):
    """
    Forum kategorilerini listeler
    """
    kategoriler = ForumKategori.objects.all().order_by('sira')
    
    # Sayfalama
    paginator = Paginator(kategoriler, 10)  # Sayfa başına 10 kategori
    sayfa = request.GET.get('sayfa', 1)
    
    try:
        kategoriler_sayfa = paginator.page(sayfa)
    except PageNotAnInteger:
        kategoriler_sayfa = paginator.page(1)
    except EmptyPage:
        kategoriler_sayfa = paginator.page(paginator.num_pages)
    
    return render(request, 'forum/yonetim/kategori_listesi.html', {
        'kategoriler': kategoriler_sayfa
    })


@login_required
@yetkili_required
def forum_kategori_ekle(request):
    """
    Yeni forum kategorisi ekleme işlemi
    """
    from .forms import ForumKategoriForm
    
    if request.method == 'POST':
        form = ForumKategoriForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Kategori başarıyla eklendi.")
            return redirect('forum:forum_kategori_listele')
    else:
        form = ForumKategoriForm()
    
    return render(request, 'forum/yonetim/kategori_ekle.html', {
        'form': form
    })


@login_required
@yetkili_required
def forum_kategori_duzenle(request, kategori_id):
    """
    Forum kategorisi düzenleme işlemi
    """
    from .forms import ForumKategoriForm
    
    kategori = get_object_or_404(ForumKategori, id=kategori_id)
    
    if request.method == 'POST':
        form = ForumKategoriForm(request.POST, instance=kategori)
        if form.is_valid():
            form.save()
            messages.success(request, "Kategori başarıyla güncellendi.")
            return redirect('forum:forum_kategori_listele')
    else:
        form = ForumKategoriForm(instance=kategori)
    
    return render(request, 'forum/yonetim/kategori_duzenle.html', {
        'form': form,
        'kategori': kategori
    })


@login_required
@yetkili_required
def forum_kategori_sil(request, kategori_id):
    """
    Forum kategorisi silme işlemi
    """
    kategori = get_object_or_404(ForumKategori, id=kategori_id)
    
    if request.method == 'POST':
        # Önce kategoriyi inaktif yap
        kategori.aktif = False
        kategori.silindi = True
        kategori.silinme_tarihi = timezone.now()
        kategori.save()
        
        # Kategoriye ait tüm konuları inaktif yap
        for konu in ForumKonu.objects.filter(kategori=kategori):
            # Konuyu inaktif yap
            konu.aktif = False
            konu.silindi = True
            konu.silinme_tarihi = timezone.now()
            konu.save()
            
            # Konuya ait tüm yorumları inaktif yap
            ForumYorum.objects.filter(konu=konu).update(aktif=False, silindi=True, silinme_tarihi=timezone.now())
        
        # Alt kategorilerin ust_kategori değerini None yap (silmek yerine)
        ForumKategori.objects.filter(ust_kategori=kategori).update(ust_kategori=None)
        
        kategori_adi = kategori.baslik
        
        messages.success(request, f"'{kategori_adi}' kategorisi ve ilişkili tüm içerikler silindi.")
        return redirect('forum:forum_kategori_listele')
    
    return render(request, 'forum/yonetim/kategori_sil.html', {
        'kategori': kategori
    })


@login_required
@yetkili_required
def forum_konu_sil(request, konu_id):
    """
    Yönetim paneli - Forum konusu silme işlemi
    """
    konu = get_object_or_404(ForumKonu, id=konu_id)
    
    if request.method == 'POST':
        # Önce konuyu inaktif yap
        konu.aktif = False
        konu.silindi = True
        konu.silinme_tarihi = timezone.now()
        konu.save()
        
        # Konuya ait tüm yorumları inaktif yap
        ForumYorum.objects.filter(konu=konu).update(aktif=False, silindi=True, silinme_tarihi=timezone.now())
        
        konu_adi = konu.baslik
        
        messages.success(request, f"'{konu_adi}' konusu ve ilişkili tüm veriler silindi.")
        return redirect('forum:forum_konu_listele')
    
    return render(request, 'forum/yonetim/konu_sil.html', {
        'konu': konu
    })


@login_required
@yetkili_required
def forum_konu_listele(request):
    """
    Forum konularını listeler
    """
    konular = ForumKonu.objects.all().order_by('-olusturma_tarihi')
    
    # Filtreleme için
    kategori_id = request.GET.get('kategori')
    if kategori_id:
        konular = konular.filter(kategori_id=kategori_id)
    
    # Sayfalama
    paginator = Paginator(konular, 10)  # Sayfa başına 10 konu
    sayfa = request.GET.get('sayfa', 1)
    
    try:
        konular_sayfa = paginator.page(sayfa)
    except PageNotAnInteger:
        konular_sayfa = paginator.page(1)
    except EmptyPage:
        konular_sayfa = paginator.page(paginator.num_pages)
    
    # Filtre seçenekleri için kategoriler
    kategoriler = ForumKategori.objects.filter(aktif=True)
    
    # Onay bekleyen konu sayısını ekle
    bekleyen_konu_sayisi = ForumKonu.objects.filter(onay_durumu='beklemede', aktif=True).count()
    
    return render(request, 'forum/yonetim/konu_listesi.html', {
        'konular': konular_sayfa,
        'kategoriler': kategoriler,
        'secili_kategori_id': kategori_id,
        'bekleyen_konu_sayisi': bekleyen_konu_sayisi
    })


@login_required
@yetkili_required
def forum_konu_ekle(request):
    """
    Yönetim panelinden forum konusu ekleme işlemi
    """
    from .forms import ForumKonuForm
    
    if request.method == 'POST':
        form = ForumKonuForm(request.POST)
        if form.is_valid():
            yeni_konu = form.save(commit=False)
            yeni_konu.yazar = request.user
            yeni_konu.save()
            
            messages.success(request, "Forum konusu başarıyla eklendi.")
            return redirect('forum:forum_konu_listele')
    else:
        form = ForumKonuForm()
    
    return render(request, 'forum/yonetim/konu_ekle.html', {
        'form': form
    })


@login_required
@yetkili_required
def forum_konu_duzenle(request, konu_id):
    """
    Forum konusu düzenleme işlemi
    """
    from .forms import ForumKonuForm
    
    konu = get_object_or_404(ForumKonu, id=konu_id)
    
    if request.method == 'POST':
        form = ForumKonuForm(request.POST, instance=konu)
        if form.is_valid():
            form.save()
            messages.success(request, "Konu başarıyla güncellendi.")
            return redirect('forum:forum_konu_listele')
    else:
        form = ForumKonuForm(instance=konu)
    
    return render(request, 'forum/yonetim/konu_duzenle.html', {
        'form': form,
        'konu': konu
    })


@login_required
def konu_sil(request, konu_id):
    """
    Kullanıcının kendi oluşturduğu forum konusunu silme işlemi
    Yetkisiz kullanıcılar sadece kendi konularını silebilir
    """
    konu = get_object_or_404(ForumKonu, id=konu_id)
    
    # Yetkisiz kullanıcı, kendi konusu değilse erişimi engelle
    if not request.user.is_staff and konu.yazar != request.user:
        messages.error(request, "Bu konuyu silme yetkiniz bulunmamaktadır.")
        return redirect('forum:konu_detay', kategori_slug=konu.kategori.slug, konu_slug=konu.slug)
    
    if request.method == 'POST':
        # Konuyu soft-delete olarak işaretle
        konu.aktif = False
        konu.silinme_tarihi = timezone.now()
        konu.save()
        
        # Konuya ait tüm yorumları inaktif yap
        ForumYorum.objects.filter(konu=konu).update(aktif=False, silinme_tarihi=timezone.now())
        
        kategori_slug = konu.kategori.slug
        
        messages.success(request, f"'{konu.baslik}' konusu başarıyla silindi.")
        
        # Yönetici ise konu listesine, normal kullanıcı ise kategoriye yönlendir
        if request.user.is_staff:
            return redirect('forum:forum_konu_listele')
        else:
            return redirect('forum:kategori_detay', kategori_slug=kategori_slug)
    
    return render(request, 'forum/konu_sil.html', {
        'konu': konu
    })


@login_required
@yetkili_required
def forum_yorum_listele(request):
    """
    Forum yorumlarını listeler
    """
    yorumlar = ForumYorum.objects.all().order_by('-olusturma_tarihi')
    
    # Filtreleme için
    konu_id = request.GET.get('konu')
    if konu_id:
        yorumlar = yorumlar.filter(konu_id=konu_id)
    
    # Konuları al (filtreleme için)
    konular = ForumKonu.objects.filter(aktif=True).order_by('baslik')
    
    # Sayfalama
    paginator = Paginator(yorumlar, 20)  # Sayfa başına 20 yorum
    sayfa = request.GET.get('sayfa', 1)
    
    try:
        yorumlar_sayfa = paginator.page(sayfa)
    except PageNotAnInteger:
        yorumlar_sayfa = paginator.page(1)
    except EmptyPage:
        yorumlar_sayfa = paginator.page(paginator.num_pages)
    
    return render(request, 'forum/yonetim/yorum_listesi.html', {
        'yorumlar': yorumlar_sayfa,
        'konular': konular,
    })


@login_required
@yetkili_required
def forum_yorum_duzenle(request, yorum_id):
    """
    Forum yorumu düzenleme işlemi
    """
    from .forms import ForumYorumForm
    
    yorum = get_object_or_404(ForumYorum, id=yorum_id)
    
    if request.method == 'POST':
        form = ForumYorumForm(request.POST, instance=yorum)
        if form.is_valid():
            form.save()
            messages.success(request, "Yorum başarıyla güncellendi.")
            return redirect('forum:forum_yorum_listele')
    else:
        form = ForumYorumForm(instance=yorum)
    
    return render(request, 'forum/yonetim/yorum_duzenle.html', {
        'form': form,
        'yorum': yorum
    })


@login_required
@yetkili_required
def forum_yorum_sil(request, yorum_id):
    """
    Forum yorumu silme işlemi
    """
    yorum = get_object_or_404(ForumYorum, id=yorum_id)
    
    if request.method == 'POST':
        # Önce yorumu inaktif yap
        yorum.aktif = False
        yorum.save()
        
        # Yorumun alt yorumlarını da inaktif yap
        ForumYorum.objects.filter(ust_yorum=yorum).update(aktif=False)
        
        # Ana yorumu tamamen sil
        yorum.delete()
        
        messages.success(request, "Yorum ve ilişkili tüm veriler tamamen silindi.")
        return redirect('forum:forum_yorum_listele')
    
    return render(request, 'forum/yonetim/yorum_sil.html', {
        'yorum': yorum
    })


@login_required
@yetkili_required
def forum_konu_onay_listesi(request):
    """
    Onay bekleyen forum konularını listeler
    """
    konular = ForumKonu.objects.filter(onay_durumu='beklemede').order_by('-olusturma_tarihi')
    
    # Kategori filtresi
    kategori_id = request.GET.get('kategori')
    if kategori_id:
        konular = konular.filter(kategori_id=kategori_id)
    
    # Sayfalama
    paginator = Paginator(konular, 20)  # Sayfa başına 20 konu
    sayfa = request.GET.get('sayfa', 1)
    
    try:
        konular_sayfa = paginator.page(sayfa)
    except PageNotAnInteger:
        konular_sayfa = paginator.page(1)
    except EmptyPage:
        konular_sayfa = paginator.page(paginator.num_pages)
    
    # Filtre seçenekleri için kategoriler
    kategoriler = ForumKategori.objects.filter(aktif=True)
    
    return render(request, 'forum/yonetim/konu_onay_listesi.html', {
        'konular': konular_sayfa,
        'kategoriler': kategoriler,
        'secili_kategori_id': kategori_id,
        'bekleyen_konu_sayisi': ForumKonu.objects.filter(onay_durumu='beklemede').count()
    })


@login_required
@yetkili_required
def forum_konu_onayla(request, konu_id):
    """
    Forum konusu onaylama işlemi
    """
    konu = get_object_or_404(ForumKonu, id=konu_id)
    
    if request.method == 'POST':
        konu.onay_durumu = 'onaylanmis'
        konu.onaylayan = request.user
        konu.onay_tarihi = timezone.now()
        konu.save()
        
        messages.success(request, f"'{konu.baslik}' başlıklı konu başarıyla onaylandı.")
        return redirect('forum:forum_konu_onay_listesi')
    
    return render(request, 'forum/yonetim/konu_onayla.html', {
        'konu': konu
    })


@login_required
@yetkili_required
def forum_konu_reddet(request, konu_id):
    """
    Forum konusu reddetme işlemi
    """
    konu = get_object_or_404(ForumKonu, id=konu_id)
    
    if request.method == 'POST':
        red_sebebi = request.POST.get('red_sebebi', '')
        
        konu.onay_durumu = 'reddedilmis'
        konu.onaylayan = request.user
        konu.onay_tarihi = timezone.now()
        konu.red_sebebi = red_sebebi
        konu.save()
        
        messages.success(request, f"'{konu.baslik}' başlıklı konu reddedildi.")
        return redirect('forum:forum_konu_onay_listesi')
    
    return render(request, 'forum/yonetim/konu_reddet.html', {
        'konu': konu
    })


@login_required
def yorum_sil(request, yorum_id):
    """
    Kullanıcının kendi yorumunu silme işlemi
    Yetkisiz kullanıcılar sadece kendi yorumlarını silebilir
    """
    yorum = get_object_or_404(ForumYorum, id=yorum_id)
    
    # Yetkisiz kullanıcı, kendi yorumu değilse erişimi engelle
    if not request.user.is_staff and yorum.yazar != request.user:
        messages.error(request, "Bu yorumu silme yetkiniz bulunmamaktadır.")
        return redirect('forum:konu_detay', kategori_slug=yorum.konu.kategori.slug, konu_slug=yorum.konu.slug)
    
    if request.method == 'POST':
        # Yorumu soft-delete olarak işaretle
        yorum.aktif = False
        yorum.silinme_tarihi = timezone.now()
        yorum.save()
        
        # Alt yorumları da inaktif yap
        ForumYorum.objects.filter(ust_yorum=yorum).update(aktif=False, silinme_tarihi=timezone.now())
        
        konu = yorum.konu
        
        messages.success(request, "Yorumunuz başarıyla silindi.")
        
        # Konu detay sayfasına geri yönlendir
        return redirect('forum:konu_detay', kategori_slug=konu.kategori.slug, konu_slug=konu.slug)
    
    return render(request, 'forum/yorum_sil.html', {
        'yorum': yorum
    })


@login_required
def kullanici_konular(request):
    """
    Kullanıcının kendi konularını listeleme sayfası
    """
    # Kullanıcının konularını getir
    konular = ForumKonu.objects.filter(yazar=request.user, aktif=True)
    
    # Staff olmayan kullanıcılar için sadece onaylanmış konuları göster
    if not request.user.is_staff:
        konular = konular.filter(onay_durumu='onaylanmis')
    
    # Sıralama parametresi
    siralama = request.GET.get('sirala', '-olusturma_tarihi')
    konular = konular.order_by(siralama)
    
    # Sayfalama
    paginator = Paginator(konular, 10)  # Sayfa başına 10 konu
    sayfa = request.GET.get('sayfa', 1)
    
    try:
        konular_sayfa = paginator.page(sayfa)
    except PageNotAnInteger:
        konular_sayfa = paginator.page(1)
    except EmptyPage:
        konular_sayfa = paginator.page(paginator.num_pages)
    
    return render(request, 'forum/kullanici_konular.html', {
        'konular': konular_sayfa,
        'siralama': siralama,
    })


@custom_login_required
def kullanici_forum_kategori_listele(request):
    """
    Normal kullanıcılar için tüm forum kategorilerini listeleyen sayfa
    """
    kategoriler = ForumKategori.objects.filter(aktif=True).order_by('sira')
    
    context = {
        'kategoriler': kategoriler,
        'aktif_menu': 'forum',
    }
    
    return render(request, 'forum/kullanici_kategori_listele.html', context)


@custom_login_required
def tum_konulari_goster(request):
    """
    Tüm forum konularını listeleyen sayfa
    """
    konular = ForumKonu.objects.filter(aktif=True)
    
    # Staff olmayan kullanıcılar için onaylanmış konuları filtrele
    if not request.user.is_staff:
        konular = konular.filter(onay_durumu='onaylanmis')
    else:
        # Staff kullanıcılar için de reddedilen konuları gizle
        konular = konular.exclude(onay_durumu='reddedilmis')
    
    # Sıralama parametresi
    siralama = request.GET.get('sirala', '-olusturma_tarihi')
    konular = konular.order_by(siralama)
    
    # Sayfalama - 4 konu göster
    paginator = Paginator(konular, 4)  # Sayfa başına 4 konu
    sayfa = request.GET.get('sayfa', 1)
    
    try:
        konular_sayfa = paginator.page(sayfa)
    except PageNotAnInteger:
        konular_sayfa = paginator.page(1)
    except EmptyPage:
        konular_sayfa = paginator.page(paginator.num_pages)
    
    context = {
        'konular': konular_sayfa,
        'siralama': siralama,
        'aktif_menu': 'forum',
    }
    
    return render(request, 'forum/tum_konular.html', context)
