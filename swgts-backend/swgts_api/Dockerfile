# We build the backend first, then the frontend, and then install everything in a new container.

ARG PYTHON_IMAGE_TAG=3.12-slim

# Backend
FROM python:$PYTHON_IMAGE_TAG AS backend-builder

# We need to build minimap2's mappy from source, because the PyPI distribution is somehow broken.
# Therefore we need those dependencies. We then build wheels for everything so we can easily install
# it into a clean Dockerimage.
RUN apt-get update && \
    apt-get --no-install-recommends --yes install git gcc libc-dev zlib1g-dev

ADD swgts-backend/swgts_api backend
RUN mkdir /dummy_git
ADD .git /dummy_git/.git
# This could also be moved to the requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir wheels \
        ./backend

# We now have all built, so we can put everything together
FROM python:$PYTHON_IMAGE_TAG

# mod_wsgi from pip. We need apache2-dev to install the module automatically
RUN apt-get update && \
    apt-get --yes --no-install-recommends install apache2 apache2-dev nano curl iproute2 && \
    pip install mod_wsgi && \
    mod_wsgi-express install-module > /etc/apache2/mods-available/wsgi.load && \
    a2enmod wsgi && \
    apt-get --yes --purge autoremove apache2-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists && \
    a2dissite "*"

# Copy artifacts from backend stage
COPY --from=backend-builder wheels wheels

# Enable our site in apache
ADD swgts-backend/swgts_api/docker/apache-site.conf /etc/apache2/sites-available/swgts.conf
RUN a2enmod http2 && \
    a2ensite swgts

# Install our application, and its dependencies
RUN pip install wheels/*.whl && \
    rm -rf wheels

# Create important directories
RUN mkdir -p /output /input /var/www/swgts

# Add the wsgi application file
ADD swgts-backend/swgts_api/docker/api.wsgi /var/www/swgts/api.wsgi

# Ensure the rights are correctly set
RUN chown -R www-data:www-data /var/www/swgts /output && \
    chmod -R a-w /var/www/swgts

# https://httpd.apache.org/docs/2.4/stopping.html#gracefulstop
STOPSIGNAL SIGWINCH

# Create important directories
RUN mkdir -p /output /input

#add entrypoint
ADD swgts-backend/swgts_api/docker/entrypoint.sh /entrypoint.sh

EXPOSE 80
CMD ["/bin/sh","/entrypoint.sh"]
