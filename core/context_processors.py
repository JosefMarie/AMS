from .models import AcademicYear, SystemSetting

def academic_timeline(request):
    settings = SystemSetting.get_settings()
    global_active_year = settings.current_academic_year
    global_active_term = settings.current_term or 'Term 1'

    # Get all academic years
    academic_years = AcademicYear.objects.all().order_by('-name')
    all_terms = ['Term 1', 'Term 2', 'Term 3']

    # Retrieve selected view state from session
    session_year_id = request.session.get('view_year_id')
    session_term = request.session.get('view_term')

    active_view_year = None
    if session_year_id:
        try:
            active_view_year = AcademicYear.objects.get(pk=session_year_id)
        except AcademicYear.DoesNotExist:
            pass

    if not active_view_year:
        active_view_year = global_active_year

    if not active_view_year and academic_years.exists():
        active_view_year = academic_years.first()

    active_view_term = session_term or global_active_term

    # Check if we are viewing a historical archive (past year or past term)
    is_historical_archive = False
    if active_view_year and global_active_year:
        if active_view_year.id != global_active_year.id or active_view_term != global_active_term:
            is_historical_archive = True
    elif active_view_term != global_active_term:
        is_historical_archive = True

    return {
        'academic_years': academic_years,
        'all_terms': all_terms,
        'active_view_year': active_view_year,
        'active_view_term': active_view_term,
        'global_active_year': global_active_year,
        'global_active_term': global_active_term,
        'is_historical_archive': is_historical_archive
    }

def global_settings(request):
    return {
        'site_settings': SystemSetting.get_settings()
    }

def unread_notifications(request):
    if request.user.is_authenticated:
        # Get unread notifications for the user
        notifications = request.user.notifications.filter(is_read=False).order_by('-created_at')
        return {
            'unread_notifications': notifications,
            'unread_notifications_count': notifications.count()
        }
    return {}
