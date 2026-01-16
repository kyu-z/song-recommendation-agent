from database.vector_store import MusicVectorStore
vs = MusicVectorStore()
vs.delete_collection()
print("Database is now clean.")