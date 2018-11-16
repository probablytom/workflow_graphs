from .workflow_utilities import *
from types import FunctionType, DictionaryType, ListType
from copy import copy, deepcopy
from Queue import Queue

class WorkflowGraph(object):

    environment = dict()  # An environment global to all workflows.

    def __init__(self):
        self.graph = []
        self.just_jumped = False
        self.action_currently_executing = None  # The index of the action currently being executed
        self.label_action_mapping = {}
        self.decision_building_stack = list()

    @property
    def __currently_building_a_decision(self):
        return len(self.decision_building_stack) is not 0

    @property
    def __last_action_added(self):
        activity = self.graph
        activity = activity[-1]

        # If we have nested decisions, this should take care of them.
        while type(activity) is dict:
            activity = activity["cases"][-1][-1]

        return activity

    def __last_action_index(self):
        last_action = [len(self.graph)-1]
        while type(self.at_index(last_action)) is dict:
            last_action.append(self.at_index(last_action)["cases"][-1][0])
            last_action.append(len(self.at_index(last_action)["cases"][-1]) - 2)
        return last_action

    @cascade
    def then(self, next_action):

        next_action = convert_functions_to_actions(next_action)

        if not self.__currently_building_a_decision:
            self.graph.append(next_action)
        else:
            self.decision_building_stack[-1]["cases"][-1].append(next_action)

    @cascade
    def decide_on(self, condition):
        new_decision = {"condition_function": condition,
                        "cases":              list()}
        self.decision_building_stack.append(new_decision)

    @cascade
    def when(self, case):
        self.decision_building_stack[-1]["cases"].append([case])

    @cascade
    def begin_with(self, first_action):
        self.then(first_action)

    @cascade
    def join(self):
        fully_built_decision = self.decision_building_stack.pop()
        self.then(fully_built_decision)

    @cascade
    def move_to_step_called(self, label):
        def move_step(ctx, actor, environment):
            # Without making a copy, Python actually makes the value in the dictionary here
            # a reference to self.action_currently_executing.
            # I have no idea why, it's _bananas_, but it took me a solid day and a half to debug. Don't remove the copy!
            self.action_currently_executing = copy(self.label_action_mapping[label])
            self.just_jumped = True
            return
        self.then(move_step)

    @cascade
    def call_that_step(self, label):
        self.label_action_mapping[label] = self.__last_action_index()
        pass

    # For code reuse, because we navigate the graph by index lots!
    def at_index(self, index):
        # Get the action currently being executed
        index = copy(index)
        graph = copy(self.graph)
        index.reverse()  # Now we can treat it like a stack
        try:
            while len(index) is not 0:
                if type(graph) is list:
                    graph = graph[index.pop()]
                elif type(graph) is dict:
                    case_to_match = index.pop()
                    position_in_case_path = index.pop()
                    path_found = False
                    for path_to_check in graph["cases"]:
                        case_for_path_to_check = path_to_check[0]
                        path = path_to_check[1:]
                        if not path_found and case_for_path_to_check == case_to_match:
                            path_found = True
                            graph = path[position_in_case_path]

                else:
                    raise NotImplemented()  # What do now?
        except:
            return CouldNotParseIndexException()

        return graph

    def run_workflow(self, ctx, actor):

        self.action_currently_executing = [0]  # Begin at the beginning of the graph!

        # Keep traversing while we haven't reached the end of the graph
        while self.action_currently_executing[0] < len(self.graph)\
                and type(self.at_index(self.action_currently_executing)) is not EndNode:

            curr_action = self.at_index(self.action_currently_executing)

            # If we've got to a decision or a subworkflow, resolve so we end up at an Action again.
            while type(curr_action) is not Action:

                if type(curr_action) is list:
                    self.action_currently_executing.append(0)

                if type(curr_action) is dict:
                    condition_func = curr_action["condition_function"]
                    case = condition_func(ctx, actor, WorkflowGraph.environment)
                    matched_yet = False

                    for case_path in curr_action["cases"]:
                        if not matched_yet and case == case_path[0]:
                            matched_yet = True
                            self.action_currently_executing.append(case)
                            self.action_currently_executing.append(0)

                curr_action = self.at_index(self.action_currently_executing)

            # Execute the action found. "graph" should now be an Action node.
            curr_action(ctx, actor, WorkflowGraph.environment)

            # If we haven't just jumped, then increment the index.
            if not self.just_jumped:
                self.action_currently_executing[-1] += 1

                finished_yet = lambda: type(self.at_index(self.action_currently_executing)) is not CouldNotParseIndexException

                while not finished_yet():
                    self.action_currently_executing.pop()
                    if type(self.action_currently_executing[-1]) is not int:
                        self.action_currently_executing.pop()
                    self.action_currently_executing[-1] += 1

            else:
                self.just_jumped = False  # reset the flag

        pass


def convert_functions_to_actions(action):
    # Convert functions to Actions
    if type(action) is FunctionType:
        action = Action(action)

    # Any conversions necessary should have taken place by now.
    return action

End = EndNode()
do_nothing = Idle()
anything_else = EqualToAnything()

