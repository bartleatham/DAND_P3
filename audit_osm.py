#!/usr/bin/env python
# -*- coding: utf-8 -*-

##This file contains audit procedures for auditing data from OSM database
#key procedures are: zip_codes_audit, city_names_audit, audit_streets
#audit_streets code comes from course material

import xml.etree.cElementTree as ET
import pprint
from collections import defaultdict
import re

#OSMFILE = "sample.osm"
OSMFILE = "beaverton_oregon.osm"

street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)


expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
            "Trail", "Parkway", "Commons", "Circle", "Highway", "Loop", "Terrace", "Way"]

# UPDATE THIS VARIABLE
mapping = { "St": "Street",
            "St.": "Street",
            "Rd.": "Road",
            "Ave": "Avenue",
            "Rd": "Road"
            }


def audit_street_type(street_types, street_name):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            street_types[street_type].add(street_name)


def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")


def audit(osmfile):
    osm_file = open(osmfile, "r")
    street_types = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'])
    osm_file.close()
    return street_types


def update_name(name, mapping):
    #added try/expect to deal with streets to keep that aren't in expected
    m = street_type_re.search(name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            try:
                name = re.sub(street_type_re, mapping[street_type], name)
            except:
                pass
    return name


def audit_streets():
    st_types = audit(OSMFILE)
    for st_type, ways in st_types.iteritems():
        for name in ways:
            better_name = update_name(name, mapping)
            print name, "=>", better_name

"""
This function parses the input file for user id's, returns the count and top 5 contributors.
"""
def user_contribute_count(filename):
    cont_count = defaultdict(int)
    for _, element in ET.iterparse(filename):
        if element.tag == "node":
            user = (element.attrib["user"])
            if user in cont_count:
                cont_count[user] += 1
            else:
                cont_count[user] = 1
        if element.tag == "way":
            user = (element.attrib["user"])
            if user in cont_count:
                cont_count[user] += 1
            else:
                cont_count[user] = 1
        if element.tag == "relation":
            user = (element.attrib["user"])
            if user in cont_count:
                cont_count[user] += 1
            else:
                cont_count[user] = 1    
    print('The total number of contributions to this OSM data file is {}.'.format(sum(cont_count.values())))
    print('There are {} unique contributors to this OSM data file.'.format(len(cont_count)))
    print('The top 5 contributors and thier contribution counts are:')
    pprint.pprint(sorted(cont_count.items(), key=lambda(k,v): v, reverse=True)[:5])
    

"""
This function audits the input fie for zip codes and flags if they are not exactly 5 digits'
"""
def zip_codes_audit(filename):
    cont_count = defaultdict(int)
    zipcodes = set()

    for event, element in ET.iterparse(filename):
        #if element.tag == 'node' or element.tag == 'way':
        for child in element:
            if child.tag == 'tag':
               
                if child.attrib['k'] == "addr:postcode" or child.attrib['k'] == "tiger:zip_left" or child.attrib['k'] == "tiger:zip_right":
                    value = (child.attrib['v']) 
                    if not re.match(r"^[0-9]{5}$", value):
                        print('This zip code is bad {}!'.format(value))
                        value = value[:5]
                        print('The cleaned up zip code will be {}'.format(value))
                    else:
                        zipcodes.add(value)
                else:
                    pass
    print('The zipcodes in the Beaverton Oregon region are:')
    pprint.pprint(zipcodes)

"""
This function returns set of city names'
"""
def city_names_audit(filename):
    cities = set()
    for event, element in ET.iterparse(filename):
        for child in element:
            if child.tag == 'tag':
               if child.attrib['k'] == "addr:city":
                    if re.findall(r',', child.attrib['v']):
                        cities.add(child.attrib['v'])
                        value = (child.attrib['v'].split(",")[0])
                        print('{} will be replaced with {}'.format(child.attrib['v'], value))
                    else:
                        cities.add(child.attrib['v'])
            else:
                pass
    pprint.pprint(cities)

if __name__ == "__main__":
    zip_codes_audit(OSMFILE)
    city_names_audit(OSMFILE)
    audit_streets()
