from sqlalchemy import *
from app import db

class Hubs(db.Model):
    __tablename__ = 'Hubs'

    hid = db.Column(db.Integer(), primary_key=True)
    center_longitude = db.Column(db.Float(precision=6))
    center_latitude = db.Column(db.Float(precision=6))
    pre_decimal_lat_hub = Column(db.Integer())
    pre_decimal_lng_hub = Column(db.Integer())
    streets = db.relationship('ParkingStreet', backref='hub_ids', lazy='dynamic')


class ParkingStreet(db.Model):
    __tablename__ = 'ParkingStreet'

    sid = Column(db.Integer(), primary_key=True)
    latitude = db.Column(db.Float(precision=6))
    longitude = db.Column(db.Float(precision=6))
    pre_decimal_lat_street = db.Column(db.Integer())
    pre_decimal_lng_street = db.Column(db.Integer())
    hub_id = db.Column(db.Integer, ForeignKey('Hubs.hid'))
    parkings = db.relationship('ParkingSpots', backref='street_ids', lazy='dynamic')


class ParkingSpots(db.Model):
    __tablename__ = 'ParkingSpots'

    pid = db.Column(db.Integer(), primary_key=True)
    cost = db.Column(db.Float())
    platitude = db.Column(db.Float(precision=6))
    plongitude = db.Column(db.Float(precision=6))
    street_id = db.Column(db.Integer, ForeignKey('ParkingStreet.sid'))
    bookings = db.relationship('Bookings', backref='booking_ids', lazy='dynamic')


class RegisteredUsers(db.Model):
    __tablename__ = 'RegisteredUsers'
    phone_number = db.Column(db.BigInteger(), primary_key=True)
    otp = db.Column(db.Integer)
    bookings = db.relationship('Bookings', backref='user_ids', lazy='dynamic')


class Bookings(db.Model):
    __tablename__ = 'Bookings'
    __table_args__ = (
        CheckConstraint('booking_slot > 0'),
        CheckConstraint('booking_slot < 25'),
    )
    bid = db.Column(db.Integer(), primary_key=True)
    phone_number = db.Column(db.Integer(), ForeignKey('RegisteredUsers.phone_number'))
    booking_date = db.Column(db.String(10), index=True, nullable=False)
    booking_slot = db.Column(db.Integer(), index=True, nullable=False)
    bookedon = db.Column(db.DateTime())
    parking_id = db.Column(db.Integer(), ForeignKey('ParkingSpots.pid'))