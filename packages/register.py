from vk_api import keyboard
from SDK.timeExtension import Timestamp
from SDK.database import db, Struct, ProtectedProperty
from SDK.cmd import command, set_after, after_func
from SDK.keyboard import Keyboard
import math, re

class User(Struct):
    def __init__(self, *args, **kwargs):
        self.save_by = ProtectedProperty("user_id")
        self.table_name = ProtectedProperty("users")
        self.user_id = ""
        self.paper_clips = 0
        self.keys = 0
        self.pencils = 0
        self.payed_out = 0.0
        self.inventory = []
        self.total_earned = 0
        super().__init__(*args, **kwargs)

airplanes = [
    {
        "id": 0,
        "level": 1,
        "per_hour": 100,
        "price": 1000
    },
    {
        "id": 1,
        "level": 2,
        "per_hour": 600,
        "price": 5000
    },
    {
        "id": 2,
        "level": 3,
        "per_hour": 3200,
        "price": 25_000
    },
    {
        "id": 3,
        "level": 4,
        "per_hour": 14_000,
        "price": 100_000
    },
    {
        "id": 4,
        "level": 5,
        "per_hour": 80_000,
        "price": 500_000
    },
    {
        "id": 5,
        "level": 6,
        "per_hour": 200_000,
        "price": 1_000_000
    }
]

#скрепки 🧷 ключи 🔑 карандаши ✏ 🚀 ✈ 🎲 ⏪ 📊

menu_kb = Keyboard({"✈Мои самолеты": "white", "💼Купить самолет": "white", "0":"line", "✏Баланс": "white", "🚀Обменник":"white", "01":"line","⚙Опции":"green"})

def toMenu(self):
    self.reply("Покупай самолеты и зарабатывай деньги!", keyboard = menu_kb)
    self.set_after("handle_menu")

@after_func("handle_menu")
def handle_menu(self):
    user_profile = self.db.select_one_struct("select * from users where user_id = ?", [self.user.id])
    if self.text == "✈мои самолеты":
        all_collected = 0
        collecting_per_hour = 0
        m = "Это ваши самолеты, они приносят 🧷, которые можно собирать и обменивать в обменнике 🚀.\n\n"
        cur_time = Timestamp().get_time()
        for airplane in airplanes:
            cur_count = 0
            cur_collected = 0
            for j in user_profile.inventory:
                if j["type"] == "airplane" and airplane["id"] == j["id"]:
                    cur_count += 1
                    collecting_per_hour += airplane["per_hour"]
                    h =  math.floor(((cur_time - j["last_collected"]) / 60) * (airplane["per_hour"] / 60))
                    cur_collected += h
                    all_collected += h
            if cur_count != 0:
                m += f"✈Самолет {airplane['id']+1} ур.\nКоличество: {cur_count}\nЗаработано: {cur_collected}\n\n"
        m += f"🧷Заработано с последнего сбора: {all_collected}\n📊Ваши самолеты приносят {collecting_per_hour}🧷 в час"
        self.reply(m, keyboard = Keyboard({"🧷Собрать скрепки":"green", "⏪Назад":"white"}, strategy="insert_lines"))
        self.set_after("handle_collect")
    elif self.text == "💼купить самолет":
        k = Keyboard(strategy="insert_lines")
        for airplane in airplanes:
            k.add_button(f"Самолет {airplane['id']+1} ур. ({airplane['per_hour']}🧷/час) - {airplane['price']}🔑", color = Keyboard.colors["blue"])
        k.add_button("⏪ Назад", color = Keyboard.colors["red"])
        self.reply("Тут Вы можете покупать самолеты, чтобы получать больше скрепок🧷", keyboard = k)
        self.set_after("handle_buy_airplane")
    elif self.text == "✏баланс":
        self.reply(f"✏Баланс\n\nСкрепки: {user_profile.paper_clips}🧷\nКлючи: {user_profile.keys}🔑\nКарандаши: {user_profile.pencils}✏", keyboard = Keyboard({"✏Пополнить баланс":"green","🔑Вывод":"red", "⏪Назад":"blue"}, strategy="insert_lines"))
        self.set_after("handle_balance")
    elif self.text == "🚀обменник":
        self.reply(f"🚀Курс обмена\n\n100 скрепок🧷 - 1 ключ🔑\n\nПосле обмена будет получено {user_profile.paper_clips // 100} ключей🔑. Вы согласны произвести обмен?", keyboard = Keyboard({"Да": "green", "Нет":"red"}))
        self.set_after("handle_convert")
    elif self.text == "⚙опции":
        self.reply(f"⚙Опции\n\n✈Аэродром\n👨‍👨‍👦‍👦{len(self.db.select('select * from users'))} в игре\nВы заработали: {user_profile.total_earned}🧷\nВы вывели: {user_profile.payed_out:.2f}", keyboard = Keyboard({"История выводов":"white","⏪Назад":"red"}, strategy="insert_lines"))
        self.set_after("handle_options")
    else:
        self.reply("Команда не распознана!")
        return True

@after_func("handle_balance")
def handle_balance(self):
    if self.text == "✏пополнить баланс":
        self.reply("✏Пополнение баланса\n\nТекущий курс:\n1✏ - 2₽\n\nВыберите сумму доната, на которую хотите пополнить баланс.", keyboard = Keyboard({"300 ₽":"green","500 ₽":"green","0":"line","150 ₽":"blue","200 ₽":"blue", "250 ₽": "blue", "1": "line", "750 ₽": "blue", "1000 ₽":"blue", "1500 ₽":"blue","2":"line", "⏪Назад":"red"}))
        self.set_after("handle_payment")
    elif self.text == "🔑вывод":
        self.reply("Выберите платежную систему", keyboard = Keyboard({"QIWI Кошелек":"blue", "Банковская карта": "blue", "Баланс телефона":"blue", "ЮMoney":"blue", "⏪Назад":"red"}, strategy="insert_lines"))
        self.set_after("choose_payment_system")
    else:
        toMenu(self)
        

@after_func("choose_payment_system")
def choose_payment_system(self):
    if self.text == "⏪назад": 
        toMenu(self)
        return False
    user_profile = self.db.select_one_struct("select * from users where user_id = ?", [self.user.id])
    if user_profile.pencils >= 75 and user_profile.keys / 100 >= 10000:
        self.reply("Введите реквизит", keyboard = Keyboard({"⏪Назад":"red"}))
        self.set_after("withdraw")
    else:
        self.reply("Для вывода у Вас должно быть не менее 75 ✏ и 10000🔑", keyboard = Keyboard({"✏Пополнить баланс":"green","⏪Назад":"red"},strategy="insert_lines"))
        self.set_after("handle_balance")

@after_func("withdraw")
def withdraw(self):
    if self.text == "⏪назад": 
        toMenu(self)
        return False
    else:
        user_profile = self.db.select_one_struct("select * from users where user_id = ?", [self.user.id])
        self.reply(f"Введите сумму вывода\n\nСейчас вы можете вывести {(user_profile.keys / 100):.2f} ₽", keyboard = Keyboard({"⏪Назад":"red"}))
        self.set_after("withdraw_part_2")


@after_func("withdraw_part_2")
def withdraw_part_2(self):
    user_profile = self.db.select_one_struct("select * from users where user_id = ?", [self.user.id])
    numbers = re.findall("\d+\.\d+", self.text)
    can_withdraw = user_profile.pencils / 100
    if not numbers or float(numbers[0]) > can_withdraw:
        self.reply("Неверно указана сумма платежа!")
        return True
    else:
        should_withdraw = float(numbers[0])
        user_profile.pencils -= 75
        user_profile.payed_out += should_withdraw
        self.reply("Деньги отправлены на вывод!")
        toMenu(self)

@after_func("handle_payment")
def handle_payment(self):
    if self.text == "⏪назад": toMenu(self)
    else:
        numbers = re.findall(r'\d+', self.text)
        if not numbers: 
            self.reply("Не указана сумма платежа!")
            return True
        kb = Keyboard(inline=True)
        kb.add_openlink_button(label="✅Продолжить", link=f"https://qiwi.com/payment/form/99?extra%5B%27account%27%5D={self.qiwi_wallet}&amountInteger={numbers[0]}&amountFraction=0&extra%5B%27comment%27%5D={self.user.id}&currency=643&blocked[0]=account&blocked[1]=comment")
        self.reply("Для доната перейдите по ссылке ниже", keyboard = kb)
        toMenu(self)
    

@after_func("handle_options")
def handle_options(self):
    if self.text == "⏪назад":
        toMenu(self)
    else:
        self.reply("Вы еще ни разу не производили вывод.", keyboard=menu_kb)
        self.set_after("handle_menu")

@after_func("handle_convert")
def handle_convert(self):
    if self.text == "нет": toMenu(self)
    else:
        user_profile = self.db.select_one_struct("select * from users where user_id = ?", [self.user.id])
        paper_clips = user_profile.paper_clips
        gained = paper_clips // 100
        user_profile.keys += gained
        user_profile.paper_clips -= gained * 100
        self.reply(f"Вы получили {gained} ключей🔑 взамен на {gained * 100} скрепок", keyboard=menu_kb)
        self.set_after("handle_menu")

@after_func("handle_buy_airplane")
def handle_buy_airplane(self):
    user_profile = self.db.select_one_struct("select * from users where user_id = ?", [self.user.id])
    if self.text == "⏪ назад": toMenu(self)
    else:
        numbers = re.findall(r'\d+', self.text)
        if not numbers or int(numbers[0]) > len(airplanes):
            self.reply("Произошла ошибка при покупке самолета!")
            toMenu(self)
        elif user_profile.keys < airplanes[int(numbers[0])-1]["price"]:
            self.reply("Недостаточно ключей🔑 для покупки!")
            toMenu(self)
        else:
            self.reply(f"Покупка произошла успешно! Вы купили самолет {int(numbers[0])} уровня.", keyboard = menu_kb)
            self.set_after("handle_menu")
            airplane = int(numbers[0])-1
            user_profile.keys -= airplanes[airplane]["price"]
            user_profile.inventory.append({"type": "airplane", "last_collected": Timestamp().get_time(), "id": airplane})

@after_func("handle_collect")
def handle_collect(self):
    if self.text == "🧷собрать скрепки":
        user_profile = self.db.select_one_struct("select * from users where user_id = ?", [self.user.id])
        collected: int = 0
        cur_time = Timestamp().get_time()
        for airplane in user_profile.inventory:
            if airplane["type"] == "airplane":
                from_list = airplanes[airplane["id"]]
                collected += math.floor(((cur_time - airplane["last_collected"]) / 60) * (from_list["per_hour"] / 60))
        if collected != 0:
            for airplane in user_profile.inventory:
                if airplane["type"] == "airplane":
                    airplane["last_collected"] = cur_time
            user_profile.paper_clips += collected
            user_profile.total_earned += collected
            self.reply(f"Скрепки собраны!\n\nВы собрали: {collected} 🧷\n\nСобранные скрепки можно поменять на 🔑 в обменнике 🚀")
            toMenu(self)
        else:
            self.reply("Прибыль от самолетов пока что отсутствует.")
            toMenu(self)
    elif self.text == "⏪назад": toMenu(self)


        

@command("начать")
def hi(self, args):
    s = self.db.select_one_struct("select * from users where user_id = ?", [self.user.id])
    if s is None:
        self.reply(f"Добро пожаловать в игру!\n🎁Вы получили подарок от игры - Самолет первого уровня, который приносит {airplanes[0]['per_hour']} 🧷 в час!", keyboard = menu_kb)
        User(self.db, user_id = self.user.id, inventory = [{"type": "airplane", "last_collected": Timestamp().get_time(), "id": airplanes[0]["id"]}])
        self.set_after("handle_menu")
    else:
        toMenu(self)