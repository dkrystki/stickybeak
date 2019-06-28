
=============================================
Stickybeak - Life changing E2E tests solution
=============================================

Stickybeak is an end to end test library helper that saves lots of testing endpoints and boilerplate code.
Usually end to end testing is hard to debug when someting goes wrong, using this library debugging is easy and can save
hundreds of unit tests and integration tests.

How it works
------------
Stickybeak uses code injection to execute arbitrary python code on remote servers in local python script environment.
Code injection might sound scary but this solution is completely safe since code injection endpoints are only enabled
in testing or staging environment.
Results of executed code including all local variables, raised exceptions are pickled on remote server and sent back to
the testing script where are unpickled and available for further testing and debugging - just like the code was executed locally.
Pretty amazing huh:) ?
At the moment stickybeak supports Django and Flask frameworks.


Installation
------------
.. code-block:: console

    pip install stickybeak


Example usage
-------------

Django app (remote server)
##########################

.. code-block:: python

    from django.contrib import admin
    from django.urls import path
    from stickybeak.django_view import inject

    urlpatterns = [
        path('admin/', admin.site.urls),
        inject,
    ]


Flask app (remote server)
#########################
.. code-block:: python

    from flask import Flask
    from stickybeak.flask_view import inject

    app = Flask(__name__)
    app.register_blueprint(inject)


Testing app (local server)
##########################
.. code-block:: python

    def test_exception(self):
        injector = Injector(address='http://django-srv:8000')

        with pytest.raises(ZeroDivisionError):
            injector.run_code('1/0')

    def test_simple_code(self):
        injector = Injector(address='http://django-srv:8000')
        ret = injector.run_code('a = 123')
        assert ret['a'] == 123

    def test_function(self):
        injector = Injector(address='http://django-srv:8000')

        def fun():
            # this code executes on the remote server
            a = 5
            b = 3
            c = a + b

        ret = injector.run_fun(fun)
        assert ret['a'] == 5
        assert ret['b'] == 3
        assert ret['c'] == 8

    def test_using_decorators(self):
        injector = Injector(address='http://django-srv:8000')

        @injector.decorator
        def fun():
            # this code executes on the remote server
            a = 1
            b = 4

        ret = fun()

        assert ret['a'] == 1
        assert ret['b'] == 4

    def test_django_feature(self):
        injector = Injector(address='http://django-srv:8000')

        @injector.decorator
        def fun():
            # this code executes on the remote server
            from app.models import DjangoModel
            objects = DjangoModel.objects.all()
            object = DjangoModel.objects.all()[0]
            assert objects.count() == 2

        ret = fun()

        # using and magic the object is available locally as if we were running code on the remote server
        assert ret['object'].model_field == "test_value"
        # it is also available for debugger so it is possible to lookup all values and even run some class functions on it


Development
-----------
Stickybeak uses docker to create an isolated development environment so your system is not being polluted.

Requirements
############
In order to run local development you have to have Docker and Docker Compose installed.


Starting things up
##################
.. code-block:: console

    docker-compose up -d

Logging into the docker terminal
################################
.. code-block:: console

    ./bin/terminal

The code is synchronised between a docker container and the host using volumes so any changes ( ``pipenv install`` etc ) will be affected on the host.
