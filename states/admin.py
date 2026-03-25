from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    choose_service_category = State()
    add_service_name = State()
    add_service_price = State()
    add_service_description = State()

    add_slots_time = State()
