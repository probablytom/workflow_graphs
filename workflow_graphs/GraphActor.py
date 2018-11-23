from theatre_ag import Actor, Cast, allocate_workflow_to, Task, Empty, OutOfTurnsException
from workflow_utilities import EndNode
from Queue import Queue
from functools import partial
from workflow import WorkflowGraph, End
import sys
import traceback


class MessagingActor(Actor):
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


class GraphActor(MessagingActor, TeamMember):
    
    def __init__(self, *args, **kwargs):
        self.signal_flow_mapping = dict()
        self.actor_state = {}
        self.context = None
        self.action_generator = None
        self.current_workflow = None
        self.current_task = None
        super(GraphActor, self).__init__(*args, **kwargs)
        self.idle_flow = WorkflowGraph().begin_with(self.idling).then(End)
        
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
        if type(self.current_task) is EndNode or type(self.current_workflow) is not WorkflowGraph:
            self.get_next_workflow()

        try:
            next_action_and_vars = self.action_generator.next()
        except StopIteration:
            self.get_next_workflow()
            next_action_and_vars = self.action_generator.next()
            

        # Equivalent of a LISP `apply` of Python's Partial to the next action, context, actor state and env.
        return partial(*next_action_and_vars)

    def perform(self):
        '''
        Overrides Actor.Perform() so that WorkflowGraph actions can be processed as Tasks from Theatre.
        :return: None
        '''
        while self.wait_for_directions or self.tasks_waiting():
            task = None
            try:
                try:
                    task = self.get_next_task()

                    entry_point_name = task.entry_point.func_name
                    allocate_workflow_to(self, task.workflow)
                    task.entry_point = task.workflow.__getattribute__(entry_point_name)

                except Empty:
                    task = Task(self.idling.idle, self.idling)

                if task is not None:
                    self._task_history.append(task)
                    self.current_task = task
                    self.handle_task_return(task, task.entry_point(*task.args))

            except OutOfTurnsException:
                break
            except Exception as e:
                print >> sys.stderr, "Warning, actor [%s] encountered exception [%s], in workflow [%s]." % \
                                     (self.logical_name, str(e.message), str(task))
                traceback.print_exc(file=sys.stderr)
                pass

        # Ensure that clock can proceed for other listeners.
        self.clock.remove_tick_listener(self)
        self.waiting_for_tick.set()
