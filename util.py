from __future__ import print_function

import argparse

import networkx as nx
import numpy as np
from sklearn.model_selection import train_test_split

# import matplotlib.pyplot as plt

cmd_opt = argparse.ArgumentParser(description='Argparser for graph_classification')
cmd_opt.add_argument('-mode', default='cpu', help='cpu/gpu')
cmd_opt.add_argument('-gm', default='mean_field', help='mean_field/loopy_bp')
cmd_opt.add_argument('-data', default=None, help='data folder name')
cmd_opt.add_argument('-batch_size', type=int, default=50, help='minibatch size')
cmd_opt.add_argument('-seed', type=int, default=1, help='seed')
cmd_opt.add_argument('-feat_dim', type=int, default=0, help='dimension of node feature')
cmd_opt.add_argument('-num_class', type=int, default=0, help='#classes')
cmd_opt.add_argument('-fold', type=int, default=1, help='fold (1..10)')
cmd_opt.add_argument('-num_epochs', type=int, default=1000, help='number of epochs')
cmd_opt.add_argument('-latent_dim', type=int, default=64, help='dimension of latent layers')
cmd_opt.add_argument('-out_dim', type=int, default=1024, help='s2v output size')
cmd_opt.add_argument('-hidden', type=int, default=100, help='dimension of regression')
cmd_opt.add_argument('-max_lv', type=int, default=4, help='max rounds of message passing')
cmd_opt.add_argument('-learning_rate', type=float, default=0.0001, help='init learning_rate')

cmd_args, _ = cmd_opt.parse_known_args()

print(cmd_args)


class S2VGraph(object):
    def __init__(self, g, node_tags, label):
        self.num_nodes = len(node_tags)
        self.node_tags = node_tags
        self.label = label

        x, y = zip(*g.edges())
        self.num_edges = len(x)
        self.edge_pairs = np.ndarray(shape=(self.num_edges, 2), dtype=np.int32)
        self.edge_pairs[:, 0] = x
        self.edge_pairs[:, 1] = y
        self.edge_pairs = self.edge_pairs.flatten()


def load_data():
    print('loading data')

    g_list = []
    label_dict = {}
    feat_dict = {}

    with open('./data/%s/%s.txt' % (cmd_args.data, cmd_args.data), 'r') as f:
        graph_count = int(f.readline().strip())
        print(f"Loading {graph_count} graphs")
        for i in range(graph_count):
            double_counter = 0
            row = f.readline().strip().split()
            node_count, graph_label = [int(w) for w in row]
            if not graph_label in label_dict:
                mapped = len(label_dict)
                label_dict[graph_label] = mapped
            g = nx.Graph()
            node_tags = []
            n_edges = 0
            for node_idx in range(node_count):
                g.add_node(node_idx)
                row = f.readline().strip().split()
                row = [int(w) for w in row]
                if not row[0] in feat_dict:
                    mapped = len(feat_dict)
                    feat_dict[row[0]] = mapped
                node_tags.append(feat_dict[row[0]])

                n_edges += row[1]
                for k in range(2, len(row)):
                    if row[k] not in g[node_idx]:
                        g.add_edge(node_idx, row[k])
                    else:
                        double_counter += 1
            assert len(g.edges()) + double_counter == n_edges
            assert len(g) == node_count
            g_list.append(S2VGraph(g, node_tags, graph_label))
    for g in g_list:
        g.label = label_dict[g.label]
    cmd_args.num_class = len(label_dict)
    cmd_args.feat_dim = len(feat_dict)
    print('# classes: %d' % cmd_args.num_class)
    print('# node features: %d' % cmd_args.feat_dim)
    benign_sample_idx: list[int] = []
    malware_sample_idx: list[int] = []

    for i in range(len(g_list)):
        if g_list[i].label == 0:
            malware_sample_idx.append(i)
        elif g_list[i].label == 1:
            benign_sample_idx.append(i)

    assert len(malware_sample_idx) + len(benign_sample_idx) == len(g_list)

    if len(benign_sample_idx) > len(malware_sample_idx):
        max_len = len(malware_sample_idx)
    else:
        max_len = len(benign_sample_idx)

    malware_sample_idx = malware_sample_idx[:max_len]
    benign_sample_idx = benign_sample_idx[:max_len]

    assert len(malware_sample_idx) == max_len
    assert len(benign_sample_idx) == max_len

    all_sample_idx: list[int] = list()
    mal_i = 0
    ben_i = 0

    for i in range(max_len * 2):
        if i % 2 == 0:
            all_sample_idx.append(malware_sample_idx[mal_i])
            mal_i += 1
        else:
            all_sample_idx.append(benign_sample_idx[ben_i])
            ben_i += 1

    assert len(all_sample_idx) == max_len * 2

    train_idxes, test_idxes = train_test_split(all_sample_idx, test_size=0.2, train_size=0.8, shuffle=True)

    train_graphs = [g_list[i] for i in train_idxes]
    test_graphs = [g_list[i] for i in test_idxes]

    print(f"Malware graphs: {len([graph for graph in test_graphs if graph.label == 1])}")
    print(f"Benign graphs: {len([graph for graph in test_graphs if graph.label == 0])}")

    return train_graphs, test_graphs
