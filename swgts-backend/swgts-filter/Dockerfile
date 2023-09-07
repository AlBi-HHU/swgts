# We build the backend first, then the frontend, and then install everything in a new container.
ARG PYTHON_IMAGE_TAG=3.11-slim

# Backend
FROM python:$PYTHON_IMAGE_TAG AS backend-builder

# We need to build minimap2's mappy from source, because the PyPI distribution is somehow broken.
# Therefore we need those dependencies. We then build wheels for everything so we can easily install
# it into a clean Dockerimage.
RUN apt-get update && \
    apt-get --no-install-recommends --yes install git gcc libc-dev zlib1g-dev

ADD swgts-backend/swgts-filter swgts-filter
RUN mkdir /dummy_git
ADD .git /dummy_git/.git
# This could also be moved to the requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir wheels \
        git+https://github.com/lh3/minimap2.git@v2.26 \
        ./swgts-filter

# Install our application, and its dependencies
RUN pip install wheels/*.whl && \
    rm -rf wheels

ENTRYPOINT ["python","swgts-filter/server/app.py"]
