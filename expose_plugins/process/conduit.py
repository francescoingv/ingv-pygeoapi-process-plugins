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

from pathlib import Path
import shutil

from pygeoapi.process.base import (
    ProcessorExecuteError,
)
from expose_plugins.process.base_remote_execution import (
    BaseRemoteExecutionProcessorLocalReference,
    validate_json,
    CHART_SCHEMA,
)

LOGGER = logging.getLogger(__name__)

INPUT_SCHEMA = {
  '$schema': 'https://json-schema.org/draft/2020-12/schema',
  '$id': 'https://example.com/schemas/conduit_plugin_schema.json',
  'title': 'Conduit Input Schema',
  'description': 'Schema for Conduit plugin inputs',
  'type': 'object',
  'required': ['melt_composition', 'volatiles', 'crystals', 'fragmentation',
               'pressure_temperature', 'geometry', 'searching_mode'],

  'additionalProperties': False,
  
  'properties': {
    'melt_composition': {
      'title': 'Melt composition',
      'description': 'Melt oxides',
      'type': 'object',
      'required': ['sio2', 'tio2', 'al2o3', 'fe2o3', 'feo',
                   'mno', 'mgo', 'cao', 'na2o', 'k2o'],
      'properties': {
        'sio2': {
          'type': 'number',
          'title': 'SiO2',
          'description': 'Weight fraction of SiO2.',
          'exclusiveMinimum': 0.0,
          'exclusiveMaximum': 1.0
        },
        'tio2': {
          'type': 'number',
          'title': 'TiO2',
          'description': 'Weight fraction of TiO2',
          'exclusiveMinimum': 0.0,
          'exclusiveMaximum': 1.0
        },
        'al2o3': {
          'type': 'number',
          'title': 'Al2O3',
          'description': 'Weight fraction of Al2O3',
          'exclusiveMinimum': 0.0,
          'exclusiveMaximum': 1.0
        },
        'fe2o3': {
          'type': 'number',
          'title': 'Fe2O3',
          'description': 'Weight fraction of Fe2O3',
          'exclusiveMinimum': 0.0,
          'exclusiveMaximum': 1.0
        },
        'feo': {
          'type': 'number',
          'title': 'FeO',
          'description': 'Weight fraction of FeO',
          'exclusiveMinimum': 0.0,
          'exclusiveMaximum': 1.0
        },
        'mno': {
          'type': 'number',
          'title': 'MnO',
          'description': 'Weight fraction of MnO',
          'exclusiveMinimum': 0.0,
          'exclusiveMaximum': 1.0
        },
        'mgo': {
          'type': 'number',
          'title': 'MgO',
          'description': 'Weight fraction of MgO',
          'exclusiveMinimum': 0.0,
          'exclusiveMaximum': 1.0
        },
        'cao': {
          'type': 'number',
          'title': 'CaO',
          'description': 'Weight fraction of CaO',
          'exclusiveMinimum': 0.0,
          'exclusiveMaximum': 1.0
        },
        'na2o': {
          'type': 'number',
          'title': 'Na2O',
          'description': 'Weight fraction of Na2O',
          'exclusiveMinimum': 0.0,
          'exclusiveMaximum': 1.0
        },
        'k2o': {
          'type': 'number',
          'title': 'K2O',
          'description': 'Weight fraction of K2O',
          'exclusiveMinimum': 0.0,
          'exclusiveMaximum': 1.0
        },
      }
    },
    'volatiles': {
      'title': 'Volatile composition',
      'description': 'Volatile oxides',
      'type': 'object',
      'required': ['h2o', 'co2'],
      'properties': {
        'h2o': {
          'type': 'number',
          'title': 'H2O',
          'description': 'Weight fraction of total H2O',
          'exclusiveMinimum': 0.0,
          'exclusiveMaximum': 1.0
        },
        'co2': {
          'type': 'number',
          'title': 'CO2',
          'description': 'Weight fraction of total CO2',
          'exclusiveMinimum': 0.0,
          'exclusiveMaximum': 1.0
        },
      }
    },
    'crystals': {
      'title': 'Crystals',
      'description': 'Crystals',
      'type': 'object',
      'required': ['c', 'den'],
      'properties': {
        'c': {
          'type': 'number',
          'title': 'Crystal volume fraction',
          'description':
            'Volume fraction of crystals relative to a degassed magma.',
          'exclusiveMinimum': 0.0,
          'maximum': 0.7
        },
        'den': {
          'type': 'number',
          'title': 'Crystal density [kg/m^3]',
          'description': 'Average density of the crystal phase.',
          'exclusiveMinimum': 0.0,
        }
      }
    },
    'fragmentation': {
      'title': 'Fragmentation',
      'description': 'Fragmentation parameters',
      'type': 'object',
      'required': ['fe', 'pd', 'dp', 'ds', 'dc'],
      'properties': {
        'fe': {
          'type': 'number',
          'title': 'Fragmentation efficiency',
          'description': 'Parameter for fragmentation efficiency',
          'minimum': 0.2,
          'maximum': 1.0
        },
        'pd': {
          'type': 'number',
          'title': 'Pumice degassing',
          'description': 'Parameter for pumice degassing',
          'minimum': 0.0,
          'maximum': 1.0
        },
        'dp': {
          'type': 'number',
          'title': 'Diameter of the pumices [m]',
          'description': 'Average diameter of the pumices at fragmentation',
          'exclusiveMinimum': 0.0,
        },
        'ds': {
          'type': 'number',
          'title': 'Diameter of the shards [m]',
          'description': 'Average diameter of the shards at fragmentation',
          'exclusiveMinimum': 0.0,
        },
        'dc': {
          'type': 'number',
          'title': 'Diameter of the crystals [m]',
          'description':
            'Average diameter of the crystals at fragmentation',
          'exclusiveMinimum': 0.0,
        },
      }
    },
    'pressure_temperature': {
      'title': 'Pressure and temperature',
      'description': 'Pressure and temperature',
      'type': 'object',
      'required': ['p', 't'],
      'properties': {
        'p': {
          'type': 'number',
          'title': 'Pressure [Pa]',
          'description': 'Pressure in the magma chamber.',
          'exclusiveMinimum': 101325.0
        },
        't': {
          'type': 'number',
          'title': 'Temperature [K]',
          'description': 'Magma temperature',
          'exclusiveMinimum': 273.15
        },
      }
    },
    'geometry': {
      'title': 'Geometry',
      'description': 'Geometry of the conduit',
      'type': 'object',
      'required': ['g', 'l'],
      'properties': {
        'g': {
          'type': 'string',
          'title': 'Geometry',
          'description': 'Geometry: cylindrical conduit (\'conduit\'), '
            'planar fissure (\'fissure\')',
          'enum': ['conduit', 'fissure']
        },
        'l': {
          'type': 'number',
          'title': 'Conduit length [m]',
          'description': 'Length of the cylindrical conduit',
          'exclusiveMinimum': 0.0
        },
      }
    },
    'searching_mode': {
      'title': 'Searching mode',
      'description': 'Searching for mass flow rate or diameter',
      'type': 'object',
      'oneOf': [
        {
          'title': '[placeholder per titolo 1]',
          'description': '[placeholder per description 1]',
          'required': ['d'],
          'additionalProperties': False,
          'properties': {
            'd': {
              'type': 'number',
              'title': 'Conduit diameter [m]',
              'description': 'Diameter of the cylindrical conduit/fissure width',
              'exclusiveMinimum': 0.0
            },
            'fg': {
              # optional
              'type': 'number',
              'title': 'Mass flow rate [kg/s] (-g cylinder) or mass flow rate per '
                'unit surface [kg/(s m^2)] (-g fissure)',
              'description': 'Initial guess for the mass flow rate along a '
                'cylindrical conduit/fissure (optional, default value: 1.0E8/1.0E5).',
              'exclusiveMinimum': 0.0
            },
          }
        },
        {
          'title': '[placeholder per titolo 2]',
          'description': '[placeholder per description 2]',
          'required': ['f'],
          'additionalProperties': False,
          'properties': {
            'f': {
              'type': 'number',
              'title': 'Mass flow rate [kg/s] (-g cylinder) or mass flow rate per '
                'unit surface [kg/(s m^2)] (-g fissure)',
              'description': 'Mass flow rate along a cylindrical conduit/fissure.',
              'exclusiveMinimum': 0.0
            },
            'dg': {
              # optional
              'type': 'number',
              'title': 'Conduit diameter [m]',
              'description': 'Initial guess for the diameter of the cylindrical conduit/fissure width',
              'exclusiveMinimum': 0.0
            },
          }
        },
      ]
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

  'id': 'conduit',
  # type string

  'version': '2.2.1',
  # type string

  # Optional properties:
  # ####################

  'jobControlOptions': [
    'async-execute',
    'sync-execute'
  ],
  # type: array,
  #   items: {type: string, enum: ['sync-execute', 'async-execute', 'dismiss']}
  
  'outputTransmission': [
    'value', 'reference'
  ],
  # type: array, 
  #   items: {type: string, enum: ['value', 'reference'], default: 'value'}

  'links': [
  {
    'href': 'https://agupubs.onlinelibrary.wiley.com/doi/abs/10.1029/2000JB900428',
    'rel': 'describedby',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'Dynamics of magma flow in volcanic conduits with variable fragmentation efficiency and nonequilibrium pumice degassing'
  },
  {
    'href': 'https://www.nature.com/articles/17109',
    'rel': 'related',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'Strain-induced magma fragmentation in explosive eruptions'
  },
  {
    'href': 'https://doi.org/10.1002/2016JB013383',
    'rel': 'related',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'Non-Newtonian flow of bubbly magma in volcanic conduits'
  },
  {
    'href': 'https://doi.org/10.3389/feart.2021.681083',
    'rel': 'related',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'Deep Magma Transport Control on the Size and Evolution of Explosive Volcanic Eruptions'
  },
  {
    'href': 'https://doi.org/10.1016/S0377-0273(02)00381-5',
    'rel': 'related',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'Coupled conduit and atmospheric dispersal dynamics of the AD 79 Plinian eruption of Vesuvius'
  },
  {
    'href': 'https://link.springer.com/article/10.1007/s004450000123',
    'rel': 'related',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'Textural heterogeneities in pumices from the climactic eruption of Mount Pinatubo, 15 June 1991, and implications for magma ascent dynamics'
  },
  {
    'href': 'https://doi.org/10.1130/G25402A.1',
    'rel': 'related',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'Origin of basalt fire-fountain eruptions on Earth versus the Moon'
  },
  {
    'href': 'https://doi.org/10.5194/se-1-61-2010',
    'rel': 'related',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'Rheological control on the dynamics of explosive activity in the 2000 summit eruption of Mt. Etna'
  },
  {
    'href': 'https://doi.org/10.1016/S0377-0273(03)00319-6',
    'rel': 'related',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'Dynamics of magma ascent and fragmentation in trachytic versus rhyolitic eruptions'
  },
  {
    'href': 'https://doi.org/10.1016/j.jvolgeores.2008.05.012',
    'rel': 'related',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'Vent conditions for expected eruptions at Vesuvius'
  },
  {
    'href': 'https://doi.org/10.1016/j.chemgeo.2006.06.007',
    'rel': 'related',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'The effect of H2O on the viscosity of K-trachytic melts at magmatic temperatures'
  },
  {
    'href': 'https://doi.org/10.1016/S0377-0273(98)00101-2',
    'rel': 'related',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'The role of magma composition and water content in explosive eruptions: 1. Conduit ascent dynamics'
  },
  {
    'href': 'https://doi.org/10.1029/93JB02972',
    'rel': 'related',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'Magma flow along the volcanic conduit during the Plinian and pyroclastic flow phases of the May 18, 1980, Mount St. Helens eruption'
  },
  {
    'href': 'https://doi.org/10.1016/0377-0273(93)90104-Y',
    'rel': 'related',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'Modeling of the ascent of magma during the plinian eruption of Vesuvius in A.D. 79'
  },
  {
    'href': 'https://link.springer.com/article/10.1007/s004450050253',
    'rel': 'related',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'Role of carbon dioxide in the dynamics of magma ascent in explosive eruptions'
  },
  {
    'href': 'https://doi.org/10.1016/S1464-1895(99)00142-8',
    'rel': 'related',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'Numerical simulations of magma ascent along volcanic conduits'
  },
  {
    'href': 'https://doi.org/10.1016/S1464-1895(99)00144-1',
    'rel': 'related',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'The role of water content and magma composition on explosive eruption dynamics'
  },
  {
    'href': 'https://doi.org/10.1016/0012-821X(94)90037-X',
    'rel': 'related',
    'type': 'application/pdf',
    'hreflang': 'en-US',
    'title': 'Erosion processes in volcanic conduits and application to the AD 79 eruption of Vesuvius'
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

  'title': 'CONDUIT',
  # type: string

  'description':
    'CONDUIT4 is a Fortran code for computing the one-dimensional, steady, '
    'isothermal, multiphase and multicomponent flow of magma in volcanic '
    'conduits. The code solves the compressible mass balance and momentum '
    'balance equations separately for a gas phase and a dense phase '
    'constituted by liquid+crystals (below fragmentation), or by pyroclasts '
    '(above fragmentation). A user-defined fragmentation efficiency parameter '
    'describes the relative amounts of non-vesicular ash, vesicular pumice, '
    'and free crystals generated at fragmentation; while another user-defined '
    'parameter describes pumice degassing disequilibrium. The model takes '
    'either choked flow or atmospheric pressure conditions at the conduit '
    'exit, with the alternative being part of the solution thus depending on '
    'the selected conditions. The numerical algorithm searches for such an '
    'exit condition by adapting the mass flow-rate to the selected conduit '
    'diameter. Thermodynamic equilibrium phase between the gas (H2O+CO2) and '
    'the silicate melt is calculated through the SOLWCAD model '
    '(Papale et al., 2006, [Chemical Geology, 229(1-3), 78-95]), '
    'implemented within CONDUIT4. Magma fragmentation is determined based on '
    'Maxwell\'s theory for visco-elastic materials, as described in '
    'Papale (1999) [Nature, 397(6718), 425-428]. The viscosity of the liquid '
    'is calculated according to Giordano et al. (2008) [Earth and Planetary '
    'Science Letters, 271.1-4: 123-134], and the effect of crystals on '
    'viscosity is based on the model of Costa et al. (2009) '
    '[Geochemistry, Geophysics, Geosystems, 10(3)]. The transport and '
    'constitutive equations, as well as the numerical approach, are detailed '
    'in Papale (2001) '
    '[Journal of Geophysical Research: Solid Earth, 106(B6), 11043-11065].',
  # type: string
  
  'keywords': ['Fortran code', 'conduit flow'],
  # type: array
  #   items: type: string

  # 'metadata':
  # type: array
  #   items: {type: object, title: string, role: string, href: string}

  # additionalParameters (metadata.yaml + parameters [additionalParameter.yaml]) 


  # process.yaml
  # >>>>>>>>>>>>
  'inputs': {
    # inputDescription.yaml
    'melt_composition': {
      'title': INPUT_SCHEMA['properties']['melt_composition']['title'],
      'description': INPUT_SCHEMA['properties']['melt_composition']['description'],
      'schema': INPUT_SCHEMA['properties']['melt_composition'],
      'minOccurs': 1,
      'maxOccurs': 1
    },
    'volatiles': {
      'title': INPUT_SCHEMA['properties']['volatiles']['title'],
      'description': INPUT_SCHEMA['properties']['volatiles']['description'],
      'schema': INPUT_SCHEMA['properties']['volatiles'],
      'minOccurs': 1,
      'maxOccurs': 1
    },
    'crystals': {
      'title': INPUT_SCHEMA['properties']['crystals']['title'],
      'description': INPUT_SCHEMA['properties']['crystals']['description'],
      'schema': INPUT_SCHEMA['properties']['crystals'],
      'minOccurs': 1,
      'maxOccurs': 1
    },
    'fragmentation': {
      'title': INPUT_SCHEMA['properties']['fragmentation']['title'],
      'description': INPUT_SCHEMA['properties']['fragmentation']['description'],
      'schema': INPUT_SCHEMA['properties']['fragmentation'],
      'minOccurs': 1,
      'maxOccurs': 1
    },
    'pressure_temperature': {
      'title': INPUT_SCHEMA['properties']['pressure_temperature']['title'],
      'description': INPUT_SCHEMA['properties']['pressure_temperature']['description'],
      'schema': INPUT_SCHEMA['properties']['pressure_temperature'],
      'minOccurs': 1,
      'maxOccurs': 1
    },
    'geometry': {
      'title': INPUT_SCHEMA['properties']['geometry']['title'],
      'description': INPUT_SCHEMA['properties']['geometry']['description'],
      'schema': INPUT_SCHEMA['properties']['geometry'],
      'minOccurs': 1,
      'maxOccurs': 1
    },
    'searching_mode': {
      'title': INPUT_SCHEMA['properties']['searching_mode']['title'],
      'description': INPUT_SCHEMA['properties']['searching_mode']['description'],
      'schema': INPUT_SCHEMA['properties']['searching_mode'],
      'minOccurs': 1,
      'maxOccurs': 1
    },
  },

  'outputs': {
    'gas': {
      'title': 'Plot gas volume fraction',
      'description': 'Profile of gas volume fraction along the conduit.',
      'schema': {
        '$ref': '#/$defs/chart',
#        'contentMediaType': 'application/json'
      }
    },
    'velocity': {
      'title': 'Plot Velocity',
      'description': 'Velocity profiles of liquid and gas along the conduit.',
      'schema': {
        '$ref': '#/$defs/chart',
#        'contentMediaType': 'application/json'
      }
    },
    'pressure': {
      'title': 'Plot Pressure',
      'description': 'Pressure profile along the conduit.',
      'schema': {
          '$ref': '#/$defs/chart',
#          'contentMediaType': 'application/json'
      }
    },
    'outfile': {
      'title': 'Table of output variables',
      'description':
        'Dependent variables and physical properties along the conduit.'
        'Columns:'
        '1) conduit length [m];'
        '2) gas in pumice [volume %];'
        '3) gas before fragmentation [volume %];'
        '4) gas velocity [m/s];'
        '5) liquid velocity [m/s];'
        '6) pressure [MPa];'
        '7) dissolved H2O [mass %];'
        '8) dissolved CO2 [mass %];'
        '9) gas H2O [mass %];'
        '10) gas CO2 [mass %];'
        '11)  gas before fragmentation [mass %];'
        '12)  crystals [volume %];'
        '13) crystals [mass %];'
        '14) liquid+crystals+gas viscosity [Pa s];'
        '15) liquid+crystals viscosity [Pa s];'
        '16) liquid viscosity [Pa s];'
        '17) liquid+crystals+gas density [kg/m^3];'
        '18) liquid+crystals density [kg/m^3];'
        '19) liquid density [kg/m^3];'
        '20) gas density [kg/m^3];'
        '21) rate of strain [s^-1].',
      'schema': {
        'type': 'string',
        'contentMediaType': 'text/csv; header=present'
      }
    },
    'exit': {
      'title': 'Conditions at the conduit exit',
      'description': 'Density, velocity, pressure and mass/volumetric flow rate at the conduit exit',
      'schema': {
        'type': 'string',
          'contentMediaType': 'text/plain'
      }
    }
  },

  # not defined in process.yaml
  # >>>>>>>>>>>>>>>>>>>>>>>>>
  'examples': [
    {
      'payload_example': {
        'inputs': {
          'melt_composition' : {
            'value' : {
              'sio2': 0.7669, 'tio2': 0.0012, 'al2o3': 0.1322,
              'fe2o3': 0.0039, 'feo': 0.0038, 'mno': 0.0007, 'mgo': 0.0006,
              'cao': 0.0080, 'na2o': 0.0300, 'k2o': 0.0512
            }
          },
          'volatiles' : {
            'value' : {
              'h2o': 0.0500e0, 'co2': 0.0200e0
            } 
          },
          'crystals' : {
            'value' : {
              'c': 0.1, 'den': 2800.0e0
            }
          },
          'fragmentation' : {
            'value' : {
              'fe': 0.2, 'pd': 0.9, 'dp': 200e-6, 'ds': 200e-6, 'dc': 200e-6
            }
          },
          'pressure_temperature' : {
            'value' : {
              'p': 1.0e8, 't': 1050.0e0
            }
          },
          'geometry' : {
            'value' : {
              'g': 'conduit', 'l': 4000.0e0
            }
          },
          'searching_mode' : {
            'value' : {
              'f': 0.88393e8
            }
          }
        },
        'outputs': {
          'gas': {
            'transmissionMode': 'value'
          },
          'velocity': {
            'transmissionMode': 'value'
          }
        }
      }
    },
    {
      'curl_example': (
        'curl -i -k -L -X POST '
        '"https://voice.pi.ingv.it/geoinquire/processes/conduit/execution" '
        '-H "Content-Type: application/json" '
        '-d \'{'
          '"inputs": {'
            '"melt_composition": {'
              '"value": {'
                '"sio2": 0.7669, "tio2": 0.0012, "al2o3": 0.1322, '
                '"fe2o3": 0.0039, "feo": 0.0038, "mno": 0.0007, '
                '"mgo": 0.0006, "cao": 0.0080, "na2o": 0.0300, '
                '"k2o": 0.0512} }, '
            '"volatiles": {'
              '"value": {"h2o": 0.0500e0, "co2": 0.0200e0} }, '
            '"crystals": {"value": {"c": 0.1, "den": 2800.0e0} }, '
            '"fragmentation": {'
              '"value": {'
                '"fe": 0.2, "pd": 0.9, "dp": 200e-6, "ds": 200e-6,'
                '"dc": 200e-6} }, '
            '"pressure_temperature": {'
              '"value": {"p": 1.0e8, "t": 1050.0e0} }, '
            '"geometry": {"value": {"g": "conduit", "l": 4000.0e0} }, '
            '"searching_mode": {"value": {"f": 0.88393e8} } '
          '},'
          '"outputs": {"gas": {}, "velocity": {} } }\''
      )
    },
    {
      'curl_example_alsoByReference': (
        'curl -i -k -L -X POST '
        '"https://voice.pi.ingv.it/geoinquire/processes/conduit/execution" '
        '-H "Content-Type: application/json" '
        '-d \'{'
          '"inputs": {'
            '"melt_composition": {'
              '"value": {'
                '"sio2": 0.7669, "tio2": 0.0012, "al2o3": 0.1322, '
                '"fe2o3": 0.0039, "feo": 0.0038, "mno": 0.0007, '
                '"mgo": 0.0006, "cao": 0.0080, "na2o": 0.0300, '
                '"k2o": 0.0512} }, '
            '"volatiles": {'
              '"value": {"h2o": 0.0500e0, "co2": 0.0200e0} }, '
            '"crystals": {"value": {"c": 0.1, "den": 2800.0e0} }, '
            '"fragmentation": {'
              '"value": {'
                '"fe": 0.2, "pd": 0.9, "dp": 200e-6, "ds": 200e-6,'
                '"dc": 200e-6} }, '
            '"pressure_temperature": {'
              '"value": {"p": 1.0e8, "t": 1050.0e0} }, '
            '"geometry": {"value": {"g": "conduit", "l": 4000.0e0} }, '
            '"searching_mode": {"value": {"f": 0.88393e8} } '
          '},'
          '"outputs":{"gas":{"transmissionMode": "reference"}, '
                       '"velocity":{"transmissionMode": "value"}}}\''
      )
    },
    {
      'curl_jobStatus_request': 
          'curl -k -L '
          '"https://voice.pi.ingv.it/geoinquire/jobs/<jobID>"'
    },
    {
      'curl_jobResults_request': 
          'curl -k -L '
          '"https://voice.pi.ingv.it/geoinquire/jobs/<jobID>/results\?f=json"'
    }
  ]

  # NEW VERSION : TEST 
  # curl localhost:5000/processes/conduit/execution -H 'Content-Type: application/json' -d '{ "inputs" : 
  #   { "melt_composition" : { "value" : {"sio2": 0.7669, "tio2": 0.0012, "al2o3": 0.1322, "fe2o3": 0.0039, "feo": 0.0038,  "mno": 0.0007, "mgo": 0.0006, "cao": 0.0080, "na2o": 0.0300, "k2o": 0.0512} },
  #     "volatiles" : { "value" : {"h2o": 0.0500e0, "co2": 0.0200e0} },
  #     "crystals" : { "value" : {"c": 0.1, "den": 2800.0e0} },
  #     "fragmentation" : { "value" : {"fe": 0.2, "pd": 0.9, "dp": 200e-6, "ds": 200e-6, "dc": 200e-6} },
  #     "pressure_temperature" : { "value" : {"p": 1.0e8, "t": 1050.0e0} },
  #     "geometry" : { "value" : {"g": "conduit", "l": 4000.0e0} },
  #     "searching_mode" : { "value" : {"f": 0.88393e8} }
  #   }, "outputs" : { "gas" : { "transmissionMode": "value" }, "velocity" : { "transmissionMode": "value" } } }'
  # NEW VERSION : TEST 
  # curl localhost:5000/processes/conduit/execution -H 'Content-Type: application/json' -d '{ "inputs" : { "melt_composition" : { "value" : {"sio2": 0.7669, "tio2": 0.0012, "al2o3": 0.1322, "fe2o3": 0.0039, "feo": 0.0038,  "mno": 0.0007, "mgo": 0.0006, "cao": 0.0080, "na2o": 0.0300, "k2o": 0.0512} }, "volatiles" : { "value" : {"h2o": 0.0500e0, "co2": 0.0200e0} }, "crystals" : { "value" : {"c": 0.1, "den": 2800.0e0} }, "fragmentation" : { "value" : {"fe": 0.2, "pd": 0.9, "dp": 200e-6, "ds": 200e-6, "dc": 200e-6} }, "pressure_temperature" : { "value" : {"p": 1.0e8, "t": 1050.0e0} }, "geometry" : { "value" : {"g": "conduit", "l": 4000.0e0} }, "searching_mode" : { "value" : {"f": 0.88393e8} } }, "outputs" : { "gas" : { "transmissionMode": "value" }, "velocity" : { "transmissionMode": "value" } } }'
  # curl -k -L -X POST "https://voice.pi.ingv.it/geoinquire/processes/conduit/execution" -H "Content-Type: application/json" -d '{ "inputs" : { "melt_composition" : { "value" : {"sio2": 0.7669, "tio2": 0.0012, "al2o3": 0.1322, "fe2o3": 0.0039, "feo": 0.0038,  "mno": 0.0007, "mgo": 0.0006, "cao": 0.0080, "na2o": 0.0300, "k2o": 0.0512} }, "volatiles" : { "value" : {"h2o": 0.0500e0, "co2": 0.0200e0} }, "crystals" : { "value" : {"c": 0.1, "den": 2800.0e0} }, "fragmentation" : { "value" : {"fe": 0.2, "pd": 0.9, "dp": 200e-6, "ds": 200e-6, "dc": 200e-6} }, "pressure_temperature" : { "value" : {"p": 1.0e8, "t": 1050.0e0} }, "geometry" : { "value" : {"g": "conduit", "l": 4000.0e0} }, "searching_mode" : { "value" : {"f": 0.88393e8} } }, "outputs" : { "gas" : { "transmissionMode": "value" }, "velocity" : { "transmissionMode": "value" } } }'
  #
}


class ConduitProcessor(BaseRemoteExecutionProcessorLocalReference):
    """Conduit Processor example"""
    def __init__(self, processor_def):
        """
        Initialize object
        :param processor_def: provider definition

        :returns: pygeoapi.process.conduit.ConduitProcessor
        """
        super().__init__(processor_def, PROCESS_METADATA)
        self.supports_outputs = True

    def prepare_output(self, info, working_path: Path, req_outputs):
        # Checks for error on outputs request performed by
        # base class in execute().

        # Prepare outputs
        # ###############

        # The code produce an output file: the file name is fixed by the code:
        out_file_name = 'conduit.out'
        exit_file_name = 'exit.out'
        # Load values returned by the program
        x_vals = []
        not_used = []
        gas_volume_fraction = []
        gas_velocity = []
        liquid_velocity = []
        pressure = []

        produced_outputs = {}
        try:
            with open(working_path / out_file_name) as output_file:
                for line in output_file:
                    # Remove spaces and split values
                    parts = line.split()
            
                    # If needed convert 'D' in 'E'
                    # (scientific Python notation: should not happen)
                    values = [float(p.replace('D', 'E')) for p in parts]

                    # Add values to elements
                    x_vals.append(values[0])
                    not_used.append(values[1])
                    gas_volume_fraction.append(values[2])
                    gas_velocity.append(values[3])
                    liquid_velocity.append(values[4])
                    pressure.append(values[5])

            if 'gas' in req_outputs:
                value = {
                    'chartType': 'line',
                    'domain': {
                        'key': 'Conduit length',
                        'label': 'Conduit length',
                        'unit': 'm',
                        'values': x_vals
                    },
                    'series': [
                        {
                            'key': 'Gas volume fraction',
                            'label': 'Gas volume fraction',
                            'unit': '-',
                            'values': gas_volume_fraction
                        }
                    ]
                }

                produced_outputs['gas'] = {'mediaType': 'application/json'}
                transmission_mode = req_outputs['gas'].get(
                    'transmissionMode', ''
                )
                if transmission_mode == 'value':
                    produced_outputs['gas']['value'] =  value
                elif (transmission_mode == 'reference'):
                    dst_file = self.base_reference_path / (
                        f'{self.job_id}_gas.json'
                    )

                    with open(dst_file, 'w', encoding='utf-8') as json_file:
                        json.dump(value, json_file)

                    file_href = (
                        f'{self.base_reference_url}'
                        f'{self.job_id}_gas.json'
                    )
                    produced_outputs['gas']['href'] = file_href
                else: # should never happen: cheched in _check_output_request()
                    raise ProcessorExecuteError('Program error.')

            if 'velocity' in req_outputs:
                value = {
                    'chartType': 'line',
                    'domain': {
                        'key': 'Conduit length',
                        'label': 'Conduit length',
                        'unit': 'm',
                        'values': x_vals
                    },
                    'series': [
                        {
                            'key': 'Gas velocity',
                            'label': 'Gas velocity',
                            'unit': 'm/s',
                            'values': gas_velocity
                        },
                        {
                            'key': 'Liquid velocity',
                            'label': 'Liquid velocity',
                            'unit': 'm/s',
                            'values': liquid_velocity
                        },
                    ]
                }

                produced_outputs['velocity'] = {'mediaType': 'application/json'}
                transmission_mode = req_outputs['velocity'].get(
                    'transmissionMode', ''
                )
                if transmission_mode == 'value':
                    produced_outputs['velocity']['value'] =  value
                elif (transmission_mode == 'reference'):
                    dst_file = self.base_reference_path / (
                        f'{self.job_id}_velocity.json'
                    )

                    with open(dst_file, 'w', encoding='utf-8') as json_file:
                        json.dump(value, json_file)

                    file_href = (
                        f'{self.base_reference_url}'
                        f'{self.job_id}_velocity.json'
                    )
                    produced_outputs['velocity']['href'] = file_href
                else: # should never happen: cheched in _check_output_request()
                    raise ProcessorExecuteError('Program error.')

            if 'pressure' in req_outputs:
                value = {
                    'chartType': 'line',
                    'domain': {
                        'key': 'Conduit length',
                        'label': 'Conduit length',
                        'unit': 'm',
                        'values': x_vals
                    },
                    'series': [
                        {
                            'key': 'Pressure',
                            'label': 'Pressure',
                            'unit': 'Mpa',
                            'values': pressure
                        },
                    ]
                }

                produced_outputs['pressure'] = {'mediaType': 'application/json'}
                transmission_mode = req_outputs['pressure'].get(
                    'transmissionMode', ''
                )
                if transmission_mode == 'value':
                    produced_outputs['pressure']['value'] =  value
                elif (transmission_mode == 'reference'):
                    dst_file = self.base_reference_path / (
                        f'{self.job_id}_pressure.json'
                    )

                    with open(dst_file, 'w', encoding='utf-8') as json_file:
                        json.dump(value, json_file)

                    file_href = (
                        f'{self.base_reference_url}'
                        f'{self.job_id}_pressure.json'
                    )
                    produced_outputs['pressure']['href'] = file_href
                else: # should never happen: cheched in _check_output_request()
                    raise ProcessorExecuteError('Program error.')

            if 'outfile' in req_outputs:
                header = [
                    'verticalCoordinate_m',
                    'gasInPumice_volumePerCent',
                    'gasBeforeFragmentation_volumePerCent',
                    'gasVelocity_mPers',
                    'liquidVelocity_mPers',
                    'pressure_MPa',
                    'dissolvedH2O_massPerCent',
                    'dissolvedCO2_massPerCent',
                    'gasH2O_massPerCent',
                    'gasCO2_massPerCent',
                    'gasBeforeFragmentation_massPerCent',
                    'crystals_volumePerCent',
                    'crystals_massPerCent',
                    'liquidPlusCrystalsPlusGasViscosity_Pas',
                    'liquidPlusCrystalsViscosity_Pas',
                    'liquidViscosity_Pas',
                    'liquidPlusCrystalsPlusGasDensity_kgPerm3',
                    'liquidPlusCrystalsDensity_kgPerm3',
                    'liquidDensity_kgPerm3',
                    'gasDensity_kgPerm3',
                    'rateOfStrain_pers'
                ]

                produced_outputs['outfile'] = {'mediaType': 'text/csv; header=present'}
                transmission_mode = req_outputs['outfile'].get(
                    'transmissionMode', ''
                )

                rows = [header]
                with open(working_path / out_file_name) as f:
                    for line in f:
                        line = line.rstrip('\n')
                        if not line:
                            break
                        
                        fields = [field.replace('D', 'E').replace('d', 'e')
                                  for field in line.split()]
                        if len(fields) != len(header):
                            raise ProcessorExecuteError(
                                'Program error: report to the administrator'
                            )
                        rows.append(fields)

                temp_value = '\n'.join(','.join(row) for row in rows)
                if transmission_mode == 'value':
                    produced_outputs['outfile']['value'] = temp_value
                elif (transmission_mode == 'reference'):
                    dst_file = self.base_reference_path / (
                        f'{self.job_id}_outfile.csv'
                    )
                    dst_file.write_text(temp_value, newline='')

                    file_href = (
                        f'{self.base_reference_url}'
                        f'{self.job_id}_outfile.csv'
                    )
                    produced_outputs['outfile']['href'] = file_href
                else: # should never happen: cheched in _check_output_request()
                    raise ProcessorExecuteError('Program error.')

            if 'exit' in req_outputs:
                produced_outputs['exit'] = {'mediaType': 'text/plain'}
                transmission_mode = req_outputs['exit'].get(
                    'transmissionMode', ''
                )
                if transmission_mode == 'value':
                    with open(working_path / exit_file_name) as f:
                        contenuto = f.read()
                    produced_outputs['exit']['value'] = contenuto
                elif (transmission_mode == 'reference'):
                    src_file = working_path / exit_file_name
                    dst_file = self.base_reference_path / (
                        f'{self.job_id}_exit.txt'
                    )
                    shutil.copy(src_file, dst_file)

                    file_href = (
                        f'{self.base_reference_url}'
                        f'{self.job_id}_exit.txt'
                    )
                    produced_outputs['exit']['href'] = file_href
                else: # should never happen: cheched in _check_output_request()
                    raise ProcessorExecuteError('Program error.')

        except OSError as e:
            LOGGER.error(f'Errore apertura file: {e}')
            raise ProcessorExecuteError(
                f'Program error: please report to the service provider '
                f'for this job_id: {info["job_id"]}.'
            )

        return self.format_output(produced_outputs, req_outputs)

    def prepare_input(self, inputData, working_path: Path, outputs):
        data = self.resolveInputData(inputData)

        # Create the dictionary with the properties to be passed to the 'code'
        # where property_name=parameter_name, property_value=parameter_value
        # ###############################################
        code_input_param = {}
        for input_item in data.values():
            for name, value in input_item.items():
              # Add as input parameter
              input_flag = '-' + name
              code_input_param[input_flag] = value
        
        return code_input_param

    def remove_resources(self, job_id: str) -> None:
        resource_file = self.base_reference_path / f"{job_id}_gas.json"
        resource_file.unlink(missing_ok=True)

        resource_file = self.base_reference_path / f"{job_id}_velocity.json"
        resource_file.unlink(missing_ok=True)

        resource_file = self.base_reference_path / f"{job_id}_pressure.json"
        resource_file.unlink(missing_ok=True)

        resource_file = self.base_reference_path / f"{job_id}_outfile.csv"
        resource_file.unlink(missing_ok=True)

        resource_file = self.base_reference_path / f"{job_id}_exit.txt"
        resource_file.unlink(missing_ok=True)

    def __repr__(self):
        return f'<ConduitProcessor> {self.name}'
