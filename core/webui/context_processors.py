from django.urls import reverse
from .models import Mesaj

def notifications_processor(request):
    """
    Kullanıcının okunmamış mesaj sayısını ve bildirimlerini her şablonda 
    kullanılabilecek şekilde context'e ekler
    """
    context = {
        'okunmayan_mesaj_sayisi': 0,
        'bildirimler': []
    }
    
    if request.user.is_authenticated:
        # Okunmamış mesaj sayısını hesapla
        okunmayan_mesajlar = Mesaj.objects.filter(
            alici=request.user,
            okundu=False
        ).count()
        
        # User nesnesine okunmayan mesaj sayısını ekle (şablonda kolay erişim için)
        request.user.okunmayan_mesaj_sayisi = okunmayan_mesajlar
        context['okunmayan_mesaj_sayisi'] = okunmayan_mesajlar
        
        # Son 5 bildirimi al (mesajlar)
        son_bildirimler = Mesaj.objects.filter(
            alici=request.user,
            okundu=False
        ).order_by('-olusturma_tarihi')[:5]
        
        bildirimler = []
        for bildirim in son_bildirimler:
            bildirimler.append({
                'id': bildirim.id,
                'tur': 'mesaj',
                'baslik': bildirim.konu,
                'icerik': bildirim.icerik[:50] + '...' if len(bildirim.icerik) > 50 else bildirim.icerik,
                'tarih': bildirim.olusturma_tarihi,
                'url': reverse('mesaj_detay', args=[bildirim.id])
            })
        
        context['bildirimler'] = bildirimler
    
    return context 