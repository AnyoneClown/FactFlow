from django.core.exceptions import PermissionDenied

ADMIN_GROUP_NAME = "Admin"
USER_GROUP_NAME = "User"


def is_admin(user) -> bool:
    return bool(
        user.is_authenticated
        and (user.is_superuser or user.groups.filter(name=ADMIN_GROUP_NAME).exists())
    )


def admin_required(view_func):
    def wrapped(request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapped
