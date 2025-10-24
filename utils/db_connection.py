import mongomock

def get_collection():
    """Return an in-memory MongoDB-like collection."""
    client = mongomock.MongoClient()
    db = client["water_quality_data"]
    coll = db["asv_1"]
    coll.create_index("timestamp")
    return coll
