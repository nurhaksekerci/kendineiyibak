from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Sözlükte belirtilen anahtarın değerini döndürür"""
    return dictionary.get(key) 