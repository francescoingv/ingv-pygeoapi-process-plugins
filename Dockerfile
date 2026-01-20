# Dockerfile
FROM geopython/pygeoapi:latest

LABEL maintainer="francesco.martinelli@ingv.it"

###############################################################################
# ARG VALIDATION
###############################################################################

ARG IP_ADDRESS_POSTGRES_SERVER
ARG PORT_POSTGRES_SERVER
ARG PYGEOAPI_OUTPUT_DIR
ARG PYGEOAPI_BASE_PRIVATE_DIRECTORY
ARG SOLWCAD_URL_BASE
ARG SOLWCAD_SERVICE_ID
ARG CONDUIT_URL_BASE
ARG CONDUIT_SERVICE_ID
ARG SERVER_NAME_epos
ARG LOCATION_epos_pygeoapi

RUN test -n "$IP_ADDRESS_POSTGRES_SERVER" || (echo "IP_ADDRESS_POSTGRES_SERVER not set: required build argument." && false) \
    && test -n "$PORT_POSTGRES_SERVER" || (echo "PORT_POSTGRES_SERVER not set: required build argument." && false) \
    && test -n "$PYGEOAPI_OUTPUT_DIR" || (echo "PYGEOAPI_OUTPUT_DIR not set: required build argument." && false) \
    && test -n "$PYGEOAPI_BASE_PRIVATE_DIRECTORY" || (echo "PYGEOAPI_BASE_PRIVATE_DIRECTORY not set: required build argument." && false) \
    && test -n "$SOLWCAD_URL_BASE" || (echo "SOLWCAD_URL_BASE not set: required build argument." && false) \
    && test -n "$SOLWCAD_SERVICE_ID" || (echo "SOLWCAD_SERVICE_ID not set: required build argument." && false) \
    && test -n "$CONDUIT_URL_BASE" || (echo "CONDUIT_URL_BASE not set: required build argument." && false) \
    && test -n "$CONDUIT_SERVICE_ID" || (echo "CONDUIT_SERVICE_ID not set: required build argument." && false) \
    && test -n "$SERVER_NAME_epos" || (echo "SERVER_NAME_epos not set: required build argument." && false) \
    && test -n "$LOCATION_epos_pygeoapi" || (echo "LOCATION_epos_pygeoapi not set: required build argument." && false)

RUN mkdir -p ${PYGEOAPI_BASE_PRIVATE_DIRECTORY}

###############################################################################
# Installazione plugin custom
###############################################################################
WORKDIR /ingv_plugin
COPY ./ingv_plugin ./
# # La seguente istruzione va sostituita:
# a partire da Debian 12 (Bookworm) e Ubuntu 23.04+, Python 3.11/3.12 include PEP 668, che:
# -) "vieta pip install nel sistema"
# -) chiede di usare --break-system-packages o un virtualenv
# RUN python3 -m pip install --no-cache-dir -e . 
RUN python3 -m pip install --no-cache-dir --break-system-packages -e .


###############################################################################
# Configurazione pygeoapi
###############################################################################
WORKDIR /pygeoapi
COPY ./my.pygeoapi.config.yml ./local.config.yml

# Substitute configuration parameters:
RUN sed -i 's/\$SERVER_NAME_epos\$/'${SERVER_NAME_epos}'/g'                                  ./local.config.yml \
    && sed -i 's/\$LOCATION_epos_pygeoapi\$/'${LOCATION_epos_pygeoapi}'/g'                   ./local.config.yml \
    && sed -i 's/\$IP_ADDRESS_POSTGRES_SERVER\$/'${IP_ADDRESS_POSTGRES_SERVER}'/g'           ./local.config.yml \
    && sed -i 's/\$PORT_POSTGRES_SERVER\$/'${PORT_POSTGRES_SERVER}'/g'                       ./local.config.yml \
    && sed -i 's#\$PYGEOAPI_OUTPUT_DIR\$#'${PYGEOAPI_OUTPUT_DIR}'#g'                         ./local.config.yml \
    && sed -i 's#\$PYGEOAPI_BASE_PRIVATE_DIRECTORY\$#'${PYGEOAPI_BASE_PRIVATE_DIRECTORY}'#g' ./local.config.yml \
    && sed -i 's#\$SOLWCAD_URL_BASE\$#'${SOLWCAD_URL_BASE}'#g'                               ./local.config.yml \
    && sed -i 's#\$SOLWCAD_SERVICE_ID\$#'${SOLWCAD_SERVICE_ID}'#g'                           ./local.config.yml \
    && sed -i 's#\$CONDUIT_URL_BASE\$#'${CONDUIT_URL_BASE}'#g'                               ./local.config.yml \
    && sed -i 's#\$CONDUIT_SERVICE_ID\$#'${CONDUIT_SERVICE_ID}'#g'                           ./local.config.yml


