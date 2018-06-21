import json
import logging
import os
import pandas as pd
import re
import requests
import sys
import xmltodict

try:
    # Python 2.7
    from urllib import urlencode
except ImportError:
    # Python 3.x
    from urllib.parse import urlencode

# Setting up logging
logging.basicConfig(filename='data/bin/cosmic_uniprot_map.log', filemode='w', level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout)) # Print to stderror

# Configuration
COSMIC_FILE_PATH = 'data/cosmic.csv'
OUTPUT_FILE_PATH = 'data/cosmic_uniprot_ids.csv'

# Constants
HUMAN_TAXON = 9606 # Corresponds to http://purl.uniprot.org/core/taxonomy/9606
UNIPROT_API_URL = 'http://www.uniprot.org/uniprot/'

def main():
    # Checking if COSMIC file exists
    if not os.path.isfile(COSMIC_FILE_PATH):
        logging.fatal('COSMIC data file not found.')
        raise FileNotFoundError

    # Read COSMIC csv, create output map
    cosmic = pd.read_csv(COSMIC_FILE_PATH, sep=',')
    output_map = pd.DataFrame(columns=['EntrezGeneId', 'UniProtID', 'UniProtVersion'])

    for index, row in cosmic.iterrows():
        # Constructing request metadata
        params = constructParams(row['Entrez GeneId'], row['Gene Symbol'])
        headers = {'Content-Type': 'text/html'}

        # Making request
        r = requests.get(UNIPROT_API_URL, params=params, headers=headers)
        if r.status_code == 200:
            logging.info('GET {0}'.format(r.url))
        else:
            logging.warning('FAILED GET request {0} with code {1}.'.format(r.url, r.status_code))
            continue
        raw = r.text
        try:
            response = xmltodict.parse(raw) # Parse XML
        except xmltodict.expat.ExpatError:
            logging.warning('XML loading failed for Entrez ID {0} ({1})'.format(row['Entrez GeneId'], row['Gene Symbol']))
            continue
        
        # Extract Uniprot ID
        uniprot_id, version = extractUniprotID(response, row['Entrez GeneId'])

        # Adding to output
        output_map.loc[index] = [row['Entrez GeneId'], uniprot_id, version]

    # Writing output csv
    output_map.to_csv(OUTPUT_FILE_PATH, index=False)


def extractUniprotID(response, entrez):
    uniprot_id = ''
    version = 0 # initial
    if type(response['uniprot']['entry']) is list:
        for entry in response['uniprot']['entry']:
            # Check if it is for Uniprot
            try:
                if entry['@dataset'] == 'Swiss-Prot':
                    # Check if it is from latest possible version
                    if int(entry['@version']) > version:
                        # Only take one alias
                        uniprot_id = entry['accession'][0] if type(entry['accession']) is list else entry['accession']
                        version = int(entry['@version']) # update version
            except TypeError:
                continue
    else:
        entry = response['uniprot']['entry']
        # Only take one alias
        uniprot_id = entry['accession'][0] if type(entry['accession']) is list else entry['accession']
        version = int(entry['@version']) # update version
    if uniprot_id == '':
        # Uniprot ID not found
        logging.warning('FAILED Uniprot ID Extraction for Entrez ID {0}'.format(entrez))
        uniprot_id = 'NOTFOUND'
    else:
        logging.info('Entrez ID {0} mapped to {1} from version {2}'.format(entrez, uniprot_id, version))
    return uniprot_id, version

def constructParams(entrez, genename):
    query = 'GENEID:{0}+AND+{1}+AND+taxonomy:{2}'.format(entrez, genename, HUMAN_TAXON)
    request_param = {
        'query': query,
        'format': 'xml'
    }
    return request_param

if __name__ == "__main__":
    main()