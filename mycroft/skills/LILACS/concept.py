from mycroft.util.log import getLogger
import numpy as np
import random

__authors__ = ["jarbas", "heinzschmidt"]

logger = getLogger("Skills")


class ConceptNode():
    def __init__(self, name, data={}, parent_concepts={},
        child_concepts={}, synonims=[], antonims=[]):
        self.name = name
        self.synonims = synonims
        self.antonims = antonims
        self.parent_concepts = parent_concepts
        self.child_concepts = child_concepts
        self.data = {}

    def add_synonim(self, synonim):
        if synonim not in self.synonims:
            self.synonims.append(synonim)

    def add_data(self, key, data={}):
        if key in self.data:
            self.data[key] = data
        else:
            self.data.setdefault(key, data)

    def add_parent(self, parent_name, gen = 1, update = True):

        # a node cannot be a parent  of itself
        if parent_name == self.name:
            return

        # a node cannot be a parent and a child (would it make sense in some corner case?)
        if parent_name in self.child_concepts:
            return

        if parent_name not in self.parent_concepts:
            self.parent_concepts.setdefault(parent_name, gen)
        elif parent_name in self.parent_concepts and update:
            self.parent_concepts[parent_name] = gen

    def add_child(self, child_name, gen=1, update = True):
        # a node cannot be a child of itself
        if child_name == self.name:
            return

        if child_name in self.parent_concepts:
            return

        if child_name not in self.child_concepts:
            self.child_concepts.setdefault(child_name, gen)
        elif child_name in self.child_concepts and update:
            self.child_concepts[child_name] = gen

    def remove_synonim(self, synonim):
        i = 0
        for name in self.synonims:
            if name == synonim:
                self.child_concepts.pop(i)
                return
            i += 1

    def remove_data(self, key):
        self.data.pop(key)

    def remove_parent(self, parent_name):
        self.parent_concepts.pop(parent_name)

    def remove_child(self, child_name):
        self.child_concepts.pop(child_name)


class ConceptConnector():
    def __init__(self, logger,  concepts = {}):
        self.concepts = concepts
        self.logger = logger

    def add_concept(self, concept_name, concept):
        if concept_name in self.concepts:
            #  merge fields
            for parent in concept.parent_concepts:
                if parent not in self.get_parents(concept_name):
                    self.concepts[concept_name].add_parent(parent, gen=concept.parent_concepts[parent])
            for child in concept.child_concepts:
                if child not in self.get_childs(concept_name):
                    self.concepts[concept_name].add_child(child, gen=concept.child_concepts[child])
            for antonim in concept.antonims:
                if antonim not in self.concepts[concept_name].antonims:
                    self.concepts[concept_name].antonims.add_antonim(antonim)
            for synonim in concept.synonims:
                if synonim not in self.concepts[concept_name].synonims:
                    self.concepts[concept_name].synonims.add_synonim(synonim)
        else:
            self.concepts.setdefault(concept_name, concept)

    def remove_concept(self, concept_name):
        self.concepts.pop(concept_name)

    def get_childs(self, concept_name):
        return self.concepts[concept_name].child_concepts

    def get_parents(self, concept_name):
        return self.concepts[concept_name].parent_concepts

    def get_antonims(self, concept_name):
        return self.concepts[concept_name].antonims

    def get_synonims(self, concept_name):
        return self.concepts[concept_name].synonims

    def create_concept(self, new_concept_name, data={},
                       child_concepts={}, parent_concepts={}, synonims=[], antonims=[]):

        self.logger.info("processing concept " + new_concept_name)


        # safe - checking
        if new_concept_name in parent_concepts:
            parent_concepts.pop(new_concept_name)
        if new_concept_name in child_concepts:
            child_concepts.pop(new_concept_name)

        # handle new concept
        self.logger.info("creating concept node for: " + new_concept_name)
        concept = ConceptNode(name=new_concept_name, data=data, child_concepts=child_concepts, parent_concepts=parent_concepts,
                              synonims=synonims, antonims=antonims)
        self.add_concept(new_concept_name, concept)

        # handle parent concepts
        for concept_name in parent_concepts:
            self.logger.info("checking if parent node exists: " + concept_name)
            gen = parent_concepts[concept_name]
            # create parent if it doesnt exist
            if concept_name not in self.concepts:
                self.logger.info("creating node: " + concept_name )
                concept = ConceptNode(concept_name, data={}, child_concepts={}, parent_concepts={}, synonims=[], antonims=[])
                self.add_concept(concept_name, concept)
            # add child to parent
            self.logger.info("adding child: " + new_concept_name + " to parent: " + concept_name)
            self.concepts[concept_name].add_child(new_concept_name, gen=gen)

        # handle child concepts
        for concept_name in child_concepts:
            self.logger.info("checking if child node exists: " + concept_name)
            gen = child_concepts[concept_name]
            # create child if it doesnt exist
            if concept_name not in self.concepts:
                self.logger.info("creating node: " + concept_name)
                concept = ConceptNode(concept_name, data={}, child_concepts={}, parent_concepts={}, synonims=[], antonims=[])
                self.add_concept(concept_name, concept)
            #add parent to child
            self.logger.info("adding parent: " + new_concept_name + " to child: " + concept_name)
            self.concepts[concept_name].add_parent(new_concept_name, gen=gen)


class ConceptCrawler():
    def __init__(self, center_node, depth=20, concept_connector=None):
        # https://github.com/ElliotTheRobot/LILACS-mycroft-core/issues/9
        self.logger = logger
        # concept database
        self.concept_db = concept_connector
        if self.concept_db is None:
            self.concept_db = ConceptConnector(logger)
        # crawl depth
        self.depth = depth
        # crawl path
        self.crawl_path = [center_node]
        # crawled antonims
        self.do_not_crawl = []
        # nodes we left behind without checking
        self.uncrawled = []
        # nodes we already checked
        self.crawled = []
        # count visits to each node
        self.visits = {}


    def build_tree(self, center_node, target_node, depth=20, direction="parents", tree = [], step=0):
        # start in center_node, add all parents / childs
        parents = []
        try:
            self.logger.info("Getting parents of: " + center_node)
            concepts = self.concept_db.get_parents(center_node)
            for key in concepts:
                parents.append(key)
        except:
            self.logger.error("no node named " + str(center_node))

        if parents != []:
            self.logger.info("adding to tree: " + str(parents))
            tree.append(parents)
            for node in tree[step]:
                self.logger.info("Checking next node: " + node)
                depth -= 1
                self.logger.info("Current depth: " + str(depth))
                if depth <= 0:
                    break
                tree = self.build_tree(node, target_node, depth, direction, tree, step + 1)
        return tree

    def find_path(self, center_node, target_node, path=[]):
        # find first path to connection
        path = path + [center_node]
        if center_node == target_node:
            return path

        if center_node not in self.parents_tree:
            return None

        for node in self.parents_tree[center_node]:
            if node not in path:
                newpath = self.find_path(center_node, target_node, path)
                if newpath:
                    return newpath
        return None

    def find_all_paths(self, center_node, target_node, path=[]):
        path = path + [center_node]

        if center_node == target_node:
            return [path]

        if center_node not in self.parents_tree:
            return []

        paths = []
        for node in self.parents_tree[center_node]:
            if node not in path:
                newpaths = self.find_all_paths(node, target_node, path)
                for newpath in newpaths:
                    paths.append(newpath)
        return paths

    def find_shortest_path(self, center_node, target_node, path=[]):

        path = path + [center_node]
        if center_node == target_node:
            return path

        if center_node not in self.parents_tree:
            return None

        shortest = None

        for node in self.parents_tree[center_node]:
            if node not in path:
                newpath = self.find_shortest_path(node, target_node, path)
                if newpath:
                    if not shortest or len(newpath) < len(shortest):
                        shortest = newpath
        return shortest

    def find_minimum_node_distance(self, center_node, target_node):
        return len(self.find_shortest_path(center_node, target_node))

    def get_total_crawl_distance(self):
        return len(self.crawled)

    def get_crawl_path_distance(self):
        return len(self.crawl_path
                   )

    def drunk_crawl(self, target):
        pass

    @staticmethod
    def sigmoid(x):
        return 1 / (1 + np.exp(-x))

    def choose_next_node(self, node, direction="parents"):
        # when choosing the next node we have to think about what matters more
        # - checking child or parent?
        # - does node have synonims?
        # - is any of the connected nodes blacklisted in this crawl (antonim)?
        # - choose stronger connections preferably
        # - number of times we visited this node
        if node is None:
            return node

        # keep count of visits to this node
        if node in self.visits:
            self.visits[node] += 1
        else:
            self.visits[node] = 1

        # add current node to crawl path
        self.crawl_path.append(node)

        # add current node to crawled list
        if node not in self.crawled:
            self.crawled.append(node)

        # are we checking parents or childs?
        if direction == "parents":
            nodes = self.concept_db.get_parents(node)
            # check if node as synonims
            synonims = self.concept_db.get_synonims(node)
            for synonim in synonims:
            # get connections of these synonims also
                nodes += self.concept_db.get_parents(synonim)
        elif direction == "childs":
            nodes = self.concept_db.get_childs(node)
            # check if node as synonims
            synonims = self.concept_db.get_synonims(node)
            for synonim in synonims:
                # get connections of these synonims also
                nodes += self.concept_db.get_childs(synonim)
        else:
            self.logger.error("Invalid crawl direction")
            return None

        # if no connections found return
        if len(nodes) == 0:
            return None

        # add these nodes to "nodes to crawl"
        for node in nodes:
            self.uncrawled.append(node)
            # add all antonims from these nodes to do no crawl
            for antonim in self.concept_db.get_antonims(node):
                self.do_not_crawl.append(antonim)
            # remove any node we are not supposed to crawl
            if node in self.do_not_crawl:
                nodes.pop(node)
            # if we already crawled this node, increase its count but do not re-visit
            if node in self.crawled:
                nodes.pop(node)
                self.visits[node] += 1

        # create a weighted list giving preference
        for node in nodes:
            # turn all values into a value between 0 and 1
            # multiply by 100
            # smaller values are more important
            nodes[node] = 100 - self.sigmoid(nodes[node]) * 100

        list = [k for k in nodes for dummy in range(int(nodes[k]))]
        # choose a node to crawl next
        next_node = random.choice(list)
        print nodes
        print next_node
        return next_node


