################################################################################
### Builder Image
################################################################################

# use a databricks runtime base image: https://hub.docker.com/u/databricksruntime, https://docs.databricks.com/clusters/custom-containers.html
FROM databricksruntime/standard:latest as builder
LABEL maintainer="rashad <rashad.moarref@gmail.com>"

ENV PATH $PATH:/databricks/conda/envs/dcs-minimal/bin:/venv-test/bin

# copy files needed to install requirements
COPY deploy/pip.config /etc/pip.conf
COPY requirements.txt /requirements.txt
COPY setup.py /setup.py

# copy app source
COPY app/  /app

# install app requirements
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++
ENV PYTHONUSERBASE /databricks/conda/envs/dcs-minimal/
RUN pip install --upgrade pip && \
    pip install --ignore-installed --no-warn-script-location --user -U cryptography certifi idna ndg-httpsclient pyasn1 && \
    pip install --ignore-installed --no-warn-script-location --user -e .

# download spacy model
RUN /databricks/conda/envs/dcs-minimal/bin/python -m spacy download en_core_web_sm

# # test the service before building the container
COPY . /src
ENV PYTHONUSERBASE /venv-test
RUN mkdir /venv-test && \
    pip install --ignore-installed --user -U tox pytest
RUN cd /src && tox

################################################################################
### Runner Image
################################################################################

# use a databricks runtime base image: https://hub.docker.com/u/databricksruntime, https://docs.databricks.com/clusters/custom-containers.html
FROM databricksruntime/standard:latest as runner
LABEL maintainer="rashad <rashad.moarref@gmail.com>"

# BUILD_TARGET to be set at build time: local | databricks
ARG BUILD_TARGET

# setup dependencies
COPY --from=builder /databricks/conda/envs/dcs-minimal/lib/python3.7/site-packages/ /databricks/conda/envs/dcs-minimal/lib/python3.7/site-packages/

# download spacy model
RUN /databricks/conda/envs/dcs-minimal/bin/python -m spacy download en_core_web_sm

# setup the app
ENV TZ=America/Los_Angeles
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
COPY app/  /app

# The databricks container service loads spark into container at runtime
# For local environment, install spark and its dependencies
# For databricks environment, uninstall pyspark

RUN if [ "$BUILD_TARGET" = "local" ] ; then \
        apt-get update && \
        apt-get install -y --no-install-recommends vim wget default-jdk scala && \
        wget https://downloads.apache.org/spark/spark-3.0.2/spark-3.0.2-bin-hadoop2.7.tgz && \
        tar xvf spark-3.0.2-bin-hadoop2.7.tgz && \
        mv spark-3.0.2-bin-hadoop2.7 /opt/spark ; \
    else \
        export PYTHONPATH=/databricks/conda/envs/dcs-minimal/lib/python3.7/site-packages/ && \
        /databricks/conda/bin/pip uninstall -y pyspark ; \
    fi
