def user_group_names(request):
    if request.user.is_authenticated:
        return {'user_group_names': list(request.user.groups.values_list('name', flat=True))}
    return {'user_group_names': []}