def cascade(method):
    # Implements cascading method calls as a decorator.
    def _(*args, **kwargs):
        method(*args, **kwargs)
        return args[0]  # This _should_ be self...
    return _


class Action(object):
    def __init__(self,
                 associated_function,
                 previous_action=list(),
                 next_action=None):
        self.associated_function = associated_function
        self.previous_action = previous_action
        self.next_action = next_action

    def __call__(self, *args, **kwargs):
        return self.execute(*args, **kwargs)

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


class Decision(Action):
    pass


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

class StartNode(DummyAction):
    pass


class NoCurrentActionException(Exception):
    pass


class BadWorkflowFormation(Exception):
    pass


class NoCaseException(Exception):
    pass


class CouldNotParseIndexException(Exception):
    pass


class EqualToAnything(object):
    def __eq__(self, other):
        return True
