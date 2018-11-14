from .workflow_utilities import *
from types import FunctionType

class WorkflowGraph(object):

    environment = dict()  # An environment global to all workflows.

    def __init__(self):
        self.graph = dict()
        self.root = StartNode()
        self.current_action_being_built = self.root
        self.decision_case_mappings = dict()
        self.label_action_mapping = dict()
        self.current_executing_action = self.root  # We'll start here

    def then(self, next_action):
        next_action = convert_functions_to_actions(next_action)  # If we're passed something other than an Action, convert it if possible.
        self.graph[self.current_action_being_built] = next_action
        self.current_action_being_built = next_action

    def decide_on(self, condition):
        pass

    def when(self, case):
        pass

    def begin_with(self, first_action):

    def join(self):
        pass

    def move_to_step_called(self, label):
        def move_step(ctx, actor, environment):
            self.current_executing_action = self.label_action_mapping[label]
            return
        self.then(move_step)

    def call_that_step(self, label):
        self.label_action_mapping[label] = self.current_action_being_built

    def run_workflow(self, ctx, actor):
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