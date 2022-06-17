import torch as th
import os
from dgl.data import DGLBuiltinDataset
from dgl.data.utils import load_graphs, save_graphs
import pickle, csv

__all__ = ['ICDM2022Dataset']


class ICDM2022Dataset(DGLBuiltinDataset):
    def __init__(self, init_emb=False, item_embedding_dim=50, non_item_embedding_dim=30, raw_dir=None,
                 force_reload=False,
                 verbose=False,
                 transform=None):
        name = 'icdm2022'
        self.init_emb = init_emb
        self.item_embedding_dim = item_embedding_dim
        self.non_item_embedding_dim = non_item_embedding_dim

        super(ICDM2022Dataset, self).__init__(
            name,
            url='https://s3.cn-north-1.amazonaws.com.cn/dgl-data/dataset/openhgnn/{}.zip'.format(name),
            raw_dir=raw_dir,
            force_reload=force_reload, verbose=verbose, transform=transform)

    def process(self):
        self.load()

    def has_cache(self):
        graph_path = os.path.join(self.save_path, 'graph.bin')
        return os.path.exists(graph_path)

    def save(self):
        graph_path = os.path.join(self.save_path, 'graph.bin')
        save_graphs(graph_path, self._g)

    def load(self):
        # load graph
        print('loading dataset...')
        graph_path = os.path.join(self.save_path, 'graph.bin')
        gs, _ = load_graphs(graph_path)
        g = gs[0]
        # load node map
        nodes_path = os.path.join(self.save_path, 'icdm2022.nodes.dgl')
        with open(nodes_path, 'rb') as f:
            nodes_info = pickle.load(f)

        # load label
        labels_path = os.path.join(self.save_path, 'icdm2022_labels.csv')
        labels = th.tensor([th.nan] * g.num_nodes(self.category))
        with open(labels_path, 'r') as f:
            csvreader = csv.reader(f)
            item_maps = nodes_info['maps']['item']
            for row in csvreader:
                orig_id = int(row[0])
                new_id = item_maps.get(orig_id)
                if new_id is not None:
                    labels[new_id] = int(row[1])

        label_mask = ~th.isnan(labels)
        label_idx = th.nonzero(label_mask, as_tuple=False).squeeze()
        g.nodes[self.category].data['label'] = labels.type(th.int64)
        split_ratio = [0.8, 0.1, 0.1]
        num_labels = len(label_idx)
        num_nodes = g.num_nodes(self.category)
        train_mask = th.zeros(num_nodes).bool()
        train_mask[label_idx[0: int(split_ratio[0] * num_labels)]] = True
        val_mask = th.zeros(num_nodes).bool()
        val_mask[
            label_idx[int(split_ratio[0] * num_labels): int((split_ratio[0] + split_ratio[1]) * num_labels)]] = True
        test_mask = th.zeros(num_nodes).bool()
        test_mask[label_idx[int((split_ratio[0] + split_ratio[1]) * num_labels):]] = True
        g.nodes[self.category].data['train_mask'] = train_mask
        g.nodes[self.category].data['val_mask'] = val_mask
        g.nodes[self.category].data['test_mask'] = test_mask
        if self.init_emb:
            for ntype in g.ntypes:
                if ntype == 'item':
                    g.nodes[ntype].data['h'] = th.rand(g.num_nodes(ntype), self.item_embedding_dim, dtype=th.float32)
                else:
                    g.nodes[ntype].data['h'] = th.rand(g.num_nodes(ntype), self.non_item_embedding_dim,
                                                       dtype=th.float32)
        self._g = gs[0]

        print('finish loading dataset')

    @property
    def category(self):
        return 'item'

    @property
    def target_ntype(self):
        return 'item'

    @property
    def num_classes(self):
        return 2

    def __getitem__(self, idx):
        assert idx == 0
        return self._g

    def __len__(self):
        return 1
