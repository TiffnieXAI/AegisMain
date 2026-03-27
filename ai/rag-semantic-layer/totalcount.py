import chromadb
from chromadb.config import Settings

# initialize persistent client
client = chromadb.PersistentClient(
    path='./aegis_db',
    settings=Settings(anonymized_telemetry=False)
)

# get the collection
col = client.get_collection('library_of_truth')

# print total documents
print(f'Total documents: {col.count()}')
