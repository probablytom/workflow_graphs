from theatre_ag import Cast, allocate_workflow_to, Task, Empty, OutOfTurnsException
from theatre_ag import Actor as TheatreActor
from Queue import Queue
from au import construct_task
from workflow import WorkflowGraph, End, do_nothing
import sys
import traceback


class MessagingActor(TheatreActor):
    def __init__(self, *args, **kwargs):
        self.inbox = Queue()
        super(MessagingActor, self).__init__(*args, **kwargs)

    def send_message(self, other_actor, message):
        if isinstance(other_actor, Department):
            other_actor.department_work_queue.put(message, block=True)
        else:
            other_actor.inbox.put(message, block=True)


class Signal(object):
    def __eq__(self, pattern):
        '''
        To be subclassed by signals which are passed in as pattern-matchable cases for actor messages.
        :param pattern: Any data type or structure (some message), which we want to see whether a Signal would indicate.
        For example, 5 == 5, but 5 may also == "five", or "<6", if we want.
        Note as well that there's not a total ordering; we can't necessarily say whether a signal's < or > a message,
        which is fine, we only care about == anyway.
        :return: bool indicating whether signal indicated a message.
        '''
        pass


class TeamMember(object):
    '''
    A class to give Theatre agents the ability to take work from a Department.
    To be used as a Mixin; see GraphActor for an example.
    '''
    def __init__(self, *args, **kwargs):
        super(TeamMember, self).__init__(*args, **kwargs)
        self.departments = []


class Department(Cast):
    def __init__(self, *args, **kwargs):
        self.department_work_queue = Queue()
        super(Department, self).__init__(*args, **kwargs)

    def add_member(self, actor):
        super(Department, self).add_member(actor)
        actor.departments.append(self)
        

class Actor(TeamMember):
    def __init__(self, clock, name=None, *args, **kwargs):
        super(Actor, self).__init__(*args, **kwargs)
        
        self.clock = clock
        clock.add_listener(self)
        self.signal_flow_mapping = dict()
        self.actor_state = dict()
        self.idle_flow = WorkflowGraph().begin_with(do_nothing).then(End)
        self.inbox = Queue()
        self.context = None
        self.action_generator = None
        self.current_workflow = None
        self.current_task = None
        
        self.name = name  # Not necessary, just useful for ID sometimes.
        
    def on_signal_process_workflow(self, signal, workflow):
        self.signal_flow_mapping[signal] = workflow

    def get_next_workflow(self):

        self.context = {}  # A new context for every workflow invocation

        flow = None

        # Anything handed to us personally?
        if not self.inbox.empty():
            flow = self.inbox.get(block=True)

            # If the flow's not a graph, it's some sort of signal, so resolve it from our mapping.
            if not isinstance(flow, WorkflowGraph):
                flow = self.signal_flow_mapping[flow]

        else:
            found_work = False

            for dept in self.departments:
                if not found_work and not dept.department_work_queue.empty(block=True):

                    found_work = True

                    flow = dept.department_work_queue.get(block=True)

                    # If the flow's not a graph, it's some sort of signal, so resolve it from our mapping.
                    if not isinstance(flow, WorkflowGraph):
                        flow = self.signal_flow_mapping[flow]

        if flow is None:
            flow = self.idle_flow

        self.current_workflow = flow
        self.action_generator = self.current_workflow.yield_actions(self.context, self.actor_state)

    def get_next_task(self):
        '''
        Gets the next task (and the associated arguments for it) from the WorkflowGraph being processed.
        :return: 
        '''
        
        if self.current_task is End \
                or type(self.current_workflow) is not WorkflowGraph \
                or self.current_workflow == self.idle_flow:
            self.get_next_workflow()
            
        elif not self.current_task.just_ran():
            return self.current_task, self.context, self.actor_state, self.current_workflow.environment


        try:
            act, ctx, actor, env = self.action_generator.next()
        except StopIteration:
            self.get_next_workflow()
            act, ctx, actor, env = self.action_generator.next()

        task = construct_task(act)
        self.current_task = task

        return task, ctx, actor, env
    
    def recieve_message(self, message):
        self.inbox.put(message)

    def perform(self):
        while True:
            task, ctx, actor, env = self.get_next_task()
            
            # Run at least once.
            # task.invocations is reset to 0 if enough invocations == associated cost (or always 0 if no cost)
            completed = False
            while not completed:
                yield task(ctx, actor, env)
                completed = task.just_ran()

