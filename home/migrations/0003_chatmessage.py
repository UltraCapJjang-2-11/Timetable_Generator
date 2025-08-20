from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0002_delete_authgroup_delete_authgrouppermissions_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('room', models.CharField(db_index=True, max_length=100)),
                ('course_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('user_id', models.IntegerField(blank=True, null=True)),
                ('username', models.CharField(default='익명', max_length=150)),
                ('message', models.TextField()),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
            ],
            options={
                'db_table': 'chat_messages',
                'ordering': ['created_at'],
            },
        ),
    ] 