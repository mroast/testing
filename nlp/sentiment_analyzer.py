# nlp/sentiment_analyzer.py

# ======== IMPORTS ========
# spaCy → NLP library for tokenization, POS tagging, named entities, etc.
import spacy

# pandas → DataFrame library for handling structured data
import pandas as pd

# tqdm → progress bar for loops and pandas apply()
from tqdm import tqdm

# transformers → Hugging Face library for loading pre-trained NLP models
from transformers import pipeline

# typing → used for type hints
from typing import List, Dict, Optional

# logging → for status and error messages
import logging

# ThreadPoolExecutor → run multiple tasks in parallel threads for speed
from concurrent.futures import ThreadPoolExecutor


# ======== LOGGING CONFIGURATION ========
# Set logging to INFO level and include timestamps
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Enable tqdm for pandas so DataFrame.apply() shows a progress bar
tqdm.pandas()


# ======== LOAD SPACY MODEL ========
# Load English NLP model, disabling features we don't need (faster)
# - "lemmatizer" (word root form) → disabled for speed
# - "textcat" (text classification) → disabled for speed
nlp = spacy.load("en_core_web_sm", disable=["lemmatizer", "textcat"])


# ======== LOAD SENTIMENT ANALYSIS MODEL ========
# We try to load a Twitter-specific sentiment model (CardiffNLP)
#   It outputs 3 labels: negative, neutral, positive
model_name = "cardiffnlp/twitter-roberta-base-sentiment"

try:
    sentiment_pipeline = pipeline(
        "sentiment-analysis",
        model=model_name,
        truncation=True  # cut off texts longer than model's max length
    )
except Exception:
    # If Cardiff model isn't available (e.g., no internet), use fallback SST-2 model
    #   This fallback only has POSITIVE and NEGATIVE labels
    sentiment_pipeline = pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english",
        truncation=True
    )


# ======== LABEL MAPPING FOR CARDIFF MODEL ========
# The Cardiff model returns "LABEL_0", "LABEL_1", "LABEL_2"
# This map converts them into human-readable labels
LABEL_MAP_CARDIFF = {
    "LABEL_0": "NEGATIVE",
    "LABEL_1": "NEUTRAL",
    "LABEL_2": "POSITIVE"
}


# ======== KEYWORD EXTRACTION FUNCTION ========
def extract_keywords(text: str) -> List[str]:
    """
    Extracts *unique* noun phrases from text.
    Example: "The red car is fast" → ["red car"]

    Steps:
    1. If empty text → return empty list
    2. Use spaCy to tokenize and extract noun chunks
    3. Convert to lowercase, strip spaces
    4. Remove duplicates while keeping order
    """
    if not text:
        return []
    doc = nlp(text)
    chunks = [
        chunk.text.lower().strip()
        for chunk in doc.noun_chunks
        if len(chunk.text.strip()) > 2  # ignore very short words like "a", "an"
    ]
    seen = set()
    out = []
    for c in chunks:
        if c not in seen:  # ensure uniqueness
            out.append(c)
            seen.add(c)
    return out


# ======== ENTITY EXTRACTION FUNCTION ========
def extract_entities(text: str) -> List[tuple]:
    """
    Extracts named entities (like names, places, dates) from text.
    Example: "Apple was founded in 1976" → [("Apple", "ORG"), ("1976", "DATE")]
    """
    if not text:
        return []
    doc = nlp(text)
    return [(ent.text.strip(), ent.label_) for ent in doc.ents]


# ======== BATCHING UTILITY ========
def _batchify(lst, batch_size):
    """
    Splits a large list into smaller lists of size 'batch_size'.
    This is important because sending 1,000+ texts to the model at once
    will cause memory errors, so we process in smaller chunks.
    """
    for i in range(0, len(lst), batch_size):
        yield lst[i:i+batch_size]


# ======== MAIN DATA PROCESSING FUNCTION ========
def process_dataframe(
    raw_tweets: Optional[list] = None,  # raw tweet dicts
    pd_path: Optional[str] = None,      # JSON file path with tweet data
    from_file: bool = False,            # whether to load from file
    batch_size: int = 64,               # number of tweets per sentiment batch
    max_workers: int = 4                # number of threads to use
) -> pd.DataFrame:
    """
    Processes tweet data:
    1. Loads tweets (from list or file)
    2. Extracts keywords and named entities
    3. Runs sentiment analysis in batches (multi-threaded for speed)
    4. Adds readable results to DataFrame
    """

    # --- Step 1: Load data ---
    if from_file and pd_path:
        # Load JSON file into DataFrame
        df = pd.read_json(pd_path, lines=False)
        logging.info(f"Loaded DataFrame from {pd_path}, shape={df.shape}")
    else:
        if raw_tweets is None:
            raise ValueError("Provide raw_tweets list or pd_path with from_file=True")
        df = pd.DataFrame(raw_tweets)
        logging.info(f"Created DataFrame from raw tweets, shape={df.shape}")

    # Ensure 'text' column exists (fill with empty strings if missing)
    df['text'] = df.get('text', pd.Series([""] * len(df))).fillna("").astype(str)

    # --- Step 2: Extract keywords & entities ---
    logging.info("Extracting keywords and entities...")
    df['keywords'] = df['text'].progress_apply(extract_keywords)
    df['entities'] = df['text'].progress_apply(extract_entities)

    # --- Step 3: Sentiment analysis ---
    logging.info(f"Running sentiment analysis in batches of {batch_size} with {max_workers} workers...")
    texts = df['text'].tolist()  # list of all tweet texts
    sentiments = []  # to store sentiment results

    def process_batch(batch):
        """
        Processes a single batch of tweets through the model.
        Returns a list of dicts: {label: str, score: float}
        """
        batch_results = []
        try:
            res = sentiment_pipeline(batch)
            for r in res:
                label = r.get("label", "")
                score = r.get("score", 0.0)

                # Normalize label names to uppercase
                if label in LABEL_MAP_CARDIFF:
                    mapped_label = LABEL_MAP_CARDIFF[label]
                elif label.upper() in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
                    mapped_label = label.upper()
                elif label.lower() in ("positive", "negative", "neutral"):
                    mapped_label = label.upper()
                else:
                    mapped_label = label  # unknown label, keep as is

                batch_results.append({
                    "label": mapped_label,
                    "score": round(float(score), 3)  # round score to 3 decimals
                })

        except Exception as e:
            logging.error(f"Sentiment batch failed: {e}")
            # If an error happens, assign NEUTRAL with score 0
            for _ in batch:
                batch_results.append({"label": "NEUTRAL", "score": 0.0})

        return batch_results

    # Run batches in parallel threads for speed
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for batch_result in executor.map(process_batch, _batchify(texts, batch_size)):
            sentiments.extend(batch_result)

    # If something went wrong and results are fewer than tweets → pad with neutral
    if len(sentiments) < len(df):
        sentiments.extend([{"label": "NEUTRAL", "score": 0.0}] * (len(df) - len(sentiments)))

    # --- Step 4: Add sentiment results to DataFrame ---
    df['sentiment'] = [s['label'] for s in sentiments]
    df['sentiment_score'] = [s['score'] for s in sentiments]

    # --- Step 5: Create readable combined output per tweet ---
    def format_output(row):
        return {
            "username": row.get("username", ""),
            "text": row.get("text", ""),
            "sentiment": row.get("sentiment", ""),
            "score": row.get("sentiment_score", 0.0),
            "keywords": row.get("keywords", []),
            "entities": row.get("entities", []),
            "created_at": row.get("created_at", ""),
            "url": row.get("url", "")
        }

    df['readable_output'] = df.apply(format_output, axis=1)

    logging.info("NLP processing complete.")
    return df


# ======== SENTIMENT BUCKET FUNCTION ========
def get_sentiment_buckets(df: pd.DataFrame) -> Dict[str, list]:
    """
    Groups tweets into sentiment categories.
    Returns:
    {
        "POSITIVE": [list of positive tweet texts],
        "NEGATIVE": [list of negative tweet texts],
        "NEUTRAL":  [list of neutral tweet texts]
    }
    """
    buckets = {"POSITIVE": [], "NEGATIVE": [], "NEUTRAL": []}
    for _, row in df.iterrows():
        sentiment = str(row.get("sentiment", "NEUTRAL")).upper()
        if sentiment not in buckets:
            # If sentiment is unknown, treat it as NEUTRAL
            buckets["NEUTRAL"].append(row.get("text", ""))
        else:
            buckets[sentiment].append(row.get("text", ""))
    return buckets
