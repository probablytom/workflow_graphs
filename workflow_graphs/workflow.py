from workflow_utilities import *
from types import FunctionType


class WorkflowGraph(object):

    environment = dict()

    def __init__(self, root=None):
        self.flow = []
        self.ended = False
        self.dont_jump = False
        self.root = root
        self.current_executing_action = root
        self.action_adding_stack = []  # For building workflows.
        self.decision_adding_stack = []
        self.labels_map = dict()
        self.decision_case_mapping = dict()  # A dictionary of lists of tuples. decision node -> [(case -> next action)]
        self.condition_to_build_decision_path_with = None

    @property
    def currently_building_decision(self):
        return type(self.action_adding_stack[-1]) == Decision

    @property
    def finished_executing(self):
        return type(self.current_executing_action) == EndNode

    @property
    def decision_currently_being_built(self):
        if len(self.decision_adding_stack) == 0:
            return None

        return self.decision_adding_stack[-1]

    def run_workflow(self, context=dict(), actor=dict()):
        '''
        Runs a workflow.
        '''
        # Check to see whether there are any actions set up to run. We can't
        # run anything if we don't have anything set up!
        if self.root is None:
            raise NoCurrentActionException("Workflow made but no actions ever provided.")

        self.current_executing_action = self.root

        while not self.finished_executing:
            self.current_executing_action.execute(context, actor, WorkflowGraph.environment)
            if not self.dont_jump:
                self.current_executing_action = self.current_executing_action.next_action
            else:
                self.dont_jump = False

    @cascade
    def begin_with(self, first_action):
        if self.root is not None:
            raise BadWorkflowFormation("Already got somewhere to begin, but being given a second entrypoint! Conflicting\
        information!")

        if type(first_action) == FunctionType:
            first_action = Action(first_action)

        self.root = first_action
        self.action_adding_stack.append(self.root)

    @cascade
    def call_that_step(self,label):
        self.labels_map[label] = self.action_adding_stack[-1]

    @cascade
    def move_to_step_called(self, label):
        def set_correct_action(ctx, actor, env):
            self.current_executing_action = self.labels_map[label]
            self.dont_jump = True

        self.then(set_correct_action)

    @cascade
    def then(self, next_action):

        if type(next_action) == FunctionType:
            next_action = Action(next_action)

        # Just in case we're building a new path on a decision node
        if self.condition_to_build_decision_path_with is not None:

            curr_case_list = self.decision_case_mapping[self.decision_currently_being_built]
            curr_case_list.append((self.condition_to_build_decision_path_with, next_action))
            self.action_adding_stack.pop()
            self.action_adding_stack.append(next_action)  # We do this manually so as not to set previous actions.

            self.condition_to_build_decision_path_with = None
            return  # We're done; exit, we don't care about the rest.


        # Make sure we have something to happen previous to this! Semantically that's essential.
        if len(self.action_adding_stack) == 0:
            raise BadWorkflowFormation("Asked to do something after something else with 'then', but I hold no\
        information about what happened before!")

        # Set the next action
        curr = self.action_adding_stack.pop()
        curr.set_next_action(next_action)

        self.action_adding_stack.append(next_action)

    @cascade
    def decide_on(self, condition_function):
        def decision_action_function(ctx, actor, env):

            for case, path in self.decision_case_mapping[self.current_executing_action]:
                if condition_function(ctx, actor, env) == case:
                    self.current_executing_action = path
                    self.dont_jump = True
                    return

            # We didn't return, which means we must have to take the default action.
            raise NotImplemented("Need to implement logic for default actions.")

        # We have a function which represents our decision. Now, we set up an action for it...
        # ...which can sit in our workflow.
        decision_action = Action(decision_action_function)
        self.decision_adding_stack.append(decision_action)
        self.decision_case_mapping[decision_action] = list()
        self.then(decision_action)

    @cascade
    def when(self, cond):
        self.condition_to_build_decision_path_with = cond

    @cascade
    def join(self):
        decision_being_built = self.decision_adding_stack.pop()  # We get it manually to take it off the stack, too.
        join_for_decision = JoinNode()

        #
        def find_end_of_path(curr):
            while curr.next_action is not None:
                curr = curr.next_action
            return curr

        # If a path doesn't end with an EndNode, then join back to the end of the decision by default.
        for _, path in self.decision_case_mapping[decision_being_built]:
            end_of_path = find_end_of_path(path)
            if end_of_path != End:
                end_of_path.set_next_action(join_for_decision)

        self.then(join_for_decision)


End = EndNode()
anything_else = EqualToAnything()
