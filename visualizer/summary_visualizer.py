# visualizer/summary_visualizer.py
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import seaborn as sns
import pandas as pd
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def plot_sentiment_pie(df: pd.DataFrame, path: str):
    counts = df["sentiment"].value_counts()
    plt.figure(figsize=(6,6))
    # choose colors dynamically to avoid mismatches
    labels = counts.index.tolist()
    counts.plot.pie(autopct="%1.1f%%", startangle=90)
    plt.title("Sentiment Distribution")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()

def plot_wordcloud(df: pd.DataFrame, path: str):
    text = " ".join(df["text"].dropna().tolist())
    if not text.strip():
        logging.warning("No text to create wordcloud.")
        return
    wc = WordCloud(width=800, height=400, background_color="white").generate(text)
    plt.figure(figsize=(10,5))
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.title("Word Cloud of Tweets")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()

def plot_keywords_bar(df: pd.DataFrame, path: str):
    all_keywords = [kw for sublist in df["keywords"].dropna() for kw in sublist]
    if not all_keywords:
        logging.warning("No keywords to plot.")
        return
    keywords_series = pd.Series(all_keywords).value_counts().head(15)
    plt.figure(figsize=(10,5))
    sns.barplot(x=keywords_series.values, y=keywords_series.index)
    plt.title("Top Keywords")
    plt.xlabel("Frequency")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()

def plot_entities_bar(df: pd.DataFrame, path: str):
    all_entities = [ent[0] for sublist in df["entities"].dropna() for ent in sublist]
    if not all_entities:
        logging.warning("No entities to plot.")
        return
    entities_series = pd.Series(all_entities).value_counts().head(15)
    plt.figure(figsize=(10,5))
    sns.barplot(x=entities_series.values, y=entities_series.index)
    plt.title("Top Named Entities")
    plt.xlabel("Frequency")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()

def generate_visuals(df: pd.DataFrame, query: str):
    os.makedirs("output/visuals", exist_ok=True)
    safe = "".join(c if c.isalnum() or c in (" ", "_", "-") else "_" for c in query).strip()
    plot_sentiment_pie(df, f"output/visuals/{safe}_sentiment_pie.png")
    plot_wordcloud(df, f"output/visuals/{safe}_wordcloud.png")
    plot_keywords_bar(df, f"output/visuals/{safe}_keywords_bar.png")
    plot_entities_bar(df, f"output/visuals/{safe}_entities_bar.png")
    logging.info("Visuals saved to output/visuals/")
