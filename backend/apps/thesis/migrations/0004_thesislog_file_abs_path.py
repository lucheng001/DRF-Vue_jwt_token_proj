# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-27 02:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('thesis', '0003_auto_20171224_0358'),
    ]

    operations = [
        migrations.AddField(
            model_name='thesislog',
            name='file_abs_path',
            field=models.CharField(blank=True, default='', max_length=255, null=True),
        ),
    ]
