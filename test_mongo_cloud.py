from pymongo import MongoClient


def main():
    uri = ""
    client = MongoClient(uri,
                         tls=True,
                         tlsCertificateKeyFile='mongo.pem')

    db = client['falcon']
    collection = db['rules']
    doc_count = collection.count_documents({})
    print(doc_count)


if __name__ == '__main__':
    main()
