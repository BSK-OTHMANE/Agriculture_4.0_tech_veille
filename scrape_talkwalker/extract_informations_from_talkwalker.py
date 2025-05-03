import re
import os
from datetime import datetime, timedelta
from pathlib import Path
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError

# Configuration MongoDB
MONGO_CONFIG = {
    "host": "localhost",
    "port": 27017,
    "db_name": "veille_agriculture",
    "collection_name": "talkwalker_alerts_Agricuture_4.0"
}

# Configuration des dossiers
TALKWALKER_FOLDER = Path("scrape_talkwalker\talkwalker")  # Chemin relatif au script

class TalkwalkerImporter:
    def __init__(self, mongo_config):
        self.mongo_config = mongo_config
        self.db = self._connect_to_mongodb()
        
    def _connect_to_mongodb(self):
        """Connexion à MongoDB avec gestion des erreurs"""
        try:
            client = MongoClient(
                host=self.mongo_config["host"],
                port=self.mongo_config["port"],
                serverSelectionTimeoutMS=5000  # 5 secondes de timeout
            )
            # Test de la connexion
            client.admin.command('ping')
            db = client[self.mongo_config["db_name"]]
            print(f"✅ Connecté à MongoDB: {self.mongo_config['host']}:{self.mongo_config['port']}")
            return db
        except ConnectionFailure as e:
            print(f"🚨 Échec de connexion à MongoDB: {str(e)}")
            print("Vérifiez que:")
            print("- MongoDB Compass est bien lancé")
            print("- Le serveur MongoDB tourne en local")
            print("- Le port 27017 est accessible")
            return None

    def _clean_data(self, raw_data):
        """Nettoyage et validation des données"""
        # Nettoyage du titre
        if 'title' in raw_data:
            patterns = [
                r'^\[Talkwalker Alerts\].*?(?=Sujet :|$)',
                r'(Sujet :|De :|Date :|Pour :|Tell a Friend|Latest News from our blog).*$',
                r'^Icon\s+',
                r'\s*Icon\s+',
                r'\.\.\..*$',
                r'[\n\t]',
                r'\s{2,}'
            ]
            for pattern in patterns:
                raw_data['title'] = re.sub(pattern, ' ', raw_data['title'], flags=re.IGNORECASE)
            raw_data['title'] = raw_data['title'].strip()[:300]

        # Normalisation de la date
        if 'date' in raw_data:
            try:
                raw_data['date'] = datetime.strptime(raw_data['date'], '%d/%m/%y %H:%M').strftime('%Y-%m-%d')
            except ValueError:
                raw_data['date'] = None

        # Nettoyage de l'URL
        if 'source' in raw_data:
            url = re.sub(r'(\?|&)(utm_[^=]+=[^&]*|fbclid=[^&]*)+', '', raw_data['source'])
            domain_match = re.search(r'^(https?://)?(www\.)?([^/]+)', url.strip().lower())
            raw_data['source'] = f"https://{domain_match.group(3)}" if domain_match else None

        return raw_data

    def _extract_articles(self, file_content):
        """Extraction des articles depuis le contenu du fichier"""
        articles = []
        pattern = re.compile(
            r'(?P<title>.+?)\n'
            r'(?P<date>\d{2}/\d{2}/\d{2},? \d{2}:\d{2})'
            r'(?:\s?[|,]\s?)'
            r'(?P<country>.+?)'
            r'(?:\s?[|,]\s?)'
            r'(?P<source>.+?)(?:\n|$)',
            re.DOTALL | re.MULTILINE
        )

        for match in pattern.finditer(file_content):
            try:
                article = {
                    'titre': match.group('title'),
                    'date': match.group('date'),
                    'pays': match.group('country').strip(),
                    'lien': match.group('source'),
                    'metadata': {
                        'original_date': match.group('date'),
                        'source_raw': match.group('source')
                    }
                }
                
                article = self._clean_data(article)
                
                # Validation finale
                if all([article['titre'], article['date'], article['pays'], article['lien']]):
                    article.update({
                        'processed_at': datetime.utcnow(),
                        'source': 'Talkwalker',
                        'local_import': True
                    })
                    articles.append(article)
                    
            except Exception as e:
                print(f"⚠ Erreur lors de l'extraction: {str(e)}")
                continue

        return articles

    def _process_file(self, file_path):
        """Traitement d'un fichier individuel"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                if not content.strip():
                    print(f"⚠ Fichier vide: {file_path.name}")
                    return 0, 0

                articles = self._extract_articles(content)
                if not articles:
                    print(f"ℹ️ Aucun article valide dans: {file_path.name}")
                    return 0, 0

                inserted = self._store_articles(articles)
                print(f"✔ {file_path.name}: {len(articles)} articles extraits, {inserted} insérés")
                return len(articles), inserted

        except UnicodeDecodeError:
            print(f"🚨 Problème d'encodage avec: {file_path.name}")
            return 0, 0
        except Exception as e:
            print(f"🚨 Erreur critique avec {file_path.name}: {str(e)}")
            return 0, 0

    def _store_articles(self, articles):
        """Stockage des articles dans MongoDB"""
        if not articles or not self.db:
            return 0

        collection = self.db[self.mongo_config["collection_name"]]
        
        # Création des index (si inexistants)
        collection.create_index([('lien', 1)], unique=True)
        collection.create_index([('date', 1)])
        collection.create_index([('pays', 1)])

        inserted_count = 0
        batch_size = 50
        batch = []

        for article in articles:
            try:
                batch.append(article)
                if len(batch) >= batch_size:
                    result = collection.insert_many(batch, ordered=False)
                    inserted_count += len(result.inserted_ids)
                    batch = []
            except Exception as e:
                continue

        if batch:
            try:
                result = collection.insert_many(batch, ordered=False)
                inserted_count += len(result.inserted_ids)
            except Exception as e:
                print(f"⚠ Erreur sur dernier lot: {str(e)}")

        return inserted_count

    def _generate_stats(self):
        """Génération des statistiques"""
        if not self.db:
            return

        collection = self.db[self.mongo_config["collection_name"]]
        
        stats = {
            "total": collection.count_documents({}),
            "new": collection.count_documents({"local_import": True, "processed_at": {"$gte": datetime.now() - timedelta(hours=1)}}),
            "top_countries": list(collection.aggregate([
                {"$group": {"_id": "$pays", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 5}
            ])),
            "recent": list(collection.aggregate([
                {"$match": {"date": {"$gte": (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')}}},
                {"$group": {"_id": "$date", "count": {"$sum": 1}}},
                {"$sort": {"_id": -1}},
                {"$limit": 7}
            ]))
        }
        
        print("\n📊 Statistiques MongoDB Compass:")
        print(f"- Documents totaux: {stats['total']}")
        print(f"- Nouveaux articles (dernière heure): {stats['new']}")
        
        print("\n🌍 Top 5 des pays:")
        for country in stats['top_countries']:
            print(f"  - {country['_id']}: {country['count']}")
        
        print("\n📅 Répartition récente:")
        for day in stats['recent']:
            print(f"  - {day['_id']}: {day['count']}")

    def run_import(self):
        """Exécution complète de l'import"""
        if not self.db:
            return False

        try:
            # Vérification du dossier
            if not TALKWALKER_FOLDER.exists():
                raise FileNotFoundError(f"Dossier introuvable: {TALKWALKER_FOLDER.absolute()}")
            
            files = list(TALKWALKER_FOLDER.glob("*.txt")) + list(TALKWALKER_FOLDER.glob("*.TXT"))
            if not files:
                raise ValueError(f"Aucun fichier .txt trouvé dans: {TALKWALKER_FOLDER.absolute()}")

            print(f"\n📂 Dossier analysé: {TALKWALKER_FOLDER.absolute()}")
            print(f"📄 Fichiers à traiter: {len(files)}")

            # Traitement
            total_articles = 0
            total_inserted = 0
            
            for file in sorted(files):
                found, inserted = self._process_file(file)
                total_articles += found
                total_inserted += inserted

            # Résultats
            print("\n" + "="*50)
            print("RAPPORT FINAL".center(50))
            print("="*50)
            print(f"• Fichiers traités: {len(files)}")
            print(f"• Articles valides: {total_articles}")
            print(f"• Nouveaux articles insérés: {total_inserted}")
            
            if total_inserted > 0:
                print(f"\n💾 Taux de nouveauté: {(total_inserted/total_articles)*100:.1f}%")
                self._generate_stats()
            
            return True
            
        except Exception as e:
            print(f"\n🚨 ERREUR PRINCIPALE: {str(e)}")
            return False

if __name__ == "__main__":
    print("=== Import Talkwalker vers MongoDB Compass ===")
    print(f"=== {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")
    
    importer = TalkwalkerImporter(MONGO_CONFIG)
    importer.run_import()
    
    print("\n" + "="*50)
    print("Conseils pour MongoDB Compass:".center(50))
    print("="*50)
    print("- Actualisez la vue dans Compass (F5)")
    print("- Filtrez par 'local_import: true' pour voir les nouveaux documents")
    print("- Utilisez les index créés (date, pays, lien) pour des requêtes plus rapides")
    print("- Supprimez 'local_import' après vérification si nécessaire\n")