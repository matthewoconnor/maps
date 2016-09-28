import re
import matplotlib.path as matplotlib_path
import numpy as np

from pyquery import PyQuery as pq
from sodapy import Socrata

from django.db import models
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.files.base import ContentFile

from .utils import kml_hex_color_from_value_range, kml_height_from_value_range

AREA_TYPES = (
	("UNCATEGORIZED", "Uncategorized"),
	("NEIGHBORHOOD", "Neighborhood"),
	("WARD", "Ward"),
	("DISTRICT", "District"),
	("STATE", "State"),
	("COUNTRY", "Country"),
	("REGION", "Region"),
	("COUNTY", "County"),
)

BOUNDARY_TYPES = (
	("OUTER", "Outer Boundary"),
	("INNER", "Inner Boundary")
)

class Area(models.Model):
	"""
	A single enclosed area
	"""
	name = models.CharField(max_length=255)
	external_identifier = models.CharField(max_length=255)
	area_type = models.CharField(max_length=50, choices=AREA_TYPES)
	boundary_type = models.CharField(max_length=50, choices=BOUNDARY_TYPES)
	polygon = models.TextField()
	mbr = models.CharField(max_length=255) #n,e,s,w
	outer_area = models.ForeignKey("Area", related_name="inner_area", null=True, blank=True)

	created_time = models.DateTimeField()

	def __str__(self):
		return self.name

	def contains_point(self, lng, lat, polygon_list=None):
		""" tests if a point is within this area
				test for minumum bounding rectangle 
				before trying more expensive contains_point method """
		n, e, s, w = self.mbr.split(",")
		if lng < float(e) and lng > float(w) and lat < float(n) and lat > float(s):
			vertices = polygon_list or self.get_polygon_list()
			path = matplotlib_path.Path(np.array(vertices))
			return path.contains_point((lng, lat))
		else:
			return False

	def get_polygon_list(self):
		return [point.split(",") for point in self.polygon.split(";")]

	def mbr_from_polygon(self):
		points = self.polygon.split(";")
		lngs = []
		lats = []
		for point in points:
			coords = point.split(",")
			lngs.append(float(coords[0]))
			lats.append(float(coords[1]))
		return "{n},{e},{s},{w}".format(n=max(lats), e=max(lngs), s=min(lats), w=min(lngs))

	def save(self, *args, **kwargs):
		self.created_time = self.created_time or timezone.now()
		return super().save(*args, **kwargs)


class AreaMap(models.Model):
	""" A collection of areas (e.g. Chicago Neighborhoods)"""
	name = models.CharField(max_length=255)
	areas = models.ManyToManyField("Area", null=True, blank=True)
	data_source = models.CharField(max_length=255, null=True, blank=True) # e.g. "data.cityofchicago.org"
	dataset_identifier = models.CharField(max_length=255, null=True, blank=True)

	kml_file = models.FileField(upload_to="uploads/areamap/", null=True, blank=True)
	area_name_path = models.CharField(max_length=255, null=True, blank=True)
	area_external_identifier_path = models.CharField(max_length=255, null=True, blank=True)
	area_default_type = models.CharField(max_length=50, null=True, blank=True)

	created_time = models.DateTimeField()

	def import_areas_from_kml_file(self):
		
		d = pq(filename=self.kml_file.path, parser="xml")

		for placemark in d("Placemark").items():

			# can there be multiple outer boundaries?
			outer_boundary_text = placemark.find("outerBoundaryIs LinearRing coordinates").text()
			inner_boundaries = placemark.find("innerBoundaryIs")

			area = Area(
				polygon=re.sub(r"\s+", ";", outer_boundary_text.strip()),
				name=placemark.find(self.area_name_path).text(), # e.g. "Data[name='ntaname'] value"
				external_identifier=placemark.find(self.area_external_identifier_path).text(), # e.g. "Data[name='ntacode'] value"
				area_type=self.area_default_type,
				boundary_type="OUTER"
			)

			area.mbr = area.mbr_from_polygon()
			area.save()

			for inner_boundary in inner_boundaries.items():
				inner_boundary_text = inner_boundary.find("LinearRing coordinates").text()
				inner_area = Area(
					polygon=re.sub(r"\s+", ";", inner_boundary_text.strip()),
					name="{0} Inner".format(area.name),
					external_identifier=area.external_identifier,
					area_type=self.area_default_type,
					boundary_type="INNER",
					outer_area=area
				)

				inner_area.mbr = inner_area.mbr_from_polygon()
				inner_area.save()

			self.areas.add(a)

	@classmethod
	def import_from_geojson(cls, file, *args, **kwargs):
		"""write code to import from geojson file"""
		# feature_path = kwargs.get("feature_path",".")
		pass

	def import_areas_from_soda(self, field_mapping, defaults):
		
		# e.g. this is for chicago neighborhoods
		if not field_mapping:
			field_mapping = dict(
				polygon="the_geom",
				name="community",
				external_identifier="area_num_1"
			)

		if not defaults:
			defaults = dict(
				area_type="NEIGHBORHOOD",
			)

		# client = Socrata(self.data_source, "FakeAppToken", username="fakeuser@somedomain.com", password="ndKS92mS01msjJKs")
		client = Socrata(self.data_source, None)
		data = client.get(self.dataset_identifier, content_type="json")

		for area in data:
			coordinates = area[field_mapping["polygon"]]["coordinates"][0][0]
			lngs = []
			lats = []
			polygon = []
			for c in coordinates:
				lngs.append(c[0])
				lats.append(c[1])
				polygon.append( ",".join([str(i) for i in c]) )
			mbr = "{n},{e},{s},{w}".format(n=max(lats), e=max(lngs), s=min(lats), w=min(lngs))

			area_data = dict(
				polygon= ";".join(polygon),
				name=area[field_mapping["name"]],
				external_identifier=area[field_mapping["external_identifier"]],
				mbr=mbr,
				**defaults
			)

			a = Area.objects.create(**area_data)

			self.areas.add(a)

	def __str__(self):
		return self.name

	def save(self, *args, **kwargs):
		self.created_time = self.created_time or timezone.now()
		return super().save(*args, **kwargs)



class KmlMap(models.Model):
	""" A generated KML file for a data map"""
	name = models.CharField(max_length=255)
	user = models.ForeignKey("auth.User")

	data_source = models.CharField(max_length=255, null=True, blank=True) # e.g. "data.cityofchicago.org"
	dataset_identifier = models.CharField(max_length=255, null=True, blank=True)
	area_map = models.ForeignKey("AreaMap", null=True, blank=True)

	kml_file = models.FileField(upload_to="uploads/datamap/", null=True, blank=True)

	created_time = models.DateTimeField()
	updated_time = models.DateTimeField()

	def kml_mapplot_from_soda_dataset(self, *args, **kwargs):
		
		search_kwargs = kwargs.get("search_kwargs", dict())
		lng_fieldname = kwargs.get("lng_field", "longitude")
		lat_fieldname = kwargs.get("lat_field", "latitude")
		client = Socrata(self.data_source, None)

		areas = self.area_map.areas.filter(boundary_type="OUTER")

		area_bins = [dict(
				area=area,
				polygon=area.get_polygon_list(),
				count=0
			) for area in areas]

		LIMIT = 5000
		offset = 0
		without_coords = 0

		while True and offset < 20000:

			data = client.get(
				self.dataset_identifier, 
				content_type="json", 
				limit=LIMIT, 
				offset=offset, **search_kwargs)

			if not data:
				print("done with data")
				break
			else:
				print("data {0} to {1}".format(offset, offset + 5000))

			for row in data:

				try:
					lat_value = row[lat_fieldname]
					lng_value = row[lng_fieldname]
					if isinstance(lat_value, dict) and lat_value.get("type", "") == "Point":
						coords = lat_value.get("coordinates")
						lng = float(coords[0])
						lat = float(coords[1])
					else:
						lng = float(lng_value)
						lat = float(lat_value)

					for ab in area_bins:
						if ab["area"].contains_point(lng, lat, polygon_list=ab["polygon"]):
							ab["count"] += 1
							break
				except:
					without_coords += 1

			offset += LIMIT

		print("without coordinates: " + str(without_coords))

		counts = [ab["count"] for ab in area_bins]
		min_count = min(counts)
		max_count = max(counts)

		print(counts)

		for ab in area_bins:
			ab["height"] = kml_height_from_value_range(ab["count"], min_count, max_count)
			ab["color"] = kml_hex_color_from_value_range(ab["count"], min_count, max_count)

		print("rendering file...")

		kml_string = render_to_string("map/map_template.kml", dict(
			kml_map=self,
			area_bins=area_bins
		))

		self.kml_file.save("{0} {1}.kml".format(self.name, self.id), ContentFile(kml_string))
		
		return self.kml_file.path

	def __str__(self):
		return self.name

	def save(self, *args, **kwargs):
		now = timezone.now()
		self.created_time = self.created_time or timezone.now()
		self.updated_time = now
		return super().save(*args, **kwargs)


