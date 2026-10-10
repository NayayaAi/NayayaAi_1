import bcrypt
from pymongo import MongoClient
from datetime import datetime

client = MongoClient("mongodb://127.0.0.1:27017/")
db = client["NyayaAI_DB"]
users_collection = db["users"]

email = "admin@gmail.com"     
fullname = "admin"             
password = "admin_1"     

password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

users_collection.insert_one({
    'fullname': fullname,
    'email': email,
    'password_hash': password_hash,
    'role': 'admin',
    'unique_id': 'ADM001',
    'created_at': datetime.utcnow(),
    'failed_attempts': 0,
    'locked_until': None,
})

print("Admin created.")


#adding this to the main repo for now. REMOVE LATER
#http://127.0.0.1:5000/api/evidence/access-log/<a real FIR number> to view the train as an admin 