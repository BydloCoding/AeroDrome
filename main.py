import re

import vk_api
import pyqiwi
import random
import string
from vk_api.longpoll import VkLongPoll, VkEventType

from SDK.stringExtension import StringExtension
from SDK import (database, jsonExtension, user, imports, cmd, thread)
import sqlite3
import math

config = jsonExtension.load("config.json")


class LongPoll(VkLongPoll):
    def listen(self):
        while True:
            try:
                for event in self.check():
                    yield event
            except:
                # we shall participate in large amount of tomfoolery
                pass

class Voucher(database.Struct):
    def __init__(self, *args, **kwargs):
        self.save_by = database.ProtectedProperty("user_id")
        self.table_name = database.ProtectedProperty("voucher")
        self.user_id = ""
        self.voucher = ""
        super().__init__(*args, **kwargs)

class Main(object):
    bot = None
    def __init__(self):
        self.bot = self
        self.attachments = []
        self.config = config
        imports.ImportTools(["packages", "Structs"])
        self.database = database.Database(config["db_file"], config["db_backups_folder"], self)
        self.db = self.database
        database.db = self.database
        self.vk_session = vk_api.VkApi(token=self.config["vk_api_key"])
        self.longpoll = LongPoll(self.vk_session)
        self.vk = self.vk_session.get_api()
        self.all_payments_list = jsonExtension.load("data/all_payments.json")
        self.group_id = "-" + re.findall(r'\d+', self.longpoll.server)[0]
        self.qiwi_wallet = self.config["qiwi_wallet"]
        self.qiwi_token = self.config["qiwi_api_key"]
        self.wallet = pyqiwi.Wallet(token=self.qiwi_token, number=self.qiwi_wallet)
        thread.every(300, name = "Qiwi-Payments")(self.qiwi_payments)
        thread.every(18000, name = "Voucher-Giveaway")(self.voucher_giveaway)
        print("Bot started!")
        self.poll()

    def parse_attachments(self):
        for attachmentList in self.attachments_last_message:
            attachment_type = attachmentList['type']
            attachment = attachmentList[attachment_type]
            access_key = attachment.get("access_key")
            self.attachments.append(
                f"{attachment_type}{attachment['owner_id']}_{attachment['id']}") if access_key is None \
                else self.attachments.append(
                f"{attachment_type}{attachment['owner_id']}_{attachment['id']}_{access_key}")

    def voucher_giveaway(self):
        db = sqlite3.connect(self.db.file)
        db.row_factory = sqlite3.Row
        cur = db.cursor()
        users = db.execute("select * from users").fetchall()
        generate = min(self.config["voucher_users"], len(users))
        generated = []
        # populate list
        while len(generated) != generate:
            choice = random.choice(users)
            if choice not in generated:
                generated.append(choice)
        for _user in generated:
            generated_voucher = f"Aero{''.join(random.choices(string.ascii_uppercase, k = 3))}{''.join(random.choices(string.digits, k=2))}"
            voucher = db.execute("select * from voucher where user_id = ?", [_user["user_id"]]).fetchone()
            self.db.create_execute_task("insert into voucher (user_id, voucher) values (?, ?)", [_user["user_id"], generated_voucher]) if voucher is None else self.db.create_execute_task("update voucher set voucher = ? where user_id = ?", [generated_voucher, _user["user_id"]])
            user.User(self.vk, _user["user_id"]).write(f"🔑Новая раздача!\n\n⭐ Ваучер🎁\n✅ Код ваучера 👉 {generated_voucher}\n\n💵Даёт от 500.000 до 5.000.000 скрепок🧷\n🤖Для использования ваучера введите его в сообщения с ботом☝🏻")


    def qiwi_payments(self):
        db = sqlite3.connect(self.db.file)
        db.row_factory = sqlite3.Row
        cur = db.cursor()
        transactions = self.wallet.history(rows=50)["transactions"]
        for payment in transactions:
            if payment.type == "IN" and payment.txn_id not in self.all_payments_list and payment.comment is not None:
                self.all_payments_list.append(payment.txn_id)
                cur.execute("select * from users where user_id = ?", [payment.comment])
                user_profile = cur.fetchone()
                if user_profile is not None:
                    self.db.create_execute_task("update users set pencils = ? where user_id = ?", [user_profile["pencils"] + math.floor(payment.sum.amount // 2 * 0.95), user_profile["user_id"]])
                    user.User(self.vk, user_profile["user_id"]).write(f"Оплата прошла успешно! На ваш счет зачислено {math.floor(payment.sum.amount // 2 * 0.95)}✏\n\n(С доната была списана комиссия 5%)")
        db.close()

    def reply(self, *args, **kwargs):
        return self.user.write(*args, **kwargs)

    def wait(self, x, y):
        return cmd.set_after(x, self.user.id, y)

    def set_after(self, x, y=None):
        if y is None:
            y = []
        cmd.set_after(x, self.user.id, y)

    def poll(self):
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                self.db.check_tasks()
                self.user = user.User(self.vk, event.user_id)
                self.raw_text = StringExtension(event.message.strip())
                self.event = event
                self.text = StringExtension(self.raw_text.lower().strip())
                self.txtSplit = self.text.split()
                self.command = self.txtSplit[0] if len(self.txtSplit) > 0 else ""
                self.args = self.txtSplit[1:]
                self.messages = self.user.messages.getHistory(count=3)["items"]
                self.last_message = self.messages[0]
                self.attachments_last_message = self.last_message["attachments"]
                self.parse_attachments()
                voucher = self.db.select_one_struct("select * from voucher where user_id = ?", [self.user.id])
                if voucher is not None and self.raw_text == voucher.voucher:
                    generated_money = random.randint(500_000, 5_000_000)
                    self.reply(f"✅Вы успешно активировали ваучер, на ваш баланс зачислено {generated_money}🧷")
                    user_profile = self.database.select_one_struct("select * from users where user_id = ?", [self.user.id])
                    user_profile.paper_clips += generated_money
                else:
                    cmd.execute_command(self)


Main()
