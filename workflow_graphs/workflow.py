from .workflow_utilities import *
from types import FunctionType, DictionaryType, ListType
from copy import deepcopy
from Queue import Queue

class WorkflowGraph(object):

    environment = dict()  # An environment global to all workflows.

    def __init__(self):
        self.graph = []
        self.label_action_mapping = dict()
        self.decision_building_stack = list()

    @cascade
    def then(self, next_action):
        next_action = convert_functions_to_actions(next_action)
        self.graph.append(next_action)
        # next_action = convert_functions_to_actions(next_action)  # If we're passed something other than an Action, convert it if possible.
        # self.graph[self.current_action_being_built] = next_action
        # self.current_action_being_built = next_action

    @cascade
    def decide_on(self, condition):
        pass

    @cascade
    def when(self, case):
        pass

    @cascade
    def begin_with(self, first_action):
        self.then(first_action)

    @cascade
    def join(self):
        pass

    @cascade
    def move_to_step_called(self, label):
        def move_step(ctx, actor, environment):
            self.current_executing_action = self.label_action_mapping[label]
            return
        self.then(move_step)

    @cascade
    def call_that_step(self, label):
        self.label_action_mapping[label] = self.current_action_being_built

    def run_workflow(self, ctx, actor):

        # We keep a seperate action stack. Actions we perform are taken from the stack, and when the stack is empty, it
        # gets refilled.
        # The benefit of this approach is that, when we're choosing a path on a decision, we just add the whole path
        # we're going to be traversing to the top of the stack. When we're finished with that path, pos increments and
        # we move past the decision we've just joined from.

        action_performing_queue = Queue()

        # So we can do this recursively if we have to (for nested decisions/subworkflows), we make this a function.
        def add_action_to_queue(action):
            # If the action is a dictionary, it's a decision!
            # Run the condition function, and then match cases until one is equal to the condition function's output.
            # When one is found, add all of the actions associated with the case, and then trigger a `matched_yet`
            # flag so we don't keep going.
            if type(action) is DictionaryType:
                case_yielded = action["condition_function"](ctx, actor, WorkflowGraph.environment)
                matched_yet = False
                for action_list in action["cases"]:

                    if action_list[0] == case_yielded and not matched_yet:
                        matched_yet = True

                        for dec_action in action_list[1:]:
                            add_action_to_queue(dec_action)


            # If we don't have a decision, we might have a subworkflow! If we do, process the subworkflow instead.
            elif type(action) is ListType:
                for list_action in action:
                    add_action_to_queue(list_action)

            else:
                action = convert_functions_to_actions(action)
                action_performing_queue.put(action)

        # Naviage the queue of 
        pos = 0
        while pos < len(self.graph):

            # Add to the action queue if it's empty.
            if action_performing_queue.empty():
                action = self.graph[pos]
                pos += 1
                add_action_to_queue(action)

            action = action_performing_queue.get()

            action(ctx, actor, WorkflowGraph.environment)


def convert_functions_to_actions(action):
    # Convert functions to Actions
    if type(action) is FunctionType:
        action = Action(action)

    # Any conversions necessary should have taken place by now.
    return action

End = EndNode()
do_nothing = Idle()
anything_else = EqualToAnything()

