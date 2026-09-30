from django import template

register = template.Library()

@register.filter
def kes(value):
    try:
        return "KES " + format(float(value or 0), ",.0f")
    except (TypeError, ValueError):
        return "KES 0"
