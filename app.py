import os
import random
import sys
import math
import time
import pandas as pd
import geopy
import unittest
import logging
from flask import Flask, session, jsonify, request, current_app,url_for,redirect,abort
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.sql.expression import bindparam
from sqlalchemy import *
from geopy.geocoders import Nominatim
from geopy.distance import great_circle
geolocator = Nominatim(user_agent='calculate_distance')

# metadata = MetaData()

#################################################### Flask Config ############################################

basedir = os.path.abspath(os.path.dirname(__file__))
# moment = Moment()

#### FLASK CONFIG ####

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

#### SQLITE CONFIG ####

app.config['SQLALCHEMY_DATABASE_URI'] ='sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
from models import *

logging.basicConfig(filename='./logs/app.log', level=logging.DEBUG)
#################################################### API ROUTES ##############################################

################# Map related APIS #################

@app.route('/')
def index():
     return "<h1>Parking Slots</h1>"

@app.before_request
def before_request():
    route_list = ['getAllBookings','addBookings','getAllUsers'] # these require user to add phone number
    if (session.get('validated',False) == False or 'phone_number' not in session) and request.endpoint in route_list:
        if 'phone_number' not in session:
            return {'registered' : False, 'message':'Kindly provide your phone number'}
        elif session.get('validated',False) == False:
            return {'registered': False, 'message': 'Kindly validate your phone number'}
        else:
            return {'registered' : False, 'message':'Kindly register'}

@app.route('/getTotals',methods=['GET'])
def getTotals():
    '''Get total parking, booked parking, available parking'''
    # total=len(ParkingSpots.query.all()) # 0.06399273872375488 for 1000 records, # 0.4855365753173828 for 10k recs
    total=len(pd.read_sql('ParkingSpots', db.session.bind)) # 0.05399966239929199 for 1000 recs, # 0.10849881172180176 for 10k recs
    booked=len(pd.read_sql('Bookings', db.session.bind))
    available = total-booked
    total_users= len(pd.read_sql('RegisteredUsers', db.session.bind))
    result = {"total" : total, "booked":booked, "available":available,'total_users': total_users}
    return jsonify(result)

@app.route('/getAllHubsInMapView',methods=['GET'])
def getAllHubsInMapView():
    '''Get all hubs in  Hubs table'''
    total = pd.read_sql('Hubs', db.session.bind)
    result = {"total" : len(total), "hub_list":total.to_dict('records')}
    return jsonify(result)

@app.route('/getHub',methods=['POST'])
def getHub():
    '''Given latitude, longitude, radius find nearby hubs and closest hub'''
    result = {}
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    radius = request.form.get('radius')
    limiter = 0.5
    if latitude and longitude:
        lat_limited = round(float(latitude),0)
        lng_limited = round(float(longitude),0)

        qry = db.session.query(Hubs).filter(
            Hubs.pre_decimal_lat_hub >= lat_limited - limiter,
            Hubs.pre_decimal_lat_hub <= lat_limited + limiter,
            Hubs.pre_decimal_lng_hub >= lng_limited - limiter,
            Hubs.pre_decimal_lng_hub <= lng_limited + limiter,
            )
        total = pd.read_sql_query(qry.statement, db.session.bind)
        closest_distance = float(radius)
        closest_hub = ''
        for hub_id,lat,lng in set(zip(total['hid'], total['center_latitude'], total['center_longitude'])):
            distance = get_distance(lat, latitude, lng, longitude)
            if distance < closest_distance:
                closest_distance = distance
                closest_hub = hub_id
        result = {'total_nearby_hubs':len(total),
                  'hub_list':total.to_dict('records'),
                  'closest_hub': closest_hub
                  }
    else:
        abort(400)
    return jsonify(result)

@app.route('/getStreet',methods=['POST'])
def getStreet():
    '''Given latitude, longitude, radius find nearby streets and closest street'''
    result = {}
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    radius = request.form.get('radius')
    if latitude and longitude and radius:
        lat_limited = round(float(latitude),2)
        lng_limited = round(float(longitude),2)
        limiter = 0.002
        qry = db.session.query(Hubs,ParkingStreet).filter(
            ParkingStreet.latitude >= lat_limited - limiter,
            ParkingStreet.latitude <= lat_limited + limiter,
            ParkingStreet.longitude >= lng_limited - limiter,
            ParkingStreet.longitude <= lng_limited + limiter,
        ).join(ParkingStreet)
        total = pd.read_sql_query(qry.statement, db.session.bind)
        closest_distance = float(radius)
        closest_street=''
        for street_id, lat,lng in zip(total['sid'],total['latitude'], total['longitude']):
            distance = get_distance(lat,latitude,lng,longitude)
            if distance < closest_distance:
                closest_distance = distance
                closest_street = street_id
        result = {'total_nearby_streets':len(total),
                  'street_list':total.to_dict('records'),
                  'closest_street':closest_street}
    else:
        abort(400)
    return jsonify(result)

@app.route('/getParking',methods=['POST'])
def getParking():
    # get closest hubs for a given location
    result = {}
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    radius = request.form.get('radius')
    if latitude and longitude and radius:
        lat_limited = round(float(latitude),3)
        lng_limited = round(float(longitude),3)
        limiter = 0.001
        qry = db.session.query(ParkingStreet,ParkingSpots).filter(
            ParkingStreet.latitude >= lat_limited - limiter,
            ParkingStreet.latitude <= lat_limited + limiter,
            ParkingStreet.longitude >= lng_limited - limiter,
            ParkingStreet.longitude <= lng_limited + limiter,
        ).join(ParkingSpots)

        total = pd.read_sql_query(qry.statement, db.session.bind)
        latitude=float(latitude)
        longitude=float(longitude)
        closest_distance = float(radius)
        closest_parking = ''
        for parking_id, lat, lng in zip(total['pid'], total['platitude'], total['plongitude']):
            distance = get_distance(lat, latitude, lng, longitude)
            if distance < closest_distance:
                closest_distance = distance
                closest_parking = parking_id
        result = {'total_nearby_parking':len(total),
                  'parking_list':total.to_dict('records'),
                  'closest_parking':closest_parking,
                  }
    else:
        abort(400)
    return jsonify(result)

@app.route('/getAllStreetsInMapView',methods=['GET','POST'])
def getAllStreetsInMapView():
    '''Given hub_id get all streets'''
    if request.method=='POST':
        hub_id = request.form.get('hub_id')
        if hub_id:
            qry = db.session.query(ParkingStreet).filter_by(hub_id=hub_id)
            total = pd.read_sql_query(qry.statement, db.session.bind)
    else:
        total = pd.read_sql('ParkingStreet', db.session.bind)
    result = {"total": len(total), "street_list": total.to_dict('records')}
    return jsonify(result)

@app.route('/getAllParkingSlotsInStreet',methods=['GET','POST'])
def getAllParkingSlotsInStreet():
    '''Given street_id get all parking spots'''
    if request.method == 'POST':
        street_id = request.form.get('street_id')
        if street_id:
            qry = db.session.query(ParkingSpots).filter_by(street_id=street_id)
            total = pd.read_sql_query(qry.statement, db.session.bind)
    else:
        total = pd.read_sql('ParkingSpots', db.session.bind)
    result = {"total": len(total), "parking_list": total.to_dict('records')}
    return jsonify(result)

@app.route('/getAllUsers', methods=['GET'])
def getAllUsers():
    '''Get all userlist from RegisteredUsers table'''
    qry = db.session.query(RegisteredUsers)
    total = pd.read_sql_query(qry.statement, db.session.bind)
    result = {"total": len(total), "user_list": total.to_dict('records')}
    return jsonify(result)

################ USER CRUD RELATED APIS #############

@app.route('/validateAddPhoneNumber', methods=['POST','PATCH'])
def validateAddPhoneNumber():
    '''
        POST : for given phone number check if it already exists else validate by sending otp
        PATCH : user sends received otp which will be checked with otp in session
        Once validate user is added in RegisteredUsers table and session
        :return: appropriate response for UI
    '''
    session['validated'] = False
    phone_number = request.form.get('phone_number')
    already_exists = request.form.get('already_exists')
    validated = request.form.get('validated')
    invalid_number = request.form.get('invalid_number')
    entered_otp =  request.form.get('entered_otp')
    country_code = request.form.get('country_code')
    if request.method == 'PATCH' and entered_otp:
        # check phone+otp combo in table
        if session.get('phone_number',False) and str(entered_otp) == str(session.get('otp','')):
            user = RegisteredUsers(
                phone_number = session['phone_number'],
                otp = session['otp']
            )
            db.session.add(user)
            db.session.commit()
            session['validated']=True
            return {'validated' : True }
        else:
            if session.get(otp,''):
                del session['otp']
            if session.get('phone_number',''):
                del session['phone_number']
            return { 'validated' : False }
    if request.method == 'POST':
        if not phone_number:
            abort(400)
        if session.get('phone_number'):
            session.pop('phone_number')
        if session.get('otp'):
            session.pop('otp')
        qry = db.session.query(RegisteredUsers).filter_by(phone_number = phone_number)
        total = pd.read_sql_query(qry.statement, db.session.bind)
        session['phone_number'] = phone_number
        if len(total)>0:
            already_exists = True
            validated = True
            session['validated']=True
        else:
            try:
                # generate otp & send sms
                otp = generate_otp(phone_number)
                # enter phone number + otp in table
                session['otp'] = otp
                return { 'check_otp' : True }
            except Exception as e:
                print(e)
                invalid_number = True
                return { 'invalid_number' : True }

@app.route('/checkAddBookings', methods=['GET','POST','PATCH'])
def checkAddBookings():
    '''
    POST : Given booking_date, booking_slot and parking_id. Check availability of parking slot
    :return: Available / Not Available
    GET : For the requested parking_id return its parking cost.
    PATCH : After payment confirmation from UI add entry in Bookings table
    :return: Parking Booked / Failed
    '''
    phone_number = session.get('phone_number')
    if request.method == 'PATCH' and request.form.get('confirmed'):
        try:
            # not required ; used only on sqlite
            bid=db.session.query(func.max(Bookings.bid)).scalar()
            if not bid:
                bid=0
            else:
                bid=int(bid)
            ####
            booking = Bookings(
                bid = bid+1,
                phone_number = phone_number,
                booking_date = session['booking_date'],
                booking_slot = session['booking_slot'],
                parking_id = session['parking_id'],
                bookedon = datetime.utcnow()
            )
            db.session.add(booking)
            db.session.commit()
            pd.read_sql('Bookings', db.session.bind).to_csv('./data/booking.csv', index=False) # required because SQLite is used which reloads after app restart
            session.pop('booking_date')
            session.pop('booking_slot')
            session.pop('parking_id')
            return {'booked' : True}
        except Exception as e:
            print(e)
            return {'booked' : False, 'message': 'Wrong booking values'}
    if request.method == 'POST':
        booking_date = request.form.get('booking_date')
        booking_slot = request.form.get('booking_slot')
        parking_id = request.form.get('parking_id')

        qry = db.session.query(Bookings).filter_by(
            parking_id=parking_id,
            booking_date=booking_date,
            booking_slot=booking_slot,
        )
        total = pd.read_sql_query(qry.statement, db.session.bind)

        if len(total)>0:
            return {'message' : 'Parking Slot not available'}
        else:
            session['booking_date'] = booking_date
            session['booking_slot'] = booking_slot
            session['parking_id'] = parking_id
            return {'booking_available' : True, 'confirmed':False}
    if request.method == 'GET':
        # to get cost of current booking or given parking id
        parking_id = session.get('parking_id')
        if not parking_id:
            parking_id=request.headers.get('parking_id')
        if parking_id:
            qry = db.session.query(ParkingSpots).filter_by(pid=parking_id)
            total = pd.read_sql_query(qry.statement, db.session.bind)
            return jsonify(total.to_dict('records'))
        else:
            abort(400)

@app.route('/removeBooking', methods=['POST'])
def removeBooking():
    # given booking_id remove it from Bookings table
    '''
    Given booking_id check if booking exists and if it does delete the entry
    :return: appropriate response for UI
    '''
    bid =  request.form.get('bid')
    if bid:
        try:
            qry = db.session.query(Bookings).filter_by(bid=bid)
            total = pd.read_sql_query(qry.statement, db.session.bind)
            if len(total>0):
                Bookings.query.filter_by(bid=bid).delete()
                db.session.commit()
                pd.read_sql('Bookings', db.session.bind).to_csv('./data/booking.csv', index=False) # required because SQLite is used which reloads after app restart
                return { 'deleted': True }
            else:
                abort(400)
        except Exception as e:
            print(e)
            return { 'deleted': False }
    else:
        abort(400)

@app.route('/getAllBookings', methods=['GET'])
def getAllBookings():
    '''get all bookings for current user'''
    phone_number = session.get('phone_number')
    if phone_number:
        qry = db.session.query(Bookings).filter_by(phone_number=phone_number)
        total = pd.read_sql_query(qry.statement, db.session.bind)
        result = {"total": len(total), "booking_list": total.to_dict('records')}
    else:
        abort(400)
    return jsonify(result)

####################################################### HELPER FUNCTIONS ##########################################

def get_distance(lat1,lat2,lng1,lng2):
    '''
    :param lat1: available latitude
    :param lat2: user latitude
    :param lng1: available longitude
    :param lng2: user longitude
    :return: Distince in kilometers using vincenty / great_circle method
    '''
    coords1 = (lat1,lng1)
    coords2 = (lat2,lng2)
    try:
        return geopy.distance.vincenty(coords1,coords2).km
    except:
        return geopy.distance.great_circle(coords1,coords2).km

def generate_otp(phone_number):
    '''
    :param phone_number: to generate otp
    :return: otp
    '''
    otp = random.randrange(100000, 999999)

    return otp

class DB_INIT():
    '''for db initialization and extraction'''
    def __init__(self):
        self.db_initialized = False

    def run(self):
        print('initializing DB from scratch')
        if not self.db_initialized:
            start=time.time()
            db.drop_all()
            db.create_all()
            latitude = 19.01
            longitude = 73.02
            # hub_id between 10 to 99
            for h in range(10,20):
                dec_lat = random.random()/100
                dec_lon = random.random()/100
                hub_id = h # 1 digit #'H'+'_'+str(h
                hub = Hubs(
                     hid = hub_id,
                     center_longitude = longitude + dec_lon,
                     center_latitude = latitude + dec_lat,
                    pre_decimal_lat_hub = int(latitude),
                    pre_decimal_lng_hub = int(longitude)
                )
                db.session.add(hub)
                # street_id between 100 to 999
                for s in range(100, 200):
                     dec_lat = random.random()/100
                     dec_lon = random.random()/100
                     street_id = int(str(h)+str(s)) #4 digit #'S' + '_' + hub_id + '_' + str(s)
                     street = ParkingStreet(
                          sid = street_id,
                          latitude = latitude + dec_lon,
                          longitude =  longitude + dec_lat,
                          pre_decimal_lat_street=int(latitude),
                          pre_decimal_lng_street=int(longitude),
                          hub_id = hub_id
                     )
                     db.session.add(street)
                     # parking_id between 1000 t0 9999
                     for p in range(1000,1010):
                        dec_lat = random.random() / 1000
                        dec_lon = random.random() / 1000
                        parking_id = int(str(h)+str(s)+str(p)) #'P' + '_'+ street_id+'_'+str(p)
                        parking  = ParkingSpots(
                            pid = parking_id,
                            cost = random.randint(20,50),
                            platitude=latitude + dec_lon,
                            plongitude=longitude + dec_lat,
                            street_id = street_id
                        )
                        db.session.add(parking)
                latitude += 0.2
                longitude += 0.2
            # registered users phone number between 9870474000 to 9870477000
            for n in random.sample(range(9870474000,9870477000),1000):
                user = RegisteredUsers(
                    phone_number=n,
                    otp=random.randint(100001, 999999),
                )
                db.session.add(user)
            db.session.commit()
            end=time.time()
            print('DB initialization time ',str(end-start))

            self.db_initialized = True

    def extract_data(self):
        hubs=pd.read_sql('Hubs',db.session.bind).to_csv('./data/hubs.csv',index=False)
        streets=pd.read_sql('ParkingStreet',db.session.bind).to_csv('./data/streets.csv',index=False)
        parking=pd.read_sql('ParkingSpots',db.session.bind).to_csv('./data/parking.csv',index=False)
        users=pd.read_sql('RegisteredUsers',db.session.bind).to_csv('./data/users.csv',index=False)
        bookings=pd.read_sql('Bookings',db.session.bind).to_csv('./data/booking.csv',index=False)

    def check_data(self):
        hub_path = './data/hubs.csv'
        street_path = './data/streets.csv'
        parking_path = './data/parking.csv'
        users_path = './data/users.csv'
        booking_path = './data/booking.csv'
        try:
            hubs = pd.read_csv('./data/hubs.csv')
            streets = pd.read_csv('./data/streets.csv')
            parking = pd.read_csv('./data/parking.csv')
            users = pd.read_csv('./data/users.csv')
            booking = pd.read_csv('./data/booking.csv')
            return {'hub': hubs,'street':streets,'parking':parking,'users':users,'booking':booking}
        except Exception as e:
            # print(e)
            return False

@app.cli.command()
def test():
 """Run the unit tests."""
 import unittest
 tests = unittest.TestLoader().discover('tests')
 unittest.TextTestRunner(verbosity=2).run(tests)

if __name__ == '__main__':
    print('Initializing DB and APP')
    data = DB_INIT().check_data()
    if not data:
        DB_INIT().run()
        DB_INIT().extract_data()
    else:
        try:
            hubs = data['hub'].to_sql('Hubs', db.session.bind,if_exists='replace',index=False)
            streets = data['street'].to_sql('ParkingStreet', db.session.bind,if_exists='replace',index=False)
            parking = data['parking'].to_sql('ParkingSpots', db.session.bind,if_exists='replace',index=False)
            users = data['users'].to_sql('RegisteredUsers', db.session.bind,if_exists='replace',index=False)
            booking = data['booking'].to_sql('Bookings', db.session.bind,if_exists='replace',index=False)
            print('Loaded Data from files')
        except Exception as e:
            print(e)
            DB_INIT().run()
            DB_INIT().extract_data()
    app.run(host='0.0.0.0', port='8080', debug=False)
