import django.utils.timezone as timezone


def year(request):
    """Добавляет переменную с текущим годом."""
    return {
        'year': timezone.now().year
    }
