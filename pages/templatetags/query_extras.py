from django import template

register = template.Library()


@register.simple_tag
def url_replace(request, field, value):
    qdict = request.GET.copy()
    qdict[field] = value
    return qdict.urlencode()