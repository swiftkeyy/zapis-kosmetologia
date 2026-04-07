from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    add_service_name = State()
    add_service_price = State()
    add_service_description = State()

    edit_service_name = State()
    edit_service_price = State()

    add_slots_time = State()

    transfer_choose_date = State()
    transfer_choose_slot = State()
