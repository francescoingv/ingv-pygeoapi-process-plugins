# =================================================================
#
# Authors: Francesco Martinelli <francesco.martinelli@ingv.it>
#
# Copyright (c) 2024 Francesco Martinelli
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================

import json
import logging
import re
import copy
import base64
import shutil
import uuid

from pathlib import Path

from pygeoapi.process.base import (
    ProcessorExecuteError,
    ProcessorGenericError,
)
from expose_plugins.process.base_remote_execution import (
    BaseRemoteExecutionProcessorLocalReference,
    CHART_SCHEMA,
)

LOGGER = logging.getLogger(__name__)

INPUT_SCHEMA = {
  '$schema': 'https://json-schema.org/draft/2020-12/schema',
  '$id': 'https://example.com/schemas/pybox_plugin_schema.json',
  'title': 'PyBox Input Schema',
  'description': 'Schema for PyBox plugin inputs',
  'type': 'object',
  'required': ['lat', 'lon', 'l0', 'h0', 'theta0', 'multiple_values',
               'dt', 'margin'],
  'additionalProperties': False,
  'properties': {
    'lat': {
      'title': 'Latitude',
      'description': 'Geographic latitude of the vent in Decimal degrees',
      'type': 'number',
      'minimum': -90.0,
      'maximum': 90.0
    },
    'lon': {
      'title': 'Longitude',
      'description': 'Geographic longitude of the vent in Decimal degrees',
      'type': 'number',
      'minimum': -180.0,
      'maximum': 180.0
    },
    'l0': {
      'title': 'Initial Radius',
      'description': 'Initial horizontal extent (l0) of the current in meters',
      'type': 'number',
      'minimum': 100.0,
      'maximum': 2000.0
    },
    'h0': {
      'title': 'Initial height',
      'description': 'Initial vertical thickness (h0) of the current in meters',
      'type': 'number',
      'minimum': 100.0,
      'maximum': 2000.0
    },
    'theta0': {
      'title': 'Temperature',
      'description': 'Initial temperature of the current in Kelvin',
      'type': 'number',
      'minimum': 300.0,
      'maximum': 1400.0
    },
    'multiple_values': {
      'title': 'Multiple particle classes',
      'description': (
        'When simulating multiple particle classes, the volume fraction '
        '(eps0), density (rhos), and diameter (ds) of each class should be '
        'specified and the sum of eps0 must be < 1'
      ),
      'type': 'array',
      'minItems': 1,
      'maxItems': 21,
      'items': {
        'type': 'object',
        'required': ['eps0', 'rhos', 'ds'],
        'additionalProperties': False,
        'properties': {
          'eps0': {
            'title': 'Particle volume fraction',
            'description': 'Volume fraction of particle class',
            'type': 'number',
            'minimum': 0.001,
            'maximum': 0.1
          },
          'rhos': {
            'title': 'Particle density',
            'description': 'Density of particle class in kg/m3',
            'type': 'number',
            'minimum': 500.0,
            'maximum': 3500.0
          },
          'ds': {
            'title': 'Particle diameter',
            'description':
              'Diameter of particle class (10 micron-5 mm) in meters',
            'type': 'number',
            'minimum': 0.00001,
            'maximum': 0.005
          }
        }
      }
    },
    'dt': {
      'title': 'Time step',
      'description':
        'Temporal resolution of the numerical integration in seconds',
      'type': 'number',
      'minimum': 0.1,
      'maximum': 30.0
    },
    'margin': {
      'title': 'Margin',
      'description': (
          '-x, -y, x, y distance from the given vent location '
          '(i.e. bounding box of the requested DSM) in meters'
      ),
      'type': 'number',
      'minimum': 5000,
      'maximum': 50000
    }
  }
}

#: Process metadata and description
PROCESS_METADATA = {
  '$defs': {
    'chart': CHART_SCHEMA
  },    

  # process.yaml -> processSummary.yaml
  # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

  # Required properties:
  # ####################

  'id': 'pybox',
  # type string

  'version': '1.0.0',
  # type string

  # optional properties:
  # ####################

  'jobControlOptions': [
      'async-execute'
  ],
  # type: array,
  #   items: {type: string, enum: ['sync-execute', 'async-execute', 'dismiss']}
    
  'outputTransmission': [
      'value',
      'reference'
  ],
  # type: array, 
  #   items: {type: string, enum: ['value', 'reference'], default: 'value'}

  'links': [
    {
    'href': 'https://civ.pi.ingv.it/project/pybox-2/',
    'rel': 'related',
    'type': 'text/html',
    'title': 'CIV repository'
    },
    {
    'href': 'https://doi.org/10.5281/zenodo.2616551',
    'rel': 'describedby',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'PyBox: a Python tool for simulating the kinematics of Pyroclastic '
        'density currents with the box-model approach, Reference and User\'s Guide'
    },
    {
    'href': 'http://dx.doi.org/10.1016/j.jvolgeores.2016.08.002',
    'rel': 'describedby',
    'type': 'text/html',
    'hreflang': 'en-US',
    'title': 'A fast, calibrated model for pyroclastic density currents kinematics and hazard'
    },
    {
    'href': 'https://doi.org/10.5281/zenodo.18920969',
    'rel': 'cite-as',
    'type': 'text/html',
    'title': 'PyBOX-Web release on Zenodo (DOI: 10.5281/zenodo.18920969)'
    },
    {
    'href': 'https://github.com/silviagians/PyBOX-Web',
    'rel': 'source',
    'type': 'text/html',
    'title': 'PyBOX-Web source code repository on GitHub'
    }
  ],
  # type: array, 
  #   items: {type: object, required: 'href', properties:
  #       href: type: string, rel: type: string,
  #       type: type: string, hreflang: type: string,
  #       title: type: string }

  # process.yaml -> processSummary.yaml -> descriptionType.yaml
  # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

  # Optional properties:
  # ####################

  'title': 'PYBOX',
  # type: string

  'description':
    'Python code to simulate the dispersals of a gravity-driven '
    'pyroclastic density current (PDC) using a box model physical '
    'description. It produces a 2D invasion area adopting the '
    'energy conoid approach and using a Digital Surface Model '
    '(DSM) as topography. '
    'Note: the script supports multiple particle classes.',
  # type: string
    
  'keywords': ['Python code', 'Box model', 'Pyroclastic density currents',
               'Invasion maps', 'Hazard assessment'],
  # type: array
  #   items: type: string

  'metadata': [
    {
      'title': 'Source repository',
      'role': 'repository',
      'href': 'https://github.com/silviagians/PyBOX-Web'
    },
    {
      'title': 'Silvia Giansante',
      'role': 'author',
      'href': 'https://orcid.org/0009-0008-2803-0873'
    },
  ],
  # 'metadata':
  # type: array
  #   items: {type: object, title: string, role: string, href: string}

  # additionalParameters (metadata.yaml + parameters [additionalParameter.yaml]) 


  # process.yaml
  # >>>>>>>>>>>>
  'inputs': {
    # inputDescription.yaml
    'lat': {
      'title': INPUT_SCHEMA['properties']['lat']['title'],
      'description': INPUT_SCHEMA['properties']['lat']['description'],
      'schema': INPUT_SCHEMA['properties']['lat'],
      'minOccurs': 1,
      'maxOccurs': 1
    },
    'lon': {
      'title': INPUT_SCHEMA['properties']['lon']['title'],
      'description': INPUT_SCHEMA['properties']['lon']['description'],
      'schema': INPUT_SCHEMA['properties']['lon'],
      'minOccurs': 1,
      'maxOccurs': 1
    },
    'l0': {
      'title': INPUT_SCHEMA['properties']['l0']['title'],
      'description': INPUT_SCHEMA['properties']['l0']['description'],
      'schema': INPUT_SCHEMA['properties']['l0'],
      'minOccurs': 1,
      'maxOccurs': 1
    },
    'h0': {
      'title': INPUT_SCHEMA['properties']['h0']['title'],
      'description': INPUT_SCHEMA['properties']['h0']['description'],
      'schema': INPUT_SCHEMA['properties']['h0'],
      'minOccurs': 1,
      'maxOccurs': 1
    },
    'theta0': {
      'title': INPUT_SCHEMA['properties']['theta0']['title'],
      'description': INPUT_SCHEMA['properties']['theta0']['description'],
      'schema': INPUT_SCHEMA['properties']['theta0'],
      'minOccurs': 1,
      'maxOccurs': 1
    },
    'multiple_values': {
      'title': INPUT_SCHEMA['properties']['multiple_values']['title'],
      'description': 
        INPUT_SCHEMA['properties']['multiple_values']['description'],
      'schema': INPUT_SCHEMA['properties']['multiple_values'],
      'minOccurs': 1,
      'maxOccurs': 1
    },
    'dt': {
      'title': INPUT_SCHEMA['properties']['dt']['title'],
      'description': INPUT_SCHEMA['properties']['dt']['description'],
      'schema': INPUT_SCHEMA['properties']['dt'],
      'minOccurs': 1,
      'maxOccurs': 1
    },
    'margin': {
      'title': INPUT_SCHEMA['properties']['margin']['title'],
      'description': INPUT_SCHEMA['properties']['margin']['description'],
      'schema': INPUT_SCHEMA['properties']['margin'],
      'minOccurs': 1,
      'maxOccurs': 1
    }
  },
    
  'outputs': {
    'input_data': {
      'title': 'Input parameters',
      'description': 'Log of all input parameters used',
      'schema': {
          'type': 'string',
          'contentMediaType': 'text/plain'
      }
    },
    'dem': {
      'title': 'Primary DEM',
      'description': 'The local DSM (GeoTIFF) used for the simulation.',
      'schema': {
        'type': 'object',
        'properties': {
          'geotiff': {
            'description': 'Reference to the GeoTIFF.',
            'allOf': [
              {
                '$ref': 'link.yaml'
              },
              {
                'type': 'object',
                'required': ['type'],
                'properties': {
                  'type': {
                    'enum': [
                      'image/tiff; application=geotiff',
                      'application/tiff; application=geotiff'
                    ]
                  }
                }
              }
            ]
          },
          'sld': {
            'description': 'Reference to the Styled Layer Descriptor (SLD) '
                    'defining the visualization style for this GeoTIFF.',
            'allOf': [
              {
                '$ref': 'link.yaml'
              },
              {
                'type': 'object',
                'required': ['type'],
                'properties': {
                  'type': {
                    'const': 'application/vnd.ogc.sld+xml'
                  }
                }
              }
            ]
          }
        }
      }
    },
    'invasion_map': {
      'title': 'Invasion Map',
      'description':
        '2D GeoTIFF showing PDC invaded area, '
        'based on the energy conoid method.',
      'schema': {
        'type': 'object',
        'properties': {
          'geotiff': {
            'description': 'Reference to the GeoTIFF.',
            'allOf': [
              {
                '$ref': 'link.yaml'
              },
              {
                'type': 'object',
                'required': ['type'],
                'properties': {
                  'type': {
                    'enum': [
                      'image/tiff; application=geotiff',
                      'application/tiff; application=geotiff'
                    ]
                  }
                }
              }
            ]
          },
          'sld': {
            'description': 'Reference to the Styled Layer Descriptor (SLD) '
                    'defining the visualization style for this GeoTIFF.',
            'allOf': [
              {
                '$ref': 'link.yaml'
              },
              {
                'type': 'object',
                'required': ['type'],
                'properties': {
                  'type': {
                    'const': 'application/vnd.ogc.sld+xml'
                  }
                }
              }
            ]
          }
        }
      }
    },
    'spatial_evolution': {
      'title': 'Spatial evolution of current mean properties.',
      'description': 'Spatial evolution of current mean properties.',
      'schema': {
          '$ref': '#/$defs/chart',
#          'contentMediaType': 'application/json'
      }
    },
    'deposit_thickness': {
      'title': 'Deposit thickness left by the current with distance from vent.',
      'description':
        'Deposit thickness left by the current with distance from vent.',
      'schema': {
        '$ref': '#/$defs/chart',
#        'contentMediaType': 'application/json'
      }
    }
  },

  # not defined in process.yaml
  # >>>>>>>>>>>>>>>>>>>>>>>>>
  'examples': [
    {
      'payload_example': {
        'inputs': {
          'lon': 14.428, 'lat': 40.820, 'l0': 150, 'h0': 150, 'theta0': 500,
          'multiple_values': [{
            'eps0': 0.01, 'rhos': 1000, 'ds': 0.0001
          }],
          'dt': 0.5, 'margin': 5000,
        },
        'outputs': {
            'input_data': {}, 'dem': {}, 'invasion_map': {},
             'spatial_evolution': {},'deposit_thickness': {}
        }
      }
    },
    {
      'curl_request_example': 
          'curl -k -L -X POST '
          '"https://voice.pi.ingv.it/geoinquire/processes/pybox/execution" '
          '-H "Content-Type: application/json" '
          '-d \'{"inputs":{"lon":14.428,"lat":40.820,"l0":150,"h0":150,'
          '"theta0":500,"multiple_values":[{'
          '"eps0":0.01,"rhos":1000,"ds":0.0001}],'
          '"dt":0.5,"margin":5000},'
          '"outputs":{"dem":{"transmissionMode": "reference"},'
          '"spatial_evolution":{"transmissionMode": "value"}}}\''
    },
    {
      'curl_request_with_qualified_example__href-only_not_supported_yet': 
          'curl -k -L -X POST '
          '"https://voice.pi.ingv.it/geoinquire/processes/pybox/execution" '
          '-H "Content-Type: application/json" '
          '-d \'{"inputs":{"lon":{"value":14.428},'
          '"lat":{"value":40.820},"l0":150,"h0":150,'
          '"theta0":500,"multiple_values":[{'
          '"eps0":0.01,"rhos":1000,"ds":0.0001}],'
          '"dt":0.5,"margin":5000},'
          '"outputs":{"dem":{"transmissionMode": "reference"},'
          '"spatial_evolution":{"transmissionMode": "value"}}}\''
    },
    {
      'curl_jobStatus_request': 
          'curl -k -L '
          '"https://voice.pi.ingv.it/geoinquire/jobs/<jobID>"'
    },
    {
      'curl_jobResults_request': 
          'curl -k -L '
          '"https://voice.pi.ingv.it/geoinquire/jobs/<jobID>/results"?f=json'
    }
  ]
  # curl -k -L -X POST "https://voice.pi.ingv.it/geoinquire/processes/pybox/execution" -H 'Content-Type: application/json' -d '{ "inputs" : { "lon" : 14.428, "lat" : 40.820, "l0" : 150, "h0" : 150, "theta0" : 500, "multiple_values" : [{"eps0": 0.01, "rhos": 1000, "ds": 0.0001}],"dt" : 0.5, "margin" : 5000 }, "outputs" : ["input_data", "dem", "spatial_evolution"] }'
  # per asincrono aggiungere: -H "Prefer: respond-async"

  # curl localhost:5000/processes/pybox/execution 
  #       -H 'Content-Type: application/json' 
  #       -d '{ "inputs" : { "lon" : 14.428, "lat" : 40.820, "l0" : 150, "h0" : 150, 
  #                          "theta0" : 500, "multiple_values" : [{"eps0": 0.01, "rhos": 1000, "ds": 0.0001}], 
  #                          "dt" : 0.5, "margin" : 5000 }}'
  # curl localhost:5000/processes/pybox/execution -H 'Content-Type: application/json' -d '{ "inputs" : { "lon" : 14.428, "lat" : 40.820, "l0" : 150, "h0" : 150, "theta0" : 500, "multiple_values" : [{"eps0": 0.01, "rhos": 1000, "ds": 0.0001}],"dt" : 0.5, "margin" : 5000 }, "outputs" : ["input_data", "dem", "spatial_evolution"] }'
  # curl localhost:5000/processes/pybox/execution -H 'Content-Type: application/json' -d '{ "inputs" : { "lon" : { "value" : 14.428 }, "lat" : 40.820, "l0" : 150, "h0" : 150, "theta0" : 500, "multiple_values" : [{"eps0": 0.01, "rhos": 1000, "ds": 0.0001}],"dt" : 0.5, "margin" : 5000 }, "outputs" : ["input_data", "dem", "spatial_evolution"] }'
  # curl localhost:5000/processes/pybox/execution -H 'Content-Type: application/json' -d '{ "inputs" : { "lon" : "lon" : 14.428, "lat" : 40.820, "l0" : 150, "h0" : 150, "theta0" : 500, "multiple_values" : [{"eps0": 0.01, "rhos": 1000, "ds": 0.0001}],"dt" : 0.5, "margin" : 5000 }, "outputs" : {"input_data": { "transmissionMode": "value" }, "dem" : { "transmissionMode": "value" }, "spatial_evolution": { "transmissionMode": "value" } } }'
  #
}


class PyboxProcessor(BaseRemoteExecutionProcessorLocalReference):
    """
    PyboxProcessor
    """
    def __init__(self, processor_def):
        """
        Initialize object
        :param processor_def: provider definition

        :returns: pygeoapi.process.pybox.PyboxProcessor
        """
        super().__init__(processor_def, PROCESS_METADATA)
        self.supports_outputs = True

        self.base_output_filename = 'out_file'

    def prepare_output(self, info, working_path: Path, req_outputs):
        # Checks for error on outputs request performed by
        # base class in execute().

        # Prepare outputs
        # ###############
        produced_outputs = {}
        try:
            if 'input_data' in req_outputs:
                produced_outputs['input_data'] = {'mediaType': 'text/plain'}
                transmission_mode = req_outputs['input_data'].get(
                    'transmissionMode', ''
                )
                if transmission_mode == 'value':
                    with open(
                        working_path / 
                        f'{self.base_output_filename}_params.txt'
                    ) as output_file:
                        contenuto = output_file.read()
                    produced_outputs['input_data']['value'] = contenuto
                elif (transmission_mode == 'reference'):
                    src_file = (
                        working_path /
                        f'{self.base_output_filename}_params.txt'
                    )
                    dst_file = (
                        self.base_reference_path /
                        f'{self.job_id}_input_data.txt'
                    )
                    shutil.copy(src_file, dst_file)

                    file_href = (
                        f'{self.base_reference_url}'
                        f'{self.job_id}_input_data.txt'
                    )
                    produced_outputs['input_data']['href'] = file_href
                else: # should never happen: cheched in _check_output_request()
                    raise ProcessorExecuteError('Program error.')
 
            if 'dem' in req_outputs:
                # GeoTIFF file is always made available by reference
                src_tiff_file = (
                    working_path / 
                    f'{self.base_output_filename}.tif'
                )
                dst_tiff_file = (
                    self.base_reference_path /
                    f'{self.job_id}_dem.tif'
                )
                shutil.copy(src_tiff_file, dst_tiff_file)
                file_tiff_href = (
                    f'{self.base_reference_url}'
                    f'{self.job_id}_dem.tif'
                )

                # SLD file is always made available by reference
                src_sld_file = (
                    working_path / 
                    f'{self.base_output_filename}.sld'
                )
                dst_sld_file = (
                    self.base_reference_path /
                    f'{self.job_id}_dem.sld'
                )
                shutil.copy(src_sld_file, dst_sld_file)
                file_sld_href = (
                    f'{self.base_reference_url}'
                    f'{self.job_id}_dem.sld'
                )

                dem_metadata = PROCESS_METADATA['outputs']['dem']
                dem_properties = dem_metadata['schema']['properties']
                value = {
                    'geotiff': {
                        'title': dem_properties['geotiff']['description'],
                        'type': 'application/tiff; application=geotiff',
                        'href': file_tiff_href
                    },
                    'sld': {
                        'title': dem_properties['sld']['description'],
                        'type': 'application/vnd.ogc.sld+xml',
                        'href': file_sld_href
                    },
                }

                produced_outputs['dem'] = {
                    'mediaType': 'application/json'
                }

                transmission_mode = req_outputs['dem'].get(
                    'transmissionMode', ''
                )
                if transmission_mode == 'value':
                    produced_outputs['dem']['value'] = value
                elif (transmission_mode == 'reference'):
                    dst_file = (
                        self.base_reference_path /
                        f'{self.job_id}_dem.json'
                    )
                    with open(dst_file, 'w', encoding='utf-8') as json_file:
                        json.dump(value, json_file)

                    file_href = (
                        f'{self.base_reference_url}'
                        f'{self.job_id}_dem.json'
                    )
                    produced_outputs['dem']['href'] = file_href
                else: # should never happen: cheched in _check_output_request()
                    raise ProcessorExecuteError('Program error.')
            
            if 'invasion_map' in req_outputs:
                # GeoTIFF file is always made available by reference
                src_tiff_file = (
                    working_path / 
                    f'{self.base_output_filename}_EC2.tif'
                )
                dst_tiff_file = (
                    self.base_reference_path /
                    f'{self.job_id}_invasion_map.tif'
                )
                shutil.copy(src_tiff_file, dst_tiff_file)
                file_tiff_href = (
                    f'{self.base_reference_url}'
                    f'{self.job_id}_invasion_map.tif'
                )

                # SLD file is always made available by reference
                src_sld_file = (
                    working_path / 
                    f'{self.base_output_filename}_EC2.sld'
                )
                dst_sld_file = (
                    self.base_reference_path /
                    f'{self.job_id}_invasion_map.sld'
                )
                shutil.copy(src_sld_file, dst_sld_file)
                file_sld_href = (
                    f'{self.base_reference_url}'
                    f'{self.job_id}_invasion_map.sld'
                )

                invasion_metadata = PROCESS_METADATA['outputs']['invasion_map']
                invasion_properties = invasion_metadata['schema']['properties']
                value = {
                    'geotiff': {
                        'title': invasion_properties['geotiff']['description'],
                        'type': 'application/tiff; application=geotiff',
                        'href': file_tiff_href
                    },
                    'sld': {
                        'title': invasion_properties['sld']['description'],
                        'type': 'application/vnd.ogc.sld+xml',
                        'href': file_sld_href
                    },
                }

                produced_outputs['invasion_map'] = {
                    'mediaType': 'application/json'
                }

                transmission_mode = req_outputs['invasion_map'].get(
                    'transmissionMode', ''
                )
                if transmission_mode == 'value':
                    produced_outputs['invasion_map']['value'] = value
                elif (transmission_mode == 'reference'):
                    dst_file = (
                        self.base_reference_path /
                        f'{self.job_id}_invasion_map.json'
                    )
                    with open(dst_file, 'w', encoding='utf-8') as json_file:
                        json.dump(value, json_file)

                    file_href = (
                        f'{self.base_reference_url}'
                        f'{self.job_id}_invasion_map.json'
                    )
                    produced_outputs['invasion_map']['href'] = file_href
                else: # should never happen: cheched in _check_output_request()
                    raise ProcessorExecuteError('Program error.')
            
            if 'spatial_evolution' in req_outputs:
                x_length = []
                y_height = []
                y_rho_c = []
                y_u = []
                y_TPE = []
                y_TKE = []
                y_hmax = []
                y_time = []
                y_eps_n = [] # variable number of columns (eps_0, eps_1, ...)

                with open(
                    working_path / f'{self.base_output_filename}.csv'
                ) as output_file:
                    for line in output_file:
                        # Skip spaces
                        line = line.strip()
                        # Skip empty lines
                        if not line:
                            continue

                        # Skip headers, i.e. lines not starting with a number 
                        if not line[0].isdigit() and line[0] != '-':
                            continue

                        parts = [p.strip() for p in line.split(',')]

                        # Add values to elements
                        values = [float(p) for p in parts]
                        x_length.append(values[0])
                        y_height.append(values[1])
                        y_rho_c.append(values[2])
                        y_u.append(values[3])
                        y_TPE.append(values[4])
                        y_TKE.append(values[5])
                        y_hmax.append(values[6])
                        y_time.append(values[7])

                        # --- variable columns (from column 9) ---
                        extra_values = values[8:]

                        # Initialize y_eps_n first time in loop
                        if not y_eps_n:
                            y_eps_n = [[] for _ in range(len(extra_values))]

                        # Add values to variable columns
                        for i, v in enumerate(extra_values):
                            y_eps_n[i].append(v)

                # Fixed sets:
                series = [
                    {
                        'key': 'height(m)',
                        'label': 'height(m)',
                        'unit': 'm',
                        'description': 
                            'average thickness (height) of the current',
                        'values': y_height
                    },
                    {
                        'key': 'rho_c(kg/m3)',
                        'label': 'rho_c(kg/m3)',
                        'unit': 'kg/m^3',
                        'description': 'bulk density of the current',
                        'values': y_rho_c
                    },
                    {
                        'key': 'u(m/s)',
                        'label': 'u(m/s)',
                        'unit': 'm/s',
                        'description': 'front propagation velocity',
                        'values': y_u
                    },
                    {
                        'key': 'TPE(J)',
                        'label': 'TPE(J)',
                        'unit': 'J',
                        'description': 'total potential energy',
                        'values': y_TPE
                    },
                    {
                        'key': 'TKE(J)',
                        'label': 'TKE(J)',
                        'unit': 'J',
                        'description': 'total kinetic energy',
                        'values': y_TKE
                    },
                    {
                        'key': 'hmax(m)',
                        'label': 'hmax(m)',
                        'unit': 'm',
                        'description': 
                            'maximum run-up height (potential to '
                            'overcome topographic obstacles)',
                        'values': y_hmax
                    },
                    {
                        'key': 'time(s)',
                        'label': 'time(s)',
                        'unit': 's',
                        'description':
                            'time from the start of the propagation',
                        'values': y_time
                    }
                ]
                # Variable sets (eps_n):
                for i, eps_values in enumerate(y_eps_n):
                    series.append(
                        {
                            'key': f'eps_{i}',
                            'label': f'eps_{i}',
                            'unit': '-',
                            'description':
                                f'volume fraction of particle class {i}',
                            'values': eps_values
                        }
                    )

                value = {
                    'chartType': 'line',
                    'domain': {
                        'key': 'length(m)',
                        'label': 'length(m)',
                        'description': (
                            'distance of the current front from the vent'
                        ),
                        'unit': 'm',
                        'values': x_length
                    },
                    'series': series
                }

                produced_outputs['spatial_evolution'] = {
                    'mediaType': 'application/json'
                }
                
                transmission_mode = req_outputs['spatial_evolution'].get(
                    'transmissionMode', ''
                )
                if transmission_mode == 'value':
                    produced_outputs['spatial_evolution']['value'] =  value
                elif (transmission_mode == 'reference'):
                    dst_file = (
                        self.base_reference_path /
                        f'{self.job_id}_spatial_evolution.json'
                    )

                    with open(dst_file, 'w', encoding='utf-8') as json_file:
                        json.dump(value, json_file)

                    file_href = (
                        f'{self.base_reference_url}'
                        f'{self.job_id}_spatial_evolution.json'
                    )
                    produced_outputs['spatial_evolution']['href'] = file_href
                else: # should never happen: cheched in _check_output_request()
                    raise ProcessorExecuteError('Program error.')

            if 'deposit_thickness' in req_outputs:
                x_position = []
                y_cumulative = []
                # variable number of columns (y_thikness_0, y_thikness_1, ...)
                y_thikness_n = [] 
    
                with open(
                    working_path / f'{self.base_output_filename}_thickness.csv'
                ) as output_file:
                    for line in output_file:
                        # Skip spaces
                        line = line.strip()
                        # Skip empty lines
                        if not line:
                            continue

                        # Skip headers, i.e. lines not starting with a number 
                        if not line[0].isdigit() and line[0] != '-':
                            continue

                        parts = [p.strip() for p in line.split(',')]

                        # Add values to elements
                        values = [float(p) for p in parts]
                        x_position.append(values[0])
                        y_cumulative.append(values[1])

                        # --- variable columns (from column 3) ---
                        extra_values = values[2:]

                        # Initialize y_eps_n first time in loop
                        if not y_thikness_n:
                            y_thikness_n = [[] for _ in range(len(extra_values))]

                        # Add values to variable columns
                        for i, v in enumerate(extra_values):
                            y_thikness_n[i].append(v)

                # Fixed sets:
                series = [
                    {
                        'key': 'total deposit thickness(m)',
                        'label': 'total deposit thickness(m)',
                        'unit': 'm',
                        'description':
                            'cumulative thickness of all deposited '
                            'particle classes',
                        'values': y_cumulative
                    }
                ]
                # Variable sets (y_thikness_n):
                for i, thikness_values in enumerate(y_thikness_n):
                    series.append(
                        {
                            'key': f'thickness_{i}',
                            'label': f'thickness_{i}',
                            'unit': '-',
                            'description':
                                f'granulometric class {i} deposit thickness(m)',
                            'values': thikness_values
                        }
                    )
                
                value = {
                    'chartType': 'line',
                    'domain': {
                        'key': 'current front position(m)',
                        'label': 'current front position(m)',
                        'description': (
                            'front distance from vent at the moment '
                            'of deposition'
                        ),
                        'unit': 'm',
                        'values': x_position
                    },
                    'series': series
                }

                produced_outputs['deposit_thickness'] = {
                    'mediaType': 'application/json'
                }
                transmission_mode = req_outputs['deposit_thickness'].get(
                    'transmissionMode', ''
                )
                if transmission_mode == 'value':
                    produced_outputs['deposit_thickness']['value'] =  value
                elif (transmission_mode == 'reference'):
                    dst_file = (
                        self.base_reference_path /
                        f'{self.job_id}_deposit_thickness.json'
                    )

                    with open(dst_file, 'w', encoding='utf-8') as json_file:
                        json.dump(value, json_file)

                    file_href = (
                        f'{self.base_reference_url}'
                        f'{self.job_id}_deposit_thickness.json'
                    )
                    produced_outputs['deposit_thickness']['href'] = file_href
                else: # should never happen: cheched in _check_output_request()
                    raise ProcessorExecuteError('Program error.')

        except OSError as e:
            LOGGER.error(f'Errore apertura file: {e}')
            raise ProcessorExecuteError(
                f'Program error: please report to the service provider '
                f'for this job_id: {info["job_id"]}.'
            )

        return self.format_output(produced_outputs, req_outputs)

    def prepare_input(self, inputData, working_dir: Path, outputs):
        # Verify input parameters matching definitions.
        LOGGER.debug(f'Validating input')
        # NOTE: input attributes are all simple values or array,
        # they are never "complex object" where there is the option "value"
        # or "reference".
        # The items of the array "multiple_values" are complex object, but
        # they are not input attributes, and the option "value"/"reference"
        # does not apply.
        data = self.resolveInputData(inputData)
        
#        validation_errors = validate_json(
#            INPUT_SCHEMA, data
#        )
#        if validation_errors:
#            raise ProcessorExecuteError(validation_errors)

        valori_eps0 = []
        valori_rhos = []
        valori_ds = []

        for i, multiple_value in enumerate(data['multiple_values'], 1):
            # add to input parameter            
            valori_eps0.append(multiple_value['eps0'])
            valori_rhos.append(multiple_value['rhos'])
            valori_ds.append(multiple_value['ds'])

        if sum(valori_eps0) >= 1:
            err_msg = f'In multiple_values, the sum of eps0 must be < 1'
            raise ProcessorExecuteError(err_msg)

        # Create the dictionary with the properties to be passed to the 'code'
        # where property_name=parameter_name, property_value=parameter_value
        # ###############################################
        code_input_param = {}
        
        # Make lists of numbers
        code_input_param['--eps0'] = list(map(str, valori_eps0))
        code_input_param['--rhos'] = list(map(str, valori_rhos))
        code_input_param['--ds']   = list(map(str, valori_ds))

        # Checks all the other parameters and add as input parameters
        for name in data:
            if name == 'multiple_values':
                # Already treated before.
                continue

            # Add as input parameter
            input_flag = '--' + name
            code_input_param[input_flag] = data[name]

        # Adding parameter output file (not custom specified)
        code_input_param['-o'] = self.base_output_filename

        return code_input_param

    def remove_resources(self, job_id: str) -> None:
        resource_file = self.base_reference_path / f"{job_id}_input_data.txt"
        resource_file.unlink(missing_ok=True)

        resource_file = self.base_reference_path / f"{job_id}_dem.json"
        resource_file.unlink(missing_ok=True)

        resource_file = self.base_reference_path / f"{job_id}_invasion_map.json"
        resource_file.unlink(missing_ok=True)

        resource_file = self.base_reference_path / f"{job_id}_spatial_evolution.json"
        resource_file.unlink(missing_ok=True)

        resource_file = self.base_reference_path / f"{job_id}_deposit_thickness.json"
        resource_file.unlink(missing_ok=True)

    def __repr__(self):
        return f'<PyboxProcessor> {self.name}'
