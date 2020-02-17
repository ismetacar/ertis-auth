import datetime

from pymongo import MongoClient

from src.utils.json_helpers import maybe_object_id

db = MongoClient(host='mongodb://localhost:27017/blupoint_auth_test').get_default_database()


def insert_mock_data():
    membership_doc = {
        "name": "sample_membership"
    }

    inserted_doc = db.memberships.insert_one(membership_doc)
    membership_doc['_id'] = inserted_doc.inserted_id

    role_doc = {
        "name": "admin-2",
        "permissions": [
            "users.*",
            "applications.*",
            "roles.*"
        ],
        "slug": "admin-1",
        "membership_id": str(membership_doc['_id']),
        "sys": {
            "created_at": datetime.datetime.utcnow(),
            "created_by": "ismetacar"
        }
    }
    inserted_doc = db.roles.insert_one(role_doc)
    role_doc['_id'] = inserted_doc.inserted_id

    user_doc = {
        "status": "active",
        "username": "gunererd",
        "password": "$2b$12$6ANncHsqxmKkSC8ZulIaL.SjAG7qTqEzkpqzYaEEC4naq5KVPObFm",
        "email": "eguner@blutv.com",
        "membership_id": str(membership_doc['_id']),
        "sys": {
            "created_at": datetime.datetime.utcnow(),
            "created_by": "ismetacar"
        },
        "display_name": "Erdem Güner",
        "firstname": "erdem",
        "lastname": "guner",
        "photo_url": "",
        "link": "",
        "email_verified": "",
        "providers": [],
        "role": role_doc['slug'],
        "token": {}
    }

    inserted_doc = db.users.insert_one(user_doc)
    user_doc['_id'] = inserted_doc.inserted_id

    return membership_doc, role_doc, user_doc


def remove_mock_data(membership, user, role):
    db.memberships.remove({
        '_id': maybe_object_id(membership['_id'])
    })

    db.users.remove({
        '_id': maybe_object_id(user['_id'])
    })

    db.roles.remove({
        '_id': maybe_object_id(role['_id'])
    })
