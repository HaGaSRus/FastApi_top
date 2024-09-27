from transitions import Machine

class QuestionStateMachine:
    states = [
        'initial',
        'creating_parent_question',
        'creating_sub_questions',  # Добавлено состояние для создания подвопросов
        'adding_multiple_sub_questions',
        'increasing_depth'
    ]

    transitions = [
        {'trigger': 'create_parent', 'source': 'initial', 'dest': 'creating_parent_question'},
        {'trigger': 'create_sub', 'source': 'creating_parent_question', 'dest': 'creating_sub_questions'},
        {'trigger': 'add_sub_questions', 'source': 'creating_sub_questions', 'dest': 'adding_multiple_sub_questions'},
        {'trigger': 'increase_depth', 'source': 'adding_multiple_sub_questions', 'dest': 'increasing_depth'},
    ]

    def __init__(self):
        self.machine = Machine(model=self, states=self.states, transitions=self.transitions, initial='initial')