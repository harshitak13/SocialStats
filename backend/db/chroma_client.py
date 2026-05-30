# SocialStats: persistent vector store

import chromadb


chroma_client = chromadb.PersistentClient(path="./socialstats_store")
collection = chroma_client.get_or_create_collection(name="socialstats_transcripts")
