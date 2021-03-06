# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-01-10 20:41
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Area',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256)),
                ('external_identifier', models.CharField(max_length=256)),
                ('area_type', models.CharField(choices=[('UNCATEGORIZED', 'Uncategorized'), ('NEIGHBORHOOD', 'Neighborhood'), ('WARD', 'Ward'), ('DISTRICT', 'District'), ('STATE', 'State'), ('COUNTRY', 'Country'), ('REGION', 'Region'), ('COUNTY', 'County')], max_length=64)),
                ('boundary_type', models.CharField(choices=[('OUTER', 'Outer Boundary'), ('INNER', 'Inner Boundary')], max_length=64)),
                ('polygon', models.TextField()),
                ('mbr', models.CharField(max_length=256)),
                ('is_primary', models.BooleanField(default=True)),
                ('created_time', models.DateTimeField()),
                ('outer_area', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='inner_areas', related_query_name='inner_area', to='map.Area')),
                ('primary_area', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='child_areas', related_query_name='child_area', to='map.Area')),
            ],
        ),
        migrations.CreateModel(
            name='AreaBin',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.FloatField(default=0.0)),
                ('count', models.IntegerField(default=0)),
                ('area', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='map.Area')),
            ],
        ),
        migrations.CreateModel(
            name='AreaMap',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256)),
                ('description', models.CharField(blank=True, max_length=256)),
                ('data_source', models.CharField(blank=True, max_length=256, null=True)),
                ('dataset_identifier', models.CharField(blank=True, max_length=256, null=True)),
                ('kml_file', models.FileField(blank=True, null=True, upload_to='uploads/areamap/')),
                ('area_name_path', models.CharField(blank=True, max_length=256, null=True)),
                ('area_external_identifier_path', models.CharField(blank=True, max_length=256, null=True)),
                ('area_default_type', models.CharField(blank=True, max_length=64, null=True)),
                ('created_time', models.DateTimeField()),
                ('areas', models.ManyToManyField(blank=True, null=True, to='map.Area')),
            ],
        ),
        migrations.CreateModel(
            name='DataMap',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256)),
                ('description', models.CharField(blank=True, max_length=256)),
                ('dataset_type', models.CharField(blank=True, choices=[('SOCRATA', 'Socrata Soda Data Portal'), ('OTHER', 'Url for Other Data Source')], max_length=256)),
                ('data_source', models.CharField(blank=True, max_length=256, null=True)),
                ('dataset_identifier', models.CharField(blank=True, max_length=256, null=True)),
                ('dataset_url', models.URLField(blank=True, max_length=256)),
                ('weight_type', models.CharField(choices=[('COUNT', 'Count Instances'), ('SUM', 'Sum Field value')], max_length=64)),
                ('categorize_type', models.CharField(choices=[('POINT', 'Location Point'), ('LATLNG', 'Latitude Longitude'), ('JOIN', 'Join on Common Field'), ('JOIN_MAP', 'Join on Field Mapping')], max_length=64)),
                ('point_key', models.CharField(blank=True, max_length=256)),
                ('latitude_key', models.CharField(blank=True, max_length=256)),
                ('longitude_key', models.CharField(blank=True, max_length=256)),
                ('join_key', models.CharField(blank=True, max_length=256)),
                ('join_map_file', models.FileField(blank=True, null=True, upload_to='uploads/joinmap/')),
                ('value_key', models.CharField(blank=True, max_length=256)),
                ('querystring', models.CharField(blank=True, max_length=256)),
                ('kml_file', models.FileField(blank=True, null=True, upload_to='uploads/datamap/')),
                ('task_id', models.CharField(blank=True, max_length=256)),
                ('created_time', models.DateTimeField()),
                ('updated_time', models.DateTimeField()),
                ('area_map', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='map.AreaMap')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='areabin',
            name='data_map',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='map.DataMap'),
        ),
    ]
