from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_staff and request.user.is_superuser

class HasWarehouseAccess(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff and request.user.is_superuser:
            return True
            
        
        if hasattr(obj, 'warehouse'):
            return request.user in obj.warehouse.authorized_users.all()
        elif hasattr(obj, 'source_warehouse'):
            has_source_access = (obj.source_warehouse and 
                               request.user in obj.source_warehouse.authorized_users.all())
            has_dest_access = (obj.destination_warehouse and 
                             request.user in obj.destination_warehouse.authorized_users.all())
            return has_source_access or has_dest_access
        
        return False
