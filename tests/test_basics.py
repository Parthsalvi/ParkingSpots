import unittest
import sqlalchemy
from flask import current_app
from app import app, db
from models import RegisteredUsers, Bookings
from datetime import datetime

class BasicsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_app_exists(self):
        self.assertFalse(app is None)

    def test_app_secret_key(self):
        self.assertTrue(app.secret_key == b'_5#y2L"F4Q8z\n\xec]/')

class DBTest(unittest.TestCase):
    def test_phone_number_length_booking_slot(self):
        with self.assertRaises(sqlalchemy.exc.OperationalError):
            user = RegisteredUsers(phone_number=1002)
            booking = Bookings(booking_slot=25)
            db.session.add_all([user,booking])
            db.session.commit()
