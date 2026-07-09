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

from pathlib import Path

from pygeoapi.process.base import (
    ProcessorExecuteError,
    #    ProcessorGenericError,
)
from expose_plugins.process.base_remote_execution import (
    BaseRemoteExecutionProcessorLocalReference,
)

LOGGER = logging.getLogger(__name__)

INPUT_SCHEMA = {
  '$schema': 'https://json-schema.org/draft/2020-12/schema',
  '$id': 'https://example.com/schemas/solwcad_plugin_schema.json',
  'title': 'Conduit Input Schema',
  'description': 'Schema for Conduit plugin inputs',
  'type': 'object',
  'required': ['swinput.data', 'sw.data'],
  'additionalProperties': False,
  'properties': {
    'swinput.data': {
      'title': 'Desired computation',
      'description': 'Specifics for the desired computation.',
      'type': 'object',
      'oneOf': [
        {
          'title': '[placeholder per titolo 1]',
          'description':
            'The computation is performed at user-defined P-T '
            'conditions in sw.data. H2O and CO2 contents in '
            'sw.data refer to total amounts in the two-phase '
            'magma, or to (mass of volatile component) / '
            '(mass of melt + fluid phases). '
            'SOLWCAD computes the partitioning of the two '
            'volatiles in the fluid and melt phases for '
            'user-defined composition. '
            'Computations are performed from item ndat1 to '
            'item ndat2 (only one computation is performed if '
            'ndat1 = ndat2).',
          'required': [
            'ndat1',
            'ndat2',
            'kl'
          ],
          'additionalProperties': False,
          'properties': {
            'ndat1': {
              'type': 'integer',
              'description':
                'Computations are performed from item '
                'ndat1 of sw.data'
            },
            'ndat2': {
              'type': 'integer',
              'description':
                'Computations are performed up to item '
                'ndat2 of sw.data'
            },
            'kl': {
              'type': 'integer',
              'enum': [0]  # the only one accepted value
            }
            # not used for kl = 0:
            # 'iopen', 'fopen', 'dt', 'tlimit'
          }
        },
        {
          'title': '[placeholder per titolo 2]',
          'description':
            'The computation is performed with reference to '
            'item ndat1 in sw.data, at constant user-defined '
            'T and for pressure from user-defined P to '
            'atmospheric. At each pressure, a computation '
            'similar to the one for kl=0 is performed.',
          'required': [
            'ndat1',
            'kl',
            'iopen'
          ],
          'properties': {
            'ndat1': {
              'type': 'integer',
              'description':
                'Computations are performed from item '
                'ndat1 of sw.data'
            },
            'kl': {
              'type': 'integer',
              'enum': [1],  # the only one accepted value
            },
            'iopen': {
              'type': 'integer',
              'enum': [0, 1],
              'description':
                '0 for closed-system calculations, '
                '1 for open system calculations.'
            },
            'fopen': {
              'type': 'string',
              'pattern':
                r'^([+-]?([\d]+\.|[\d]*\.[\d]+))'
                r'([Dd][+-]?[\d]+)?$',
              'description':
                'Only used with iopen =1. It specifies '
                'the weight fraction of fluid phase lost '
                'at each subsequent computation step.'
            }
            # not used for kl = 0:
            # 'dt', 'tlimit'
          }
        },
        {
          'title': '[placeholder per titolo 3]',
          'description':
            'Same as for kl=1, but for fixed P (from sw.data) '
            'and T from the item ndat1 in sw.data to a '
            'user-defined value tlimit, with user-defined '
            'T-steps.',
          'required': [
            'ndat1',
            'kl',
            'iopen',
            'dt',
            'tlimit'
            # 'fopen' is not always required, only if iopen=1
          ],
          'properties': {
            'ndat1': {
              'type': 'integer',
              'description':
                'Computations are performed on item ndat1 '
                'of sw.data'
            },
            'kl': {
              'type': 'integer',
              'enum': [2],  # the only one accepted value
            },
            'iopen': {
              'type': 'integer',
              'enum': [0, 1],
              'description':
                '0 for closed-system calculations, '
                '1 for open system calculations.'
            },
            'fopen': {
              'type': 'string',
              'pattern':
                r'^([+-]?([\d]+\.|[\d]*\.[\d]+))'
                r'([Dd][+-]?[\d]+)?$',
              'description':
                'Only used with iopen =1. It specifies '
                'the weight fraction of fluid phase lost '
                'at each subsequent computation step.'
            },
            'dt': {
              'type': 'string',
              'pattern':
                r'^([+-]?([\d]+\.|[\d]*\.[\d]+))'
                r'([Dd][+-]?[\d]+)?$',
              'description':
                'The length of the T-steps (either '
                'positive or negative).'
            },
            'tlimit': {
              'type': 'string',
              'pattern':
                r'^([+-]?([\d]+\.|[\d]*\.[\d]+))'
                r'([Dd][+-]?[\d]+)?$',
              'description':
                'The temperature up to which separate '
                'computations are performed. It can be '
                'either higher (dt>0) or lower (dt<0) '
                'than T.'
            }
          }
        },
        {
          'title': '[placeholder per titolo 4]',
          'description':
            'H2O and CO2 in sw.data items represent amounts '
            'dissolved in the melt phase. For user-defined '
            'melt composition and temperature, SOLWCAD '
            'returns the equilibrium pressure and composition '
            'of the coexisting fluid phase. Computations are '
            'performed from item ndat1 to item ndat2 (only '
            'one computation is performed if ndat1=ndat2 ). '
            'This kind of computation is commonly used in the '
            'analysis of melt inclusion data.',
          'required': [
            'ndat1',
            'ndat2',
            'kl'
          ],
          'properties': {
            'ndat1': {
              'type': 'integer',
              'description':
                'Computations are performed on item ndat1 '
                'of sw.data'
            },
            'ndat2': {
              'type': 'integer',
              'description':
                'Computations are performed up to item '
                'ndat2 of sw.data'
            },
            'kl': {
              'type': 'integer',
              'enum': [-1],   # the only one accepted value
            }
            # not used for kl = 0:
            # 'iopen', 'fopen', 'dt', 'tlimit'
          }
        }
      ]
    },
    'sw.data': {
      'title': 'User data',
      'description':
        'user-defined conditions in terms of pressure, temperature, '
        'and composition, each one arranged on a single item. Each '
        'item contains the followings: pressure (Pa); '
        'temperature (K); H2O content (wt fraction)**; '
        'CO2 content (wt fraction)**; the following ten quantities '
        'specify the volatile-free melt composition (wt fraction)***, '
        'in the following order: SiO2; TiO2; Al2O3; Fe2O3; FeO; MnO; '
        'MgO; CaO; Na2O; K2O. '
        '**H2O and CO2 contents may refer to i) total amounts in the '
        'two-phase magma, equal to (mass of volatile in the '
        'fluid + mass of volatile dissolved in the melt) / (mass of '
        'the gas phase + mass of the melt phase); or ii) the amounts '
        'dissolved in the melt phase, that is, (mass of volatile '
        'dissolved in the melt) / (mass of the melt phase). The '
        'specific choice is determined by the parameter kl in '
        'swinput.data.',
      'type': 'array',
      'minItems': 1,
      'items': {
        'type': 'array',
        'minItems': 14,
        'maxItems': 14,
        'items': {
          'type': 'string',
          'pattern':
            r'^([+-]?([\d]+\.|[\d]*\.[\d]+))'
            r'([Dd][+-]?[\d]+)?$',
        }
      }
    }
  }
}

#: Process metadata and description
PROCESS_METADATA = {
  # process.yaml -> processSummary.yaml
  # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

  # Required properties:
  # ####################

  'id': 'solwcad',
  # type string

  'version': '1.0.1',
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
    'value',
# Currently the framework does not support all outputs by reference.
# The processor have one output only, therefore reference is not supported.
#    'reference' 
  ],
  # type: array, 
  #   items: {type: string, enum: ['value', 'reference'], default: 'value'}

  'links': [{
    'href': 'https://civ.pi.ingv.it/project/solwcad/',
    'rel': 'about',
    'type': 'text/html',
    'hreflang': 'en-US',
    'title': 'SOLWCAD | Computational Infrastructure for Volcanology'
  },
  {
    'href': 'https://www.pi.ingv.it/progetti/eurovolc/#solwcad',
    'rel': 'alternate',
    'type': 'text/html',
    'hreflang': 'en-US',
    'title': 'EUROVOLC: Volcano Dynamics Computational Centre'
  },
  {
    'href': 'https://www.sciencedirect.com/science/article/pii/S0009254106000532?via%3Dihub',
    'rel': 'describedby',
    'type': 'text/html',
    'hreflang': 'en-US',
    'title': 'The compositional dependence of the saturation surface of H2O + CO2 fluids in silicate melts'
  }],
  # type: array, 
  #   items: {type: object, required: 'href', properties:
  #       href: type: string, rel: type: string,
  #       type: type: string, hreflang: type: string,
  #       title: type: string }

  # process.yaml -> processSummary.yaml -> descriptionType.yaml
  # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

  # Optional properties:
  # ####################

  'title': 'SOLWCAD',
  # type: string

  'description':
    'Fortran code to compute the saturation surface of H2O-CO2 '
    'fluids in silicate melts of arbitrary composition.',
  # type: string

  'keywords': ['Fortran code', 'saturation surface', 'other keywords...'],
  # type: array
  #   items: type: string
    
  # 'metadata':
  # type: array
  #   items: {type: object, title: string, role: string, href: string}

  # additionalParameters (metadata.yaml + parameters [additionalParameter.yaml]) 


  # process.yaml
  # >>>>>>>>>>>>
  'inputs': {
    'swinput.data': {
      'title': INPUT_SCHEMA['properties']['swinput.data']['title'],
      'description': INPUT_SCHEMA['properties']['swinput.data']['description'],
      'schema': INPUT_SCHEMA['properties']['swinput.data'],
      'minOccurs': 1,
      'maxOccurs': 1
    },
    'sw.data': {
      'title': INPUT_SCHEMA['properties']['sw.data']['title'],
      'description': INPUT_SCHEMA['properties']['sw.data']['description'],
      'schema': INPUT_SCHEMA['properties']['sw.data'],
      'minOccurs': 1,
      'maxOccurs': 1
    }
  },
  
  'outputs': {
    'solwcad_out': {
      'title': 'Output result',
      'description':
        'Each record item contains the following quantities: '
        'Pressure (Mpa); Temperature (K); Total ( kl >0) or '
        'dissolved ( kl =-1) H2O (wt%); '
        'Total ( kl >0) or dissolved ( kl =-1) CO2 (wt%); '
        'H2O dissolved in the melt (wt%); '
        'CO2 dissolved in the melt (ppm); CO2 in the fluid (wt%); '
        'CO2 in the fluid (mol%); Amount of fluid phase '
        'in magma (wt%); Amount of fluid phase in magma (vol%); '
        'Density of the melt phase (kg/m3 ); Density of the gas '
        'phase (kg/m3 ); Density of the two-phase magma (kg/m3 ); '
        'Viscosity of the melt phase [log (Pa s)]; Viscosity of '
        'the two-phase magma [log (Pa s)].',
      'minOccurs': 1,
      'maxOccurs': 1,
      'schema': {
        'oneOf': [
          {
            'title': 'JSON Array',
            'type': 'array',
            'minItems': 1,
            'items': {
              'type': 'array',
              'minItems': 15,
              'maxItems': 15,
              'items': {
                'type': 'string',
                'pattern':
                  r'^([+-]?(?:[[:digit:]]+\.|[[:digit:]]*\.'
                  r'[[:digit:]]+))(?:[Dd][+-]?[[:digit:]]+)?$',
              }
            },
            'contentMediaType': 'application/json'
          },
          {
            'title': 'Plain text Array',
            'type': 'array',
            'minItems': 1,
            'items': {
              'type': 'array',
              'minItems': 15,
              'maxItems': 15,
              'items': {
                'type': 'string',
                'pattern':
                  r'^([+-]?(?:[[:digit:]]+\.|[[:digit:]]*\.'
                  r'[[:digit:]]+))(?:[Dd][+-]?[[:digit:]]+)?$',
              }
            },
            'contentMediaType': 'text/plain'
          }
        ]
      }
    }
  },
  
  
  'examples': [
    {
      'payload_example': {
        'inputs': {
          'swinput.data': {
            'value': {'ndat1': 1, 'ndat2': 2, 'kl': 0}
          },
          'sw.data': [
            [
              '1.00d8', '1273.', '.0400', '.0200', '.7653', '.0032', '.1201',
              '.0027', '.0246', '.0006', '.0018', '.0132', '.0378', '.0306'
            ],
            [
              '2.00d8', '1173.', '.0200', '.0010', '.7053', '.0032', '.1301',
              '.0027', '.0146', '.0006', '.0118', '.0232', '.0378', '.0306'
            ]
          ]
        },
        'outputs': {
          'solwcad_out': {
            'format': {
              'mediaType': 'text/plain'
            }
          }
        }
      }
    },
    {
        'curl_example': (
            'curl -i -k -L -X POST '
            '"https://voice.pi.ingv.it/geoinquire/processes/solwcad/execution" '
            '-H "Content-Type: application/json" '
            '-d \'{ "inputs":{"swinput.data":{"value":{'
            '"ndat1":1,"ndat2":2,"kl":0}},'
            '"sw.data":['
            '["1.00d8","1273.",".0400",".0200",".7653",'
            '".0032",".1201",".0027",".0246",".0006",".0018",'
            '".0132",".0378",".0306"],'
            '["2.00d8","1173.",".0200",".0010",'
            '".7053",".0032",".1301",".0027",".0146",".0006",'
            '".0118",".0232",".0378",".0306"]]}, '
            '"outputs":{"solwcad_out":{"format":{"mediaType":"text/plain"}}}}\''
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
          '"https://voice.pi.ingv.it/geoinquire/jobs/<jobID>/results?f=json"'
    }
  ]

    # curl localhost:5000/processes/solwcad/execution -H 'Content-Type: application/json' -d '{"inputs": {"swinput.data": {"value": {"ndat1": 1, "ndat2": 2, "kl": 0}}, "sw.data": [["1.00d8", "1273.", ".0400", ".0200", ".7653", ".0032", ".1201", ".0027", ".0246", ".0006", ".0018", ".0132", ".0378", ".0306"], ["2.00d8", "1173.", ".0200", ".0010", ".7053", ".0032", ".1301", ".0027", ".0146", ".0006", ".0118", ".0232", ".0378", ".0306"] ] } }'
    # curl localhost:5000/processes/solwcad/execution -H 'Content-Type: application/json' -d '{"inputs": {"swinput.data": {"value": {"ndat1": 1, "ndat2": 2, "kl": 0}}, "sw.data": [["1.00d8", "1273.", ".0400", ".0200", ".7653", ".0032", ".1201", ".0027", ".0246", ".0006", ".0018", ".0132", ".0378", ".0306"], ["2.00d8", "1173.", ".0200", ".0010", ".7053", ".0032", ".1301", ".0027", ".0146", ".0006", ".0118", ".0232", ".0378", ".0306"] ] }, "outputs": {"solwcad_out": {"format": {"mediaType": "text/plain"} } } }'
    #
    # curl -k -L -X POST "https://voice.pi.ingv.it/geoinquire/processes/solwcad/execution" -H "Content-Type: application/json" -d '{ "inputs" : {  "swinput.data" : { "value" : { "ndat1" : 1 , "ndat2" : 2 , "kl" : 0 } }, "sw.data" : [ [ "1.00d8" , "1273." , ".0400" , ".0200" , ".7653" , ".0032" , ".1201" , ".0027" , ".0246" , ".0006" , ".0018" , ".0132" , ".0378" , ".0306" ], [ "2.00d8" , "1173." , ".0200" , ".0010" , ".7053" , ".0032" , ".1301" , ".0027" , ".0146" , ".0006" , ".0118" , ".0232" , ".0378" , ".0306" ] ] } }'
    #
}


class SolwcadProcessor(BaseRemoteExecutionProcessorLocalReference):
    """Solwcad Processor example"""
    def __init__(self, processor_def):
        """
        Initialize object
        :param processor_def: provider definition

        :returns: pygeoapi.process.solwcad.SolwcadProcessor
        """
        super().__init__(processor_def, PROCESS_METADATA)
        self.supports_outputs = True

    def prepare_output(self, info, working_path: Path, req_outputs):
        # Checks for error on outputs request performed by
        # base class in execute().

        # Prepare outputs
        # ###############

        # output file-name returned as code parameter
        code_params = info['params']
        solwcad_out = []
        with open(
            working_path / code_params['-output'], mode='r+t'
        ) as output_file:
            while len(line_items := output_file.readline().strip('\n')) > 0:
                fields = line_items.split()
                if len(fields) != 15:
                    raise ProcessorExecuteError(
                        'Program error: report to the administrator'
                    )
                solwcad_out.append(fields)

        produced_outputs = {}
        try:
            if 'solwcad_out' in req_outputs:
                format = req_outputs.get('solwcad_out').get('format')
                if format is None:
                    # set to default
                    # (TODO: get first contentMediaType for the output_ID)
                    mediaType = 'application/json'
                elif not isinstance(format, dict):
                    raise ProcessorExecuteError(
                        'Invalid output parameter: format is not a dictionary.'
                    )
                else:
                    mediaType = format.get('mediaType', 'application/json')

                # (TODO: get accepted mediaType from contentMediaType)
                if mediaType not in ['application/json', 'text/plain']:
                    # set to default
                    # (TODO: get first contentMediaType for the output_ID)
                    mediaType = 'application/json'

                produced_outputs['solwcad_out'] = {'mediaType': mediaType}

                if mediaType == 'application/json':
                    # NOTE: should be
                    # value = json.dumps(solwcad_out)
                    # but this way compensate a bug in the framework.
                    value = solwcad_out
                elif mediaType == 'text/plain':
                    value = '\n'.join(', '.join(row) for row in solwcad_out)
                else: # should never happen:
                    raise ProcessorExecuteError('Program error.')
                
                transmission_mode = req_outputs['solwcad_out'].get(
                    'transmissionMode', ''
                )
                if transmission_mode == 'value':
                    produced_outputs['solwcad_out']['value'] =  value
                elif (transmission_mode == 'reference'):
                    if mediaType == 'application/json':
                        filename = f'{self.job_id}_solwcad_out.json'
                        dst_file = Path(self.base_reference_path) / filename
                        with open(dst_file, 'w', encoding='utf-8') as out_file:
                            # NOTE: value should already contain the JSON string,
                            # but (as for the NOTE above) it is not.
                            # When the bug in the framework is solved should be substituted by:
                            # out_file.write(value)
                            json.dump(value, out_file)
                    elif mediaType == 'text/plain':
                        filename = f'{self.job_id}_solwcad_out.txt'
                        dst_file = Path(self.base_reference_path) / filename
                        with open(dst_file, 'w', encoding='utf-8') as out_file:
                            out_file.write(value)
                    else: # should never happen:
                        raise ProcessorExecuteError('Program error.')
                    
                    file_href = f'{self.base_reference_url}/{filename}'
                    produced_outputs['solwcad_out']['href'] = file_href
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

        swinput = data['swinput.data']
        sw = data['sw.data']

        kl = swinput.get('kl', None)

        ndat1 = swinput.get('ndat1', None)
        ndat2 = swinput.get('ndat2', None)
        iopen = swinput.get('iopen', None)
        fopen = swinput.get('fopen', None)
        dt = swinput.get('dt', None)
        tlimit = swinput.get('tlimit', None)
        match kl:
            case 0 | -1:
                int(ndat1)
                int(ndat2)
                swinput['iopen'] = 0
                swinput['fopen'] = swinput['dt'] = swinput['tlimit'] = '0.0'
            case 1:
                swinput['iopen'] = iopen = int(iopen)
                swinput['fopen'] = fopen = str(fopen)
                if (iopen == 1):
                    pass
                else:
                    swinput['fopen'] = '0.0'

                swinput['ndat2'] = 0
                swinput['dt'] = swinput['tlimit'] = '0.0'
            case 2:
                swinput['iopen'] = iopen = int(iopen)
                swinput['fopen'] = fopen = str(fopen)
                if (iopen == 1):
                    pass
                else:
                    swinput['fopen'] = '0.0'

                swinput['dt'] = dt = str(dt)
                swinput['tlimit'] = tlimit = str(tlimit)
                swinput['ndat2'] = 0

        # Create input file(s) required to run the 'code'
        # ###############################################
        swinput_filename = 'swinput.data'
        # The file must not exist, otherwise there is a problem!
        with open(working_path / swinput_filename,
                  mode='x+t') as swinput_file:
            swinput_file.write(str(swinput['ndat1']) + '\t')
            swinput_file.write(str(swinput['ndat2']) + '\t')
            swinput_file.write(str(swinput['kl']) + '\t')
            swinput_file.write(str(swinput['iopen']) + '\t')
            swinput_file.write(str(swinput['fopen']) + '\t')
            swinput_file.write(str(swinput['dt']) + '\t')
            swinput_file.write(str(swinput['tlimit']) + '\n')

        sw_filename = 'sw.data'
        # The file must not exist, otherwise there is a problem!
        with open(working_path / sw_filename, mode='x+t') as sw_file:
            for line in sw:
                for value in line:
                    sw_file.write(str(value) + '\t')
                sw_file.write('\n')

        # Create the dictionary with the properties to be passed to the 'code'
        # where property_name=parameter_name, property_value=parameter_value
        # ###############################################
        code_input_param = {}
        code_input_param['-swinput'] = swinput_filename
        code_input_param['-sw'] = sw_filename
        code_input_param['-output'] = 'output.txt'

        return code_input_param

    def __repr__(self):
        return f'<SolwcadProcessor> {self.name}'
