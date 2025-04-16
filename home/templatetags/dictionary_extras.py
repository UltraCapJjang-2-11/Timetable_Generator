from django import template

register = template.Library()

@register.filter(name='dict_get')
def dict_get(value, arg):
    """Dictionary에서 key를 찾아 반환하는 필터.
       사용법: {{ some_dict|dict_get:"key" }}
    """
    if isinstance(value, dict):
        return value.get(arg, "")
    return ""

@register.filter(name='dict_items')
def dict_items(value):
    """Dictionary의 항목들을 반환하는 필터.
       사용법: {% for key, val in some_dict|dict_items %}
    """
    if isinstance(value, dict):
        return value.items()
    return []

@register.filter(name='subtract')
def subtract(value, arg):
    """두 값을 뺄셈 처리하는 필터.
       사용법: {{ value|subtract:arg }}
       만약 결과가 음수이면 0을 반환.
    """
    try:
        result = float(value) - float(arg)
        if result < 0:
            result = 0
        if result.is_integer():
            return int(result)
        return result
    except Exception:
        return ""
