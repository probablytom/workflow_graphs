def cascade(method):
    # Implements cascading method calls as a decorator.
    def _(*args, **kwargs):
        method(*args, **kwargs)
        return args[0]  # This _should_ be self...
    return _


class Decision(object):
    # TODO: will we use this at all?! I feel like we should, for the purpsoe of "typing"...
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
            raise BadWorkflowFormation("Same case used to define two different workflows!")

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
                 previous_action=list(),
                 next_action=None):
        self.associated_function = associated_function
        self.previous_action = previous_action
        self.next_action = next_action

    def set_previous_action(self, prev_act):
        '''
        Properly sets a node's expected previous action (forwards and backwards).
        @param prev_act: A GraphNode representing the previous action for this node.
        '''
        self.previous_action.append(prev_act)
        prev_act.next_action = self

    def set_next_action(self, next_act):
        '''
        Properly sets a node's expected next action (forwards and backwards).
        @param next_act: A GraphNode representing the next action for this node.
        '''
        self.next_action = next_act
        next_act.previous_action.append(self)

    def execute(self, context, actor, env):
        return self.associated_function(context, actor, env)


class DummyAction(Action):
    '''
    For actions which just signal things, like a Join or an End, and which don't actually do anything themselves.
    Intended to be subclassed.
    '''
    def __init__(self):
        def identity(ctx, actor, env):
            pass
        super(DummyAction, self).__init__(identity)


class EndNode(DummyAction):
    '''
    TODO is there anything this actually needs to do? Maybe callbacks eventually. Right now it kind of acts as a
    sentinel of sorts.
    '''
    pass


class JoinNode(DummyAction):
    '''
    TODO is there anything this actually needs to do? Maybe callbacks eventually. Right now it kind of acts as a
    sentinel of sorts.
    '''
    pass


class Idle(DummyAction):
    pass


class NoCurrentActionException(Exception):
    pass


class BadWorkflowFormation(Exception):
    pass


class NoCaseException(Exception):
    pass


class EqualToAnything(object):
    def __eq__(self, other):
        return True
