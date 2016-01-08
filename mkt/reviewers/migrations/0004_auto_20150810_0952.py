# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reviewers', '0003_auto_20150727_1017'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='editorsubscription',
            name='addon',
        ),
        migrations.RemoveField(
            model_name='editorsubscription',
            name='user',
        ),
        migrations.DeleteModel(
            name='EditorSubscription',
        ),
    ]
