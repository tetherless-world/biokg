from __future__ import absolute_import
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
    from urllib import urlencode


# Setting up logging
logging.basicConfig(filename=u'log/cosmic_uniprot_map.log', filemode=u'w', level=logging.INFO)
# Print to stdout
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

# Configuration
COSMIC_FILE_PATH = u'data/cosmic.csv'
OUTPUT_FILE_PATH = u'data/cosmic_uniprot_ids.csv'

# Constants
HUMAN_TAXON = 9606 # Corresponds to http://purl.uniprot.org/core/taxonomy/9606
UNIPROT_API_URL = u'http://www.uniprot.org/uniprot/'
UNIPROT_PREFIX = u'http://www.uniprot.org/uniprot/'


def mapToUniProt(entrez, gene_symbol):
    u"""
    Map a given COSMIC Entrez Gene ID and  Gene Symbol to a UniProt ID

    :param  entrez:         Entrez Gene ID to be converted
    :param  gene_symbol:    Gene symbol to be converted
    :return                 Corresponding UniProt ID
    """
    uniprot_id = __makeRequest(entrez, gene_symbol)
    return uniprot_id

def main():
    u"""
    Map each of the COSMIC IDs to their UniProt IDs, isolating the ID from the latest
    version of the UniProt database.
    """
    # Checking if COSMIC file exists
    if not os.path.isfile(COSMIC_FILE_PATH):
        logging.fatal(u'COSMIC data file not found.')
        raise FileNotFoundError

    # Read COSMIC csv, create output map
    cosmic = pd.read_csv(COSMIC_FILE_PATH, sep=u',')
    output_map = pd.DataFrame(columns=[u'EntrezGeneId', u'UniProtID'])

    for index, row in cosmic.iterrows():
        uniprot_id = __makeRequest(row[u'Entrez GeneId'], row[u'Gene Symbol'])

        # Adding to output
        output_map.loc[index] = [row[u'Entrez GeneId'], u','.join(uniprot_id)]

    # Writing output csv
    output_map.to_csv(OUTPUT_FILE_PATH, index=False)


def __makeRequest(entrez, gene_id):
    u"""
    Make request to the UniProt API, and extract the UniProt IDs

    :param  entrez:         Entrez Gene ID to be converted
    :param  gene_symbol:    Gene symbol to be converted
    :return:                Corresponding UniProt IDs
    """
    # Constructing request metadata
    params = __constructParams(entrez, gene_id)
    headers = {u'Content-Type': u'text/html'}

    # Making request
    r = requests.get(UNIPROT_API_URL, params=params, headers=headers)
    if r.status_code == 200:
        logging.info(u'GET {0}'.format(r.url))
    else:
        logging.warning(u'FAILED GET request {0} with code {1}.'.format(r.url, r.status_code))
        return list() # Unknown

    # Parsing response
    raw = r.text

    try:
        response = xmltodict.parse(raw) # Parse XML
    except xmltodict.expat.ExpatError:
        logging.warning(u'XML loading failed for Entrez ID {0} ({1}).'.format(entrez, gene_id))
        return list() # Unknown
    else:
        # Extract UniProt ID
        uniprot_id = __extractUniprotID(response, entrez)
        return uniprot_id


    raw = r.text

def __extractUniprotID(response, entrez):
    u"""
    Extract the UniProt ID from the response from an API call to the UniProt endpoint.

    :param  response:   Response object from the UniProt API call
    :param  entrez:     Entrez GeneId to be mapped to a UniProt ID
    :return:            Tuple of UniProt ID and the version of the database it was extracted from
    """
    uniprot_id = list()
    # Two cases - one protein mapping or multiple protein mappings
    if type(response[u'uniprot'][u'entry']) is list:
        # Multiple protein mappings available
        for entry in response[u'uniprot'][u'entry']:
            # Check if it is for Uniprot
            try:
                if entry[u'@dataset'] == u'Swiss-Prot':
                    # Append to list of IDs (only take one)
                    uniprot_id.append(entry[u'accession'][0] if type(entry[u'accession']) is list else entry[u'accession'])
            except TypeError:
                continue
    else:
        # Only version of UniProt available
        entry = response[u'uniprot'][u'entry']
        # Only take one alias
        uniprot_id.append(entry[u'accession'][0] if type(entry[u'accession']) is list else entry[u'accession'])

    if len(uniprot_id) == 0:
        # Uniprot ID not found
        logging.warning(u'FAILED Uniprot ID Extraction for Entrez ID {0}'.format(entrez))
        return uniprot_id
    else:
        uniprot_id = [__buildURI(i) for i in uniprot_id]
        logging.info(u'Entrez ID {0} mapped to {1}.'.format(entrez, uniprot_id))
    return uniprot_id


def __constructParams(entrez, genename, taxonomy = HUMAN_TAXON):
    u"""
    Constructs a dictionary of parameters to be passed in the API call to the UniProt endpoint.

    :param  entrez      Entrez GeneId to be queried
    :param  genename    Name of the gene to be queried
    :param  taxonomy    Taxonomy to be queried (defaults to HUMAN_TAXON)
    :return:            Dictionary of the request parameters
    """
    query = u'GENEID:{0}+AND+{1}+AND+taxonomy:{2}'.format(entrez, genename, taxonomy)
    request_param = {
        u'query': query,
        u'format': u'xml'
    }
    return request_param


def __buildURI(unirpot_id):
    u"""
    Builds a UniProt KB URI, using the prefix defined in the constants.

    :param  uniprot_id  UniProt KB ID to be converted to URI
    :return:            UniProt KB URI
    """
    return UNIPROT_PREFIX + unirpot_id


if __name__ == u"__main__":
    main()