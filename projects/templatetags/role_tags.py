from django import template

register = template.Library()


@register.filter
def has_role(user, role_name):
    if not hasattr(user, "is_authenticated") or not user.is_authenticated:
        return False
    return user.roles.filter(name__iexact=role_name).exists() or getattr(user, "is_superuser", False)
