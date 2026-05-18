from .roles import is_admin


def crm_navigation(request):
    return {"crm_is_admin": is_admin(request.user)}
