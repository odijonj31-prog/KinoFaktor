from aiogram.fsm.state import State, StatesGroup


class SearchMovie(StatesGroup):
    waiting_code = State()


class AddMovie(StatesGroup):
    waiting_video = State()
    waiting_code = State()
    waiting_title = State()
    waiting_description = State()
    waiting_vip_only = State()


class DeleteMovie(StatesGroup):
    waiting_code = State()


class AddChannel(StatesGroup):
    waiting_forward_or_id = State()


class Broadcast(StatesGroup):
    waiting_content = State()
    waiting_confirm = State()


class VipPurchase(StatesGroup):
    waiting_receipt = State()


class AddVipPlan(StatesGroup):
    waiting_name = State()
    waiting_price = State()
    waiting_duration = State()
