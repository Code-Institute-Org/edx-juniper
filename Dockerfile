FROM docker.io/ubuntu:16.04
MAINTAINER CodeInstitute <platform@codeinstitute.net>

############ common to lms & cms

# Install system requirements
RUN apt update && \
    # Global requirements
    apt install -y language-pack-en git build-essential software-properties-common curl git-core libmysqlclient-dev libxml2-dev libxslt1-dev python-apt python-dev libxmlsec1-dev libfreetype6-dev swig gcc g++ \
    # openedx requirements
    vim iputils-ping dnsutils telnet \
    gettext gfortran graphviz graphviz-dev libffi-dev libfreetype6-dev libgeos-dev libjpeg8-dev liblapack-dev libpng12-dev libsqlite3-dev libxml2-dev libxmlsec1-dev libxslt1-dev lynx nodejs npm ntp pkg-config \
    libbz2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /openedx/edx-platform

# Install python with pyenv
ARG PYTHON_VERSION=3.5.9
ENV PYENV_ROOT /opt/pyenv
RUN git clone https://github.com/pyenv/pyenv $PYENV_ROOT --branch v1.2.18 --depth 1 \
    && $PYENV_ROOT/bin/pyenv install $PYTHON_VERSION

# Copying requirements and specific submodules included in requirements
COPY ./requirements/ /openedx/edx-platform/requirements
COPY ./common/lib/ /openedx/edx-platform/common/lib/

ENV PATH /opt/pyenv/versions/3.5.9/bin:${PATH}
RUN pip install setuptools==39.0.1 pip==9.0.3

# Install patched version of ora2
RUN pip install https://github.com/overhangio/edx-ora2/archive/overhangio/boto2to3.zip

# Install ironwood-compatible scorm xblock
RUN pip install "openedx-scorm-xblock<11.0.0,>=10.0.0"

# Install updated version of edxval
COPY ./edx-val/ /openedx/edx-val/
RUN cd /openedx/edx-val && python3 setup.py install

# Install development libraries
RUN pip install -r requirements/edx/ci-dev.txt

# Using local version
COPY ./lms/ /openedx/edx-platform/lms
COPY ./cms/ /openedx/edx-platform/cms

# Copying common subdirs separately as the common/lib dir was alreaedy copied / installed above
COPY ./common/djangoapps/ /openedx/edx-platform/common/djangoapps/
COPY ./common/static/ /openedx/edx-platform/common/static/
COPY ./common/templates/ /openedx/edx-platform/common/templates/
COPY ./common/test/ /openedx/edx-platform/common/test/
COPY ./common/__init__.py /openedx/edx-platform/common/__init__.py

COPY ./conf/ /openedx/edx-platform/conf
COPY ./docs/ /openedx/edx-platform/docs
COPY ./openedx/ /openedx/edx-platform/openedx
COPY ./pavelib/ /openedx/edx-platform/pavelib
COPY ./scripts/ /openedx/edx-platform/scripts
COPY ./vendor_extra/ /openedx/edx-platform/vendor_extra
COPY ./webpack-config/ /openedx/edx-platform/webpack-config
COPY ./themes/ /openedx/edx-platform/themes
COPY ./test_root/ /openedx/edx-platform/test_root
COPY ./.tx/ /openedx/edx-platform/.tx
COPY ./*.js /openedx/edx-platform/
COPY ./*.py /openedx/edx-platform/
COPY ./*.json /openedx/edx-platform/
#COPY ./* /openedx/edx-platform/
COPY ./openedx.yaml /openedx/edx-platform/
COPY ./codecov.yml /openedx/edx-platform/
COPY ./circle.yml /openedx/edx-platform/
COPY ./setup.cfg ./setup.py /openedx/edx-platform/
# COPY ./setup.py /openedx/edx-platform/
COPY ./.babelrc /openedx/edx-platform/
COPY ./.coveragerc /openedx/edx-platform/
COPY ./.editorconfig /openedx/edx-platform/
COPY ./.eslintignore /openedx/edx-platform/
COPY ./.gitattributes /openedx/edx-platform/
COPY ./.gitignore /openedx/edx-platform/
COPY ./.npmrc /openedx/edx-platform/
COPY ./.stylelintignore /openedx/edx-platform/
COPY ./Makefile /openedx/edx-platform/
COPY ./pylintrc /openedx/edx-platform/
COPY ./pylintrc_tweaks /openedx/edx-platform/
COPY ./tox.ini /openedx/edx-platform/

# adding config in as defaults
COPY ./config /openedx/config

# Install edx local
RUN pip install setuptools_scm==5.0.2
RUN pip install -r requirements/edx/base.txt
RUN pip install -r requirements/constraints.txt


# Adding this to allow staticfile access from debug server
RUN ln -s /openedx/staticfiles /openedx/static


# Install a recent version of nodejs
RUN nodeenv /openedx/nodeenv --node=12.13.0 --prebuilt
ENV PATH /openedx/nodeenv/bin:${PATH}

# Install nodejs requirements
ARG NPM_REGISTRY=https://registry.npmjs.org/
RUN npm set progress=false \
    && npm install --verbose --registry=$NPM_REGISTRY
ENV PATH ./node_modules/.bin:${PATH}

# Create folder that will store *.env.json and *.auth.json files
RUN mkdir -p /openedx/config
ENV CONFIG_ROOT /openedx/config

# Copy user-specific locales to /openedx/locale/user/locale and compile them
RUN mkdir -p /openedx/locale/user
COPY ./locale/ /openedx/locale/user/locale/
RUN cd /openedx/locale/user && \
    django-admin.py compilemessages -v1
# Compile i18n strings: in Ironwood, js locales are not properly compiled out of the box
# and we need to do a pass ourselves. Also, we need to compile the djangojs.js files for
# the downloaded locales.
RUN ./manage.py lms --settings=i18n compilejsi18n
RUN ./manage.py cms --settings=i18n compilejsi18n

# Copy scripts
COPY ./bin /openedx/bin
RUN chmod a+x /openedx/bin/*
ENV PATH /openedx/bin:${PATH}



# Collect production assets. By default, only assets from the default theme
# will be processed. This makes the docker image lighter and faster to build.
# Only the custom themes added to /openedx/themes will be compiled.
# Here, we don't run "paver update_assets" which is slow, compiles all themes
# and requires a complex settings file. Instead, we decompose the commands
# and run each one individually to collect the production static assets to
# /openedx/staticfiles.
ENV NO_PYTHON_UNINSTALL 1
RUN openedx-assets xmodule \
    && openedx-assets npm \
    && openedx-assets webpack --env=prod \
    && openedx-assets common
COPY ./themes/ /openedx/themes/
RUN openedx-assets themes \
    && openedx-assets collect --settings=assets

# Create a data directory, which might be used (or not)
RUN mkdir /openedx/data

# service variant is "lms" or "cms"
ENV SERVICE_VARIANT lms
ENV SETTINGS production
ENV LMS_CFG /openedx/config/lms.env.json
ENV STUDIO_CFG /openedx/config/cms.env.json

# Copy new entrypoint (to take care of permission issues at runtime)
COPY ./bin /openedx/bin
RUN chmod a+x /openedx/bin/*

# Configure new user
#ARG USERID=1000
#RUN create-user.sh $USERID

# Default django settings

# Entrypoint will set right environment variables
ENTRYPOINT ["docker-entrypoint.sh"]

# Run server
COPY gunicorn_conf.py /openedx/gunicorn_conf.py
COPY lms/uwsgi.ini /openedx/edx-platform
COPY cms/uwsgi.ini /openedx/edx-platform

EXPOSE 8000
CMD gunicorn -c /openedx/gunicorn_conf.py --name ${SERVICE_VARIANT} --bind=0.0.0.0:8000 --max-requests=1000 --access-logfile - ${SERVICE_VARIANT}.wsgi:application
