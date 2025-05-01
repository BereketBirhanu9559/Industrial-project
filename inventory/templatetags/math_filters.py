from django import template

register = template.Library()

@register.filter
def sub(value, arg):
    """Subtracts the arg from the value"""
    return value - arg