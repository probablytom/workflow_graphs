from .workflow_utilities import *
from types import FunctionType
from copy import copy

class WorkflowGraph(object):

    environment = dict()  # An environment global to all workflows.

    def __init__(self):
        self.graph = []
        self.just_jumped = False
        self.action_currently_executing = None  # The index of the action currently being executed
        self.label_action_mapping = {}
        self.decision_building_stack = list()

    def run_workflow(self, *args, **kwargs):
        self(*args, **kwargs)

    @property
    def __currently_building_a_decision(self):
        return len(self.decision_building_stack) is not 0

    @property
    def __last_action_added(self):
        activity = self.graph
        activity = activity[-1]

        # If we have nested decisions, this should take care of them.
        while type(activity) is dict or type(activity) is list:
            if type(activity) is list:
                activity = activity[-1]
            else:
                activity = activity["cases"][-1][-1]

        return activity

    def index_of(self, action):
        item_not_in_path = ItemNotInPath()

        def _recurse_find_index(graph, index_under_construction):

            if action in graph:
                index_under_construction.append(graph.index(action))
                return index_under_construction

            else:
                for act_index in range(len(graph)):
                    act = graph[act_index]
                    index_under_construction.append(act_index)

                    if type(act) is list:
                        deeper_index = _recurse_find_index(act, copy(index_under_construction))
                        if deeper_index is not item_not_in_path:
                            return deeper_index

                    if type(act) is dict:
                        for case_list in act["cases"]:
                            index_under_construction.append(case_list[0])
                            deeper_index = _recurse_find_index(case_list[1:], copy(index_under_construction))
                            if deeper_index is not item_not_in_path:
                                return deeper_index

                            index_under_construction.pop()  # Wasn't at this case, move to the next one.

                    index_under_construction.pop()  # wasn't at this index, move to the next one.

            # Never returned with an index, so can't be in path.
            return item_not_in_path

        return _recurse_find_index(self.graph, [])

    @cascade
    def then(self, next_action):

        next_action = convert_to_actions(next_action)

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
            self.action_currently_executing = self.index_of(self.label_action_mapping[label])
            self.just_jumped = True
            return
        self.then(move_step)

    @cascade
    def call_that_step(self, label):
        self.label_action_mapping[label] = self.__last_action_added
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

    def __call__(self, context, actor):
        [act(ctx, _actor, env) for act, ctx, _actor, env in self.yield_actions(context, actor)]

    def yield_actions(self, ctx, actor):

        self.action_currently_executing = [0]  # Begin at the beginning of the graph!

        # Keep traversing while we haven't reached the end of the graph
        while len(self.action_currently_executing) > 0 \
                and self.at_index(self.action_currently_executing) is not End:

            curr_action = self.at_index(self.action_currently_executing)

            # If we've got to a decision or a subworkflow, resolve so we end up at an Action again.
            while type(curr_action) is not FunctionType:

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
            yield curr_action, ctx, actor, WorkflowGraph.environment

            # If we haven't just jumped, then increment the index.
            if not self.just_jumped:
                self.action_currently_executing[-1] += 1

                def finished_yet():
                    return type(self.at_index(self.action_currently_executing)) is not CouldNotParseIndexException \
                           or len(self.action_currently_executing) is 0

                while not finished_yet():
                    self.action_currently_executing.pop()
                    if len(self.action_currently_executing) is not 0:
                        if type(self.action_currently_executing[-1]) is not int:
                            self.action_currently_executing.pop()
                        self.action_currently_executing[-1] += 1

            else:
                self.just_jumped = False  # reset the flag

        # Stop if we've reached the end.
        if len(self.action_currently_executing) is 0:
            raise StopIteration



def convert_to_actions(action):
    # Convert WorkflowGraphs to their list-representation, which is a valid action
    if type(action) is WorkflowGraph:
        action = action.graph

    # Any conversions necessary should have taken place by now.
    return action


anything_else = EqualToAnything()
