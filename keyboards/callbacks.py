from aiogram.filters.callback_data import CallbackData


class MenuCb(CallbackData, prefix="menu"):
    action: str


class CalendarCb(CallbackData, prefix="cal"):
    scope: str
    year: int
    month: int
    day: int


class CategoryCb(CallbackData, prefix="cat"):
    category: str


class ServiceCb(CallbackData, prefix="srv"):
    service_id: int


class SlotCb(CallbackData, prefix="slot"):
    slot_id: int


class ConfirmCb(CallbackData, prefix="cfm"):
    action: str
    entity_id: int


class AdminCb(CallbackData, prefix="adm"):
    action: str


class ServiceAdminCb(CallbackData, prefix="sad"):
    action: str
    service_id: int


class SlotAdminCb(CallbackData, prefix="slt"):
    action: str
    slot_id: int


class AppointmentAdminCb(CallbackData, prefix="app"):
    action: str
    appointment_id: int


class AppointmentMoveSlotCb(CallbackData, prefix="ams"):
    appointment_id: int
    slot_id: int


class SubscriptionCb(CallbackData, prefix="sub"):
    action: str


class ClientAdminCb(CallbackData, prefix="cli"):
    action: str
    user_id: int
