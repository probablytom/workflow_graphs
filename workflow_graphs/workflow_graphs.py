class WorkflowGraph(object):

    environment = dict()

    def __init__(self, root=None):
        self.flow = []
        self.ended = False
        self.root = root
        self.current_executing_action = root
        self.action_adding_stack = []  # For building workflows.
        self.labels_map = dict()

    @property
    def currently_building_decision(self):
        return type(self.action_adding_stack[-1]) == Decision

    @property
    def finished_executing(self):
        return type(self.current_executing_action) == EndNode

    def run_workflow(self, actor, context=dict()):
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
            self.current_executing_action = self.current_executing_action.next_action

    @cascade
    def begin_with(self, first_action):
        if self.root is not None:
            raise BadWorkflowFormation("Already got somewhere to begin, but being given a second entrypoint! Conflicting\
        information!")
        self.root = first_action
        self.action_adding_stack.append(self.root)

    @cascade
    def call_that_step(self,label):
        self.labels_map[label] = self.action_adding_stack[-1]

    @cascade
    def move_to_step_called(self, label):
        def set_correct_action(ctx, actor, env):
            self.current_executing_action = self.labels_map[label]

            # We need to set the action to whatever came *before* the label, because after running the action we make from
            # this function, we move forward one step.
            # TODO THIS WILL CERTAINLY HAVE A BUG. WHAT IF THE PREVIOUS ACTION IS A DECISION? WHAT IF THERE COULD BE
            # MULTIPLE PREVIOUS STEPS?
            self.current_executing_action = self.current_executing_action.previous_action
        self.then(Action())

    @cascade
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

    @cascade
    def decide_on(condition_function):
        pass

    @cascade
    def when(cond):
        pass


class Decision(object):
    def __init__(self, condition):
        self.condition = condition  # This should be a function which takes anything and returns a bool.
        self.cases = {}
        self.current_case = None
        self.finished_construction = False

    @property
    def current_case_being_built(self):
        return self.cases[self.current_case]

    @cascade
    def when(self, cond):
        if cond in self.cases.keys():
            raise BadWorkflowFormationException("Same case used to define two different workflows!")

        #  If we're building a nested decision currently, pass this down to the one currently being built.
        if self.current_case_being_built.currently_building_decision:
            self.current_case_being_built.when(cond)

        self.cases[cond] = WorkflowGraph()
        self.current_case = None


    @cascade
    def then(self, next_action):
        self.current_case_being_built.then(next_action)

    @cascade
    def decide_on(self, condition_function):
        self.current_case_being_built.decide_on(next_action)

    @cascade
    def otherwise(self, next_action):
        #  If we're building a nested decision currently, pass this down to the one currently being built.
        if self.current_case_being_built.currently_building_decision:
            self.current_case_being_built.otherwise(cond)

        # TODO Define a default case
        pass

    @cascade
    def join(self):
        # TODO: What are the requirements for a decision being able to be joined?
        # We need a default case
        # Need to decide whether ending / joining is implicit at the end of a flow here (and which one if so), or whether
        # they're *always* explicit. If explicit, are they also required?
        self.construction_status = "finished"


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



class NoCurrentActionException(Exception):
    pass

class BadWorkflowFormation(Exception):
    pass


def cascade(method):
    def _(*args, **kwargs):
        method()
        return method.im_self
    return _

def add_message_to_ctx(ctx, actor, env):
    ctx["first_message"] = "hello world!"

def print_first_message(ctx, actor, env):
    print(ctx["first_message"])

flow = WorkflowGraph()
flow.begin_with(Action(add_message_to_ctx))
flow.then(Action(print_first_message))
flow.then(EndNode())
flow.run_workflow(dict(), dict())
