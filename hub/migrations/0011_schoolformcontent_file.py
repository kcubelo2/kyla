from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('hub', '0010_section_course_section'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schoolformcontent',
            name='form_type',
            field=models.CharField(
                choices=[
                    ('SF1', 'School Register'),
                    ('SF2', 'Daily Attendance'),
                    ('SF3', 'Books Issued'),
                    ('SF4', 'Monthly Learner Movement'),
                    ('SF5', 'Report on Promotion'),
                    ('SF6', 'Summarized Report on Promotion'),
                    ('SF7', 'School Personnel Assignment'),
                    ('SF8', 'Learner Basic Health Profile'),
                    ('SF9', "Learner's Progress Report Card"),
                    ('SF10JHS', 'SF 10 JHS Permanent Academic Record'),
                    ('SF10SHS', 'SF 10 SHS Permanent Academic Record'),
                ],
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name='schoolformcontent',
            name='content',
            field=models.TextField(blank=True, help_text='Rich text content of the form'),
        ),
        migrations.AddField(
            model_name='schoolformcontent',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='school_forms/'),
        ),
    ]
