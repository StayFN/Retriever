from src.data.dataset import download_dataset, import_queries, import_collection, import_qrels, import_training_set
import pandas as pd
from tqdm import tqdm
from src.data.preprocessing import preprocess
from src.features.generator import create_w2v_embeddings, create_w2v_feature, create_tfidf_embeddings, create_all, create_BM2_feature, create_tfidf_feature, create_jaccard_feature, create_POS_features, create_interpretation_features, create_sentence_features
import logging
import os
from src.utils.utils import check_path_exists
import time

tqdm.pandas()
LOGGER = logging.getLogger('pipeline')


class Pipeline(object):
    """ Class to combine the different download, preprocessing, modeling and evaluation steps. """

    collection = None
    queries = None
    queries_test = None
    qrels = None
    features = pd.DataFrame()

    def __init__(self, collection: str = None, queries: str = None, queries_test: str = None,
                 features: str = None, qrels: str = None):
        if collection is not None:
            self.collection = pd.read_pickle(collection)
        if queries is not None:
            self.queries = pd.read_pickle(queries)
        if queries_test is not None:
            self.queries_test = pd.read_pickle(queries_test)
        if features is not None:
            self.features = pd.read_pickle(features)
        if qrels is not None:
            self.qrels = pd.read_pickle(qrels)

    def setup(self, datasets: list = None, path: str = 'data/TREC_Passage'):
        if datasets is None:
            datasets = ['collection.tsv', 'queries.train.tsv', 'msmarco-test2019-queries.tsv',
                        '2019qrels-pass.txt', 'qidpidtriples.train.full.2.tsv']

        #download_dataset(datasets)

        if 'collection.tsv' in datasets:
            self.collection = import_collection(path)
        if 'qidpidtriples.train.full.2.tsv' in datasets:
            self.features = import_training_set(path, list(self.collection['pID']))
        if 'queries.train.tsv' or 'msmarco-test2019-queries.tsv' in datasets:
            self.queries, self.queries_test = import_queries(path, list(self.features['qID']))
        if '2019qrels-pass.txt' in datasets:
            self.qrels = import_qrels(path)

        return self.save()

    def preprocess(self):
        LOGGER.info('Preprocessing collection')
        self.collection['preprocessed'] = preprocess(self.collection.Passage)

        LOGGER.info('Preprocessing queries')
        self.queries['preprocessed'] = preprocess(self.queries.Query)

        LOGGER.info('Preprocessing test queries')
        self.queries_test['preprocessed'] = preprocess(self.queries_test.Query)

        return self.save()

    def create_tfidf_embeddings(self):
        assert self.collection['preprocessed'] is not None, "Preprocess the data first"

        tfidf, self.collection = create_tfidf_embeddings(self.collection, name='collection')
        tfidf, self.queries = create_tfidf_embeddings(self.queries, tfidf=tfidf, name='query')
        tfidf, self.queries_test = create_tfidf_embeddings(self.queries_test, tfidf=tfidf, name='query_test')

        return self.save()


    def create_w2v_embeddings(self):
        assert self.collection['preprocessed'] is not None, "Preprocess the data first"

        w2v, self.collection = create_w2v_embeddings(self.collection, name='collection')
        w2v, self.queries = create_w2v_embeddings(self.queries, w2v=w2v, name='query')
        w2v, self.queries_test = create_w2v_embeddings(self.queries_test, w2v=w2v, name='query_test')

        return self.save()

    def create_w2v_feature(self, path_collection: str = 'data/embeddings/w2v_collection_embeddings.pkl',
                             path_query: str = 'data/embeddings/w2v_query_embeddings.pkl'):
        self.features = create_w2v_feature(self.features, self.collection, self.queries, path_collection, path_query)

        return self.save()

    def create_tfidf_feature(self, path_collection: str = 'data/embeddings/tfidf_collection_embeddings.pkl',
                             path_query: str = 'data/embeddings/tfidf_query_embeddings.pkl'):
        self.features = create_tfidf_feature(self.features, self.collection, self.queries, path_collection, path_query)

        return self.save()

    def create_jaccard_feature(self):
        self.features = create_jaccard_feature(self.features, self.collection, self.queries)

        return self.save()

    def create_sentence_features(self):
        self.features = create_sentence_features(self.features, self.collection, self.queries)

        return self.save()

    def create_interpretation_features(self):
        self.features = create_interpretation_features(self.features, self.collection, self.queries)

        return self.save()

    def create_POS_features(self):
        self.features = create_POS_features(self.features, self.collection, self.queries)

        return self.save()

    def create_BM25_features(self):
        self.features = create_BM2_feature(self.features, self.collection, self.queries)

        return self.save()

    def evaluate(self):
        features_test = pd.DataFrame()
        for index, query in self.queries_test.iterrows():
            features_test = pd.concat([features_test, pd.DataFrame({
                'qID': [query['qID']] * len(self.collection),
                'pID': self.collection['pID']
            })])
        create_all(features_test, self.collection, self.queries_test)

    def save(self, path: str = 'data/processed'):
        check_path_exists(path)
        self.queries.to_pickle(os.path.join(path, 'queries' + str(time.time()) + '.pkl'))
        self.collection.to_pickle(os.path.join(path, 'collection' + str(time.time()) + '.pkl'))
        self.features.to_pickle(os.path.join(path, 'features' + str(time.time()) + '.pkl'))
        return self
