from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import Farm, Livestock, HealthRecord, AMURecord, FeedRecord, YieldRecord

class IsFarmOwner(BasePermission):
    """
    Allows access only to the owner of the farm.
    This permission is intended for views that operate on the Farm model itself.
    """
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Farm):
            return obj.owner == request.user
        return False

class IsFarmMember(BasePermission):
    """
    - Farm owners have full access.
    - Approved labourers have read-only access to most things.
    - Approved labourers can create/read/update FeedRecord and YieldRecord.
    - No one can delete FeedRecord and YieldRecord except the owner.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # This allows any authenticated user to proceed to the object-level permission check
        # or to the view's queryset which should be filtered.
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        farm = self._get_farm_from_obj(obj)

        if not farm:
            return False

        # Farm owner has full permissions
        if farm.owner == user:
            return True

        # Check for approved labourer status
        try:
            is_approved_labourer = (
                user.labourer_profile.farm == farm and
                user.labourer_profile.status == 'approved'
            )
        except AttributeError: # Catches if user has no labourer_profile
            is_approved_labourer = False

        if not is_approved_labourer:
            return False

        # Labourer permissions
        viewset_name = view.__class__.__name__

        # Labourers can do anything on Feed and Yield records except delete
        if viewset_name in ['FeedRecordViewSet', 'YieldRecordViewSet']:
            if request.method == 'DELETE':
                return False # Only owner can delete
            return True

        # For all other views, labourers have read-only access
        if request.method in SAFE_METHODS:
            return True

        return False

    def _get_farm_from_obj(self, obj):
        if isinstance(obj, Farm):
            return obj
        if hasattr(obj, 'farm') and obj.farm is not None:
            return obj.farm
        if hasattr(obj, 'livestock') and obj.livestock.farm is not None:
            return obj.livestock.farm
        return None