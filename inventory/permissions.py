from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdmin(BasePermission):
    """
    Custom permission to allow only admin users to modify data.
    """
    def has_permission(self, request, view):
        # Admins can do anything
        if request.user.is_authenticated and request.user.role == 'admin':
            return True
        # Deny access for others
        return False


class IsStaffOrAdmin(BasePermission):
    """
    Custom permission to allow both Admin and Staff to create or manage stock transactions.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'staff']
