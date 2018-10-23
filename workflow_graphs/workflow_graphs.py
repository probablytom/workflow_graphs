class WorkflowGraph(object):

    environment = dict()

    def __init__(self, root=None):
        self.flow = []
        self.ended = False
        self.root = root
        self.current_executing_action = root
        self.action_adding_stack = []  # For building workflows.
        self.decision_nesting_stack = []

    def run_workflow(self, actor, context=dict()):
        '''
        Runs a workflow.
        '''
        # Check to see whether there are any actions set up to run. We can't
        # run anything if we don't have anything set up!
        if self.root is None:
            raise NoCurrentActionException("Workflow made but no actions ever provided.")

        self.current_executing_action = self.root

        while self.current_executing_action.__class__ is not EndNode:
            self.current_executing_action.execute(context, actor, WorkflowGraph.environment)
            self.current_executing_action = self.current_executing_action.next_action

    def begin_with(self, first_action):
        if self.root is not None:
            raise BadWorkflowFormation("Already got somewhere to begin, but being given a second entrypoint! Conflicting\
        information!")
        self.root = first_action
        self.action_adding_stack.append(self.root)

        return self

    def then(self, next_action):

        # TODO
        raise Exception("Need to add logic to determine whether we're working out a decision node construction.")

        # Make sure we have something to happen previous to this! Semantically that's essential.
        if len(self.action_adding_stack) == 0:
            raise BadWorkflowFormarion("Asked to do something after something else with 'then', but I hold no\
        information about what happened before!")

        # Set the next action
        curr = self.action_adding_stack.pop()
        curr.set_next_action(next_action)

        self.action_adding_stack.append(next_action)

        return self

    def decide_on(condition_function):
        self.decision_building_stack.append(DecisionNode())
        pass

    def when(cond):
        pass



class Action(object):
    def __init__(self,
                 associated_function,
                 previous_action=None,
                 next_action=None):
        self.func = associated_function
        self.previous_action = previous_action
        self.next_action = next_action

    def set_previous_action(self, prev_act):
        '''
        Properly sets a node's expected previous action (forwards and backwards).
        @param prev_act: A GraphNode representing the previous action for this node.
        '''
        self.previous_action = prev_act
        prev_act.next_action = self

    def set_next_action(self, next_act):
        '''
        Properly sets a node's expected next action (forwards and backwards).
        @param next_act: A GraphNode representing the next action for this node.
        '''
        self.next_action = next_act
        next_act.previous_action = self

    def execute(self, context, actor, env):
        return self.func(context, actor, env)

class EndNode(object):
    '''
    TODO is there anything this actually needs to do? Maybe callbacks eventually. Right now it kind of acts as a
    sentinel of sorts.
    '''
    pass


class Decision(object):
    pass


class NoCurrentActionException(Exception):
    pass

class BadWorkflowFormation(Exception):
    pass


def add_message_to_ctx(ctx, actor, env):
    ctx["first_message"] = "hello world!"

def print_first_message(ctx, actor, env):
    print(ctx["first_message"])

flow = WorkflowGraph()
flow.begin_with(Action(add_message_to_ctx))
flow.then(Action(print_first_message))
flow.then(EndNode())
flow.run_workflow(dict(), dict())
