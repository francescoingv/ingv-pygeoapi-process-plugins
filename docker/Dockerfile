# Dockerfile
FROM geopython/pygeoapi:0.22.0

LABEL maintainer="francesco.martinelli@ingv.it"

###############################################################################
# ARG VALIDATION
###############################################################################

# ---------------------------------------------------------------------------
# pygeoapi: server
# ---------------------------------------------------------------------------
ARG SERVER_NAME
ARG SERVER_LOCATION

# ---------------------------------------------------------------------------
# pygeoapi: server.manager (PostgreSQL)
# ---------------------------------------------------------------------------
ARG PYGEOAPI_OUTPUT_DIR
ARG IP_ADDRESS_POSTGRES_SERVER
ARG PORT_POSTGRES_SERVER

# ---------------------------------------------------------------------------
# pygeoapi: resources common
# ---------------------------------------------------------------------------
ARG PYGEOAPI_BASE_PRIVATE_DIRECTORY

# ---------------------------------------------------------------------------
# pygeoapi: resources.solwcad
# ---------------------------------------------------------------------------
ARG SOLWCAD_URL_BASE
ARG SOLWCAD_SERVICE_ID

# ---------------------------------------------------------------------------
# resources:process conduit
# ---------------------------------------------------------------------------
ARG CONDUIT_URL_BASE
ARG CONDUIT_SERVICE_ID


RUN mkdir -p ${PYGEOAPI_BASE_PRIVATE_DIRECTORY}

###############################################################################
# Installazione plugin custom
###############################################################################
WORKDIR /ingv_plugin
COPY ./ingv_plugin ./
RUN python3 -m pip install --no-cache-dir --break-system-packages -e .

###############################################################################
# Configurazione pygeoapi
###############################################################################
WORKDIR /pygeoapi
COPY ./my.pygeoapi.config.yml ./local.config.yml

# Check configuration parameters:
RUN for v in \
  IP_ADDRESS_POSTGRES_SERVER \
  PORT_POSTGRES_SERVER \
  PYGEOAPI_OUTPUT_DIR \
  PYGEOAPI_BASE_PRIVATE_DIRECTORY \
  SOLWCAD_URL_BASE \
  SOLWCAD_SERVICE_ID \
  CONDUIT_URL_BASE \
  CONDUIT_SERVICE_ID \
  SERVER_NAME \
  SERVER_LOCATION \
; do \
  test -n "$(eval echo \$$v)" || (echo "$v not set: required build argument." && exit 1); \
done

# Substitute configuration parameters:
RUN sed -i 's/\$SERVER_NAME\$/'${SERVER_NAME}'/g'                                  ./local.config.yml \
    && sed -i 's/\$SERVER_LOCATION\$/'${SERVER_LOCATION}'/g'                   ./local.config.yml \
    && sed -i 's/\$IP_ADDRESS_POSTGRES_SERVER\$/'${IP_ADDRESS_POSTGRES_SERVER}'/g'           ./local.config.yml \
    && sed -i 's/\$PORT_POSTGRES_SERVER\$/'${PORT_POSTGRES_SERVER}'/g'                       ./local.config.yml \
    && sed -i 's#\$PYGEOAPI_OUTPUT_DIR\$#'${PYGEOAPI_OUTPUT_DIR}'#g'                         ./local.config.yml \
    && sed -i 's#\$PYGEOAPI_BASE_PRIVATE_DIRECTORY\$#'${PYGEOAPI_BASE_PRIVATE_DIRECTORY}'#g' ./local.config.yml \
    && sed -i 's#\$SOLWCAD_URL_BASE\$#'${SOLWCAD_URL_BASE}'#g'                               ./local.config.yml \
    && sed -i 's#\$SOLWCAD_SERVICE_ID\$#'${SOLWCAD_SERVICE_ID}'#g'                           ./local.config.yml \
    && sed -i 's#\$CONDUIT_URL_BASE\$#'${CONDUIT_URL_BASE}'#g'                               ./local.config.yml \
    && sed -i 's#\$CONDUIT_SERVICE_ID\$#'${CONDUIT_SERVICE_ID}'#g'                           ./local.config.yml


