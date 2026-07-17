# Changelog

## [1.0.0] - 2026-03-06
Initial public release

## [1.0.1] - 2026-03-06
Metadata updates

## [1.0.2] - 2026-04-23
Service updates

## [1.1.0] - 2026-06-24
Change package name.
Minor fixes.

## [1.1.1] - 2026-06-29
Fixed reference to pygeoapi project.

## [1.2.0] - 2026-07-17
Unified string delimiter overall the project to be single quotes.

Use of a temporary custom Manager (PostgreSQLManagerWithDelete) to handle
removal of Processor specific resource when a DELETE <job_id> is received.
Added Manager class PostgreSQLManagerWithDelete in 
process/manager/postgresql.py

In all Processor added function remove_resources() to be used by
the custom Manager PostgreSQLManagerWithDelete.

In metadata of all Processor fixed example URLs to include "/geoinquire".

In all Processor commented out 'contentMediaType': 'application/json'
where 'type' is not 'string'.

CONDUIT:
- added placeholder for 'title' and 'description' metadata where missing.
Will be replaced after first implementaion of user interface.
- in output 'outfile':
  - fixed format to proper csv (i.e. comma delimited fields,
while previously were space delimited);
  - added header to result;
  - the metadata contentMediaType changed to 'text/csv; header=present';
  - where the original fields are in scientific format using Fortran specific
exponential 'D' or 'd', the scientific format is changed to use standard
'E' or 'e'

PYBOX:
- in output 'dem' and 'invasion_map', changed the schema to return a JSON
with two links, one for the GeoTIFF data (property 'geotiff'), the other for
the style to be used (property 'sld'). Both information ('geotiff' and 'sld')
will be available only by reference;
NOTE: future enhancement should consider using 'profile', see
https://github.com/opengeospatial/ogcapi-processes/issues/601
- in metadata, examples input 'lat' and 'lon' now refer to Vesuvio coordinates;

SOLWCAD:
- in metadata removed in 'outputTransmission' the item 'reference' (until the
framework will solve issue on returning reference only)
- output 'solwcad_out' now available in two format:
  - as 'type'='array' (therefore can be requested with 
  'format': {'mediaType': 'application/json'} )
  - as 'type'='string', 'contentMediaType': 'text/plain'
  (therefore can be requested with 'format': {'mediaType': 'text/plain'} )
Changed the schema for 'solwcad_out' accordingly.






