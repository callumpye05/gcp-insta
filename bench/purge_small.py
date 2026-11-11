
import time
from google.cloud import datastore
from google.cloud.datastore.query import PropertyFilter

client = datastore.Client(project="massive-data-project-513113")
prefix = "u10000"
batch_size = 100 #A cause des erreur de runtime je limite le batch à 100 


def clean(kind):
    total = 0
    while True:
        q =client.query(kind=kind)

        if kind == "Post": #pour les posts
            q.add_filter(filter=PropertyFilter("author", ">=", prefix + "_u"))
            q.add_filter(filter=PropertyFilter("author", "<", prefix + "_v")) # ont peut suivre l'ordre lexicographique 
        else: # pour les utilisateurs
            start =client.key("User", prefix +"_u")
            end = client.key("User", prefix + "_v")
            q.add_filter(filter=PropertyFilter("__key__", ">=", start))
            q.add_filter(filter=PropertyFilter("__key__", "<", end))

        q.keys_only()
        keys =[e.key for e in q.fetch(limit=batch_size)]
        if len(keys) == 0:
            break

        #les clé supprimés ne ressortiront plus, donc on peut relancer la même requete sans curseur
        client.delete_multi(keys)
        total += len(keys)

        if total % 1000 == 0:
            print(f"{kind}: {total} entites supprimees", flush=True)

        time.sleep(0.1)

    print(f"{kind}: termine, {total} entites supprimé")


clean("Post")
clean("User")
print("Purge terminee")

