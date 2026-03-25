from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    choosing_date = State()
    choosing_category = State()
    choosing_service = State()
    choosing_slot = State()
    waiting_name = State()
    waiting_phone = State()
    confirming = State()
