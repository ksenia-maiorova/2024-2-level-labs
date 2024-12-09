"""
Lab 4.

Vector search with clusterization
"""

# pylint: disable=undefined-variable, too-few-public-methods, unused-argument, duplicate-code, unused-private-member, super-init-not-called
from json import dump

from lab_2_retrieval_w_bm25.main import calculate_bm25
from lab_3_ann_retriever.main import (
    AdvancedSearchEngine,
    BasicSearchEngine,
    calculate_distance,
    SearchEngine,
    Tokenizer,
    Vector,
    Vectorizer,
)

Corpus = list[str]
"Type alias for corpus of texts."
TokenizedCorpus = list[list[str]]
"Type alias for tokenized texts."


def get_paragraphs(text: str) -> list[str]:
    """
    Split text to paragraphs.

    Args:
        text (str): Text to split in paragraphs.

    Raises:
        ValueError: In case of inappropriate type input argument or if input argument is empty.

    Returns:
        list[str]: Paragraphs from document.
    """
    if not isinstance(text, str) or not text:
        raise ValueError('Invalid input argument')
    paragraphs = text.split('\n')
    return [paragraph.strip() for paragraph in paragraphs if paragraph != ' ']


class BM25Vectorizer(Vectorizer):
    """
    BM25 Vectorizer.
    """

    _corpus: TokenizedCorpus
    _avg_doc_len: float

    def __init__(self) -> None:
        """
        Initialize an instance of the BM25Vectorizer class.
        """
        super().__init__([])
        self._corpus = []
        self._avg_doc_len = -1.0

    def set_tokenized_corpus(self, tokenized_corpus: TokenizedCorpus) -> None:
        """
        Set tokenized corpus and average document length.

        Args:
            tokenized_corpus (TokenizedCorpus): Tokenized texts corpus.

        Raises:
            ValueError: In case of inappropriate type input argument or if input argument is empty.
        """
        if not isinstance(tokenized_corpus, list) or not tokenized_corpus:
            raise ValueError('Invalid input argument')
        self._corpus = tokenized_corpus
        self._avg_doc_len = sum(len(doc) for doc in self._corpus) / len(self._corpus)

    def vectorize(self, tokenized_document: list[str]) -> Vector:
        """
        Create a vector for tokenized document.

        Args:
            tokenized_document (list[str]): Tokenized document to vectorize.

        Raises:
            ValueError: In case of inappropriate type input arguments,
                or if input arguments are empty,
                or if methods used return None.

        Returns:
            Vector: BM25 vector for document.
        """
        if not isinstance(tokenized_document, list) or not tokenized_document:
            raise ValueError('Invalid input argument')
        bm25_vector = self._calculate_bm25(tokenized_document)
        if not bm25_vector:
            raise ValueError('Failed to vectorize. BM-25 values are None')
        return bm25_vector

    def _calculate_bm25(self, tokenized_document: list[str]) -> Vector:
        """
        Get BM25 vector for tokenized document.

        Args:
            tokenized_document (list[str]): Tokenized document to vectorize.

        Raises:
            ValueError: In case of inappropriate type input argument or if input argument is empty.

        Returns:
            Vector: BM25 vector for document.
        """
        if not isinstance(tokenized_document, list) or not tokenized_document:
            raise ValueError('Invalid input argument')
        vector = [0.0] * len(self._vocabulary)
        bm25 = calculate_bm25(self._vocabulary, tokenized_document, self._idf_values,
                              avg_doc_len=self._avg_doc_len, doc_len=len(tokenized_document))
        if not bm25:
            return tuple(vector)
        for term, index in self._token2ind.items():
            vector[index] = bm25[term]
        return tuple(vector)


class DocumentVectorDB:
    """
    Document and vector database.
    """

    __vectors: dict[int, Vector]
    __documents: Corpus
    _tokenizer: Tokenizer
    _vectorizer: BM25Vectorizer

    def __init__(self, stop_words: list[str]) -> None:
        """
        Initialize an instance of the DocumentVectorDB class.

        Args:
            stop_words (list[str]): List with stop words.
        """
        self.__vectors = {}
        self.__documents = []
        self._tokenizer = Tokenizer(stop_words)
        self._vectorizer = BM25Vectorizer()

    def put_corpus(self, corpus: Corpus) -> None:
        """
        Fill documents and vectors based on corpus.

        Args:
            corpus (Corpus): Corpus of texts.

        Raises:
            ValueError: In case of inappropriate type input arguments,
                or if input arguments are empty,
                or if methods used return None.
        """
        if not isinstance(corpus, list) or not corpus:
            raise ValueError('Invalid input argument')
        tokenized_docs = []
        for doc in corpus:
            tok_doc = self._tokenizer.tokenize(doc)
            if tok_doc:
                self.__documents.append(doc)
                tokenized_docs.append(tok_doc)
        if not tokenized_docs:
            raise ValueError('Tokenized documents are either None or empty')
        self._vectorizer.set_tokenized_corpus(tokenized_docs)
        self._vectorizer.build()
        self.__vectors = {ind: vector for ind, doc in enumerate(tokenized_docs)
                          if (vector := self._vectorizer.vectorize(doc))}

    def get_vectorizer(self) -> BM25Vectorizer:
        """
        Get an object of the BM25Vectorizer class.

        Returns:
            BM25Vectorizer: BM25Vectorizer class object.
        """
        return self._vectorizer

    def get_tokenizer(self) -> Tokenizer:
        """
        Get an object of the Tokenizer class.

        Returns:
            Tokenizer: Tokenizer class object.
        """
        return self._tokenizer

    def get_vectors(self, indices: list[int] | None = None) -> list[tuple[int, Vector]]:
        """
        Get document vectors by indices.

        Args:
            indices (list[int] | None): Document indices.

        Returns:
            list[tuple[int, Vector]]: List of index and vector for documents.
        """
        if not indices:
            return list(self.__vectors.items())
        return [pair for pair in self.__vectors.items() if pair[0] in indices]

    def get_raw_documents(self, indices: tuple[int, ...] | None = None) -> Corpus:
        """
        Get documents by indices.

        Args:
            indices (tuple[int, ...] | None): Document indices.

        Raises:
            ValueError: In case of inappropriate type input argument.

        Returns:
            Corpus: List of documents.
        """
        if not indices:
            return self.__documents
        unique_indices = []
        for ind in indices:
            if ind not in unique_indices:
                unique_indices.append(ind)
        return [self.__documents[ind] for ind in unique_indices]


class VectorDBSearchEngine(BasicSearchEngine):
    """
    Engine based on VectorDB.
    """

    _db: DocumentVectorDB

    def __init__(self, db: DocumentVectorDB) -> None:
        """
        Initialize an instance of the RerankerEngine class.

        Args:
            db (DocumentVectorDB): Object of DocumentVectorDB class.
        """
        super().__init__(db.get_vectorizer(), db.get_tokenizer())
        self._db = db

    def retrieve_relevant_documents(self, query: str, n_neighbours: int) -> list[tuple[float, str]]:
        """
        Get relevant documents.

        Args:
            query (str): Query for obtaining relevant documents.
            n_neighbours (int): Number of relevant documents to return.

        Returns:
            list[tuple[float, str]]: Relevant documents with their distances.
        """
        if not isinstance(query, str) or not query or not isinstance(n_neighbours, int) \
                or n_neighbours <= 0:
            raise ValueError('Invalid input argument(s)')
        query_tokens = self._tokenizer.tokenize(query)
        if not query_tokens:
            raise ValueError('Failed to tokenize query (None or empty)')
        query_vector = self._vectorizer.vectorize(query_tokens)
        if not query_vector:
            raise ValueError('Failed to vectorize query (None or empty)')
        vectors = [vector for index, vector in self._db.get_vectors()]
        knn = self._calculate_knn(query_vector, vectors, n_neighbours)
        if not knn:
            raise ValueError('Failed to calculate k nearest neighbours (None or empty)')
        knn_indices = [pair[0] for pair in knn]
        docs = self._db.get_raw_documents(tuple(knn_indices))
        return [(pair[1], docs[ind]) for ind, pair in enumerate(knn)]


class ClusterDTO:
    """
    Store clusters.
    """

    __centroid: Vector
    __indices: list[int]

    def __init__(self, centroid_vector: Vector) -> None:
        """
        Initialize an instance of the ClusterDTO class.

        Args:
            centroid_vector (Vector): Centroid vector.
        """
        self.__centroid = centroid_vector
        self.__indices = []

    def __len__(self) -> int:
        """
        Return the number of document indices.

        Returns:
            int: The number of document indices.
        """
        return len(self.__indices)

    def get_centroid(self) -> Vector:
        """
        Get cluster centroid.

        Returns:
            Vector: Centroid of current cluster.
        """
        return self.__centroid

    def set_new_centroid(self, new_centroid: Vector) -> None:
        """
        Set new centroid for cluster.

        Args:
            new_centroid (Vector): New centroid vector.

        Raises:
            ValueError: In case of inappropriate type input arguments,
                or if input arguments are empty.
        """
        if not isinstance(new_centroid, tuple) or not new_centroid:
            raise ValueError('Invalid input argument')
        self.__centroid = new_centroid

    def erase_indices(self) -> None:
        """
        Clear indexes.
        """
        self.__indices = []

    def add_document_index(self, index: int) -> None:
        """
        Add document index.

        Args:
            index (int): Index of document.

        Raises:
            ValueError: In case of inappropriate type input arguments,
                or if input arguments are empty.
        """
        if not isinstance(index, int) or index is None or index < 0:
            raise ValueError('Invalid input argument')
        if index not in self.__indices:
            self.__indices.append(index)

    def get_indices(self) -> list[int]:
        """
        Get indices.

        Returns:
            list[int]: Indices of documents.
        """
        return self.__indices


class KMeans:
    """
    Train k-means algorithm.
    """

    __clusters: list[ClusterDTO]
    _db: DocumentVectorDB
    _n_clusters: int

    def __init__(self, db: DocumentVectorDB, n_clusters: int) -> None:
        """
        Initialize an instance of the KMeans class.

        Args:
            db (DocumentVectorDB): An instance of DocumentVectorDB class.
            n_clusters (int): Number of clusters.
        """
        self.__clusters = []
        self._db = db
        self._n_clusters = n_clusters

    def train(self) -> None:
        """
        Train k-means algorithm.
        """
        start_centroids = self._db.get_vectors()[:self._n_clusters]
        for centroid in start_centroids:
            self.__clusters.append(ClusterDTO(centroid[1]))
        while True:
            new_clusters = self.run_single_train_iteration()
            if self._is_convergence_reached(new_clusters):
                break

    def run_single_train_iteration(self) -> list[ClusterDTO]:
        """
        Run single train iteration.

        Raises:
            ValueError: In case of if methods used return None.

        Returns:
            list[ClusterDTO]: List of clusters.
        """
        centroids = []
        for cluster in self.__clusters:
            cluster.erase_indices()
            centroids.append(cluster.get_centroid())

        vectors = self._db.get_vectors()
        for vector in vectors:
            distances = []
            for centroid in centroids:
                distance = calculate_distance(vector[1], centroid)
                if distance is None:
                    raise ValueError('Failed to calculate distance between vector and centroid')
                distances.append((distance, centroids.index(centroid)))
            closest_centroid = min(distances)[1]
            self.__clusters[closest_centroid].add_document_index(vectors.index(vector))

        for cluster in self.__clusters:
            cluster_vectors = [vectors[ind][1] for ind in cluster.get_indices()]
            new_centroid = tuple(sum(scores) / len(scores) for scores in zip(*cluster_vectors))
            cluster.set_new_centroid(new_centroid)
        return self.__clusters

    def infer(self, query_vector: Vector, n_neighbours: int) -> list[tuple[float, int]]:
        """
        Launch clustering model inference.

        Args:
            query_vector (Vector): Vector of query for obtaining relevant documents.
            n_neighbours (int): Number of relevant documents to return.

        Raises:
            ValueError: In case of inappropriate type input arguments,
                or if input arguments are empty,
                or if input arguments are incorrect,
                or if methods used return None.

        Returns:
            list[tuple[float, int]]: Distance to relevant document and document index.
        """
        if not query_vector or n_neighbours <= 0:
            raise ValueError('Invalid input argument(s)')
        cent_distances = []
        for ind, cluster in enumerate(self.__clusters):
            centroid = cluster.get_centroid()
            if not centroid:
                continue
            cent_distance = calculate_distance(query_vector, centroid)
            if cent_distance is None:
                raise ValueError('Failed to calculate distance between query vector and centroid')
            cent_distances.append((cent_distance, ind))
        if not cent_distances:
            closest_cluster = 0
        else:
            closest_cluster = min(cent_distances)[1]
        doc_indices = self.__clusters[closest_cluster].get_indices()
        doc_vectors = self._db.get_vectors(doc_indices)
        doc_distances = []
        for vector in doc_vectors:
            doc_distance = calculate_distance(query_vector, vector[1])
            if doc_distance is None:
                raise ValueError('Failed to calculate distance between query and document vectors')
            doc_distances.append((doc_distance, vector[0]))
        return sorted(doc_distances, key=lambda pair: pair[0])[:n_neighbours]

    def get_clusters_info(self, num_examples: int) -> list[dict[str, int | list[str]]]:
        """
        Get clusters information.

        Args:
            num_examples (int): Number of examples for each cluster

        Returns:
            list[dict[str, int| list[str]]]: List with information about each cluster
        """
        if not isinstance(num_examples, int) or num_examples <= 0:
            raise ValueError('Invalid input argument')
        clusters_info = []
        for index, cluster in enumerate(self.__clusters):
            vectors = self._db.get_vectors(cluster.get_indices())
            distances = []
            for vector in vectors:
                distance = calculate_distance(cluster.get_centroid(), vector[1])
                if distance is None:
                    raise ValueError('Failed to calculate distance')
                distances.append((distance, vector[0]))
            distances.sort(key=lambda pair: pair[0])
            docs = self._db.get_raw_documents(tuple(pair[1] for pair in distances))
            cluster_info = {}
            cluster_info.update(cluster_id=index, documents=docs[:num_examples])
            clusters_info.append(cluster_info)
        return clusters_info

    def calculate_square_sum(self) -> float:
        """
        Get sum of squares of distance from vectors of clusters to their centroid.

        Returns:
            float: Sum of squares of distance from vector of clusters to centroid.
        """
        sse = 0.0
        for cluster in self.__clusters:
            centroid = cluster.get_centroid()
            vectors = self._db.get_vectors(cluster.get_indices())
            for vector in vectors:
                sse += sum((cent - vect) ** 2 for cent, vect in zip(centroid, vector[1]))
        return sse

    def _is_convergence_reached(
        self, new_clusters: list[ClusterDTO], threshold: float = 1e-07
    ) -> bool:
        """
        Check the convergence of centroids.

        Args:
            new_clusters (list[ClusterDTO]): Centroids after updating.
            threshold (float): Threshold for determining the distance correctness.

        Raises:
            ValueError: In case of inappropriate type input arguments,
                or if input arguments are empty,
                or if methods used return None.

        Returns:
            bool: True if the distance is correct, False in other cases.
        """
        if not isinstance(new_clusters, list) or not new_clusters \
                or not isinstance(threshold, float) or not threshold:
            raise ValueError('Invalid input argument(s)')
        old_centroids = [cluster.get_centroid() for cluster in self.__clusters]
        new_centroids = [cluster.get_centroid() for cluster in new_clusters]
        for old, new in zip(old_centroids, new_centroids):
            distance = calculate_distance(old, new)
            if distance is None:
                raise ValueError('Failed to calculate distance')
            if distance > threshold:
                return False
        return True


class ClusteringSearchEngine:
    """
    Engine based on KMeans algorithm.
    """

    __algo: KMeans
    _db: DocumentVectorDB

    def __init__(self, db: DocumentVectorDB, n_clusters: int = 3) -> None:
        """
        Initialize an instance of the ClusteringSearchEngine class.

        Args:
            db (DocumentVectorDB): An instance of DocumentVectorDB class.
            n_clusters (int): Number of clusters.
        """
        self.__algo = KMeans(db, n_clusters)
        self._db = db

    def retrieve_relevant_documents(self, query: str, n_neighbours: int) -> list[tuple[float, str]]:
        """
        Get relevant documents.

        Args:
            query (str): Query for obtaining relevant documents.
            n_neighbours (int): Number of relevant documents to return.

        Raises:
            ValueError: In case of inappropriate type input arguments,
                or if input arguments are empty,
                or if input arguments are incorrect,
                or if methods used return None.

        Returns:
            list[tuple[float, str]]: Relevant documents with their distances.
        """
        if not isinstance(query, str) or not query or not isinstance(n_neighbours, int) \
                or n_neighbours <= 0:
            raise ValueError('Invalid Input argument(s)')
        query_tokens = self._db.get_tokenizer().tokenize(query)
        if not query_tokens:
            raise ValueError('Failed to tokenize query')
        query_vector = self._db.get_vectorizer().vectorize(query_tokens)
        if not query_vector:
            raise ValueError('Failed to vectorize query')
        self.__algo.train()
        inference = self.__algo.infer(query_vector, n_neighbours)
        docs = self._db.get_raw_documents(tuple(ind for distance, ind in inference))
        return [(dist[0], docs[ind]) for ind, dist in enumerate(inference)]

    def make_report(self, num_examples: int, output_path: str) -> None:
        """
        Create report by clusters.

        Args:
            num_examples (int): number of examples for each cluster
            output_path (str): path to output file
        """
        if not isinstance(output_path, str) or not output_path:
            raise ValueError('Invalid input argument(s)')
        clusters_info = self.__algo.get_clusters_info(num_examples)
        with open(output_path, 'w', encoding='utf-8') as file:
            dump(clusters_info, file, indent=4)

    def calculate_square_sum(self) -> float:
        """
        Get sum by all clusters of sum of squares of distance from vector of clusters to centroid.

        Returns:
            float: Sum of squares of distance from vector of clusters to centroid.
        """
        return self.__algo.calculate_square_sum()


class VectorDBEngine:
    """
    Engine wrapper that encapsulates different engines and provides unified API to it.
    """

    _db: DocumentVectorDB
    _engine: BasicSearchEngine

    def __init__(self, db: DocumentVectorDB, engine: BasicSearchEngine) -> None:
        """
        Initialize an instance of the ClusteringSearchEngine class.

        Args:
            db (DocumentVectorDB): An instance of DocumentVectorDB class.
            engine (BasicSearchEngine): A search engine.
        """
        self._db = db
        self._engine = engine

    def retrieve_relevant_documents(
        self, query: str, n_neighbours: int
    ) -> list[tuple[float, str]] | None:
        """
        Index documents for retriever.

        Args:
            query (str): Query for obtaining relevant documents.
            n_neighbours (int): Number of relevant documents to return.

        Returns:
            list[tuple[float, str]] | None: Relevant documents with their distances.

        """
        return self._engine.retrieve_relevant_documents(query, n_neighbours=n_neighbours)


class VectorDBTreeSearchEngine(VectorDBEngine):
    """
    Engine provided unified interface to SearchEngine.
    """

    def __init__(self, db: DocumentVectorDB) -> None:
        """
        Initialize an instance of the VectorDBTreeSearchEngine class.

        Args:
            db (DocumentVectorDB): An instance of DocumentVectorDB class.
        """
        super().__init__(db, SearchEngine(db.get_vectorizer(), db.get_tokenizer()))
        self._engine.index_documents(db.get_raw_documents())


class VectorDBAdvancedSearchEngine(VectorDBEngine):
    """
    Engine provided unified interface to AdvancedSearchEngine.
    """

    def __init__(self, db: DocumentVectorDB) -> None:
        """
        Initialize an instance of the VectorDBAdvancedSearchEngine class.

        Args:
            db (DocumentVectorDB): An instance of DocumentVectorDB class.
        """
        super().__init__(db, AdvancedSearchEngine(db.get_vectorizer(), db.get_tokenizer()))
        self._engine.index_documents(db.get_raw_documents())
