

# task manager functions
# add task (name, description, due_date, priority, status)
# get ready tasks
# complete task

class Task(BaseModel):
    name: str
    description: str
    due_date: datetime
    priority: int 
    status: str
    repeat_interval: int

class ScheduledTaskManager(AgentInterface):
    def __init__(self, init_keys: Optional[Dict[str, str]] = None):
        self.tasks = []

    def add_task(self, name: str, description: str, due_date: datetime, priority: int, status: str, repeat_interval: int):
