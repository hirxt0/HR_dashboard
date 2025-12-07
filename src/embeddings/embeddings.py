from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import normalize

class GetEmbeddings:
    def __init__(self, chunk_size=800, chunk_overlap=200, separators=None, model_name='sentence-transformers/all-mpnet-base-v2'):

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators
        )

        self.model = SentenceTransformer(model_name)
    
    def split(self, text):
        return self.splitter.split_text(text)
    
    def embedding(self, chunks:list, batch_size :int=32):
        return self.model.encode(chunks, normalize_embeddings=False, convert_to_numpy=True, batch_size=batch_size)

    def normalized_embeddings(self, chunks:list, batch_size :int=32):
        embeddings =  self.model.encode(chunks, normalize_embeddings=False, convert_to_numpy=True, batch_size=batch_size)
        return normalize(embeddings, norm='l2', axis=1)