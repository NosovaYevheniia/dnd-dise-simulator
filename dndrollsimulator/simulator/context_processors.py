from .models import UserPreferences


def user_preferences(request):
    preferences = None
    if request.user.is_authenticated:
        preferences = UserPreferences.objects.filter(user=request.user).first()

    return {"user_preferences": preferences}
