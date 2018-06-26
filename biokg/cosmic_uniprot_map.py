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
logging.basicConfig(filename='log/cosmic_uniprot_map.log', filemode='w', level=logging.INFO)
# Print to stdout
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

# Configuration
COSMIC_FILE_PATH = 'data/cosmic.csv'
OUTPUT_FILE_PATH = 'data/cosmic_uniprot_ids.csv'

# Constants
HUMAN_TAXON = 9606 # Corresponds to http://purl.uniprot.org/core/taxonomy/9606
UNIPROT_API_URL = 'http://www.uniprot.org/uniprot/'
UNIPROT_PREFIX = 'http://www.uniprot.org/uniprot/'
RDF_NULL = 'NONE'


def mapToUniProt(entrez: str, gene_symbol: str) -> tuple:
    """
    Map a given COSMIC Entrez Gene ID and  Gene Symbol to a UniProt ID

    :param  entrez:         Entrez Gene ID to be converted
    :param  gene_symbol:    Gene symbol to be converted
    :return                 Corresponding UniProt ID
    """
    uniprot_id = __makeRequest(entrez, gene_symbol)
    return uniprot_id

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
    output_map = pd.DataFrame(columns=['EntrezGeneId', 'UniProtID'])

    for index, row in cosmic.iterrows():
        uniprot_id = __makeRequest(row['Entrez GeneId'], row['Gene Symbol'])

        # Adding to output
        output_map.loc[index] = [row['Entrez GeneId'], ','.join(uniprot_id)]

    # Writing output csv
    output_map.to_csv(OUTPUT_FILE_PATH, index=False)


def __makeRequest(entrez: str, gene_id: str) -> list:
    """
    Make request to the UniProt API, and extract the UniProt IDs

    :param  entrez:         Entrez Gene ID to be converted
    :param  gene_symbol:    Gene symbol to be converted
    :return:                Corresponding UniProt IDs
    """
    # Constructing request metadata
    params = __constructParams(entrez, gene_id)
    headers = {'Content-Type': 'text/html'}

    # Making request
    r = requests.get(UNIPROT_API_URL, params=params, headers=headers)
    if r.status_code == 200:
        logging.info('GET {0}'.format(r.url))
    else:
        logging.warning('FAILED GET request {0} with code {1}.'.format(r.url, r.status_code))
        return list() # Unknown

    # Parsing response
    raw = r.text

    try:
        response = xmltodict.parse(raw) # Parse XML
    except xmltodict.expat.ExpatError:
        logging.warning('XML loading failed for Entrez ID {0} ({1}).'.format(entrez, gene_id))
        return list() # Unknown
    else:
        # Extract UniProt ID
        uniprot_id = __extractUniprotID(response, entrez)
        return uniprot_id


    raw = r.text

def __extractUniprotID(response: xmltodict.OrderedDict, entrez: str) -> list:
    """
    Extract the UniProt ID from the response from an API call to the UniProt endpoint.

    :param  response:   Response object from the UniProt API call
    :param  entrez:     Entrez GeneId to be mapped to a UniProt ID
    :return:            Tuple of UniProt ID and the version of the database it was extracted from
    """
    uniprot_id = list()
    # Two cases - one protein mapping or multiple protein mappings
    if type(response['uniprot']['entry']) is list:
        # Multiple protein mappings available
        for entry in response['uniprot']['entry']:
            # Check if it is for Uniprot
            try:
                if entry['@dataset'] == 'Swiss-Prot':
                    # Append to list of IDs (only take one)
                    uniprot_id.append(entry['accession'][0] if type(entry['accession']) is list else entry['accession'])
            except TypeError:
                continue
    else:
        # Only version of UniProt available
        entry = response['uniprot']['entry']
        # Only take one alias
        uniprot_id.append(entry['accession'][0] if type(entry['accession']) is list else entry['accession'])

    if len(uniprot_id) == 0:
        # Uniprot ID not found
        logging.warning('FAILED Uniprot ID Extraction for Entrez ID {0}'.format(entrez))
        return uniprot_id
    else:
        uniprot_id = [__buildURI(i) for i in uniprot_id]
        logging.info('Entrez ID {0} mapped to {1}.'.format(entrez, uniprot_id))
    return uniprot_id


def __constructParams(entrez: str, genename: str, taxonomy: int = HUMAN_TAXON) -> dict:
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


def __buildURI(unirpot_id: str) -> str:
    """
    Builds a UniProt KB URI, using the prefix defined in the constants.

    :param  uniprot_id  UniProt KB ID to be converted to URI
    :return:            UniProt KB URI
    """
    return UNIPROT_PREFIX + unirpot_id


if __name__ == "__main__":
    main()