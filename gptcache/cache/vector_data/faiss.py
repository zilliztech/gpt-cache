from gptcache.util import import_faiss
import_faiss()

import os
import faiss
from faiss import IndexHNSWFlat, Index
import numpy as np
from gptcache.cache.vector_data.vector_index import VectorIndex


class Faiss(VectorIndex):
    index: Index

    def __init__(self, index_file_path: str, dimension: int, top_k: int, skip_file=False):
        self.index_file_path = index_file_path
        self.dimension = dimension
        self.index = IndexHNSWFlat(dimension, 32)
        self.top_k = top_k
        if os.path.isfile(index_file_path) and not skip_file:
            self.index = faiss.read_index(index_file_path)

    def init(self, **kwargs):
        pass

    def add(self, key: str, data: list[any]):
        np_data = np.array(data).astype('float32').reshape(1, -1)
        self.index.add(np_data)

    def mult_add(self, datas: list[list[any]]):
        np_data = np.array(datas).astype('float32')
        self.index.add(np_data)

    def search(self, data: list[any]):
        if self.index.ntotal == 0:
            return None
        np_data = np.array(data).astype('float32').reshape(1, -1)
        D, I = self.index.search(np_data, self.top_k)
        distances = []
        for d in D[:1].reshape(-1):
            distances.append(d)
        vector_datas = [self.index.reconstruct(int(i)) for i in I[:1].reshape(-1)]
        return zip(distances, vector_datas)

    def rebuild_index(self, all_data: list[any]):
        f = Faiss(self.index_file_path, self.dimension, top_k=self.top_k, skip_file=True)
        f.mult_add(all_data)
        return f

    def close(self):
        faiss.write_index(self.index, self.index_file_path)
