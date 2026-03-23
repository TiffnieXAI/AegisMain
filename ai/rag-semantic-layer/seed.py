import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from audit_knowledge import ingest_curated_findings
from scam_knowledge import ingest_scam_patterns

client = chromadb.PersistentClient(
    path='./aegis_db',
    settings=Settings(anonymized_telemetry=False)
)
collection = client.get_or_create_collection(
    name='library_of_truth',
    metadata={'hnsw:space': 'cosine'}
)
embedder = SentenceTransformer('all-MiniLM-L6-v2')

ingest_curated_findings(collection, embedder)
ingest_scam_patterns(collection, embedder)

print('Done')
