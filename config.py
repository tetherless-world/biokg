# -*- config:utf-8 -*-

import os
import logging
from datetime import timedelta

project_name = "biokg"
import importer

import autonomic
import agents.nlp as nlp
import rdflib
from datetime import datetime

import urllib

# Set to be custom for your project
LOD_PREFIX = 'http://purl.org/twc/bio'
#os.getenv('lod_prefix') if os.getenv('lod_prefix') else 'http://hbgd.tw.rpi.edu'

skos = rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")

from biokg.agent import *

uniprot_url = 'http://sparql.uniprot.org/sparql?query=%s&format=ttl'
uniprot_query = '''PREFIX rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
construct { ?s ?p ?o }
where {
  values ?s {<%s>} 
  ?s ?p ?o.
  filter not exists { ?o rdf:subject []}
}'''


# base config class; extend it to your needs.
Config = dict(
    # use DEBUG mode?
    DEBUG = False,

    site_name = "Biology Knowledge Graph",

    site_description = "A probabilistic knowledge graph for exploring systems biology.",
    
    root_path = '/apps/whyis',

    DEFAULT_ANONYMOUS_READ = True,
    
    # use TESTING mode?
    TESTING = False,

    # use server x-sendfile?
    USE_X_SENDFILE = False,

    WTF_CSRF_ENABLED = True,
    SECRET_KEY = "r9pId2gqiSLw2GWFRUSwP4/kDqactyko",

    nanopub_archive = {
        'depot.storage_path' : "/data/nanopublications",
    },

    file_archive = {
        'depot.storage_path' : '/data/files',
        'cache_max_age' : 3600*24*7,
    },
    vocab_file = "/apps/biokg/vocab.ttl",
    WHYIS_TEMPLATE_DIR = [
        "/apps/biokg/templates",
    ],
    WHYIS_CDN_DIR = "/apps/biokg/static",

    # LOGGING
    LOGGER_NAME = "%s_log" % project_name,
    LOG_FILENAME = "/var/log/%s/output-%s.log" % (project_name,str(datetime.now()).replace(' ','_')),
    LOG_LEVEL = logging.INFO,
    LOG_FORMAT = "%(asctime)s %(levelname)s\t: %(message)s", # used by logging.Formatter

    PERMANENT_SESSION_LIFETIME = timedelta(days=7),

    # EMAIL CONFIGURATION
    ## MAIL_SERVER = "",
    ## MAIL_PORT = 587,
    ## MAIL_USE_TLS = True,
    ## MAIL_USE_SSL = False,
    ## MAIL_DEBUG = False,
    ## MAIL_USERNAME = '',
    ## MAIL_PASSWORD = '',
    ## DEFAULT_MAIL_SENDER = "James McCusker <mccusj2@rpi.edu>",

    # see example/ for reference
    # ex: BLUEPRINTS = ['blog']  # where app is a Blueprint instance
    # ex: BLUEPRINTS = [('blog', {'url_prefix': '/myblog'})]  # where app is a Blueprint instance
    BLUEPRINTS = [],

    lod_prefix = LOD_PREFIX,
    SECURITY_EMAIL_SENDER = "James McCusker <mccusj2@rpi.edu>",
    SECURITY_FLASH_MESSAGES = True,
    SECURITY_CONFIRMABLE = False,
    SECURITY_CHANGEABLE = True,
    SECURITY_TRACKABLE = True,
    SECURITY_RECOVERABLE = True,
    SECURITY_REGISTERABLE = True,
    SECURITY_PASSWORD_HASH = 'sha512_crypt',
    SECURITY_PASSWORD_SALT = '6i9umJAj4m+DrKRVqHyysOVTWITZq1QS',
    SECURITY_SEND_REGISTER_EMAIL = False,
    SECURITY_POST_LOGIN_VIEW = "/",
    SECURITY_SEND_PASSWORD_CHANGE_EMAIL = False,
    SECURITY_DEFAULT_REMEMBER_ME = True,
    ADMIN_EMAIL_RECIPIENTS = [],
    db_defaultGraph = LOD_PREFIX + '/',


    admin_queryEndpoint = 'http://localhost:8080/blazegraph/namespace/admin/sparql',
    admin_updateEndpoint = 'http://localhost:8080/blazegraph/namespace/admin/sparql',
    
    knowledge_queryEndpoint = 'http://localhost:8080/blazegraph/namespace/knowledge/sparql',
    knowledge_updateEndpoint = 'http://localhost:8080/blazegraph/namespace/knowledge/sparql',

    LOGIN_USER_TEMPLATE = "auth/login.html",
    #CELERY_BROKER_URL = 'amqp://whyis:whyis@localhost:5672/whyis',
    CELERY_BROKER_URL = 'redis://localhost:6379/0',
    #CELERY_RESULT_BACKEND = 'amqp://whyis:whyis@localhost:5672/whyis',
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0',
    default_language = 'en',


    site_header_image = 'static/images/random_network.png',
    
    namespaces = [
        importer.LinkedData(
            prefix = LOD_PREFIX+'/doi/',
            url = 'http://dx.doi.org/%s',
            headers={'Accept':'text/turtle'},
            format='turtle',
            postprocess_update= '''insert {
                graph ?g {
                    ?pub a <http://purl.org/ontology/bibo/AcademicArticle>.
                }
            } where {
                graph ?g {
                    ?pub <http://purl.org/ontology/bibo/doi> ?doi.
                }
            }
            '''
        ),
        importer.LinkedData(
            prefix = LOD_PREFIX+'/dbpedia/',
            url = 'http://dbpedia.org/resource/%s',
            headers={'Accept':'text/turtle'},
            format='turtle',
            postprocess_update= '''insert {
                graph ?g {
                    ?article <http://purl.org/dc/terms/abstract> ?abstract.
                }
            } where {
                graph ?g {
                    ?article <http://dbpedia.org/ontology/abstract> ?abstract.
                }
            }
            ''',
        ),
        importer.LinkedData(
            prefix = LOD_PREFIX+'/dbpedia/ontolgy/',
            url = 'http://dbpedia.org/ontology/%s',
            headers={'Accept':'text/turtle'},
            format='turtle',
        ),
        importer.LinkedData(
            prefix = LOD_PREFIX+'/dbpedia/class/',
            url = 'http://dbpedia.org/class/%s',
            access_url = 'http://dbpedia.org/sparql?default-graph-uri=http://dbpedia.org&query=DESCRIBE+<%s>&format=application/json-ld',
            format='json-ld',
        ),
        importer.LinkedData(
            prefix = LOD_PREFIX+'/obo/',
            url = 'http://purl.obolibrary.org/obo/%s',
            headers={'Accept':'application/rdf+xml'},
            format='xml'
        ),
        importer.LinkedData(
            prefix = LOD_PREFIX+'/protein/',
            access_url = lambda entity_name: uniprot_url % (urllib.quote_plus(uniprot_query % entity_name)),
            url = 'http://purl.uniprot.org/uniprot/%s',
            headers={'Accept':'application/rdf+xml'},
            format='turtle'
        ),
        importer.LinkedData(
            prefix = LOD_PREFIX+'/uniprot/',
            access_url = lambda entity_name: uniprot_url % (urllib.quote_plus(uniprot_query % entity_name)),
            url = 'http://purl.uniprot.org/%s',
            headers={'Accept':'application/rdf+xml'},
            format='turtle'
        ),
    ],
    inferencers = {
        "SETLr": autonomic.SETLr(),
        "OntologyImporter" : autonomic.OntologyImporter(),
#        "HTML2Text" : nlp.HTML2Text(),
#        "EntityExtractor" : nlp.EntityExtractor(),
#        "EntityResolver" : nlp.EntityResolver(),
#        "TF-IDF Calculator" : nlp.TFIDFCalculator(),
#        "SKOS Crawler" : autonomic.Crawler(predicates=[skos.broader, skos.narrower, skos.related])
    },
    inference_tasks = [
#        dict ( name="SKOS Crawler",
#               service=autonomic.Crawler(predicates=[skos.broader, skos.narrower, skos.related]),
#               schedule=dict(hour="1")
#              )
    ],
    base_rate_probability = 0.8
)


# config class for development environment
Dev = dict(Config)
Dev.update(dict(
    DEBUG = True,  # we want debug level output
    MAIL_DEBUG = True,
    EXPLAIN_TEMPLATE_LOADING = False,
    DEBUG_TB_INTERCEPT_REDIRECTS = False
))

# config class used during tests
Test = dict(Config)
Test.update(dict(
    TESTING = True,
    WTF_CSRF_ENABLED = False
))

