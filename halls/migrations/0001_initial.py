# Generated by Django 5.2 on 2025-04-09 08:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Hall',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('length', models.IntegerField(help_text='Length in meters')),
                ('breadth', models.IntegerField(help_text='Breadth in meters')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Stall',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stall_number', models.CharField(max_length=20)),
                ('x_start', models.IntegerField()),
                ('y_start', models.IntegerField()),
                ('width', models.IntegerField()),
                ('height', models.IntegerField()),
                ('selected_boxes', models.JSONField(default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('hall', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stalls', to='halls.hall')),
            ],
        ),
    ]
