#!/usr/bin/env python
# -*- coding: utf-8 -*-


# import needed libraries
import glob
import json
import os
import pandas  # type: ignore
import pickle
import sys

from rdflib import Graph, Literal, Namespace, URIRef  # type: ignore
from rdflib.namespace import RDF, RDFS, OWL  # type: ignore
from tqdm import tqdm  # type: ignore
from typing import Dict, List, Union

from omop2obo.utils import *

# set up environment variables
obo = Namespace('http://purl.obolibrary.org/obo/')
oboinowl = Namespace('http://www.geneontology.org/formats/oboInOwl#')
schema = Namespace('http://www.w3.org/2001/XMLSchema#')


class OntologyInfoExtractor(object):
    """Class processes downloaded OBO ontology OWL files. The data are processed in order to obtain important metadata
    like labels, definitions, synonyms, and database cross-references and writes the data as a Pandas DataFrame
    object. The class produces the following three files for each processed ontology (examples of the data stored in
    each object are provided in the corresponding methods:
        1. resources/ontologies/hp_ontology_hierarchy_information.pkl
        2. resources/ontologies/hp_ontology_ancestors.json
        3. resources/ontologies/hp_ontology_children.json

    As each ontology is processed, the master_ontology_dictionary object is built, which is the primary output that
    is utilized by the OMOP2OBO algorithm. An example of the data stored in this object is shown below.
        {'hp': {
                'df': 'resources/ontologies/hp_ontology_hierarchy_information.pkl',
                'ancestors': 'resources/ontologies/hp_ontology_ancestors.json',
                'children': 'resources/ontologies/hp_ontology_children.json'
                }
        }

    Attributes:
        graph: An rdflib graph object.
        ont_dictionary: A dictionary, where keys are an ontology alias (e.g., 'hp') and values are a string pointing
            the local location where the ontology was downloaded.
        master_ontology_dictionary: A string containing the filepath to the ontology data directory.

    Raises:
        OSError: If the ontology_dictionary cannot be found.
        IndexError: If ontology_dictionary is empty.
    """

    def __init__(self, ontology_directory: str, ont_dictionary: Dict) -> None:

        self.graph: Graph = Graph()
        self.ont_dictionary = ont_dictionary
        self.master_ontology_dictionary: Dict = {}

        # check for ontology data
        if not os.path.exists(ontology_directory): raise OSError("Can't find the 'resources/ontologies' directory")
        elif len(glob.glob(ontology_directory + '/*.owl')) == 0: raise IndexError('The ontologies directory is empty')
        else: self.ont_directory = ontology_directory

    def get_ontology_information(self, ont_id: str) -> Dict:
        """Queries an rdflib Graph object and returns labels, definitions, dbXRefs, and synonyms for all
        non-deprecated and obsolete ontology classes.

        Args:
            ont_id: A string containing an ontology namespace (e.g., "hp").

        Returns:
            res: A dict mapping each DbXRef to a list containing the corresponding class ID and label. For example:
                    {'label': {'narrow naris': 'http://purl.obolibrary.org/obo/HP_0009933'},
                    'definition': {'agenesis of lower primary incisor.': 'http://purl.obolibrary.org/obo/HP_0011047'},
                    'dbxref': {'SNOMEDCT_US:88598008': 'http://purl.obolibrary.org/obo/HP_0000735'},
                    'synonyms': { 'open bite': 'http://purl.obolibrary.org/obo/HP_0010807'}}
        """

        # identify current ontology classes in ont_id namespace
        print('.Querying Ontology to Obtain all OWL:Class Objects')
        ont_classes = gets_ontology_classes(self.graph, ont_id)
        print('. .Querying Ontology to Obtain all Deprecated OWL:Class Objects')
        deprecated = gets_deprecated_ontology_classes(self.graph, ont_id)
        print('. . .Querying Ontology to Obtain all Obsolete OWL:Class Objects')
        obsolete = gets_obsolete_ontology_classes(self.graph, ont_id)
        filtered_classes = set([x for x in ont_classes if x not in deprecated | obsolete])
        # obtain class-level metadata
        print('. . . .Querying Ontology to Obtain all OWL:Class Object Labels')
        ont_labels = gets_ontology_class_labels(self.graph, filtered_classes)
        print('. . . . .Querying Ontology to Obtain all OWL:Class Object Definitions')
        ont_definitions = gets_ontology_class_definitions(self.graph, filtered_classes)
        print('. . . . . .Querying Ontology to Obtain all OWL:Class Object DbXRefs')
        ont_dbx = gets_ontology_class_dbxrefs(self.graph, filtered_classes)
        print('. . . . . . .Querying Ontology to Obtain all OWL:Class Object Synonyms')
        ont_synonyms = gets_ontology_class_synonyms(self.graph, filtered_classes)
        # store results as dictionary
        res: Dict = {'label': ont_labels, 'definition': ont_definitions, 'dbxref': ont_dbx, 'synonym': ont_synonyms}

        return res

    def creates_pandas_dataframe(self, res: Dict, ont_id: str) -> pandas.DataFrame:
        """Processes ontology information stored in a nested dictionary and then outputs it as a Pandas DataFrame
        object, which is also saved to the resources/ontologies directory.

        Args:
            res: A nested dictionary containing labels, definitions, dbxrefs, and synonyms for each ontology class.
                For example:
                    {'label': {'narrow naris': 'http://purl.obolibrary.org/obo/HP_0009933'},
                    'definition': {'agenesis of lower primary incisor.': 'http://purl.obolibrary.org/obo/HP_0011047'},
                    'dbxref': {'SNOMEDCT_US:88598008': 'http://purl.obolibrary.org/obo/HP_0000735'},
                    'synonyms': { 'open bite': 'http://purl.obolibrary.org/obo/HP_0010807'}}
            ont_id: A string containing an ontology namespace (e.g., "hp").

        Returns:
             ont_df: A Pandas DataFrame object containing ontology metadata. The DataFrame is written locally as a
                pickled object. An example row of this DataFrame is shown below:
                        obo_id                                  http://purl.obolibrary.org/obo/HP_0000552
                        code                                                                   HP:0000552
                        string                                                                tritanomaly
                        string_type                                                           class label
                        dbx                                                                       D003117
                        dbx_type                                                       oboInOwl:hasDbXref
                        dbx_source                                                                    msh
                        dbx_source_name                                                               msh
                        obo_source           http://purl.obolibrary.org/obo/hp/releases/2022-02-14/hp.owl
                        obo_semantic_type                                                 human_phenotype
        """

        # get ontology metadata
        ns: Union[List, str] = list(self.graph.triples((None, URIRef(oboinowl + 'default-namespace'), None)))
        ns = str(ns[0][2]) if len(ns) > 0 else ont_id
        sab = str(list(self.graph.triples((None, OWL.versionIRI, None)))[0][2])
        # process labels, definitions, and synonyms
        labs = pandas.DataFrame({'obo_id': k, 'code': k.split('/')[-1].replace('_', ':'), 'string': v,
                                 'string_type': 'class label'} for k, v in res['label'].items())
        defs = pandas.DataFrame({'obo_id': k, 'code': k.split('/')[-1].replace('_', ':'), 'string': v,
                                 'string_type': 'class definition'} for k, v in res['definition'].items())
        syn = pandas.DataFrame({'obo_id': y[0], 'code': y[0].split('/')[-1].replace('_', ':'), 'string': x[0],
                                'string_type': x[1]} for y in [(k, v) for k, v in res['synonym'].items()] for x in y[1])
        ont_df = pandas.concat([labs, defs, syn]).drop_duplicates()
        # process dbxrefs
        dbx = pandas.DataFrame({'obo_id': y[0], 'code': y[0].split('/')[-1].replace('_', ':'), 'dbx': x[0],
                                'dbx_type': x[1], 'dbx_source': x[2], 'dbx_source_name': x[2]}
                               for y in [(k, v) for k, v in res['dbxref'].items()] for x in y[1])
        ont_df = ont_df.merge(dbx, on=['obo_id', 'code'], how='left').drop_duplicates()
        # add metadata
        ont_df['obo_source'] = sab; ont_df['obo_semantic_type'] = ns
        ont_df = ont_df.fillna('None').drop_duplicates()
        # write data to local directory (resources/ontologies)
        out = '{}/{}_ontology_hierarchy_information.pkl'.format(self.ont_directory, ont_id)
        max_bytes, bytes_out = 2 ** 31 - 1, pickle.dumps(ont_df); n_bytes = sys.getsizeof(bytes_out)
        with open(out, 'wb') as f_out:
            for idx in range(0, n_bytes, max_bytes): f_out.write(bytes_out[idx:idx + max_bytes])
        self.master_ontology_dictionary[ont_id]['df'] = out
        print('.Wrote Pandas DataFrame to: {}'.format(out))

        return ont_df

    def ontology_entity_finder(self, ont_df: pandas.DataFrame, ont_id: str) -> None:
        """Finds all ancestors and children for each ontology class. The function returns a separate dictionary for
        each entity type, for each class a dictionary is returned where keys are numbers representing the number of
        levels below (children) or above (ancestors) that each concept is found. An example of the output produced
        for each derived dictionary is shown below:
            ancestors: {'http://purl.obolibrary.org/obo/HP_0003743':
                            {'0':  ['http://purl.obolibrary.org/obo/HP_0000005'],
                             '1': ['http://purl.obolibrary.org/obo/HP_0000001']}, ...}
            children: {'http://purl.obolibrary.org/obo/HP_0003743':
                            {'0': ['http://purl.obolibrary.org/obo/HP_0003744']}, ...}

        Args:
            ont_df: A Pandas DataFrame containing ontology data (see creates_pandas_dataframe() comment for details).
            ont_id: A string containing an ontology namespace (e.g., "hp").

        Return:
            None.
        """

        print('. Obtaining Ontology Concept Ancestors')
        cls = set(ont_df['obo_id'])
        obo_ancs = {x: entity_search(self.graph, x, 'ancestors', ont_id.upper(), RDFS.subClassOf) for x in tqdm(cls)}
        print('. . Obtaining Ontology Descendants. Please be patient, this can take several minutes.')
        obo_kids = {x: entity_search(self.graph, x, 'children', ont_id.upper(), RDFS.subClassOf) for x in tqdm(cls)}

        # write results to local directory (resources/ontologies)
        anc_file_str, kid_file_str = '{}/{}_ontology_ancestors.json', '{}/{}_ontology_children.json'
        self.master_ontology_dictionary[ont_id]['ancestors'] = anc_file_str.format(self.ont_directory, ont_id)
        self.master_ontology_dictionary[ont_id]['children'] = kid_file_str.format(self.ont_directory, ont_id)
        json.dump(obo_ancs, open(self.master_ontology_dictionary[ont_id]['ancestors'], 'w'))
        json.dump(obo_kids, open(self.master_ontology_dictionary[ont_id]['children'], 'w'))
        print('. . .Wrote Ancestor Dictionary to: {}'.format(self.master_ontology_dictionary[ont_id]['ancestors']))
        print('. . . . Wrote Descendant Dictionary to: {}'.format(self.master_ontology_dictionary[ont_id]['children']))

        return None

    def ontology_processor(self) -> None:
        """Retrieves metadata (i.e., labels, definitions, synonyms, and database cross-references) for each ontology.
        Core metadata are converted to a Pandas DataFrame and two dictionaries are created to store all ontology
        class ancestor and descendant concepts. The DataFrame and dictionaries are written to the
        resources/ontologies directory.

        Returns:
            None.
        """

        for ont in self.ont_dictionary.items():
            self.master_ontology_dictionary[ont[0]] = {'df': None, 'ancestors': None, 'children': None}
            print('===' * 15 + '\nPROCESSING ONTOLOGY: {}\n'.format(ont[0]) + '===' * 15)
            print('STEP 1: Loading Data...Please be patient, this step can take several minutes.')
            self.graph = Graph().parse(ont[1], format='xml')
            print('\nSTEP 2: Obtaining Ontology Metadata')
            ont_dict = self.get_ontology_information(ont[0])
            print('\nSTEP 3: Converting Metadata into Pandas DataFrame')
            ont_df = self.creates_pandas_dataframe(ont_dict, ont[0])
            print('\nSTEP 4: Obtaining Ancestors and Descendants for each Ontology Class')
            self.ontology_entity_finder(ont_df, ont[0])

        return None
