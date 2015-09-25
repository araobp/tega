#!/usr/bin/env python3.4

# 2014/8/26
# OSPF network topology
#

from tega.tree import *
from tega.idb import *
import copy

# OSPF topology: point to point links
# Matrix: link = [src node, src port, dest node, dest port, cost]
point_to_point = [[1, 0, 2, 0, 1],
                [1, 1, 3, 0, 1],
                [1, 2, 5, 0, 1],
                [2, 0, 1, 0, 1],
                [2, 1, 3, 1, 1],
                [2, 2, 4, 0, 2],
                [3, 0, 1, 1, 1],
                [3, 1, 2, 1, 1],
                [3, 2, 4, 1, 1],
                [3, 3, 4, 2, 1],
                [4, 0, 2, 2, 1],
                [4, 1, 3, 2, 1],
                [4, 2, 3, 3, 1],
                [5, 0, 1, 2, 2]]

# OSPF topology: transit networks
# Matrix: node_and_port = [node, port]
transit_networks = [[[5,1],[6,0],[7,0]],
                    [[5,2],[8,0],[9,0]]]

# Matrix => Tree transformation
router = Cont('router')
area = router.topology.ospf.area[0]
snode = area.point_to_point.snodes
transits = area.transit_networks
for l in point_to_point:
    node = 'node{}'.format(str(l[0]))
    port = l[1]
    link = snode[node].port[port]
    link.rnode = 'node{}'.format(str(l[2]))
    link.rport = l[3] 
    link.cost = l[4] 
i = 0
for l in transit_networks:
    j = 0
    for node_and_port in l:
        transits[i][j].node = node_and_port[0]
        transits[i][j].port = node_and_port[1]
        j += 1
    i += 1
    

# Walk
print('--- walk ---')
print(router.walk_())
print('')
# Serializes the data into JSON
print('--- JSON ---')
print(router.dumps_())

# Tree => Graph transformation
#
# Lists up all the pathes from 'node' to 'dest_node'.
# If dest_node == None then this function works like walk() starting from 'node'.
def graph_walk(link_oid, node, dest_node=None):

    parent_path = []
    parent_route = []
    path_list = []

    return _graph_walk(link_oid, node, dest_node=dest_node, parent_path=parent_path, parent_route=parent_route, path_list=path_list)


def _graph_walk(link_oid, node, dest_node, parent_path, parent_route, path_list):

    path = copy.copy(parent_path)
    path.append(node)
    
    if node == dest_node:
        path_list.append((path, parent_route))
    else:
        has_children = False
        for p in link_oid[node].port:
            l = link_oid[node].port[p]
            adj_node = l.rnode
            if adj_node in path:
                pass
            else:
                route = copy.copy(parent_route)
                route.append((node, p, l.cost))
                has_children = True
                _graph_walk(link_oid, node=adj_node, dest_node=dest_node, parent_path=path, parent_route=route, path_list=path_list)
        if not has_children and dest_node == None:
            path_list.append((path, parent_route))
        return path_list


print('')

print('--- all the paths from {} to {} ---'.format('node1', 'node4'))
max_hops = 0
for path in graph_walk(snode, 'node1', 'node4'):
    print(path[1])
    hops = len(path[1])
    if hops > max_hops:
        max_hops = hops
print('max hops: {}'.format(max_hops))

print('--- all the paths from {} to {} ---'.format('node5', 'node2'))
max_hops = 0
for path in graph_walk(snode, 'node5', 'node2'):
    print(path[1])
    hops = len(path[1])
    if hops > max_hops:
        max_hops = hops
print('max hops: {}'.format(max_hops))

print('--- all the paths from {} to {} ---'.format('node1', 'None'))
max_hops = 0
for path in graph_walk(snode, 'node1', None):
    print(path)
    hops = len(path[1])
    if hops > max_hops:
        max_hops = hops
print('max hops: {}'.format(max_hops))
