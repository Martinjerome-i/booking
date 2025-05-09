from django import template

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiplies the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Template filter to access a dictionary by key
    Usage: {{ my_dict|get_item:my_key }}
    """
    return dictionary.get(key, '')