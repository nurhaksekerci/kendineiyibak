import re
import json
from django.utils import timezone
from datetime import datetime, timedelta

def youtube_embed_converter(url):
    """
    YouTube URL'lerini embed formatına dönüştürür.
    Desteklenen URL formatları:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    """
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    match = re.search(youtube_regex, url)
    
    if match:
        video_id = match.group(6)
        embed_url = f'https://www.youtube.com/embed/{video_id}'
        return embed_url
    
    return url  # Eğer eşleşme bulunamazsa orijinal URL'yi döndür

def vimeo_embed_converter(url):
    """
    Vimeo video URL'sini embed URL'sine dönüştürür.
    Desteklenen formatlar:
    - https://vimeo.com/VIDEO_ID
    """
    if not url:
        return url
        
    # Zaten embed formatında ise değiştirme
    if 'player.vimeo.com/video/' in url:
        return url
    
    vimeo_regex = r'(?:https?:\/\/)?(?:www\.)?(?:vimeo\.com\/)([0-9]+)'
    match = re.search(vimeo_regex, url)
    
    if match:
        video_id = match.group(1)
        return f'https://player.vimeo.com/video/{video_id}'
    return url

def format_duration(seconds):
    """Video süresini saat:dakika:saniye formatında gösterir"""
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    except (ValueError, TypeError):
        return "00:00" 