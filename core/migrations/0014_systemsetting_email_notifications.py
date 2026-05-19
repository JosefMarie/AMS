from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_systemsetting_gemini_api_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsetting',
            name='email_notify_marks',
            field=models.BooleanField(default=False, help_text='Email students when their marks are entered.'),
        ),
        migrations.AddField(
            model_name='systemsetting',
            name='email_notify_announcements',
            field=models.BooleanField(default=False, help_text='Email students when a new announcement is posted.'),
        ),
        migrations.AddField(
            model_name='systemsetting',
            name='email_notify_welcome',
            field=models.BooleanField(default=False, help_text='Email new users their login credentials when their account is created.'),
        ),
    ]
