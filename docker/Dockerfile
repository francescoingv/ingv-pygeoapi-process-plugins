# ------------------------------------------------------------------------------
# EPOS - pygeoapi container
#
# This image:
# - installs a custom INGv pygeoapi plugin
# - generates pygeoapi configuration at BUILD TIME
# - binds EPOS processes (solwcad, conduit) via internal HTTP
#
# IMPORTANT:
# - All configuration is resolved during image build
# - No runtime environment variables are expected
# ------------------------------------------------------------------------------

FROM geopython/pygeoapi:0.22.0

LABEL maintainer="francesco.martinelli@ingv.it"

# ------------------------------------------------------------------------------
# BUILD-TIME ARGUMENTS
# ------------------------------------------------------------------------------

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
# pygeoapi: process.solwcad
# ---------------------------------------------------------------------------
ARG SOLWCAD_URL_BASE
ARG SOLWCAD_SERVICE_ID

# ---------------------------------------------------------------------------
# pygeoapi: process.conduit
# ---------------------------------------------------------------------------
ARG CONDUIT_URL_BASE
ARG CONDUIT_SERVICE_ID

# ---------------------------------------------------------------------------
# pygeoapi: process.pybox
# ---------------------------------------------------------------------------
ARG PYBOX_URL_BASE
ARG PYBOX_SERVICE_ID


# ==============================================================================
# ARG VALIDATION
# ==============================================================================
RUN for v in \
  SERVER_NAME \
  SERVER_LOCATION \
  IP_ADDRESS_POSTGRES_SERVER \
  PORT_POSTGRES_SERVER \
  PYGEOAPI_OUTPUT_DIR \
  PYGEOAPI_BASE_PRIVATE_DIRECTORY \
  SOLWCAD_URL_BASE \
  SOLWCAD_SERVICE_ID \
  CONDUIT_URL_BASE \
  CONDUIT_SERVICE_ID \
  PYBOX_URL_BASE \
  PYBOX_SERVICE_ID \
; do \
  test -n "$(eval echo \$$v)" || (echo "<<ERROR>> Required build argument '$v' not set." && exit 1); \
done

# ==============================================================================
# Filesystem preparation
# Private directory used by pygeoapi processes for temporary and output data
# ==============================================================================
RUN mkdir -p "${PYGEOAPI_BASE_PRIVATE_DIRECTORY}"


# ==============================================================================
# Installazione plugin custom INGV
# ==============================================================================
WORKDIR /ingv_plugin
COPY ./ingv_plugin ./
RUN python3 -m pip install --no-cache-dir --break-system-packages -e .

# ==============================================================================
# pygeoapi configuration
# ==============================================================================
WORKDIR /pygeoapi
COPY ./my.pygeoapi.config.yml ./local.config.yml


# Substitute configuration parameters:
RUN sed -i 's|\$SERVER_NAME\$|'${SERVER_NAME}'|g'                                  ./local.config.yml \
 && sed -i 's|\$SERVER_LOCATION\$|'${SERVER_LOCATION}'|g'                   ./local.config.yml \
 && sed -i 's|\$IP_ADDRESS_POSTGRES_SERVER\$|'${IP_ADDRESS_POSTGRES_SERVER}'|g'           ./local.config.yml \
 && sed -i 's|\$PORT_POSTGRES_SERVER\$|'${PORT_POSTGRES_SERVER}'|g'                       ./local.config.yml \
 && sed -i 's|\$PYGEOAPI_OUTPUT_DIR\$|'${PYGEOAPI_OUTPUT_DIR}'|g'                         ./local.config.yml \
 && sed -i 's|\$PYGEOAPI_BASE_PRIVATE_DIRECTORY\$|'${PYGEOAPI_BASE_PRIVATE_DIRECTORY}'|g' ./local.config.yml \
 && sed -i 's|\$SOLWCAD_URL_BASE\$|'${SOLWCAD_URL_BASE}'|g'                               ./local.config.yml \
 && sed -i 's|\$SOLWCAD_SERVICE_ID\$|'${SOLWCAD_SERVICE_ID}'|g'                           ./local.config.yml \
 && sed -i 's|\$CONDUIT_URL_BASE\$|'${CONDUIT_URL_BASE}'|g'                               ./local.config.yml \
 && sed -i 's#\$CONDUIT_SERVICE_ID\$#'${CONDUIT_SERVICE_ID}'#g'                           ./local.config.yml \
 && sed -i 's#\$PYBOX_URL_BASE\$#'${PYBOX_URL_BASE}'#g'                                   ./local.config.yml \
 && sed -i 's#\$PYBOX_SERVICE_ID\$#'${PYBOX_SERVICE_ID}'#g'                               ./local.config.yml


