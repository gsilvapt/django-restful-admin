from django.admin import ModelAdmin
from django.db.models.base import ModelBase
from rest_framework import viewsets
from rest_framework.exceptions import Forbidden
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework.serializers import ModelSerializer


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class ImproperlyConfigured(Exception):
    pass


class RestFulModelAdmin(viewsets.ModelViewSet):
    queryset = None

    @staticmethod
    def get_doc():
        return 'asd'

    def list(self, request, *args, **kwargs):
        """list all of objects"""
        if has_view_permission(request):
            queryset = self.filter_queryset(self.get_queryset())

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        else:
            raise Forbidden

    def create(self, request, **kwargs):
        """Create new object"""
        if has_add_permission(request):
            return super().create(request, **kwargs)
        else:
            raise Forbidden

    def retrieve(self, request, pk=None, **kwargs):
        """Get object Details"""
        if has_view_permission(request):
            return super().retrieve(request, pk=pk, **kwargs)
        else:
            raise Forbidden

    def update(self, request, pk=None, **kwargs):
        """Update object"""
        if has_change_permission(request):
            return super().update(request, pk=pk, **kwargs)
        else:
            raise Forbidden

    def partial_update(self, request, pk=None, **kwargs):
        """Partial Update"""
        if has_change_permission(request):
            return super().partial_update(request, pk=pk, **kwargs)
        else:
            raise Forbidden

    def destroy(self, request, pk=None, **kwargs):
        """Delete object"""
        if has_delete_permission(request):
            return super().destroy(request, pk=pk, **kwargs)
        else:
            raise Forbidden


class BaseModelSerializer(ModelSerializer):
    class Meta:
        pass


class RestFulAdminSite:
    def __init__(self):
        self._registry = {}
        self._url_patterns = []

    def register(self, model_or_iterable, view_class=None, **options):
        if not view_class:
            view_class = RestFulModelAdmin

        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model._meta.abstract:
                raise ImproperlyConfigured(
                    'The model %s is abstract, so it cannot be registered with admin.' % model.__name__
                )

            if model in self._registry:
                raise AlreadyRegistered('The model %s is already registered' % model.__name__)
            options.update({
                "__doc__": self.generate_docs(model)
            })
            view_class = type("%sAdmin" % model.__name__, (view_class,), options)
            # self.set_docs(view_class, model)
            # Instantiate the admin class to save in the registry
            self._registry[model] = view_class

    def register_url_pattern(self, url_pattern):
        self._url_patterns.append(url_pattern)

    @classmethod
    def generate_docs(cls, model):
        return """
    ### The APIs include:


    > `GET`  {app}/{model} ===> list all `{verbose_name_plural}` page by page;

    > `POST`  {app}/{model} ===> create a new `{verbose_name}`

    > `GET` {app}/{model}/123 ===> return the details of the `{verbose_name}` 123

    > `PATCH` {app}/{model}/123 and `PUT` {app}/{model}/123 ==> update the `{verbose_name}` 123

    > `DELETE` {app}/{model}/123 ===> delete the `{verbose_name}` 123

    > `OPTIONS` {app}/{model} ===> show the supported verbs regarding endpoint `{app}/{model}`

    > `OPTIONS` {app}/{model}/123 ===> show the supported verbs regarding endpoint `{app}/{model}/123`

            """.format(
            app=model._meta.app_label,
            model=model._meta.model_name,
            verbose_name=model._meta.verbose_name,
            verbose_name_plural=model._meta.verbose_name_plural
        )

    def unregister(self, model_or_iterable):
        """
        Unregister the given model(s).

        If a model isn't already registered, raise NotRegistered.
        """
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model not in self._registry:
                raise NotRegistered('The model %s is not registered' % model.__name__)
            del self._registry[model]

    def is_registered(self, model):
        """
        Check if a model class is registered with this `AdminSite`.
        """
        return model in self._registry

    def get_urls(self):
        router = DefaultRouter()
        view_sets = []
        for model, view_set in self._registry.items():
            if view_set.queryset is None:
                view_set.queryset = model.objects.all()
            if view_set.serializer_class is None:
                serializer_class = type("%sModelSerializer" % model.__name__, (ModelSerializer,), {
                    "Meta": type("Meta", (object,), {
                        "model": model,
                        "fields": "__all__"
                    }),
                })
                view_set.serializer_class = serializer_class

            view_sets.append(view_set)
            router.register('%s/%s' % (model._meta.app_label, model._meta.model_name), view_set)

        return router.urls + self._url_patterns

    @property
    def urls(self):
        return self.get_urls(), 'django_restful_admin', 'django_restful_admin'


def has_add_permission(request):
    """
    Return True if the given request has permission to add an object.
    Can be overridden by the user in subclasses.
    """
    opts = self.opts
    codename = get_permission_codename('add', opts)
    return request.user.has_perm("%s.%s" % (opts.app_label, codename))

def has_change_permission(request, obj=None):
    """
    Return True if the given request has permission to change the given
    Django model instance, the default implementation doesn't examine the
    `obj` parameter.
    Can be overridden by the user in subclasses. In such case it should
    return True if the given request has permission to change the `obj`
    model instance. If `obj` is None, this should return True if the given
    request has permission to change *any* object of the given type.
    """
    opts = self.opts
    codename = get_permission_codename('change', opts)
    return request.user.has_perm("%s.%s" % (opts.app_label, codename))

def has_delete_permission(request, obj=None):
    """
    Return True if the given request has permission to change the given
    Django model instance, the default implementation doesn't examine the
    `obj` parameter.
    Can be overridden by the user in subclasses. In such case it should
    return True if the given request has permission to delete the `obj`
    model instance. If `obj` is None, this should return True if the given
    request has permission to delete *any* object of the given type.
    """
    opts = self.opts
    codename = get_permission_codename('delete', opts)
    return request.user.has_perm("%s.%s" % (opts.app_label, codename))

def has_view_permission(request, obj=None):
    """
    Return True if the given request has permission to view the given
    Django model instance. The default implementation doesn't examine the
    `obj` parameter.
    If overridden by the user in subclasses, it should return True if the
    given request has permission to view the `obj` model instance. If `obj`
    is None, it should return True if the request has permission to view
    any object of the given type.
    """
    opts = self.opts
    codename_view = get_permission_codename('view', opts)
    codename_change = get_permission_codename('change', opts)
    return (
        request.user.has_perm('%s.%s' % (opts.app_label, codename_view)) or
        request.user.has_perm('%s.%s' % (opts.app_label, codename_change))
    )


site = RestFulAdminSite()
