from django.core.mail import send_mail, send_mass_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def _get_from_email():
    return settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER or 'noreply@amsportal.app'


def _notifications_enabled():
    try:
        from .models import SystemSetting
        s = SystemSetting.get_settings()
        return s
    except Exception:
        return None


def send_marks_email(mark, assessment):
    s = _notifications_enabled()
    if not s or not s.email_notify_marks:
        return
    student = mark.student
    if not student.email:
        return
    try:
        pct = round((mark.score / assessment.total_marks) * 100) if assessment.total_marks > 0 else 0
        subject = f"[{s.site_name}] New Mark: {assessment.title}"
        body = (
            f"Hi {student.get_full_name() or student.username},\n\n"
            f"Your mark for '{assessment.title}' has been recorded:\n\n"
            f"  Score : {mark.score} / {assessment.total_marks} ({pct}%)\n"
            f"  Type  : {assessment.get_assessment_type_display()}\n\n"
            f"Log in to your portal to view your full gradebook.\n\n"
            f"— {s.site_name}"
        )
        send_mail(subject, body, _get_from_email(), [student.email], fail_silently=True)
        logger.info(f"Marks email sent to {student.email} for {assessment.title}")
    except Exception as e:
        logger.warning(f"Failed to send marks email to {student.email}: {e}")


def send_announcement_emails(announcement):
    s = _notifications_enabled()
    if not s or not s.email_notify_announcements:
        return
    try:
        from .models import StudentProfile
        students = StudentProfile.objects.filter(
            classroom=announcement.classroom
        ).select_related('user')
        recipients = [sp.user.email for sp in students if sp.user.email]
        if not recipients:
            return
        subject = f"[{s.site_name}] {announcement.classroom.name}: {announcement.title}"
        body = (
            f"New announcement in {announcement.classroom.name}\n"
            f"{'=' * 50}\n\n"
            f"{announcement.title}\n\n"
            f"{announcement.content}\n\n"
            f"Posted by {announcement.teacher.get_full_name() or announcement.teacher.username}\n\n"
            f"— {s.site_name}"
        )
        from_email = _get_from_email()
        messages = tuple(
            (subject, body, from_email, [email])
            for email in recipients
        )
        send_mass_mail(messages, fail_silently=True)
        logger.info(f"Announcement emails sent to {len(recipients)} students in {announcement.classroom.name}")
    except Exception as e:
        logger.warning(f"Failed to send announcement emails: {e}")


def send_welcome_email(user, temp_password=None):
    s = _notifications_enabled()
    if not s or not s.email_notify_welcome:
        return
    if not user.email:
        return
    try:
        subject = f"Welcome to {s.site_name}!"
        body = (
            f"Hi {user.get_full_name() or user.username},\n\n"
            f"Your account on {s.site_name} has been created.\n\n"
            f"  Username : {user.username}\n"
        )
        if temp_password:
            body += f"  Password : {temp_password}\n\n"
            body += f"Please log in and change your password immediately.\n"
        body += f"\n— {s.site_name}"
        send_mail(subject, body, _get_from_email(), [user.email], fail_silently=True)
        logger.info(f"Welcome email sent to {user.email}")
    except Exception as e:
        logger.warning(f"Failed to send welcome email to {user.email}: {e}")


def send_promotion_email(student_profile, action, old_level, next_level, classroom_name=None):
    s = _notifications_enabled()
    if not s:
        return
    student = student_profile.user
    if not student.email:
        return
    try:
        from_email = _get_from_email()
        
        if action == 'promote':
            if next_level == 'Graduated':
                subject = f"🎓 [{s.site_name}] Graduation Congratulations!"
                body = (
                    f"Hi {student.get_full_name() or student.username},\n\n"
                    f"Congratulations! You have officially completed Level 5 and graduated from the academy!\n\n"
                    f"This is a major milestone, and we are incredibly proud of your hard work, dedication, and academic achievements throughout secondary school.\n\n"
                    f"We wish you all the best in your future studies and career endeavors! You will always be a valued alumnus of our academy.\n\n"
                    f"Best wishes,\n"
                    f"— {s.site_name} Administration"
                )
            else:
                subject = f"🚀 [{s.site_name}] Academic Promotion: Advanced to {next_level}!"
                body = (
                    f"Hi {student.get_full_name() or student.username},\n\n"
                    f"Congratulations! You have been promoted to a higher academic tier!\n\n"
                    f"  Old Level: {old_level}\n"
                    f"  New Level: {next_level}\n"
                )
                if classroom_name:
                    body += f"  New Classroom: {classroom_name}\n"
                body += (
                    f"\nYour hard work this past academic year has paid off. Your profile and dashboard have been upgraded to reflect your new level.\n\n"
                    f"Keep up the excellent work in the next chapter of your TVET studies!\n\n"
                    f"Best regards,\n"
                    f"— {s.site_name}"
                )
        elif action == 'repeat':
            subject = f"📋 [{s.site_name}] Academic Registration: {old_level}"
            body = (
                f"Hi {student.get_full_name() or student.username},\n\n"
                f"Your registration for the upcoming academic year has been finalized.\n\n"
                f"You have been registered to repeat {old_level} to master the current curriculum outcomes.\n\n"
                f"  Academic Level: {old_level}\n"
            )
            if classroom_name:
                body += f"  Assigned Classroom: {classroom_name}\n"
            body += (
                f"\nThis is an opportunity to strengthen your skills, perfect your modules, and achieve outstanding results! Your trainers and advisors are fully dedicated to supporting your success every step of the way.\n\n"
                f"We look forward to an amazing year of progress and learning together!\n\n"
                f"Sincerely,\n"
                f"— {s.site_name}"
            )
        else:
            return
            
        send_mail(subject, body, from_email, [student.email], fail_silently=True)
        logger.info(f"Promotion email sent to {student.email} for action: {action}")
    except Exception as e:
        logger.warning(f"Failed to send promotion email to {student.email}: {e}")

