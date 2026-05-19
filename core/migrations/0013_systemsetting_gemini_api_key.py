from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_studentprofile_bio_studentprofile_profile_picture_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsetting',
            name='gemini_api_key',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Google Gemini API key for AI quiz and session plan generation.',
                max_length=200,
            ),
        ),
    ]
