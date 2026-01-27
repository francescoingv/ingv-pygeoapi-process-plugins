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

import logging
import re
import copy
import base64

from pathlib import Path

from pygeoapi.process.base import (
    ProcessorExecuteError,
    #    ProcessorGenericError,
)
from ingv_plugin_pygeoapi.process.base_remote_execution import BaseRemoteExecutionProcessor

LOGGER = logging.getLogger(__name__)

#: Process metadata and description
PROCESS_METADATA = {
    # process.yaml -> processSummary.yaml

    # Proprietà required:
    'id': 'pybox',
    # type string

    'version': '1.0.0',
    # type string

    # Altre proprietà non required:
    'jobControlOptions': [
        'async-execute',
        'sync-execute'
    ],
    # type: array,
    #   items: {type: string, enum: ['sync-execute', 'async-execute', 'dismiss']}
    
    #'proprieta_aggiunta': 'altra proprietà',
    
    # outputTransmission
    # type: array, 
    #   items: {type: string, enum: ['value', 'reference'], default: 'value'}
    'outputTransmission': [
        'value'
    ],

    # links:
    # type: array, 
    #   items: {type: object, required: 'href', properties:
    #       href: type: string
    #       rel: type: string, example: 'service'
    #       type: type: string, example: 'application/json'
    #       hreflang: type: string, example: 'en'
    #       title: type: string

    # process.yaml -> processSummary.yaml -> descriptionType.yml
    # Tutte proprietà non required:
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
    
    'keywords': ['TBD'],
    # type: array
    #   items: type: string

    # process.yaml
    'inputs': {
        # inputDescription.yaml
        'lat': {
            'title': 'Latitude',
            'description': 'Geographic latitude of the vent in Decimal degrees',
            'minOccurs': 1,
            'maxOccurs': 1,
            'schema': {
                'type': 'number',
                'minimum': -90.0,
                'maximum': 90.0
            }
        },
        'lon': {
            'title': 'Longitude',
            'description': 'Geographic longitude of the vent in Decimal degrees',
            'minOccurs': 1,
            'maxOccurs': 1,
            'schema': {
                'type': 'number',
                'minimum': -180.0,
                'maximum': 180.0
            }
        },
        'l0': {
            'title': 'Initial Radius',
            'description': 'Initial horizontal extent (l0) of the current in meters',
            'minOccurs': 1,
            'maxOccurs': 1,
            'schema': {
                'type': 'number',
                'minimum': 100.0,
                'maximum': 2000.0
            }
        },
        'h0': {
            'title': 'Initial height',
            'description': 'initial vertical thickness (h0) of the current in meters',
            'minOccurs': 1,
            'maxOccurs': 1,
            'schema': {
                'type': 'number',
                'minimum': 100.0,
                'maximum': 2000.0
            }
        },
        'theta0': {
            'title': 'Temperature',
            'description': 'Initial temperature of the current in Kelvin',
            'minOccurs': 1,
            'maxOccurs': 1,
            'schema': {
                'type': 'number',
                'minimum': 300.0,
                'maximum': 1400.0
            }
        },
        'multiple_values': {
            'title': 'valori multipli',
            'description':
                'When simulating multiple particle classes, the volume fraction '
                '(eps0), density (rhos), and diameter (ds) of each class should '
                'be specified and the sum of eps0 must be < 1',
            'minOccurs': 1,
            'maxOccurs': 21,
            'schema': {
                'type': 'object',
                'required': [
                    'eps0',
                    'rhos',
                    'ds'
                ],
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
                        'description': 'Diameter of particle class (10 micron-5 mm) in meters',
                        'type': 'number',
                        'minimum': 0.00001,
                        'maximum': 0.005
                    }
                }
            }
        },
        'dt': {
            'title': 'Time step',
            'description': 'Temporal resolution of the numerical integration in seconds',
            'minOccurs': 1,
            'maxOccurs': 1,
            'schema': {
                'type': 'number',
                'minimum': 0.1,
                'maximum': 30.0
            }
        },
        'margin': {
            'title': 'Margin ',
            'description': '-x, -y, x, y distance from the given vent location (i.e. bounding box of the requested DSM) in meters',
            'minOccurs': 1,
            'maxOccurs': 1,
            'schema': {
                'type': 'number',
                'minimum': 5000,
                'maximum': 50000
            }
        }
    },
    'outputs': {
#
#"schema": { # per geotiff
# {
#  "type": "string",
#  "contentEncoding": "binary",
#  "contentMediaType": "application/tiff; application=geotiff"
# }
#}
        'input_data': {
            'title': 'Input parameters',
            'description':
                'Log of all input parameters used',
            'schema': {
                "type": "string" # da verificare se ci sia una specifica migliore per un file di testo
            }
        },
        'dem': {
            'title': 'Primary DEM',
            'description':
                'The local DSM (GeoTIFF) used for the simulation.',
            'schema': { # da standard, pag. 77, "imagesOutput"
                "type": "string",
                "contentEncoding": "binary",
                "contentMediaType": "application/tiff; application=geotiff"
            }
        },
        'invasion_map': {
            'title': 'Invasion Map',
            'description':
                '2D GeoTIFF showing PDC invaded area, based on the energy conoid method.',
            'schema': { # da standard, pag. 77, "imagesOutput"
                "type": "string",
                "contentEncoding": "binary",
                "contentMediaType": "application/tiff; application=geotiff"
            }
        },
        'temporal_evolution': {
            'title': 'Spatial evolution of current mean properties.',
            'description':
                'Spatial evolution of current mean properties.',
#            'minOccurs': 1,
#            'maxOccurs': 'unbounded',
            'schema': {
                'contentMediaType': 'application/json', # da verificare che sia corretto .
                'type': 'object',
                'required': [
                    'Domain', 'Series'
                ],
                'properties': {
                    'Domain': {
                        'type': 'object',
                        'required': [
                            'label', 'unit', 'values'
                        ],
                        'properties': {
                            'label': {
                                'type': 'string'
                            },
                            'unit':  {
                                'type': 'string'
                            },
                            'description': {
                                'type': 'string'
                            },
                            'values': {
                                'type': 'array',
                                'items': {
                                    'type': 'number'
                                }
                            }
                        }
                    },
                    'Series': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'required': [
                                'label', 'unit', 'values'
                            ],
                            'properties': {
                                'label': {
                                    'type': 'string'
                                },
                                'unit':  {
                                    'type': 'string'
                                },
                                'description': {
                                    'type': 'string'
                                },
                                'values': {
                                    'type': 'array',
                                    'items': {
                                        'type': 'number'
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        'deposit_thickness': {
            'title': 'Deposit thickness left by the current with distance from vent.',
            'description':
                'Deposit thickness left by the current with distance from vent.',
#            'minOccurs': 1,
#            'maxOccurs': 'unbounded',
            'schema': {
                'contentMediaType': 'application/json', # da verificare che sia corretto .
                'type': 'object',
                'required': [
                    'Domain', 'Series'
                ],
                'properties': {
                    'Domain': {
                        'type': 'object',
                        'required': [
                            'label', 'unit', 'values'
                        ],
                        'properties': {
                            'label': {
                                'type': 'string'
                            },
                            'unit':  {
                                'type': 'string'
                            },
                            'values': {
                                'type': 'array',
                                'items': {
                                    'type': 'number'
                                }
                            }
                        }
                    },
                    'Series': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'required': [
                                'label', 'unit', 'values'
                            ],
                            'properties': {
                                'label': {
                                    'type': 'string'
                                },
                                'unit':  {
                                    'type': 'string'
                                },
                                'values': {
                                    'type': 'array',
                                    'items': {
                                        'type': 'number'
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
#        'csv': {
#            'title': 'Dati in formato csv',
#            'description': 'TBD',
#            'schema': {
#                'type': 'string',
#                'contentMediaType': 'text/csv'
#            }
#        }
    },
    'links': [{
        'type': 'text/html',
        'rel': 'about',
        'title': 'information',
        'href': 'https://example.org/process',
        'hreflang': 'en-US'
      }],
    'example': {
        'inputs': {
            'components': {
                'value': {'f': 1.0e8, 'p': 1.0e8, 't': 1050.0e0, 'd': 60.0e0,
                          'l': 4000.0e0, 'sio2': 0.7669, 'tio2': 0.0012, 
                          'al2o3': 0.1322, 'fe2o3': 0.0039, 'feo': 0.0038,
                          'mno': 0.0007, 'mgo': 0.0006, 'cao': 0.0080, 
                          'na2o': 0.0300, 'k2o': 0.0512, 'h2o': 0.0500e0,
                          'co2': 0.0200e0, 'b': 1.0e11, 'c': 0.2e0, 'den': 2800.0e0
                }
            }
        },
        'outputs': {
            'grafico_1': {
                'transmissionMode': 'value'
            },
            'grafico_2': {
                'transmissionMode': 'value'
            }
        }
    }
    # curl localhost:5000/processes/conduit/execution -H 'Content-Type: application/json' -d '{ "inputs" : { "components" : { "value" : {"f": 1.0e8, "p": 1.0e8, "t": 1050.0e0, "d": 60.0e0, "l": 4000.0e0, "sio2": 0.7669, "tio2": 0.0012, "al2o3": 0.1322, "fe2o3": 0.0039, "feo": 0.0038, "mno": 0.0007, "mgo": 0.0006, "cao": 0.0080, "na2o": 0.0300, "k2o": 0.0512, "h2o": 0.0500e0, "co2": 0.0200e0, "b": 1.0e11, "c": 0.2e0, "den": 2800.0e0 } } }, "outputs" : { "grafico_1" : { "transmissionMode": "value" }, "grafico_2" : { "transmissionMode": "value" } } }'
    # curl localhost:5000/processes/conduit/execution -H 'Content-Type: application/json' -H 'Prefer: respond-async' -d '{ "inputs" : { "components" : { "value" : {"f": 1.0e8, "p": 1.0e8, "t": 1050.0e0, "d": 60.0e0, "l": 4000.0e0, "sio2": 0.7669, "tio2": 0.0012, "al2o3": 0.1322, "fe2o3": 0.0039, "feo": 0.0038, "mno": 0.0007, "mgo": 0.0006, "cao": 0.0080, "na2o": 0.0300, "k2o": 0.0512, "h2o": 0.0500e0, "co2": 0.0200e0, "b": 1.0e11, "c": 0.2e0, "den": 2800.0e0 } } }, "outputs" : { "grafico_1" : { "transmissionMode": "value" }, "grafico_2" : { "transmissionMode": "value" } } }'
    # curl -k -L -X POST "https://epos_geoinquire.pi.ingv.it/epos_pygeoapi/processes/conduit/execution" -H "Content-Type: application/json" -d '{ "inputs" : { "components" : { "value" : {"f": 1.0e8, "p": 1.0e8, "t": 1050.0e0, "d": 60.0e0, "l": 4000.0e0, "sio2": 0.7669, "tio2": 0.0012, "al2o3": 0.1322, "fe2o3": 0.0039, "feo": 0.0038, "mno": 0.0007, "mgo": 0.0006, "cao": 0.0080, "na2o": 0.0300, "k2o": 0.0512, "h2o": 0.0500e0, "co2": 0.0200e0, "b": 1.0e11, "c": 0.2e0, "den": 2800.0e0 } } }, "outputs" : { "grafico_1" : { "transmissionMode": "value" }, "grafico_2" : { "transmissionMode": "value" } } }'
    #
    # ovvero:
    # curl localhost:5000/processes/conduit/execution 
    #       -H 'Content-Type: application/json' 
    #       -d '{ 
    #               "inputs" : { 
    #                   "components" : { 
    #                       "value" : {
    #                           "f": 1.0e8, "p": 1.0e8, "t": 1050.0e0, "d": 60.0e0, "l": 4000.0e0, 
    #                           "sio2": 0.7669, "tio2": 0.0012, "al2o3": 0.1322, "fe2o3": 0.0039, 
    #                           "feo": 0.0038, "mno": 0.0007, "mgo": 0.0006, "cao": 0.0080, "na2o": 0.0300, 
    #                           "k2o": 0.0512, "h2o": 0.0500e0, "co2": 0.0200e0, "b": 1.0e11, "c": 0.2e0, 
    #                           "den": 2800.0e0 
    #                       } 
    #                   } 
    #               },
    #               "outputs" : { 
    #                   "grafico_1" : { 
    #                       "transmissionMode": "value"
    #                   }, 
    #                   "grafico_2" : { 
    #                       "transmissionMode": "value" 
    #                   } 
    #               } 
    #           }'
}


class PyboxProcessor(BaseRemoteExecutionProcessor):
    """Pybox Processor example"""
    def __init__(self, processor_def):
        """
        Initialize object
        :param processor_def: provider definition

        :returns: pygeoapi.process.pybox.PyboxProcessor
        """
        super().__init__(processor_def, PROCESS_METADATA)
        self.supports_outputs = True

        self.base_output_filename = "out_file"

    def prepare_output(self, info, working_dir, outputs):
        # Only one output:
        #   "output in requested format"
        #   mediatype "as per output definition from process description"

        # Note: the 'code' may return a URL instead of the value.
        # but in this case the "product" is a string in URL format,
        # NOT the object/file that can be retrieved at the given URL.

        # Questo è il mimetype dell'intero risultato, non dei singoli
        # elementi del risultato che sono definiti nei metadati.
        mimetype = 'application/json' 

        possible_outputs = self.metadata['outputs']

        if not bool(outputs):
            requested_outputs = possible_outputs
        else:
            requested_outputs = outputs

        # In funzione di quanto presente nel parametro outputs
        # predispongo gli elementi di output
        produced_outputs = {}

        if 'input_data' in requested_outputs:
            with open(
                Path(working_dir) / 
                f"{self.base_output_filename}_params.txt", 
                mode='r'
            ) as output_file:
                contenuto = output_file.read()
            produced_outputs['input_data'] = {
                'value': contenuto,
                'mediaType': 'text/plain'
            }

        if 'dem' in requested_outputs:
            with open(
                Path(working_dir) / 
                f"{self.base_output_filename}.tif", 
                mode='rb'
            ) as output_file:
                contenuto_bytes = output_file.read()
            produced_outputs['dem'] = {
                # ref. spefifiche, pag 63, "imagesOutput"
                'value': base64.b64encode(contenuto_bytes).decode('utf-8'),
                'encoding': 'base64',
                'mediaType': 'application/tiff; application=geotiff'
            }
        
        if 'invasion_map' in requested_outputs:
            with open(
                Path(working_dir) / 
                f"{self.base_output_filename}_EC2.tif", 
                mode='rb'
            ) as output_file:
                contenuto_bytes = output_file.read()
            produced_outputs['dem'] = {
                'value': base64.b64encode(contenuto_bytes).decode('utf-8'),
                'encoding': 'base64',
                'mediaType': 'application/tiff; application=geotiff'
            }
        
        if 'temporal_evolution' in requested_outputs:
            x_length = []
            y_height = []
            y_rho_c = []
            y_u = []
            y_TPE = []
            y_TKE = []
            y_hmax = []
            y_time = []
            y_eps_n = []    # colonne variabili (eps_0, eps_1, ...)

            with open(
                Path(working_dir) / 
                f"{self.base_output_filename}.csv", 
                mode='r'
            ) as output_file:
                for line in output_file:
                    # Salta righe vuote
                    if not line:
                        continue

                    # Salta intestazioni o righe non numeriche
                    if not line[0].isdigit() and line[0] != '-':
                        continue

                    # Rimuovi spazi e usa split per separare i valori
                    parts = line.split()

                    # Aggiungi i valori alle colonne
                    values = [float(p) for p in parts]
                    x_length.append(values[0])
                    y_height.append(values[1])
                    y_rho_c.append(values[2])
                    y_u.append(values[3])
                    y_TPE.append(values[4])
                    y_TKE.append(values[5])
                    y_hmax.append(values[6])
                    y_time.append(values[7])

                    # --- colonne variabili (dalla 9 in poi) ---
                    extra_values = values[8:]

                    # inizializza y_eps_n alla prima riga numerica
                    if not y_eps_n:
                        y_eps_n = [[] for _ in range(len(extra_values))]

                    # aggiunge ogni valore alla colonna corretta
                    for i, v in enumerate(extra_values):
                        y_eps_n[i].append(v)

            # serie fisse:
            series = [
                        {
                            'label': 'height(m)',
                            'unit': 'm',
                            'description': 'average thickness (height) of the current',
                            'values': y_height
                        },
                        {
                            'label': 'rho_c(kg/m3)',
                            'unit': 'kg/m^3',
                            'description': 'bulk density of the current',
                            'values': y_rho_c
                        },
                        {
                            'label': 'u(m/s)',
                            'unit': 'm/s',
                            'description': 'front propagation velocity',
                            'values': y_u
                        },
                        {
                            'label': 'TPE(J)',
                            'unit': 'J',
                            'description': 'total potential energy',
                            'values': y_TPE
                        },
                        {
                            'label': 'TKE(J)',
                            'unit': 'J',
                            'description': 'total kinetic energy',
                            'values': y_TKE
                        },
                        {
                            'label': 'hmax(m)',
                            'unit': 'm',
                            'description': 'maximum run-up height (potential to overcome topographic obstacles)',
                            'values': y_hmax
                        },
                        {
                            'label': 'time(s)',
                            'unit': 's',
                            'description': 'time from the start of the propagation',
                            'values': y_time
                        }
                    ]
            # aggiunta dinamica delle serie eps_n
            for i, eps_values in enumerate(y_eps_n):
                series.append(
                    {
                        'label': f'eps_{i}',
                        'unit': '-',
                        'description': f'volume fraction of particle class {i}',
                        'values': eps_values
                    }
                )
            produced_outputs['temporal_evolution'] = {
                'value': {
                    'Domain': {
                        'label': 'length(m)',
                        'description': 'distance of the current front from the vent',
                        'unit': 'm',
                        'values': x_length
                    },
                    'Series': series
                },
                'mediaType': 'application/json'
            }

        if 'deposit_thickness' in requested_outputs:
            x_position = []
            y_cumulative = []
            y_thikness_n = []    # colonne variabili (y_thikness_0, y_thikness_1, ...)
 
            with open(
                Path(working_dir) / 
                f"{self.base_output_filename}_thickness.csv", 
                mode='r'
            ) as output_file:
                for line in output_file:
                    # Salta righe vuote
                    if not line:
                        continue

                    # Salta intestazioni o righe non numeriche
                    if not line[0].isdigit() and line[0] != '-':
                        continue

                    # Rimuovi spazi e usa split per separare i valori
                    parts = line.split()
            
                    # Aggiungi i valori alle colonne
                    values = [float(p) for p in parts]
                    x_position.append(values[0])
                    y_cumulative.append(values[1])

                    # --- colonne variabili (dalla 3 in poi) ---
                    extra_values = values[2:]

                    # inizializza y_thikness_n alla prima riga numerica
                    if not y_thikness_n:
                        y_thikness_n = [[] for _ in range(len(extra_values))]

                    # aggiunge ogni valore alla colonna corretta
                    for i, v in enumerate(extra_values):
                        y_thikness_n[i].append(v)

            # serie fisse:
            series = [
                        {
                            'label': 'total deposit thickness(m)',
                            'unit': 'm',
                            'description': 'cumulative thickness of all deposited particle classes',
                            'values': y_cumulative
                        }
                    ]
            # aggiunta dinamica delle serie eps_n
            for i, thikness_values in enumerate(y_thikness_n):
                series.append(
                    {
                        'label': f'eps_{i}',
                        'unit': '-',
                        'description': f'granulometric class {i} deposit thickness(m)',
                        'values': thikness_values
                    }
                )
            produced_outputs['deposit_thickness'] = {
                'value': {
                    'Domain': {
                        'label': 'current front position(m)',
                        'description': 'front distance from vent at the moment of deposition',
                        'unit': 'm',
                        'values': x_position
                    },
                    'Series': series
                },
                'mediaType': 'application/json'
            }

        return mimetype, produced_outputs

    def prepare_input(self, data, working_dir, outputs):
        if bool(outputs):
            requested_output = set(outputs.keys() if isinstance(outputs, dict) else outputs)
            if requested_output - set(self.metadata['outputs']):
                err_msg = 'Outputs contains unexpected parameters.'
                raise ProcessorExecuteError(err_msg)

        # verifica che i parametri siano completi e non ce ne siano in eccesso.
        required_key_set = {'lat', 'lon', 'l0', 'h0', 'theta0',
                            'multiple_values','dt', 'margin'}
        keys_present = set(data.keys())
        if not required_key_set.issubset(keys_present):
            err_msg = 'Input does not contains all required parameters.'
            raise ProcessorExecuteError(err_msg)
        
        extra_keys = keys_present - required_key_set
        if extra_keys:
            err_msg = f"Input contains unexpected parameters: {', '.join(extra_keys)}."
            raise ProcessorExecuteError(err_msg)

        particle_classes = len(data['multiple_values'])
        if  particle_classes > 21:
            err_msg = "Input contains too many particle classes: max 21."
            raise ProcessorExecuteError(err_msg)
        valori_eps0 = []
        valori_rhos = []
        valori_ds = []
        try:
            for i, classe in enumerate(data['multiple_values'], 1):
                if not (0.001 <= classe['eps0'] <= 0.1):
                    raise ProcessorExecuteError(f"In multiple_values, item numer {i} of eps0: must be >=0.001 and <=0.1.")
                if not (500 <= classe['rhos'] <= 3500):
                    raise ProcessorExecuteError(f"In multiple_values, item numer {i} of rhos: must be >=500 and <=3500.")
                if not (0.00001 <= classe['ds'] <= 0.005):
                    raise ProcessorExecuteError(f"In multiple_values, item numer {i} of rdshos: must be >=0.00001 and <=0.005.")
                
                valori_eps0.append(classe['eps0'])
                valori_rhos.append(classe['rhos'])
                valori_ds.append(classe['ds'])

        except KeyError as e:
            err_msg = f"In multiple_values, the item numer {i} non conteneva la chiave {e}"
            raise ProcessorExecuteError(err_msg)
        if sum(valori_eps0) >= 1:
            err_msg = f"In multiple_values, the sum of eps0 must be < 1"
            raise ProcessorExecuteError(err_msg)


        # Create the dictionary with the properties to be passed to the 'code'
        # where property_name=parameter_name, property_value=parameter_value
        # ###############################################
        code_input_param = {}
        
        # Trasforma le liste di numeri in stringhe separate da spazi
        code_input_param['--eps0'] = " ".join(map(str, valori_eps0))
        code_input_param['--rhos'] = " ".join(map(str, valori_rhos))
        code_input_param['--ds']   = " ".join(map(str, valori_ds))

        # Altri parametri
        for name in data:
            if name == 'multiple_values':
                continue
            # verifica che il formato dei numeri sia corretto
            param_value = data[name]
            if name == 'lat':
                if not (-90.0 <= param_value <= 90):
                    raise ProcessorExecuteError(f"Value 'components[{name}]' must be >=-90.0 and <=90.")
            if name == 'lon':
                if not (-180.0 <= param_value <= 180):
                    raise ProcessorExecuteError(f"Value 'components[{name}]' must be >=-180.0 and <=180.")
            if name == 'l0':
                if not (100.0 <= param_value <= 2000):
                    raise ProcessorExecuteError(f"Value 'components[{name}]' must be >=100.0 and <=2000.")
            if name == 'h0':
                if not (100.0 <= param_value <= 2000):
                    raise ProcessorExecuteError(f"Value 'components[{name}]' must be >=100.0 and <=2000.")
            if name == 'theta0':
                if not (300.0 <= param_value <= 1400):
                    raise ProcessorExecuteError(f"Value 'components[{name}]' must be >=300.0 and <=1400.")
            if name == 'dt':
                if not (0.1 <= param_value <= 30):
                    raise ProcessorExecuteError(f"Value 'components[{name}]' must be >=0.1 and <=30.")
            if name == 'margin':
                if not (5000.0 <= param_value <= 50000):
                    raise ProcessorExecuteError(f"Value 'components[{name}]' must be >=5000.0 and <=50000.")
            if name == 'theta0':
                if not (300.0 <= param_value <= 1400):
                    raise ProcessorExecuteError(f"Value 'components[{name}]' must be >=300.0 and <=1400.")
            input_flag = '--' + name
            code_input_param[input_flag] = param_value

        # si gestisce il file di output
        code_input_param['-o'] = self.base_output_filename

        return code_input_param

    def __repr__(self):
        return f'<PyboxProcessor> {self.name}'
