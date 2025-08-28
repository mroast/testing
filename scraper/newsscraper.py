from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from newspaper import Article

load_dotenv()

API_KEY = os.getenv('NEWSAPI_KEY')

if not API_KEY:
    print("Warning: NEWSAPI_KEY not found in environment variables.")


def scrape_aljazeera():
    url = 'https://www.aljazeera.com/'
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.content, 'html.parser')

    articles = []
    for item in soup.select('article'):
        title_tag = item.find('h3')
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        link = item.find('a')
        url = 'https://www.aljazeera.com' + link['href'] if link else ''
        snippet_tag = item.find('p')
        snippet = snippet_tag.get_text(strip=True) if snippet_tag else ''
        articles.append({'title': title, 'url': url, 'snippet': snippet, 'source': 'Al Jazeera'})
    return articles


def scrape_reuters():
    url = 'https://www.reuters.com/'
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.content, 'html.parser')

    articles = []
    for item in soup.select('article.story, div.story-content, div.MediaStoryCard__body__gYzGq'):
        title_tag = item.find(['h2', 'h3', 'h1'])
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        link = item.find('a')
        url = 'https://www.reuters.com' + link['href'] if link else ''
        snippet = ''
        snippet_tag = item.find('p')
        if snippet_tag:
            snippet = snippet_tag.get_text(strip=True)
        articles.append({'title': title, 'url': url, 'snippet': snippet, 'source': 'Reuters'})

    seen = set()
    unique_articles = []
    for a in articles:
        if a['title'] not in seen:
            unique_articles.append(a)
            seen.add(a['title'])
    return unique_articles


def search_newsapi(query, language='en', page_size=5):
    base_url = 'https://newsapi.org/v2/everything'
    params = {
        'q': query,
        'apiKey': API_KEY,
        'language': language,
        'sortBy': 'publishedAt',
        'pageSize': page_size,
    }
    r = requests.get(base_url, params=params)
    if r.status_code != 200:
        print(f"NewsAPI error: {r.status_code} - {r.text}")
        return []
    data = r.json()
    if data.get('status') != 'ok':
        print(f"NewsAPI error: {data.get('message')}")
        return []
    articles = data.get('articles', [])
    results = []
    for a in articles:
        results.append({
            'title': a['title'],
            'url': a['url'],
            'snippet': a['description'] or '',
            'source': a['source']['name']
        })
    return results


def simple_search(articles, query):
    q = query.lower()
    results = []
    for a in articles:
        if q in a['title'].lower() or q in a['snippet'].lower():
            results.append(a)
    return results


def save_results_to_file(results, query, fetch_full_text=True):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '_')).rstrip()
    filename = f"news_search_{safe_query}_{timestamp}.json"

    if fetch_full_text:
        print("Fetching full article texts (this may take a while)...")
        for article in results:
            full_text = get_full_article_text(article['url'])
            article['full_text'] = full_text if full_text else ""

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print(f"Saved {len(results)} results to {filename}\n")


def save_scraped_headlines(articles):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"scraped_headlines_{timestamp}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)
    print(f"Saved all scraped headlines to {filename}\n")


def get_full_article_text(url):
    # Try with newspaper3k first
    try:
        article = Article(url)
        article.download()
        article.parse()
        text = article.text
        if text.strip():
            return text
    except Exception as e:
        print(f"Newspaper3k extraction failed: {e}")

    # Fallback: custom scraping for known sites or generic heuristic for others
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            print(f"Failed to fetch article: HTTP {r.status_code}")
            return None
        soup = BeautifulSoup(r.content, 'html.parser')

        # Site-specific fallbacks:
        if 'aljazeera.com' in url:
            paragraphs = soup.select('div.wysiwyg.wysiwyg--all-content.css-1ck9wyi p')
            if not paragraphs:
                paragraphs = soup.select('div.article-p-wrapper p')
            article_text = '\n\n'.join(p.get_text(strip=True) for p in paragraphs)
            if article_text.strip():
                return article_text

        elif 'reuters.com' in url:
            paragraphs = soup.select('div.ArticleBody__content__2gQno p')
            article_text = '\n\n'.join(p.get_text(strip=True) for p in paragraphs)
            if article_text.strip():
                return article_text

        # Generic fallback for other sites: get paragraphs inside <article>
        article_tag = soup.find('article')
        if article_tag:
            paragraphs = article_tag.find_all('p')
            article_text = '\n\n'.join(p.get_text(strip=True) for p in paragraphs)
            if article_text.strip():
                return article_text

        # If no <article> or empty, try div with most paragraphs
        divs = soup.find_all('div')
        max_p_div = None
        max_p_count = 0
        for div in divs:
            p_tags = div.find_all('p')
            if len(p_tags) > max_p_count:
                max_p_count = len(p_tags)
                max_p_div = div
        if max_p_div and max_p_count > 3:
            paragraphs = max_p_div.find_all('p')
            article_text = '\n\n'.join(p.get_text(strip=True) for p in paragraphs)
            if article_text.strip():
                return article_text

        print("Could not extract article text using fallback scraper.")
        return None
    except Exception as e:
        print(f"Generic fallback scraping failed with error: {e}")
        return None


def main():
    print("Scraping latest news from Al Jazeera and Reuters...")
    aj = scrape_aljazeera()
    rt = scrape_reuters()
    all_articles = aj + rt

    print(f"Scraped {len(all_articles)} articles in total.\n")

    save_scraped_headlines(all_articles)

    for i, art in enumerate(all_articles[:10], 1):
        print(f"{i}. [{art['source']}] {art['title']}")
        print(f"   {art['url']}")
        if art['snippet']:
            print(f"   {art['snippet']}")
        print()

    while True:
        query = input("Enter search query (or 'exit' to quit): ").strip()
        if query.lower() == 'exit':
            break

        matched = simple_search(all_articles, query)
        if matched:
            print(f"\nFound {len(matched)} matches in scraped latest news:\n")
            for i, art in enumerate(matched, 1):
                print(f"{i}. [{art['source']}] {art['title']}")
                print(f"   {art['url']}")
                if art['snippet']:
                    print(f"   {art['snippet']}")
                print()

            save_results_to_file(matched, query, fetch_full_text=True)

        else:
            print("\nNo recent scraped news matches found. Searching NewsAPI for broader results...\n")
            if not API_KEY or API_KEY == 'YOUR_NEWSAPI_KEY_HERE':
                print("Please set your NewsAPI API key in the code or .env to use search fallback.")
                continue
            newsapi_results = search_newsapi(query)
            if newsapi_results:
                for i, art in enumerate(newsapi_results, 1):
                    print(f"{i}. [{art['source']}] {art['title']}")
                    print(f"   {art['url']}")
                    if art['snippet']:
                        print(f"   {art['snippet']}")
                    print()

                save_results_to_file(newsapi_results, query, fetch_full_text=True)

            else:
                print("No news found for your query.")


if __name__ == "__main__":
    main()
