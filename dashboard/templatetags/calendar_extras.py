from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    # This turns day objects into strings and looks them up in your dict
    date_str = key.strftime("%Y-%m-%d")
    return dictionary.get(date_str)