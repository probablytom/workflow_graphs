import functools
from au import default_cost

def cascade(method):
    # Implements cascading method calls as a decorator.
    def _(*args, **kwargs):
        method(*args, **kwargs)
        return args[0]  # This _should_ be self...
    return _


# class Action(object):
#     def __init__(self,
#                  associated_function,
#                  previous_action=list(),
#                  next_action=None):
#         self.associated_function = associated_function
#         self.previous_action = previous_action
#         self.next_action = next_action
#
#     def __call__(self, *args, **kwargs):
#         return self.execute(*args, **kwargs)
#
#     def set_previous_action(self, prev_act):
#         '''
#         Properly sets a node's expected previous action (forwards and backwards).
#         @param prev_act: A GraphNode representing the previous action for this node.
#         '''
#         self.previous_action.append(prev_act)
#         prev_act.next_action = self
#
#     def set_next_action(self, next_act):
#         '''
#         Properly sets a node's expected next action (forwards and backwards).
#         @param next_act: A GraphNode representing the next action for this node.
#         '''
#         self.next_action = next_act
#         next_act.previous_action.append(self)
#
#     def execute(self, context, actor, env):
#         return self.associated_function(context, actor, env)

class ItemNotInPath:
    '''
    A sentinel for an item not appearing in a path we search, used in WorkflowGraph.index_of().
    '''
    pass


def dummy_action_generator(cost=0):
    '''
    Generate new functions so they're different places in memory (and different dummy actions won't be seen as
    equal to each other)
    :return: A function which is the identity action
    '''
    @default_cost(cost)
    def dummy_action(ctx, actor, env):
        pass
    return dummy_action


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


def partial_apply(*args):
    '''
    Applies arguments to a function so long as they're all in a lisp-style list, but returns the unevaluated function
    :param args:
    :return:
    '''
    return functools.partial(*args)


End = dummy_action_generator(cost=0)
Join = dummy_action_generator(cost=0)
Idle = dummy_action_generator(cost=1)
Start = dummy_action_generator(cost=0)

do_nothing = Idle
anything_else = EqualToAnything()
