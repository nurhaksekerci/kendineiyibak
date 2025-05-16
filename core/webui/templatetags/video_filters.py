from django import template
import re
from ..utils import youtube_embed_converter, vimeo_embed_converter, format_duration

register = template.Library()

@register.filter
def youtube_embed_url(url):
    """
    YouTube video URL'sini embed URL'sine dönüştürür.
    Örnek:
    https://www.youtube.com/watch?v=VIDEO_ID -> https://www.youtube.com/embed/VIDEO_ID
    https://youtu.be/VIDEO_ID -> https://www.youtube.com/embed/VIDEO_ID
    """
    return youtube_embed_converter(url)

@register.filter
def vimeo_embed_url(url):
    """
    Vimeo video URL'sini embed URL'sine dönüştürür.
    Örnek:
    https://vimeo.com/VIDEO_ID -> https://player.vimeo.com/video/VIDEO_ID
    """
    return vimeo_embed_converter(url)

@register.filter
def divisibleby(value, arg):
    """
    Bir sayının başka bir sayıya bölümünden elde edilen tam kısmı döndürür.
    Örnek: 125|divisibleby:60 -> 2 (125 saniye = 2 dakika 5 saniye)
    """
    try:
        value = int(value)
        arg = int(arg)
        return value // arg
    except (ValueError, TypeError):
        return 0

@register.filter
def modulo(value, arg):
    """
    Bir sayının başka bir sayıya bölümünden kalan kısmı döndürür.
    Örnek: 125|modulo:60 -> 5 (125 saniye = 2 dakika 5 saniye)
    """
    try:
        value = int(value)
        arg = int(arg)
        return value % arg
    except (ValueError, TypeError):
        return 0

@register.filter
def intdiv(value, arg):
    """Tamsayı bölme işlemi yapar"""
    try:
        return int(int(value) / int(arg))
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def remainder(value, arg):
    """Modulo işlemi yapar"""
    try:
        return int(int(value) % int(arg))
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def format_duration(seconds):
    """Video süresini saat:dakika:saniye formatında gösterir"""
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    except (ValueError, TypeError):
        return "00:00"

@register.filter
def hours_from_seconds(seconds):
    """Saniyeyi saate çevirir"""
    try:
        return int(int(seconds) / 3600)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def minutes_from_seconds(seconds):
    """Saniyeyi dakikaya çevirir (saat hariç)"""
    try:
        return int((int(seconds) % 3600) / 60)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def seconds_remainder(seconds):
    """Saniyenin 60'a bölümünden kalanı verir"""
    try:
        return int(int(seconds) % 60)
    except ValueError:
        return 0

@register.filter
def get_item(dictionary, key):
    """Dictionary'den bir değer alır"""
    return dictionary.get(key, 0)

@register.filter
def index(list_object, index):
    """Bir listenin belirli bir indeksindeki değeri döndürür"""
    try:
        # List-like object'lerin kontrolü
        if list_object is None:
            return f"Satır {index+1}"
            
        if isinstance(list_object, str):
            # Eğer string içinde virgül varsa, virgülle ayrılmış liste olarak düşün
            if ',' in list_object:
                items = [item.strip() for item in list_object.split(',')]
                if 0 <= index < len(items):
                    return items[index]
            return f"Satır {index+1}"
            
        # Normal liste işleme
        if hasattr(list_object, '__getitem__'):
            if 0 <= index < len(list_object):
                return list_object[index]
        
        return f"Satır {index+1}"
    except (IndexError, TypeError):
        return f"Satır {index+1}"

@register.filter
def format_video_duration(seconds):
    """Video süresini saat:dakika:saniye formatında gösterir (alternatif isim)"""
    return format_duration(seconds)

@register.filter
def checkbox_durumu(yanitlar_json, oge_id):
    """Checkbox durumunu kontrol eder"""
    import json
    
    try:
        if not yanitlar_json:
            return False
            
        yanitlar = json.loads(yanitlar_json)
        
        # Doğrudan ID'yi deneyelim (yeni format)
        yanit = yanitlar.get(str(oge_id))
        
        # Eğer bulunamadıysa "oge_ID" formatında deneyelim (eski format)
        if yanit is None:
            oge_key = f"oge_{oge_id}"
            yanit = yanitlar.get(oge_key)
            
        # Hala bulamadıysak
        if yanit is None:
            print(f"Checkbox için yanıt bulunamadı. oge_id: {oge_id}, Mevcut anahtarlar: {list(yanitlar.keys())}")
            return False
        
        # JSON yapısı: {"123": {"deger": true, "tip": "checkbox"}}
        if isinstance(yanit, dict) and 'deger' in yanit:
            return bool(yanit['deger'])
        # Eski format: {"123": true} veya direkt true/false değeri
        elif isinstance(yanit, bool):
            return yanit
        else:
            print(f"Bilinmeyen yanıt formatı: {yanit}, oge_id: {oge_id}")
            return False
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        print(f"Checkbox durumu kontrolünde hata: {e}")
        print(f"Yanıtlar JSON: {yanitlar_json}, oge_id: {oge_id}")
        return False

@register.filter
def metin_yaniti(yanitlar_json, oge_id):
    """Metin yanıtını döndürür"""
    import json
    
    try:
        if not yanitlar_json:
            return ""
            
        yanitlar = json.loads(yanitlar_json)
        
        # Doğrudan ID'yi deneyelim (yeni format)
        yanit = yanitlar.get(str(oge_id))
        
        # Eğer bulunamadıysa "oge_ID" formatında deneyelim (eski format)
        if yanit is None:
            oge_key = f"oge_{oge_id}"
            yanit = yanitlar.get(oge_key)
            
        # Hala bulamadıysak
        if yanit is None:
            print(f"Metin yanıtı bulunamadı. oge_id: {oge_id}, Mevcut anahtarlar: {list(yanitlar.keys())}")
            return ""
        
        # JSON yapısı: {"123": {"metin": "yanıt metni", "tip": "metin"}}
        if isinstance(yanit, dict) and 'metin' in yanit:
            return str(yanit['metin'])
        # Eski format: {"123": "yanıt metni"} veya direkt string değeri
        elif isinstance(yanit, str):
            return yanit
        else:
            print(f"Bilinmeyen metin yanıtı formatı: {yanit}, oge_id: {oge_id}")
            return ""
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        print(f"Metin yanıtı kontrolünde hata: {e}")
        print(f"Yanıtlar JSON: {yanitlar_json}, oge_id: {oge_id}")
        return ""

@register.filter
def tablo_verisi(yanitlar_json, oge_id):
    """Tablo verisini döndürür"""
    import json
    
    try:
        if not yanitlar_json:
            return {}
            
        yanitlar = json.loads(yanitlar_json)
        
        # Önce string id ile deneyelim (yeni format)
        yanit = yanitlar.get(str(oge_id))
        
        # Eğer bulunamadıysa "oge_id" formatında deneyelim (eski format)
        if not yanit:
            oge_key = f"oge_{oge_id}"
            yanit = yanitlar.get(oge_key)
        
        if not yanit:
            return {}
        
        # Yeni format: {"123": {"tablo_veri": {...}, "tip": "tablo"}}
        if isinstance(yanit, dict) and 'tablo_veri' in yanit:
            return yanit.get('tablo_veri', {})
        
        return {}
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        print(f"Tablo verisi alınırken hata: {e}, oge_id: {oge_id}")
        return {}

@register.filter
def tablo_dolu_mu(yanitlar_json, oge_id):
    """Tabloya veri girilmiş mi kontrol eder"""
    import json
    
    try:
        if not yanitlar_json:
            return False
            
        yanitlar = json.loads(yanitlar_json)
        
        # Önce string id ile deneyelim (yeni format)
        yanit = yanitlar.get(str(oge_id))
        
        # Eğer bulunamadıysa "oge_id" formatında deneyelim (eski format)
        if not yanit:
            oge_key = f"oge_{oge_id}"
            yanit = yanitlar.get(oge_key)
        
        if not yanit:
            return False
        
        # Yeni format: {"123": {"tablo_veri": {...}, "tip": "tablo"}}
        if isinstance(yanit, dict) and 'tablo_veri' in yanit:
            tablo_veri = yanit['tablo_veri']
            return any(value and str(value).strip() for value in tablo_veri.values())
        
        return False
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        print(f"Tablo doluluğu kontrolünde hata: {e}, oge_id: {oge_id}")
        return False

@register.filter
def get_range(count):
    """0'dan başlayarak verilen sayıya kadar olan tam sayıları içeren bir liste döndürür"""
    try:
        count_int = int(count)
        return list(range(count_int))
    except (ValueError, TypeError):
        return []

@register.simple_tag
def tablo_verisi_hucre(yanitlar_json, oge_id, satir, sutun):
    """Tablo içindeki belirli bir hücrenin değerini döndürür"""
    import json
    
    try:
        if not yanitlar_json:
            return ""
            
        yanitlar = json.loads(yanitlar_json)
        
        # Önce string id ile deneyelim (yeni format)
        str_oge_id = str(oge_id)
        yanit = yanitlar.get(str_oge_id)
        
        # Eğer bulunamadıysa "oge_id" formatında deneyelim (eski format)
        if not yanit:
            oge_key = f"oge_{oge_id}"
            yanit = yanitlar.get(oge_key)
        
        if not yanit or not isinstance(yanit, dict):
            return ""
        
        # Tablo verisini al
        if 'tablo_veri' in yanit:
            tablo_veri = yanit['tablo_veri']
        else:
            tablo_veri = yanit
        
        # Hücre anahtarı oluştur (satır ve sütun 1'den başlayarak)
        hucre_key = f"satir{int(satir)}_sutun{int(sutun)}"
        
        # Hücre değerini al, yoksa boş string döndür
        return tablo_veri.get(hucre_key, "")
        
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        print(f"Tablo hücresi alınırken hata: {e}, oge_id: {oge_id}, satir: {satir}, sutun: {sutun}")
        return ""

@register.filter
def add_days(value, days):
    """Bir tarihe belirli gün sayısı ekler"""
    from datetime import timedelta
    try:
        return value + timedelta(days=int(days))
    except (ValueError, TypeError):
        return value

@register.filter
def multiply_days(value, multiplier):
    """Bir tarihe eklenen gün sayısını çarpar (hafta hesabı için)"""
    try:
        # Bu filtre sadece add_days filtresi ile kullanılmalıdır
        # Bu durumda value bir tarih değeri olmalıdır ve değiştirilmeden geri döndürülür
        # multiply_days sadece hafta sayısı ve gün sayısı arasındaki hesaplama için kullanılacak
        return value
    except (ValueError, TypeError):
        return value 

@register.filter
def multiply(value, arg):
    """Bir sayıyı başka bir sayıyla çarpar"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def last_completed(value, tamamlanan_moduller):
    """
    Bir modul listesindeki son elemanın ID'si tamamlanan_moduller içinde mi kontrol eder.
    Örneğin, aynı haftadaki önceki modüllerin tamamlanıp tamamlanmadığını kontrol etmek için kullanılır.
    """
    try:
        if not value or len(value) == 0:
            return True  # Boş liste olması durumunda True döndür
        
        # Listenin son elemanını al
        son_modul = value[-1]
        
        # Son modülün ID'si tamamlanan modüller içinde mi kontrol et
        return son_modul.id in tamamlanan_moduller
    except (IndexError, AttributeError, TypeError) as e:
        print(f"last_completed filtresinde hata: {e}")
        return False 