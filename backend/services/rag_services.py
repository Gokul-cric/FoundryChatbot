# backend/services/rag_service.py

import os
import glob
import re
from PyPDF2 import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def load_and_extract_texts(data_folder="data/docs/"):
    texts = []
    file_paths = glob.glob(os.path.join(data_folder, "*.pdf"))
    for file_path in file_paths:
        try:
            text = extract_text_from_pdf(file_path)
            texts.append({"text": text, "file_path": file_path})
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    return texts

def split_text_into_chunks(text, chunk_size=512):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

def retrieve_relevant_chunks(texts, query, top_k=3):
    corpus = [query] + [text["text"] for text in texts]
    vectorizer = TfidfVectorizer().fit_transform(corpus)
    vectors = vectorizer.toarray()
    cosine_matrix = cosine_similarity(vectors)
    ranked_indices = np.argsort(cosine_matrix[0][1:])[-top_k:]
    return [texts[i] for i in ranked_indices]
