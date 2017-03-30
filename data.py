#!/usr/bin/env python
# -*- coding: utf-8 -*-

#The startpoint of this code was provided in the course material.  I have made modifications 
#to the shape_element function to accomplish data cleaning needs as pointed out from the audit process.

import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET
import cerberus
import schema


#OSM_PATH = "sample.osm"
OSM_PATH = "beaverton_oregon.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


#adding mapping and procedure to update street names
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
            "Trail", "Parkway", "Commons", "Circle", "Highway", "Loop", "Terrace", "Way"]
mapping = { "St": "Street",
            "St.": "Street",
            "Rd.": "Road",
            "Ave": "Avenue",
            "Rd": "Road",
            "Dr": "Drive",
            "Hwy": "Highway",
            "GLN": "Glen"
            }

def update_street_name(name, mapping):
    #added try/expect to deal with streets to keep that aren't in expected
    #call this method from shape_element when we are iterating over the children and checking for lower_colon
    m = street_type_re.search(name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            try:
                name = re.sub(street_type_re, mapping[street_type], name)
            except:
                pass
    return name

def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements
    
    #added code for cleaning values of street name, postcode, and city names based on audit results
    if element.tag == 'node':
      for i in NODE_FIELDS:
        node_attribs[i] = element.attrib[i]
      for child in element:
        node_tags_dict = {}
        node_tags_dict['id'] = element.attrib['id']
        node_tags_dict['value'] = child.attrib['v']
        if PROBLEMCHARS.match(child.attrib['k']):
          continue
        elif LOWER_COLON.match(child.attrib['k']):
          node_tags_dict['type'] = child.attrib['k'].split(":", 1)[0]
          node_tags_dict['key'] = child.attrib['k'].split(":", 1)[1]
          if child.attrib['k'] =="addr:street":
            node_tags_dict['value'] = update_street_name(child.attrib['v'],mapping)
            tags.append(node_tags_dict)
          elif child.attrib['k']== "addr:postcode" or child.attrib['k'] == "tiger:zip_left" or child.attrib['k'] == "tiger:zip_right":
            node_tags_dict['value'] = child.attrib['v'][:5]
            #print('The Postal Code is {}'.format(node_tags_dict['value']))
            tags.append(node_tags_dict)
          elif child.attrib['k'] == "addr:city":
            node_tags_dict['value'] = child.attrib['v'].split(",")[0]
            #print('The City is {}'.format(node_tags_dict['value']))
            tags.append(node_tags_dict)
          else:
            tags.append(node_tags_dict)
        else:
          node_tags_dict["type"] = "regular"
          node_tags_dict["key"] = child.attrib["k"]
          tags.append(node_tags_dict)
            
      return {'node': node_attribs, 'node_tags': tags}
    
    elif element.tag == 'way':
        for i in WAY_FIELDS:
            way_attribs[i] = element.attrib[i]
            
        position = 0
        for child in element:
            if child.tag == 'tag':
                way_tags_dict = {}
                way_tags_dict['id'] = element.attrib['id']
                way_tags_dict['value'] = child.attrib['v']
                if PROBLEMCHARS.match(child.attrib['k']):
                    continue
                elif LOWER_COLON.match(child.attrib['k']):
                    way_tags_dict['type'] = child.attrib['k'].split(":", 1)[0]
                    way_tags_dict['key'] = child.attrib['k'].split(":", 1)[1]
                    if child.attrib['k'] =="addr:street":
                      way_tags_dict['value'] = update_street_name(child.attrib['v'],mapping)
                      tags.append(way_tags_dict)
                    elif child.attrib['k']== "addr:postcode" or child.attrib['k'] == "tiger:zip_left" or child.attrib['k'] == "tiger:zip_right":
                      way_tags_dict['value'] = child.attrib['v'][:5]
                      tags.append(way_tags_dict)
                    elif child.attrib['k'] == "addr:city":
                      way_tags_dict['value'] = child.attrib['v'].split(",")[0]
                      tags.append(way_tags_dict)
                    else:
                      tags.append(way_tags_dict)
                else:
                    way_tags_dict["type"] = "regular"
                    way_tags_dict["key"] = child.attrib["k"]
                    tags.append(way_tags_dict)
                
            elif child.tag == 'nd':
                way_nodes_dict = {}
                way_nodes_dict['id'] = element.attrib['id']
                way_nodes_dict['node_id'] = child.attrib['ref']
                way_nodes_dict['position'] = position
                position += 1
                way_nodes.append(way_nodes_dict)
                
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        
        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    process_map(OSM_PATH, validate=True)
    
