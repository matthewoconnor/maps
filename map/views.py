from django.views.generic import View, FormView
from django.http import JsonResponse

from .models import DataMap, AreaMap
from .utils import start_datamap_import_task
from .tasks import poll_task_progress
from .forms import KmlmapForm, DataMapImportSettingsForm


# NEW DATAMAP CREATE VIEWS
class DataMapCreateView(FormView):
    """
    View to create new datamap with basic-info settings
    """
    template_name = "map/app/kmlmap-form.html"
    form_class = KmlmapForm

    def form_valid(self, form):
        datamap = form.save()
        response_context = dict(success=True, datamap_id=datamap.id)
        return JsonResponse(response_context)

    def form_invalid(self, form):
        response_context = dict(success=False, messages=form.errors)
        return JsonResponse(response_context)


def DataMapUpdateView(DataMapCreateView):

    def setup(self):
        self.datamap = self.kwargs.get("datamap_id")
        return super()

    def get(self, request, *args, **kwargs):
        self.setup()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.setup()
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs["instance"] = self.datamap
        return form_kwargs


class DataMapImportSettingsView(FormView):
    template_name = ""
    form_class = DataMapImportSettingsForm

    def setup(self):
        datamap_id = self.kwargs.get("datamap_id")
        self.datamap = DataMap.objects.get(id=datamap_id)

    def get(self, request, *args, **kwargs):
        self.setup()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.setup()
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super().get_form_kwargs(*args, **kwargs)
        form_kwargs["instance"] = self.datamap
        return form_kwargs

    def form_valid(self, form):
        datamap = form.save()
        task_ids = start_datamap_import_task(datamap)
        response_context = dict(success=True, datamap_id=datamap.id, task_ids=task_ids)
        return JsonResponse(response_context)

    def form_invalid(self, form):
        response_context = dict(success=False, messages=form.errors)
        return JsonResponse(response_context)


class DataMapListJson(View):

    def get(self, request, *args, **kwargs):
        filter_ids = request.GET.get("ids", None)
        if filter_ids:
            filter_id_list = filter_ids.split(",")
            datamaps = DataMap.objects.filter(id__in=filter_id_list)
        else:
            datamaps = DataMap.objects.all()
        context = dict(
            datamaps=[dict(id=dm.id, name=dm.name, source=dm.get_file_url()) for dm in datamaps]
        )
        return JsonResponse( context )


class TaskProgressView(View):

    def get(self, request, *args, **kwargs):
        task_ids = request.GET.get("task_ids", None)
        task_id_list = task_ids.split(",") if task_ids else []
        context = poll_task_progress(task_id_list)
        return JsonResponse(context)


class KmlAreaMapAutocomplete(View):

    def get(self, request, *args, **kwargs):
        query = request.GET.get("query", None)
        if query:
            results = AreaMap.objects.filter(name__icontains=query).order_by("name").values("id", "name")
        else:
            results = []
        context = dict(success=True, results=list(results), query=query)
        return JsonResponse( context )


class SocrataDatamapMetadata(View):

    def get(self, request, *args, **kwargs):
        datamap_id = kwargs.get("datamap_id")
        datamap = DataMap.objects.get(id=datamap_id)
        metadata = datamap.get_socrata_client().get_metadata(datamap.dataset_identifier)
        return JsonResponse(metadata)


class DataMapGeometry(View):

    def get(self, request, *args, **kwargs):
        datamap = DataMap.objects.prefetch_related(
            "areabin_set__area"
        ).get(id=kwargs.get("datamap_id"))

        geometry = [ab.get_geometry() for ab in datamap.areabin_set.all()]

        datamap_json = {
            "id": datamap.id,
            "name": datamap.name,
            "geometry": geometry,
            "max_count": max(ab["count"] for ab in geometry),
            "min_count": min(ab["count"] for ab in geometry)
        }

        context = dict(success=True, data=datamap_json)

        return JsonResponse(context)
