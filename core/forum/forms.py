from django import forms
from .models import ForumKategori, ForumKonu, ForumYorum

class ForumKategoriForm(forms.ModelForm):
    """Forum kategorisi formu"""
    
    class Meta:
        model = ForumKategori
        fields = ['baslik', 'aciklama', 'ust_kategori', 'icon', 'sira', 'aktif']
        widgets = {
            'baslik': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kategori Adı'}),
            'aciklama': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Kategori Açıklaması'}),
            'ust_kategori': forms.Select(attrs={'class': 'form-control'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'fa-comments'}),
            'sira': forms.NumberInput(attrs={'class': 'form-control'}),
            'aktif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'baslik': 'Kategori Adı',
            'aciklama': 'Açıklama',
            'ust_kategori': 'Üst Kategori',
            'icon': 'İkon (Font Awesome)',
            'sira': 'Sıralama',
            'aktif': 'Aktif',
        }
        help_texts = {
            'icon': 'Örneğin: fa-comments, fa-question, fa-book vb.',
            'ust_kategori': 'Üst kategori seçilmezse ana kategori olarak görüntülenir.',
        }

class ForumKonuForm(forms.ModelForm):
    """Forum konusu formu"""
    
    class Meta:
        model = ForumKonu
        fields = ['baslik', 'icerik', 'kategori', 'sabit', 'kapali', 'aktif']
        widgets = {
            'baslik': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Konu Başlığı'}),
            'icerik': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'placeholder': 'Konunuz...'}),
            'kategori': forms.Select(attrs={'class': 'form-control'}),
            'sabit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'kapali': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'aktif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'baslik': 'Konu Başlığı',
            'icerik': 'İçerik',
            'kategori': 'Kategori',
            'sabit': 'Sabit Konu',
            'kapali': 'Yorumlara Kapalı',
            'aktif': 'Aktif',
        }
        help_texts = {
            'sabit': 'Konu listesinin en üstünde görüntülenir.',
            'kapali': 'Bu konuya yeni yorum yapılamaz.',
            'aktif': 'Pasif konular kullanıcılar tarafından görüntülenemez.',
        }

class ForumYorumForm(forms.ModelForm):
    """Forum yorumu formu"""
    
    class Meta:
        model = ForumYorum
        fields = ['icerik', 'ust_yorum', 'aktif']
        widgets = {
            'icerik': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Yorumunuz...'}),
            'ust_yorum': forms.HiddenInput(),
            'aktif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'icerik': 'Yorum',
            'aktif': 'Aktif',
        } 