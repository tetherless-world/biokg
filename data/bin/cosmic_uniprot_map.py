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
# Print to stdout
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

# Configuration
COSMIC_FILE_PATH = 'data/cosmic.csv'
OUTPUT_FILE_PATH = 'data/cosmic_uniprot_ids.csv'

# Constants
HUMAN_TAXON = 9606 # Corresponds to http://purl.uniprot.org/core/taxonomy/9606
UNIPROT_API_URL = 'http://www.uniprot.org/uniprot/'
UNIPROT_PREFIX = 'http://www.uniprot.org/uniprot/'


def main():
    """
    Map each of the COSMIC IDs to their UniProt IDs, isolating the ID from the latest
    version of the UniProt database.
    """
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
            uniprot_id, version = 'NONE', 0 # Unknown
        else:    
            # Extract Uniprot ID
            uniprot_id, version = extractUniprotID(response, row['Entrez GeneId'])
        
        # Adding to output
        output_map.loc[index] = [row['Entrez GeneId'], uniprot_id, version]

    # Writing output csv
    output_map.to_csv(OUTPUT_FILE_PATH, index=False)


def extractUniprotID(response: xmltodict.OrderedDict, entrez: str) -> tuple:
    """
    Extract the UniProt ID from the response from an API call to the UniProt endpoint.

    :param  response:   Response object from the UniProt API call
    :param  entrez:     Entrez GeneId to be mapped to a UniProt ID
    :return:            Tuple of UniProt ID and the version of the database it was extracted from
    """
    uniprot_id = ''
    version = 0 # initial
    if type(response['uniprot']['entry']) is list:
        # Multiple versions of UniProt available
        logging.warning('More than one match for {0}.'.format(entrez))
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
        # One version of UniProt available
        entry = response['uniprot']['entry']
        # Only take one alias
        uniprot_id = entry['accession'][0] if type(entry['accession']) is list else entry['accession']
        version = int(entry['@version']) # update version
    if uniprot_id == '':
        # Uniprot ID not found
        logging.warning('FAILED Uniprot ID Extraction for Entrez ID {0}'.format(entrez))
        uniprot_id = 'NOTFOUND'
    else:
        uniprot_id = buildURI(uniprot_id)
        logging.info('Entrez ID {0} mapped to {1} from version {2}'.format(entrez, uniprot_id, version))
    return uniprot_id, version


def constructParams(entrez: str, genename: str, taxonomy: int = HUMAN_TAXON) -> dict:
    """
    Constructs a dictionary of parameters to be passed in the API call to the UniProt endpoint.

    :param  entrez      Entrez GeneId to be queried
    :param  genename    Name of the gene to be queried
    :param  taxonomy    Taxonomy to be queried (defaults to HUMAN_TAXON)
    :return:            Dictionary of the request parameters
    """
    query = 'GENEID:{0}+AND+{1}+AND+taxonomy:{2}'.format(entrez, genename, taxonomy)
    request_param = {
        'query': query,
        'format': 'xml'
    }
    return request_param


def buildURI(unirpot_id: str) -> str:
    """
    Builds a UniProt KB URI, using the prefix defined in the constants.

    :param  uniprot_id  UniProt KB ID to be converted to URI
    :return:            UniProt KB URI
    """
    return UNIPROT_PREFIX + unirpot_id


if __name__ == "__main__":
    main()