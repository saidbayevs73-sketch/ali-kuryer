import os
import tempfile
import unittest
from unittest.mock import patch
from app.routers import support_bot as bot

class SupportBotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        env = patch.dict(os.environ, {
            "SUPPORT_BOT_TOKEN": "test-token",
            "SUPPORT_WEBHOOK_SECRET": "test_secret_123",
            "SUPPORT_OPERATORS_CHAT_ID": "-10012345678",
            "SUPPORT_DB_PATH": os.path.join(self.temp.name, "support.db"),
        })
        env.start()
        self.addCleanup(env.stop)
        bot.init_db()
        self.calls = []
        self.next_id = 100

        def fake_call(method, **kwargs):
            self.calls.append((method, kwargs))
            self.next_id += 1
            return {"message_id": self.next_id}

        mock = patch.object(bot, "tg_call", side_effect=fake_call)
        mock.start()
        self.addCleanup(mock.stop)

    @staticmethod
    def customer(message_id, text):
        return {"message": {
            "chat": {"id": 88, "type": "private"},
            "from": {"id": 88, "first_name": "Ali", "username": "ali_test"},
            "text": text, "message_id": message_id,
        }}

    @staticmethod
    def group(message_id, text, reply_id=None):
        message = {
            "chat": {"id": -10012345678, "type": "supergroup"},
            "from": {"id": 919, "first_name": "Operator"},
            "text": text, "message_id": message_id,
        }
        if reply_id is not None:
            message["reply_to_message"] = {"message_id": reply_id}
        return {"message": message}

    def create_ticket(self):
        bot.process_update(self.customer(1, "📦 Buyurtma bo‘yicha"))
        bot.process_update(self.customer(2, "Mening buyurtmam kelmadi"))
        with bot.get_db() as db:
            ticket = db.execute("SELECT * FROM support_tickets").fetchone()
            relay = db.execute(
                "SELECT * FROM support_relay ORDER BY message_id"
            ).fetchall()
        return ticket, relay

    def test_user_creates_ticket_and_is_routed_to_group(self):
        ticket, relay = self.create_ticket()
        self.assertEqual(ticket["user_id"], 88)
        self.assertEqual(ticket["group_id"], -10012345678)
        self.assertEqual(ticket["state"], "open")
        self.assertEqual(len(relay), 2)
        self.assertTrue(any(
            name == "copyMessage" and payload["chat_id"] == -10012345678
            for name, payload in self.calls
        ))

    def test_operator_reply_delivered_to_user(self):
        ticket, relay = self.create_ticket()
        bot.process_update(self.group(5, "Assalomu alaykum, tekshiryapmiz",
                                      relay[0]["message_id"]))
        self.assertTrue(any(
            name == "copyMessage"
            and payload["chat_id"] == ticket["user_id"]
            and payload["message_id"] == 5
            for name, payload in self.calls
        ))

    def test_operator_closes_ticket(self):
        ticket, relay = self.create_ticket()
        bot.process_update(self.group(8, "/close", relay[1]["message_id"]))
        with bot.get_db() as db:
            result = db.execute(
                "SELECT state FROM support_tickets WHERE id=?", (ticket["id"],)
            ).fetchone()
        self.assertEqual(result["state"], "closed")

    def test_category_is_not_sent_as_ticket(self):
        bot.process_update(self.customer(1, "💳 To‘lov bo‘yicha"))
        with bot.get_db() as db:
            self.assertEqual(
                db.execute("SELECT count(*) FROM support_tickets").fetchone()[0],
                0,
            )

    def test_faq_auto_reply_without_creating_ticket(self):
        bot.process_update(self.customer(1, "📍 Buyurtma holati"))
        with bot.get_db() as db:
            self.assertEqual(
                db.execute("SELECT count(*) FROM support_tickets").fetchone()[0],
                0,
            )
        self.assertTrue(any(
            name == "sendMessage" and "buyurtmalar" in payload["text"].lower()
            for name, payload in self.calls
        ))

    def test_group_chatid_works_before_group_is_configured(self):
        os.environ.pop("SUPPORT_OPERATORS_CHAT_ID")
        bot.process_update(self.group(3, "/chatid"))
        self.assertTrue(any(
            name == "sendMessage" and "Guruh ID" in payload["text"]
            for name, payload in self.calls
        ))

if __name__ == "__main__":
    unittest.main()
