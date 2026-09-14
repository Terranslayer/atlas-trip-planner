from flask import current_app
from pymongo import MongoClient
from pymongo.errors import PyMongoError


# MongoClient maintains a connection pool and TLS session state. It is designed
# to be created once per process and shared across requests. We cache it on
# app.extensions rather than flask.g so the client survives across requests;
# pymongo handles cleanup at interpreter shutdown.
def get_client():
    client = current_app.extensions.get("mongo_client")
    if client is not None:
        return client
    uri = current_app.config["MONGODB_URI"]
    if not uri:
        raise RuntimeError("MONGODB_URI is not configured (set it in .env)")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    current_app.extensions["mongo_client"] = client
    return client


def get_db():
    return get_client()[current_app.config["MONGODB_DB_NAME"]]


def ping():
    try:
        get_client().admin.command("ping")
        return True
    except PyMongoError:
        return False
