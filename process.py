import json
import os
import shapefile
import sys

class GeonamesEntry(object):

    def __init__(self, delimited_string):
        parts = delimited_string.split('\t')
        self.country_code = parts[0]
        self.postal_code = parts[1]
        self.name = parts[2]
        self.state = parts[4]
        self.county_code = parts[6]
        self.lat = float(parts[9])
        self.lng = float(parts[10])

        # Special case - if these are records for US territories,
        # we need to change the state. The source data has the
        # admin1 code as something other than what we expect
        if self.country_code in ('PR', 'VI', 'AS', 'GU'):
            self.state = self.country_code

    def __repr__(self):
        return self.postal_code

class RecordsCollection(object):
    def __init__(self):
        self.records = []

    def add_to_collection(self, record):
        self.records.append(record.to_geojson())

    def get_geojson_collection(self):
        return {
            'type': 'FeatureCollection',
            'features': reduce(lambda x,y: x+y,self.records)
        }

class ZipCodeRecord(object):

    def __init__(self):
        self.postal_code = None
        self.county_code = None
        self.state = None
        self.city = None
        self.shape = None
        self.latitude = None
        self.longitude = None

    def __repr__(self):
        return self.postal_code

    def to_geojson(self):
        return [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [
                            self.longitude,
                            self.latitude
                        ]
                    },
                    'properties': {
                        'postal-code': self.postal_code
                    }
                },
                {
                    'type': 'Feature',
                    'geometry': self.shape.__geo_interface__,
                    'properties': {
                        'postal-code': self.postal_code,
                        'county-code': self.county_code,
                        'state': self.state,
                        'city': self.city,
                    }
                }
            ]

if __name__ == '__main__':

    # Get all the entries from Geonames
    with open('source_data/US.txt', 'r') as f:
        entries = [line.strip() for line in f.readlines()]

    # Index the entries in a dictionary by key
    entries_by_zipcode = {}
    for line in entries:
        entry = GeonamesEntry(line)
        entries_by_zipcode[entry.postal_code] = entry

    # Get all the records from the shapefile
    sf = shapefile.Reader("source_data/cb_2014_us_zcta510_500k.shp")

    # Get references to the shapes and records inside the shapefile
    shapes = sf.shapes()
    records = sf.records()

    # Store a list of all the entries
    parsed_zcrecords = []

    # Iterate over all the data in the shapefiles
    for index in range(0, len(shapes)):

        current_record = records[index]
        current_shape = shapes[index]

        zcrecord = ZipCodeRecord()
        zcrecord.postal_code = current_record[2]
        zcrecord.shape = current_shape

        # Find the corresponding entry in the indexed zip code data
        try:
            entry = entries_by_zipcode[zcrecord.postal_code]
        except KeyError:
            print "Could not find geonames entry for zip code %s. Skipping." % zcrecord.postal_code
            continue

        zcrecord.county_code = entry.county_code
        zcrecord.state = entry.state
        zcrecord.city = entry.name
        zcrecord.latitude = entry.lat
        zcrecord.longitude = entry.lng

        parsed_zcrecords.append(zcrecord)

    records = RecordsCollection()
    # Write the entries out to disk
    for index, parsed_zcrecord in enumerate(parsed_zcrecords):
        print "Adding %s to collection" % parsed_zcrecord.postal_code
        records.add_to_collection(parsed_zcrecord)

    filename='US_zips.geojson'
    with open(filename, 'w') as f:
        f.write(json.dumps(records.get_geojson_collection(), indent=4))
