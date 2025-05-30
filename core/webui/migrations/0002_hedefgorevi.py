# Generated by Django 5.1 on 2025-03-20 12:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webui', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HedefGorevi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('baslik', models.CharField(max_length=255, verbose_name='Görev Başlığı')),
                ('tamamlandi', models.BooleanField(default=False, verbose_name='Tamamlandı')),
                ('tamamlanma_tarihi', models.DateTimeField(blank=True, null=True, verbose_name='Tamamlanma Tarihi')),
                ('olusturulma_tarihi', models.DateTimeField(auto_now_add=True, verbose_name='Oluşturulma Tarihi')),
                ('guncelleme_tarihi', models.DateTimeField(auto_now=True, verbose_name='Güncelleme Tarihi')),
                ('hedef', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gorevler', to='webui.haftalikhedef', verbose_name='Haftalık Hedef')),
            ],
            options={
                'verbose_name': 'Hedef Görevi',
                'verbose_name_plural': 'Hedef Görevleri',
                'ordering': ['tamamlandi', 'olusturulma_tarihi'],
            },
        ),
    ]
