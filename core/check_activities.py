import os
import django

# Django ayarlarını yükle
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from webui.models import HaftalikAktivite, User

# Aktivite sayısını kontrol et
print('Mevcut aktivite sayısı:', HaftalikAktivite.objects.count())

# Eğer aktivite yoksa bir tane oluştur
if HaftalikAktivite.objects.count() == 0:
    admin_user = User.objects.filter(is_superuser=True).first()
    if admin_user:
        aktivite = HaftalikAktivite.objects.create(
            baslik='Test Aktivitesi',
            aciklama='Bu bir test aktivitesidir.',
            hafta=1,
            tip='karma',
            aktif=True,
            olusturan=admin_user
        )
        print('Test aktivitesi oluşturuldu:', aktivite.id)
    else:
        print('Admin kullanıcı bulunamadı!')
else:
    print('Mevcut aktiviteler:')
    for a in HaftalikAktivite.objects.all():
        print(f'  {a.id}: {a.baslik} - Hafta {a.hafta} - Aktif: {a.aktif} - Silindi: {a.silindi}') 