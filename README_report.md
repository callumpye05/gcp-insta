# TinyInsta passe-t-elle à l'échelle ?
Projet Données Massives et Cloud  2026

## Introduction

TinyInsta est une application de réseau social développé avec Flask et déployée sur Google App Engine, utilisant Google Cloud Datastore pour stocker les données. Elle permet notamment de consulter une timeline contenant les publications récentes des comptes suivis.

L'objectif de cette étude est de répondre à une question, **TinyInsta peut-elle maintenir des performances satisfaisantes lorsque le volume de données et la charge augmentent?**

Pour y répondre, j'ai étudié deux aspects de la scalabilité, soit :

- **Scalabilité des données :** capacité à gérer davantage de données sans dégradation disproportionnée des performances. J'étudie trois paramètres : **U** (nombre d'utilisateurs), **P** (publications par utilisateur) et **F** (comptes suivis par utilisateur).
- **Scalabilité des ressources:** capacité à exploiter des ressources supplémentaires pour traiter davantage de requêtes.J'analyse l'influence de **N** (nombre d'instances applicatives) et de **C** (nombre de clients concurrents) sur le débit et la latence.

## Démarche expérimentale

Pour étudier la scalabilité de TinyInsta, j'ai réalisé plusieurs benchmarks avec Locust sur l'endpoint `GET /api/timeline?user=…`.

J'ai organisé mon travail en trois parties:

1. **Coût d'une requête :** mesurer l'influence de U, P et F sur la latence, avec une seule instance et un client concurrent.
2. **Capacité et passage à l'échelle :** observer l'évolution du débit et de la latence en augmentant la concurrence, avec 1, 2 puis 4 instances B1.
3. **Optimisation :** identifier un goulot d'étranglement et chercher à le corriger. Plutôt que d'ajouter des ressources, j'ai choisi d'améliorer la stratégie de requêtage de l'application. J'ai également exploré un second goulot d'étranglement,mais le temps disponible ne m'a pas permis d'en identifier précisément l'origine. Je présente néanmoins les résultats de mes investigations.

Pour chaque partie, j'ai formulé des hypothèses, réalisé les mesures, puis analysé les résultats. J'ai également conservé les données brutes au format CSV afin de pouvoir vérifier mes observations et générer les figures.

## Indicateurs de performance

Pour analyser les résultats, j'ai utilisé plusieurs indicateurs:

- **Temps serveur (`SERVER_MS`) :** durée d'exécution de `get_timeline()`,mesurée directement par l'application et transmise via l'entête HTTP `Server-Timing`
- **Latence client (`LATENCY_MS`) :** temps total mesuré par Locust entre l'envoi d'une requête et la réception de sa réponse
- **Débit :** nombre de requêtes réussies par seconde(req/s).
- **Concurrence (C) :** nombre de clients virtuels Locust sollicitant l'application simultanément

Pour les latences, j'ai principalement utilisé la **médiane**, car elle est moins sensible aux valeurs extrêmes que la moyenne.

Enfin, la différence entre la latence client et le temps serveur ne représente pas uniquement le réseau : elle peut également comprendre l'attente des requêtes, le traitement HTTP et la sérialisation des réponses.
## 1. Montage expérimental
 
### 1.1 Architecture de TinyInsta

TinyInsta utilise Flask et Gunicorn pour traiter les requêtes HTTP, tandis que les données sont stockées dans Google Cloud Datastore.

Mon étude se concentre sur l'endpoint `GET /api/timeline?user=…`, qui permet de récupérer les 20 publications les plus récentes de l'utilisateur et des comptes qu'il suit.

La fonction `get_timeline()` fonctionne de la manière suivante :

1. **Récupération de l'utilisateur :** elle récupère l'entité `User` dans Datastore.
2. **Identification des auteurs :** elle consulte la liste des comptes suivis (`follows`), ajoute l'utilisateur lui-même et supprime les doublons.
3. **Recherche des publications :** elle tente d'abord une requête GQL utilisant l'opérateur `IN`, avec un tri chronologique décroissant et une limite de 20 publications. En cas d'échec, une requête équivalente est tentée avec l'API Datastore.
4. **Mécanisme de repli (*fallback*) :** si les deux requêtes échouent, une requête individuelle est effectuée pour chaque auteur. Les publications sont ensuite regroupées, triées par date et limitées aux 20 plus récentes.

Les publications sélectionnées sont finalement renvoyées au client sous forme de réponse HTTP.


### 1.2 Environnement Google Cloud

Les expérimentations ont été réalisées sur Google Cloud Platform, en utilisant principalement deux services: Google App Engine pour l'hébergement de l'application et Google Cloud Datastore pour le stockage des données. J'ai également pu utiliser Google Cloud Metric Explorer comme outil de diagnostic. Afin de regarder l'utilisation CPU , ainsi que la consommation de mégacycles pendant des experiences en rapport avec la partie 3. 

#### Google App Engine
Google App Engine est un service de type PaaS(Platform as a Service).L'idée est de pouvoir déployer une application sans avoir à gérer soi-même les serveurs et l'infrastructure, puisque Google s'en charge.
Pour mes expériences, j'ai surtout utilisé des instances B1 en manual scaling, ce qui me permettait de choisir moi-même le nombre d'instances. J'ai également testé des instances B2 par la suite, pour voir si le fait d'avoir plus de ressources pouvait améliorer les performances de l'application.

#### Google Cloud Datastore

Comme vu avant, Google Cloud Datastore est une base de données NoSQL entièrement gérée, utilisée par TinyInsta pour stocker les utilisateurs (User) et les publications (Post). 

Contrairement à App Engine, je ne contrôle pas directement les ressources internes de Datastore.Cette distinction est importante pour notre étude, augmenter les ressources applicatives ne garantit pas une augmentation proportionnelle des performances, puisque celles-ci dépendent également des accès aux données.

### 1.3 Versions et configurations déployées

Afin de comparer les performances de TinyInsta dans des conditions contrôlées, plusieurs versions de l'application ont été déployées sur Google App Engine.

L'objectif était de distinguer les effets du **volume de données**, de la **concurrence** et du **nombre d'instances**, tout en conservant des configurations comparables entre les expériences.

#### Configurations principales

| Version | Classe | Scaling | Instances | Utilisation |
|---|---|---|---|---|
| `default` | F1 | Automatique | Variable | Application principale accessible publiquement |
| `fixed1` | B1 | Manuel | 1 | Parties 1 et 2 |
| `fixed2` | B1 | Manuel | 2 | Partie 2 |
| `fixed4` | B1 | Manuel | 4 | Partie 2 |
| `batched1` | B1 | Manuel | 1 | Partie 3 : version optimisée |

Les versions `fixed1`, `fixed2` et `fixed4` utilisent la même classe d'instance B1.Seul le nombre d'instances allouées varie, permettant d'étudier la **scalabilité horizontale**,c'est-à-dire l'augmentation de la capacité de traitement par ajout d'instances. La version `batched1` a été utilisée pour tester une modification de l'algorithme de génération des timelines. Elle conserve une instance B1 afin de comparer ses performances à celles de `fixed1` sans modifier les ressources applicatives.

#### Configuration du serveur applicatif

Les benchmarks principaux utilisent Gunicorn avec un seul processus de travail synchrone par instance, conformément à la configuration suivante:

```bash
gunicorn -b :$PORT main:app
```
Un worker synchrone traite une requête à la fois. Cette configuration permet d'étudier le comportement de l'application avec un niveau de concurrence interne fixé, tout en faisant varier le nombre d'instances App Engine.

#### Isolation des déploiements

Les versions expérimentales ont été déployées avec l'option `--no-promote`,afin de ne pas modifier la répartition du trafic de la version principale `default`.Chaque version disposait ainsi de sa propre URL, permettant à Locust de cibler explicitement la configuration à mesurer. Les versions expérimentales ont été arrêtées après les benchmarks afin de limiter le coût.

#### Vérification des instances réellement utilisées

Afin de vérifier que les instances configurées participaient réellement au traitement des requêtes, j'ai pu analysé l'entête HTTP X-Instance dans les journaux Locust.Les identifiants relevés ont confirmé l'utilisation de :

- **1 instance distincte** pour `fixed1`
- **2 instances distinctes** pour `fixed2`
- **4 instances distinctes** pour `fixed4`

### 1.4 Jeux de données : U, P et F

j'ai utilisé plusieurs jeux de données en faisant varier les paramètres U, P et F, définis précédemment.

L'augmentation de U et P accroît principalement le volume de données stockées, tandis que F influence directement le nombre d'auteurs à interroger pour construire une timeline.

Le nombre théorique de publications stocké est donné par:

$$
N_{\text{posts}} = U \times P
$$

#### Principe de variation contrôlée

Afin d'isoler l'influence de chaque paramètre, j'ai appliqué le principe de variation d'un seul facteur à la fois. 
Lorsqu'un paramètre varie, les autres sont maintenus constants. Cette méthode permet de comparer les mesures dans des conditions homogènes.

### 1.5 Outils et protocole de mesure

Les benchmarks ont été réalisés avec **Locust**, un outil de test de charge permettant de simuler des clients concurrents.Le script `bench/locustfile.py` envoie des requêtes à l'endpoint `GET /api/timeline?user=…`.

Les tests fonctionnent en **boucle fermée** : chaque client virtuel attend la réponse avant d'envoyer une nouvelle requête. Le débit dépend donc du nombre de clients actifs et du temps de réponse de l'application.

Pour les expériences principales, j'ai retenu :

- **Durée:** 45 secondes par benchmark.
- **Concurrence:** C = 1 pour les parties 1 et 3 ; C appartenant à {1, 2, 4, 8, 16, 32, 64} pour la partie 2.
- **Infrastructure:** versions App Engine configurées avec un nombre fixe d'instance.

Des tests complémentaires de 180 secondes ont également été réalisés lors des investigations de la troisième partie.

#### Instrumentation et collecte des mesures

L'application expose deux en-têtes HTTP :

- `Server-Timing`: mesure la durée d'exécution de `get_timeline()` en millisecondes.
- `X-Instance`: identifie l'instance ayant traité la requête.

Locust mesure parallèlement la **latence client**, qui comprend l'ensemble du temps de réponse HTTP, contrairement au temps serveur limité à `get_timeline()`.

Chaque requête est enregistrée dans un fichier CSV contenant notamment son statut HTTP, sa latence client (`LATENCY_MS`), son temps serveur (`SERVER_MS`), son instance (`INSTANCE`) et les éventuelles erreurs (`ERROR`).

Les scripts Python exploitent ces données pour calculer les médianes des latences, le débit en requêtes réussies par seconde, le nombre d'échecs et les instances distinctes observées. Pour la partie 2, le débit correspond au nombre de réponses HTTP 200 divisé par les 45 secondes du benchmark.

Chaque expérience consiste à préparer le jeu de données, sélectionner la configuration App Engine, exécuter Locust, conserver les mesures brutes puis analyser les résultats. Les limites sont discutée dans la section 4. 

### 1.6 Organisation du dépôt et reproductibilité

Le dépôt Git contient le code de TinyInsta, les configurations de déploiement, les données expérimentales et les outils d'analyse :

- `bench/` : génération des données et benchmarks Locust.
- `raw/` : journaux bruts des expériences.
- `analysis/` : scripts d'analyse et de génération des figures.
- `figures/` : graphiques et résultats agrégés, '/part-3-second-bottleneck' contient une investigation apart pour tenter de trouver une solution pour un deuxième goulot identifié.

Les figures peuvent être régénérées depuis la racine du dépôt avec :

```bash
bash analysis/generate_all_fig.sh
```

Cette commande permet de reproduire les analyses à partir des mesures enregistrées, sans relancer les benchmarks sur Google Cloud.

#### Configuration de l'environnement

Les expérimentations ont été réalisées sur le projet Google Cloud `massive-data-project-513113`, dans la région `europe-west9` (Paris).
```
callumpye05@cloudshell:~/tinyinsta-2026 (massive-data-project-513113)$ gcloud app describe --format="value(locationId)"
europe-west
```

J'ai déployé plusieurs versions de TinyInsta sur App Engine afin de comparer différentes configurations, sans modifier la version principale de l'application.
Les mesures ont été réalisées entre mi-fin octobre et novembre 2026.

Pour générer la charge, j'ai utilisé **Locust depuis Google Cloud Shell**. Les requêtes étaient donc envoyées depuis cet environnement distant et non depuis mon ordinateur personnel pour la totalité du projet.


## 2. Résultats expérimentaux

### 2.1 Partie 1 — Le coût d'une requête

### 2.1.1 Hypothèses sur U, P et F

Avant de réaliser les benchmarks, j'ai formulé trois hypothèses concernant l'influence des paramètres U, P et F sur les performances de la génération d'une timeline.
Ces hypothèses reposent sur l'analyse de la fonction `get_timeline()`, notamment sur les requêtes Datastore, l'utilisation du filtre `IN`, le tri chronologique et la limitation des résultats.

#### 1er hypothèse: Influence du nombre d'utilisateurs(U) ####
Je suppose que l'augmentation de U n'affectera pas significativement la latence d'une timeline.
En effet, l'application n'a pas besoin de charger les publications de tous les utilisateurs à chaque requête. Elle recherche uniquement celles des comptes suivis par l'utilisateur concerné.

Ce comportement est visible dans get_timeline():

```
follow_key = client.key('User', user)
user_entity = client.get(follow_key)
```
La fonction récupère ensuite les comptes suivis par cet utilisateur et ajoute l'utilisateur lui même à la liste des auteurs:

```
follows = user_entity.get('follows', [])
follows = list({*follows, user})
```
D'après la [documentation de Google Cloud sur les entités Datastore](https://docs.cloud.google.com/datastore/docs/concepts/entities), une entité peut être récupérée directement à partir de sa clé.

Ainsi, tant que P et F restent constants,l'augmentation de U ne devrait modifier ni le nombre d'auteurs consultés ni le nombre maximal de publications retournée.
Je m'attends donc à une latence relativement stable, même lorsque le nombre total d'utilisateurs augmente fortement.


#### Second hypothèse: Influence du nombre de publications(P) ####
Je suppose que l'augmentation de P entraînerait une croissance du volume de données stockées et des coûts de stockage, mais que son influence sur la latence resterait modérée. En effet, dans `get_timeline()`, les publications sont récupérées à l'aide de requête ordonnées par date, avec une limite de 20 résultats par défaut:

```
query = client.query(kind='Post')
query.add_filter('author', 'IN', follows)
query.order = ['-created']
timeline = list(query.fetch(limit=limit))
```

L'utilisation du filtre `IN` permet de limiter la recherche aux auteurs concernés, tandis que le tri et la limite permettent de récupérer uniquement les publications les plus récentes.
D'après la [documentation de Google Cloud sur les index](https://docs.cloud.google.com/datastore/docs/concepts/optimize-indexes), les performances de la plupart des requêtes Datastore dépendent davantage de la taille des résultats retournés que du volume total de données stockées.

Je suppose donc que, grâce aux index, Datastore n'aura pas besoin de parcourir toutes les publications pour construire une timeline.

En conservant U et F constants, je m'attends à une augmentation modérée de la latence, qui ne devrait pas être proportionnelle à l'augmentation de P.

#### Troisième hypothèse : influence du nombre de comptes suivis (F) ####

Je suppose que l'augmentation de **F** pourrait entraîner une légère hausse de la latence, puisque davantage d'auteurs doivent être pris en compte lors de la construction d'une timeline. Cependant, la fonction `get_timeline()` utilise des requêtes groupées avec l'opérateur `IN` et limite le résultat aux 20 publications les plus récentes. Je m'attendais donc à ce que les performances restent relativement stables, même lorsque le nombre de comptes suivis augmente.

Le mécanisme de repli, qui exécute une requête distincte par auteur, pourrait théoriquement entraîner une dégradation plus importante. Néanmoins, puisqu'il n'intervient qu'en cas d'échec des requêtes groupées, je ne m'attendais pas à ce qu'il influence les résultats dans des conditions normales.


#### 2.1.2 Protocole expérimental
Les expériences ont été réalisées sur la version fixed1 de TinyInsta, configurée avec une seule instance B1 et un seul client concurrent Locust (C = 1). Chaque benchmark dure nominalement 45 secondes.

Les paramètres testés sont les suivants :
U — Nombre d'utilisateurs 100, 1 000, 10 000 P = 20 ; F = 20
P — Publications par utilisateur 10, 100, 1 000	U = 1 000 ; F = 20
F — Comptes suivis	5, 10, 15, …, 100 U = 120 ; P = 20

Les résultats des variations de U et P sont présentés dans la figure 1a, tandis que ceux de F figurent dans la figure 1b.
Enfin, les journaux bruts permettent de vérifier les codes HTTP, les éventuelles erreurs et le nombre d'instances réellement sollicitées grâce à l'entete X-Instance.

##### 2.1.3 Influence de U et P — Figure 1a #####

![influence U et P](figures/fig1a.png)


La figure 1a présente l'évolution du temps serveur médian, exprimé en millisecondes, lorsque le nombre d'utilisateurs **U** ou le nombre de publications par utilisateur **P** augmente.

##### Influence du nombre d'utilisateurs (U) #####

| U | Temps serveur médian |
|---:|---:|
| 100 | 27,55 ms |
| 1 000 | 27,30 ms |
| 10 000 | 30,85 ms |

Lorsque U passe de 100 à 10 000, soit une multiplication par 100, la latence serveur passe de 27,55 ms à 30,85 ms. Cela représente une augmentation d'environ 12 %.

Nous observons donc une relative stabilité du temps d'exécution malgré une augmentation importante du nombre d'utilisateurs.

Ce comportement est cohérent avec notre hypothèse H1: la fonction get_timeline() récupère les publications d'un ensemble déterminé de comptes suivis, et non celles de l'ensemble des utilisateurs de la base. L'augmentation de U n'entraîne donc pas directement une augmentation proportionnelle du nombre d'auteurs consultés.

Les variations observées peuvent également refléter la variabilité des temps de réponse de l'infrastructure Cloud. Les mesures ne permettent pas d'attribuer avec certitude la totalité des écarts à l'augmentation de U.

##### Influence du nombre de publications (P) #####

| P | Temps serveur médian |
|---:|---:|
| 10 | 26,80 ms |
| 100 | 32,15 ms |
| 1 000 | 34,70 ms |

Lorsque P passe de 10 à 1 000 (×100), la latence serveur augmente de **26,80 ms à 34,70 ms**, soit environ **29,5 %**. Cette progression reste modérée par rapport à l'augmentation du volume de données.

Ce résultat est cohérent avec notre hypothèse H2 : `get_timeline()` utilise des requêtes ordonnées chronologiquement et limitées aux 20 publications les plus récentes. Les index Datastore peuvent ainsi limiter le travail nécessaire à leur récupération.
Cependant, je ne peux pas déterminer précisément les causes de cette hausse de latence à partir de ces seules mesures.

**Conclusion  Figure 1a**

Les résultats sont globalement compatibles avec nos deux hypothèses :

- **H1 :** l'augmentation de U a un impact limité sur la latence.
- **H2 :** l'augmentation de P entraîne une hausse modérée, non proportionnelle au volume de données.

TinyInsta présente donc une **bonne stabilité de la latence serveur vis-à-vis de U et P**, dans les conditions testées. Ces observations restent toutefois partielles et ne suffisent pas à établir la scalabilité globale de l'application.


#### 2.1.4 Influence de F — Figure 1b ####

![Figure 1b — Influence du nombre de comptes suivis](figures/fig1b.png)

La troisième hypothèse (H3) prévoyait une augmentation relativement modérée de la latence avec F. je suppose que les requêtes groupées avec l'opérateur `IN` permettraient de récupérer les publications de plusieurs auteurs sans multiplier les requêtes.

Les mesures révèlent un comportement différent. 

| F | Temps serveur médian | Latence client médiane |
|---:|---:|---:|
| 5 | 24,10 ms | 36,50 ms |
| 20 | 29,40 ms | 46,20 ms |
| 25 | 30,00 ms | 48,00 ms |
| 30 | 633,30 ms | 650,80 ms |
| 50 | 1 044,10 ms | 1 056,90 ms |
| 100 | 2 154,55 ms | 2 184,70 ms |

Jusqu'à **F = 25**, la latence serveur reste relativement stable, autour de 24 à 30 ms. En revanche, à **F = 30**, elle atteint **633,30 ms**, soit plus de **21 fois** la valeur mesurée pour F =25.

Cette dégradation se poursuit ensuite: à F = 100, le temps serveur médian dépasse **2,15 secondes**. La latence client suit la même tendance, ce qui indique que l'essentiel de cette augmentation se produit pendant l'exécution de `get_timeline()`.

Ces résultats contredisent donc notre hypothèse initiale : l'augmentation de F ne provoque pas uniquement une légère hausse de la latence, mais révèle un changement brutal dans le comportement de l'application.

**Recherche de la cause**

L'examen du code montre que `get_timeline()` tente d'abord de récupérer les publications à l'aide de requêtes groupées utilisant l'opérateur `IN`.

Or, selon la [documentation Google Cloud](https://docs.cloud.google.com/datastore/docs/concepts/queries#in), les requêtes Datastore sont limitées à **30 disjonctions**.

La fonction ajoute également l'utilisateur lui-même aux comptes suivis :

```python
follows = list({*follows, user})
```
Ainsi, pour F =30, la liste peut contenir **31 auteurs distincts**, dépassant la limite.

Lorsque les requêtes groupées échouent, le code éxecute le mécanisme de repli exécutant une requête distincte pour chaque auteur. Cette stratégie multiplie les accès à Datastore et fournit une explication cohérente de l'augmentation brutale observée. 

Afin de chercher des preuve supplementaire , j'ai crée un script simple qui simule 30 requêtes Datastore individuelles depuis Google Cloud Shell, sur cinq auteurs différents.

Lors d'une seconde série de mesures, j'ai obtenu une durée moyenne de 14,65 ms et une médiane de 12,30 ms par requête. À titre indicatif, l'exécution séquentielle de 101 requêtes représenterait donc environ 1,48 seconde, hors surcoûts supplémentaires, contre 2,15 secondes de temps serveur médian observé pour F = 100.

Cet ordre de grandeur, associé à la progression approximativement linéaire de la latence après F = 30, renforce l'hypothèse d'un passage aux requêtes individuelles. Toutefois, les mesures ayant été effectuées depuis Cloud Shell et non depuis les instances App Engine, cette comparaison reste indicative et ne constitue pas une preuve directe de l'activation du mécanisme de repli. Les résultats sont disponible dans raw/part1/individual_query_latency.csv


**Conclusion — Figure 1b**

Les résultats contredisent notre hypothèse initiale H3, contrairement à nos attentes, l'augmentation de F provoque une dégradation brutale des performances à partir de F = 30.

L'analyse du code, des contraintes de Datastore et des mesures complémentaires suggère fortement que cette rupture provient de l'activation du mécanisme de repli, qui multiplie les requêtes individuelles.


**Part de la latence liée au réseau**

J'ai comparé la latence client au temps d'exécution de `get_timeline()` afin d'estimer le temps passé en dehors de cette fonction.
Par exemple, pour F =20, la latence client médiane est de 46,20 ms, contre 29,40 ms côté serveur,soit un écart de 16,80 ms(environ 36,4 % de la latence client).

Cependant, cet écart ne correspond pas uniquement au réseau car il peut également comprendre l'attente des requêtes et le traitement HTTP. Je ne peux donc pas déterminer précisément la part due au réseau avec les mesures disponibles.


#### 2.1.5 Lectures Datastore et coût d'un million de timelines


Le nombre d'opérations Datastore dépend fortement de la stratégie de requête utilisée. J'ai donc estimé le nombre d'entités récupérées pour une timeline, en supposant que chaque auteur possède au moins 20 publications.

Lorsque la requête groupée fonctionne, l'application récupère au maximum 21 entités soit un utilisateur et 20 publications.
En revanche, lorsque le mécanisme de repli est déclenché, le nombre maximal d'entités récupérées,noté R(F),devient :

$$
R(F)=1+20(F+1)
$$

Cette formule correspond à une entité User, puis 20 publications au maximum pour chacun des F comptes suivis et l'utilisateur lui-même.
Pour F = 30, cela représente jusqu'à 621 entités, contre 21 lorsque la requête groupée fonctionne. Soit environ 30x plus d'entité. 


Afin d'estimer le coût des lectures Datastore, je m'appuie sur la [grille tarifaire officielle de Google Cloud Datastore](https://cloud.google.com/datastore/pricing), pour la région **Paris (`europe-west9`)**. Cette valeur est de 0,036 USD pour 100 000 lectures d'entités, avec 50 000 lectures gratuites par jour et par projet.

En supposant que chaque auteur possède au moins 20 publications, le nombre maximal d'entités récupérées pour une timeline peut être estimé par :

$$
R(F) =
\begin{cases}
21 & \text{si } F \leq 29 \\[6pt]
1 + 20(F + 1) & \text{si } F \geq 30
\end{cases}
$$

soit : 

$$
C(F)=\frac{10^6 \times R(F)}{100,000}\times 0{,}036
$$

| Configuration      | Lectures estimées par timeline | Le cout théorique pour 1 million |
|--------------------|-------------------------------:|------------------------------:|
| U variable, F = 20 |                             21 |                      7,56 USD |
| P variable, F = 20 |                             21 |                      7,56 USD |
| F = 5 à 25         |                             21 |                      7,56 USD |
| F = 30             |                            621 |                    223,56 USD |
| F = 50             |                          1 021 |                    367,56 USD |
| F = 100            |                          2 021 |                    727,56 USD |

Ces valeurs représentent des estimations théoriques, fondées sur le nombre maximal d'entités retournées selon la stratégie de requêtage utilisée. Elles ne tiennent pas compte de tous les mécanismes de facturation de Datastore, notamment des lectures d'index, et ne correspondent pas aux coût réellement mesurés.

Cette analyse montre qu'un passage de la requête groupée aux requêtes individuelles pourrait entraîner une augmentation importante du nombre de lectures et, par conséquent, du coût des opérations Datastore.

#### Conclusion partie 1 

Les résultats obtenus montrent que TinyInsta conserve des performances relativement stables lorsque le nombre d'utilisateurs U et le nombre de publications P augmentent. Ces résultats sont cohérents avec mes hypothèses H1 et H2. D'après la [documentation de Google Cloud sur les index](https://docs.cloud.google.com/datastore/docs/concepts/optimize-indexes), les performances de la plupart des requête dépendent davantage de la taille des résultats retournés que du volume total de données stockées.

Par contre les résultats réfutent mon hypothèse H3. Je pensais initialement que l'utilisation de l'opérateur `IN` permettrait de conserver une augmentation relativement modérée de la latence lorsque F augmente.

Mon erreur venait principalement d'une connaissance insuffisante du fonctionnement de l'opérateur `IN` dans Datastore. Je n'avais pas pris en compte la [limite de 30 disjonctions](https://docs.cloud.google.com/datastore/docs/concepts/queries#in), ni les conséquences du dépassement de cette limite sur la stratégie de requêtage de l'application. À partir de F =30, le temps d'exécution augmente brutalement, jusqu'à atteindre 2 154,55 ms pour F = 100. L'analyse du code et des contraintes de Datastore suggère fortement que cette dégradation provient du mécanisme de repli, qui multiplie les requêtes individuelles.

Ce résultat rejoint également les [bonnes pratiques recommandées par Google Cloud](https://docs.cloud.google.com/datastore/docs/best-practices),qui conseille de regrouper les opérations lorsque cela est possible afin de réduire le surcoût associé aux appels individuels.

Ce que je trouve particulièrement intéressant dans ces résultats, c'est que le problème semble davantage lié à la manière dont l'application accède aux données qu'au volume de données lui même.Cette stratégie de requêtage a non seulement un impact sur les performances, mais également sur le coût potentiel de l'application.

Je pense donc qu'augmenter les ressources de l'infrastructure ne serait pas forcément la meilleure solution à ce premier goulot d'étranglement.Il serait plus pertinent de revoir la stratégie de requêtage de `get_timeline()` afin de limiter le nombre d'accès à Datastore.
C'est cette piste d'optimisation que j'explore dans la troisième partie.


### 2.2 Partie 2 — Capacité et passage à l'échelle

#### 2.2.1 Hypothèses sur le débit et les instances

Dans cette deuxième partie, je cherche à déterminer si TinyInsta est capable d'augmenter sa capacité de traitement lorsque davantage de ressources applicatives lui sont attribuées.

Contrairement à la première partie,je conserve ici un jeu de données constant et faisons varier le nombre de clients concurrents (C) ainsi que le nombre d'instances App Engine (N).

Nous formulons quatre hypothèses principales:

#### H1 - Influence de la concurrence sur le débit ####

Je suppose qu'une augmentation du nombre de clients concurrents entraînera d'abord une hausse du débit, puisque davantage de requêtes pourront être soumises à l'application. Cependant, je m'attends à ce que cette progression ralentisse lorsque les ressources disponibles approcheront de leur capacité maximale.

#### H2 - Saturation des ressources et évolution de la latence

Je suppose que chaque configuration possède une capacité de traitement limitée.Dans `deploy_fixed.sh`,Gunicorn est lancé avec la commande suivante :

```
gunicorn -b :$PORT main:app
```
D'après la [documentation officielle de Gunicorn](https://docs.gunicorn.org/en/21.2.0/design.html#sync-workers),un worker synchrone ne peut traiter qu'une seule requête à la fois. Avec la configuration par défaut, chaque instance dispose d'un seul worker. Si les requêtes arrivent plus rapidement qu'elles ne peuvent être traitées, certaines devront attendre avant d'être prises en charge. Je m'attends donc à observer un plateau du débit au-delà d'un certain niveau de concurrence, tandis que la latence client continuera d'augmenter en raison de l'accumulation des requêtes en attente.

#### H3 - Scalabilité horizontale

Je suppose que l'ajout d'instances B1 permettra d'augmenter la capacité de traitement. Le script `deploy_fixed.sh` utilise une mise à l'échelle manuelle:

```yaml
instance_class: B1
manual_scaling:
  instances: ${N}
```
D'après la [documentation d'App Engine](https://docs.cloud.google.com/appengine/docs/standard/how-instances-are-managed), la mise à l'échelle manuelle permet de maintenir un nombre fixe d'instance. Chaque instance possède ses propres ressources et son propre processus Gunicorn. L'ajout d'instances devrait donc permettre de traiter davantage de requêtes simultanément, en les répartissant entre plusieurs instances.
Et donc en théorie,doubler le nombre d'instances pourrait approximativement doubler le débit maximal. Cependant, toutes les instances continuent d'accéder au même service Datastore. Je ne m'attends donc pas nécessairement à une progression parfaitement linéaire, notamment à cause des surcoûts liés à la distribution des requêtes et de l'utilisation de ressources partagées.

#### H4 - Influence des opérations d'entrée/sortie

Je suppose que TinyInsta pourrait être davantage limitée par les opérations d'entrée/sortie que par la puissance de calcul.
En examinant `get_timeline()`, je remarque que la fonction réalise principalement des opérations de lecture auprès de Datastore :

```
user_entity = client.get(follow_key)
```
Puis, lors de la récupération des publications :

```
timeline = list(query.fetch(limit=limit))
```

Ces opérations nécessitent des échanges avec un service distant. Le worker doit donc attendre les réponses de Datastore avant de poursuivre l'exécution de la fonction.
Or, avec un worker synchrone, Gunicorn ne peut pas profiter de cette attente pour traiter une autre requête.
Je suppose donc qu'une partie de la capacité de traitement pourrait être limitée par le temps passé à attendre les réponses de Datastore, plutôt que par la quantité de calcul nécessaire à la génération d'une timeline.
Dans `api_timeline()`, le temps serveur est mesuré de la manière suivante:

```
t0 = time.perf_counter()
entities = get_timeline(user, limit=limit)
elapsed_ms = (time.perf_counter() - t0) * 1000
```
Cette mesure correspond uniquement au temps d'exécution de `get_timeline()`, et ne comprend donc pas l'attente éventuelle avant l'exécution de cette fonction.
Je m'attends ainsi à ce qu'une forte concurrence entraîne une augmentation importante de la latence client, sans nécessairement provoquer une augmentation proportionnelle du temps serveur.
L'ajout d'instances pourrait réduire cette attente en répartissant les requêtes. Toutefois, les seules mesures de débit et de latence ne permettront pas de confirmer avec certitude que l'application est principalement limitée par les I/O plutôt que par le CPU

#### 2.2.2 Protocole expérimental

Pour tester ces hypothèses, j'ai conservé un jeu de données fixe (**U = 1 000, P = 20, F = 20**) et fait varier deux paramètres, le nombre de clients concurrents (**C**) et le nombre d'instances App Engine (**N**).

J'ai utilisé trois versions de TinyInsta,chacune configurée avec des instances B1 et une mise à l'échelle manuelle:

| Version | Instances (N) | Concurrence (C) |
|---|---:|---|
| `fixed1` | 1 | 1, 2, 4, 8, 16, 32, 64 |
| `fixed2` | 2 | 1, 2, 4, 8, 16, 32, 64 |
| `fixed4` | 4 | 1, 2, 4, 8, 16, 32, 64 |

Ça représente **21 configurations expérimentales**,avec un benchmark Locust de **45 secondes** pour chacune.

J'ai ensuite exploité les journaux CSV pour mesurer le **débit de requêtes réussies**, la **latence client** et le **temps serveur**, tout en vérifiant les erreurs et les instances réellement utilisées.

Les résultats sont présentés dans deux figures:

- **Figure 2a :** évolution du débit en fonction de C et N.
- **Figure 2b :** évolution de la latence client, avec une comparaison aux valeurs estimées à partir de la loi de Little.

Ce protocole doit permettre d'identifier les signes de saturation et de mesurer l'effet de l'ajout d'instances sur les performances.


#### 2.2.3 Débit et points de saturation — Figure 2a



![Figure 2a, debit selon la concurrence](figures/fig2a.png)

La figure 2a présente l'évolution du débit de TinyInsta en fonction du nombre de clients concurrents **C**, pour 1, 2 et 4 instances B1.

| Clients (C) | N = 1 (req/s) | N = 2 (req/s) | N = 4 (req/s) |
|---:|---:|---:|---:|
| 1 | 20,67 | 19,40 | 19,31 |
| 2 | 21,96 | 33,40 | 41,91 |
| 4 | 21,02 | 38,53 | 65,02 |
| 8 | 21,60 | 41,20 | 75,02 |
| 16 | 25,56 | 43,93 | 84,78 |
| 32 | 26,33 | 44,36 | 91,80 |
| 64 | 27,40 | 44,62 | 93,56 |

**Évolution du débit et saturation**

Avec **N = 1**,je remarque que le débit reste relativement stable, autour de 20 à 22 req/s jusqu'à C =8, puis atteint seulement 27,40 req/s à C = 64. Augmenter la concurrence apporte donc peu de gains supplémentaires.

Avec **N = 2**, le débit atteint rapidement 41,20 req/s à C = 8, avant de se stabiliser autour de 44 req/s. Le plateau de saturation est ici plus visible.

Enfin, avec **N = 4**, le débit progresse davantage et atteint 93,56 req/s à C = 64. Sa croissance ralentit aux fortes concurrences, sans permettre d'affirmer qu'un plateau définitif a été atteint.

Cette progression limitée peut s'expliquer en partie par notre configuration Gunicorn : chaque instance dispose d'un seul worker synchrone, capable de traiter une requête à la fois, comme l'indique la [documentation officielle de Gunicorn](https://gunicorn.org/design/#sync-workers).


**Influence du nombre d'instances**

À C = 64, le débit passe de **27,40 req/s avec une instance à 93,56 req/s avec quatre instances**, soit une multiplication par **3,41**, contre un facteur théorique idéal de 4.

Ce résultat soutient mon hypothèse H3 :l'ajout d'instances améliore nettement la capacité de traitement, même si les gains ne sont pas parfaitement proportionnels aux ressources ajoutées.

Ce gain s'explique notamment par l'ajout de capacités de traitement : chaque instance B1 dispose de son propre worker Gunicorn synchrone, capable de traiter une requête à la fois. En multipliant les instances, plusieurs requêtes peuvent donc être traitées en parallèle.

La [documentation Google Cloud](https://docs.cloud.google.com/appengine/docs/standard/how-instances-are-managed) confirme qu'App Engine répartit les requêtes entre les instances disponibles.

Ces résultats sont globalement cohérents avec mes hypothèses H1, H2 et H3. La concurrence améliore initialement le débit, mais les gains diminuent lorsque la charge augmente, tandis que l'ajout d'instances permet d'augmenter la capacité de traitement.

Il reste cependant à examiner l'évolution de la latence pour déterminer les conséquences de cette augmentation de charge.

#### 2.2.4 Latence et loi de Little — Figure 2b

![Figure 2b , Latence et loi de little](figures/fig2b.png)


La figure 2b présente l'évolution de la latence client en fonction du nombre de clients concurrents **C**, pour les trois configurations étudiées : N = 1, 2 et 4 instances B1.

Nous constatons que la latence augmente avec le nombre de clients concurrents, mais que cette augmentation est nettement plus importante lorsque le nombre d'instances disponibles est faible.

**Application de la loi de Little**

Pour mieux comprendre le lien entre la concurrence, le débit et la latence, j'ai choisi d'utiliser la **loi de Little**, qui établit la relation suivante pour un système stable:

$$
L = \lambda \times W
$$

Ou :
- **L** représente le nombre moyen de requêtes présentes dans le système.
- **Lambda** représente le débit moyen, en requêtes par seconde.
- **W** représente le temps moyen de réponse, en secondes.

Dans mon expérience,chaque client virtuel Locust attend la réponse avant d'envoyer une nouvelle requête. J'ai donc approximé **L par C**, en supposant que les clients n'ont pas de temps d'attente significatif entre leurs requêtes.

Je peux ainsi estimer le temps de réponse moyen en divisant le nombre de clients concurrents par le débit mesuré.

Par exemple,pour **N = 1 et C = 64**, le débit est de 27,40 req/s:

$$
W \approx \frac{64}{27{,}40} \approx 2{,}34\ \text{s}
$$

J'ai ensuite comparé les estimations avec les latences réellement mesurées pour C = 64:

| Instances | Latence moyenne mesurée | Estimation de Little |
|---|---:|---:|
| N = 1 | 2 250,49 ms | 2 335,77 ms |
| N = 2 | 1 397,33 ms | 1 434,26 ms |
| N = 4 | 673,58 ms | 684,09 ms |

Les valeurs estimées sont relativement proches des moyennes mesurées. Cela montre que les résultats sont cohérents avec la relation entre concurrence, débit et temps de réponse décrite par la loi de Little.

par contre cette loi concerne les **moyennes** et non les **médianes**. De plus, les benchmarks ne sont pas nécessairement parfaitement stables pendant leurs 45 secondes, et l'approximation L ≈ C dépend du comportement des clients Locust.

**Interprétation**

Je remarque que lorsque le débit augmente peu malgré une forte hausse de la concurrence, la latence client devient beaucoup plus importante.

Une explication possible est la mise en attente des requêtes. En effet, chaque instance utilise un seul worker Gunicorn synchrone, qui ne peut traiter qu'une requête à la fois. Lorsque tous les workers sont occupés, les requêtes supplémentaires peuvent devoir attendre.

L'ajout d'instances permet de disposer de davantage de workers. Cela pourrait expliquer pourquoi, à C = 64, la latence médiane passe de **2 252,90 ms avec une instance à 553,65 ms avec quatre instances**, soit une réduction d'environ **75,4 %**.

Ces observations soutiennent donc l'hypothèse d'une saturation accompagnée d'une mise en attente des requêtes. En revanche, elles ne suffisent pas à démontrer que TinyInsta est principalement limitée par les opérations d'entrée/sortie plutôt que par le CPU.

**Conclusion — Figure 2b**

Je constate que l'augmentation de la concurrence peut entraîner une forte hausse de la latence lorsque le débit progresse peu. L'ajout d'instances améliore nettement les temps de réponse dans les conditions testées, mais ne permet pas à lui seul d'identifier la cause exacte des limitations observées.

**Bilan des points de saturation**

À partir des figures 2a et 2b, j'estime les niveaux de saturation suivant:

| Instances | Saturation estimée | Débit maximal observé |
|---|---|---:|
| N = 1 | Forte limitation dès les faibles concurrences | 27,40 req/s |
| N = 2 | Plateau visible vers C = 8 à 16 | 44,62 req/s |
| N = 4 | Ralentissement vers C = 32 à 64, sans plateau confirmé | 93,56 req/s |

Une instance B1 atteint donc un débit maximal observé de **27,40 req/s** dans cette expérience.Il ne s'agit toutefois pas d'une capacité maximale universelle, puisqu'elle dépend de la configuration Gunicorn et du travail effectué par chaque requête.

Le fait d'utiliser **un seul worker synchrone par instance** constitue une limite importante car ce worker ne traite qu'une requête à la fois. Les autres requêtes peuvent devoir attendre, même si je ne peux pas déterminer précisément si le CPU, les accès à Datastore ou la gestion des requêtes par App Engine constituent la limitation principale.


#### Limites de la configuration de Gunicorn

La configuration par défaut de Gunicorn constitue une piste d'optimisation intéressante. Il serait pertinent de déterminer si l'augmentation du nombre de workers et de threads permettrait d'améliorer la capacité de traitement de chaque instance.

#### 2.2.5 Limites de la scalabilité horizontale

Les résultats montrent que l'ajout d'instances améliore le débit et réduit la latence sous forte concurrence. Cependant, je considère que cette approche présente certaines limites.

Tout d'abord, chaque instance supplémentaire consomme des ressources et entraîne des coûts. Avec une mise à l'échelle manuelle, les instances restent allouées même lorsque la charge diminue.

De plus, augmenter le nombre d'instances ne corrige pas les inefficacités du code. Le mécanisme de repli identifié dans la première partie, par exemple, peut toujours multiplier les requêtes Datastore lorsque F devient important.

J'en conclus que **la scalabilité horizontale améliore la capacité globale de TinyInsta, mais ne réduit pas nécessairement le coût de traitement d'une requête individuelle**.



#### 2.2.6 Conclusion sur les hypothèses de la partie 2

Les résultats obtenus sont globalement cohérents avec mes hypothèses initiale,même si certaines restent difficile à confirmer entièrement.

**H1 Confirmée :** l'augmentation du nombre de clients concurrents permet effectivement d'augmenter le débit. Cependant, comme prévu, les gains deviennent de plus en plus faibles lorsque la charge augmente.
 
**H2 Globalement confirmée:** les résultats montrent des signes de saturation, notamment avec une et deux instances. Lorsque le débit se stabilise, la latence client continue d'augmenter. Ce comportement est également cohérent avec la loi de Little. Pour quatre instances,je remarque un ralentissement de la progression du débit, mais je ne peux pas affirmer qu'un plateau définitif a été atteint.

**H3 Confirmée :** l'ajout d'instance améliore la capacité de traitement de TinyInsta. Comme je le supposais,cette progression n'est pas parfaitement linéaire. Le passage de une à quatre instances multiplie le débit par 3,41 au lieu de 4 à C =64.

**H4 Partiellement confirmée :** sous forte concurrence, la latence client augmente considérablement, alors que le temps d'exécution de `get_timeline()` reste relativement stable. Cela suggère qu'une partie importante du temps de réponse provient de l'attente des requête plutôt que de leur traitement applicatif.
Une explication possible concerne l'utilisation d'un seul worker synchrone par instance. Lorsqu'un worker attend une réponse de Datastore, il reste occupé et ne peut pas prendre en charge une autre requête, même s'il n'utilise pas pleinement le CPU. Cette configuration pourrait donc empêcher une exploitation efficace des ressources disponibles.

Cependant, le temps mesuré dans `get_timeline()` ne permet pas de distinguer le temps réellement consacré aux calculs de celui passé à attendre les réponses de Datastore. Et de même,l'écart entre la latence client et le temps serveur ne permet pas de localiser précisément l'attente, qui pourrait également se produire au niveau d'App Engine.

Les résultats sont donc cohérents avec une partie de mon hypothèse, mais sans mesures plus précises de l'utilisation du CPU, des accès à Datastore et des files d'attente, je ne peux pas affirmer que les opérations d'entrée/sortie constituent la limitation principale de TinyInsta.

Ce que je retiens principalement de cette deuxième partie, c'est que l'ajout de ressources permet d'améliorer les performances, mais ne garantit pas une scalabilité linéaire.

Je pense que la configuration par défaut de Gunicorn constitue une limitation importante, puisque chaque instance ne dispose que d'un seul worker synchrone. Cependant, je ne peux pas encore déterminer dans quelle mesure cette configuration est responsable des limites observées.
Dans la troisième partie, je chercherai donc à améliorer les performances de TinyInsta en explorant deux pistes : l'optimisation de la stratégie de requêtage de `get_timeline()` et la modification de la configuration de Gunicorn.

### 2.3 Partie 3 — Correction du goulot d'étranglement

#### 2.3.1 Problème identifié

À la suite des deux premières parties, j'ai identifié deux problèmes de performance. Le premier concerne la forte augmentation de la latence lorsque F atteint 30. Le second concerne les limites observées sous forte concurrence.

J'ai réussi à apporter une correction au premier problème. Pour le second, j'ai exploré plusieurs pistes sans parvenir à identifier précisément son origine. Je présenterai également ces investigations complémentaires.

#### 2.3.2 Hypothèse testée

À partir des résultats obtenus dans la première partie,je suppose qu'il est possible de réduire considérablement la latence lorsque F atteint ou dépasse 30, sans augmenter les ressources disponibles sur App Engine.

Comme vu avant le mécanisme de repli effectue une requête individuelle pour chaque auteur:

```python
for author in follows:
    q = client.query(kind='Post')
    q.add_filter('author', '=', author)
    q.order = ['-created']
    posts.extend(list(q.fetch(limit=limit)))
```

Le nombre de requêtes envoyées à Datastore augmente donc directement avec le nombre de comptes suivis. Pour F = 100, cela représente 101 requêtes individuelles pour récupérer les publications.
Comme vu avant, je suppose donc qu'en divisant les auteurs en lots de 30 maximum, je pourrai continuer à utiliser les requêtes groupées sans déclencher le mécanisme de repli. 

Le nombre de requêtes nécessaires pour récupérer les publications serait alors donné par :

$$
B(F)=\left\lceil\frac{F+1}{30}\right\rceil
$$

Pour F =100, je passerais donc de 101 requêtes individuelles à seulement 4 requêtes groupées.

**Comportements attendus :**

- **Pour F < 30:** je m'attends à des performances relativement proches de celles de la version initiale, puisque celle-ci utilise déjà des requêtes groupée.
- **Pour F >= 30:** je m'attends à une réduction importante de la latence grâce à la diminution du nombre de requêtes envoyées à Datastore.
- **Évolution de la latence :** je suppose que la latence évoluera par paliers, puisque chaque nouveau lot nécessite une requête supplémentaire.
- **Coût des lectures:** je m'attends également à une réduction du nombre d'entités récupérées, ce qui pourrait diminuer le coût des opérations Datastore.

Mon hypothèse principale est donc que la modification de la stratégie de requêtage permettra d'améliorer la scalabilité de TinyInsta vis-à-vis de F, sans augmenter les ressources applicatives et tout en conservant le même résultat pour un jeu de données fixe.


#### 2.3.3 Protocole 

Afin d'évaluer l'efficacité de notre optimisation, j'ai reproduis le protocole utilisé dans la première partie pour mesurer l'influence du nombre de comptes suivis (**F**).

La version optimisée de `get_timeline()` a été déployée séparément sur Google App Engine, sous le nom `batched1`, avec **une instance B1** et **un seul client concurrent Locust (C = 1)**.
Nous avons conservé les mêmes paramètres expérimentaux :

- **U = 120** utilisateurs
- **P = 20** publications par utilisateur 
- **F = 5 à 100**, par pas de 5 
- **Durée de chaque benchmark** : 45 secondes

La classe d'instance et les paramètres du jeu de données restent identiques à ceux de la version initiale (`fixed1`). Seule la stratégie de récupération des publications a été modifiée.

Pour chaque valeur de F, j'ai mesuré la **latence serveur médiane** et comparé les résultats avec ceux obtenus dans la première partie.

Cette comparaison permet d'évaluer les gains de performance apportés par l'optimisation, tout en limitant l'influence d'autres paramètres.

#### 2.3.4 Résultats de l'optimisation — Figure 3


![Figure 3 Avant et apres optimisation](figures/fig3.png)


La figure 3 présente une comparaison des **latences serveur médianes** obtenues avant et après l'optimisation de `get_timeline()`,en fonction du nombre de comptes suivis(F).

Les résultats montrent une amélioration significative des performances, particulièrement lorsque F atteint ou dépasse 30.

**Comparaison des résultats**

| F | Avant (ms) | Après (ms) | Accélération |
|---:|---:|---:|---:|
| 5 | 24,10 | 22,30 | ×1,08 |
| 25 | 30,00 | 25,10 | ×1,20 |
| 30 | 633,30 | 39,10 | ×16,20 |
| 50 | 1 044,10 | 42,00 | ×24,86 |
| 85 | 1 915,30 | 58,90 | ×32,52 |
| 100 | 2 154,55 | 80,90 | ×26,63 |

J'ai calculé l'accélération en divisant la latence médiane de la version initiale par celle de la version optimisé:

$$
A(F)=\frac{T_{\text{avant}}(F)}{T_{\text{après}}(F)}
$$


**Analyse des résultats**

Je remarque que pour **F inférieur à 30**, les gains restent modestes, puisque la version initiale utilise déjà des requêtes groupées.

En revanche, à **F = 30**, la latence passe de **633,30 ms à 39,10 ms**, soit une accélération de **×16,20** et une réduction d'environ **93,8 %**. À **F = 100**, elle passe de **2 154,55 ms à 80,90 ms**, ce qui représente une accélération de **×26,63**.

La courbe optimisé présente également une évolution par paliers. Ce comportement correspond au nombre de lots nécessaires pour interroger Datastore, donné par:

$$
B(F)=\left\lceil\frac{F+1}{30}\right\rceil
$$

Je distingue ainsi quatre niveaux de latence dans les mesures:

- **1 lot (F = 5 à 25) :** environ 22 à 25 ms
- **2 lots (F = 30 à 55) :** environ 39 à 44 ms
- **3 lots (F = 60 à 85) :** environ 58 à 59 ms
- **4 lots (F = 90 à 100) :** environ 75 à 81 ms

Chaque lot supplémentaire nécessite une nouvelle requête `IN`, ce qui explique les augmentations progressives de latence sans retrouver la dégradation brutale de la version initiale.
Ces résultats montrent que **le regroupement des auteurs permet de réduire considérablement le temps de génération des timelines**, sans augmenter les ressources App Engine. Je considère donc que cette optimisation répond efficacement au premier problème identifié, dans les conditions testées.

Un avantage important de cette optimisation est qu'elle réduit le travail demandé à Datastore pour chaque timeline. Contrairement à l'ajout d'instances App Engine, qui augmente principalement la capacité de traitement de l'application, le regroupement des requêtes diminue le nombre d'opérations nécessaires à leur exécution.

Je considère cet aspect particulièrement intéressant pour la scalabilité car si plusieurs utilisateurs consultent leur timeline simultanément, réduire les accès à Datastore par requête pourrait limiter la pression sur ce service partagé et améliorer l'utilisation globale des ressources.

Cet avantage reste toutefois théorique dans notre étude, puisque je n'ai pas mesuré directement son effet sur le débit sous forte concurrence. Les résultats confirment néanmoins mon hypothèse concernant la réduction de la latence et son évolution par paliers. J'ai donc réussi à améliorer la scalabilité de TinyInsta vis-à-vis de F sans augmenter les ressources applicative.


#### 2.3.5 complexité et compromis


**Complexité algorithmique**

Même si les gains mesurés sont importants, je tiens à distinguer l'amélioration pratique de la complexité théorique.

Comme le nombre de lots reste proportionnel à F, la complexité en nombre de requêtes demeure O(F). L'optimisation réduit donc principalement le facteur constant, sans modifier la classe de complexité asymptotique.

**Limites et compromis**

Cette solution présente néanmoins quelques limites :

- **Requêtes séquentielles :** les lots sont traités successivement, ce qui peut augmenter la latence lorsque F devient très élevé.
- **Dépendance à Datastore :** la taille des lots repose sur la limite de 30 disjonctions de l'opérateur `IN`. Une modification de cette contrainte pourrait nécessiter une adaptation du code.
- **Complexité du code :** le découpage en lots et la fusion des résultats ajoutent une logique supplémentaire à maintenir et à tester.

Je considère néanmoins que ces compromis sont acceptables au regard des gains observés. L'optimisation réduit fortement le coût de traitement d'une timeline sans nécessiter davantage de ressources App Engine, même si son efficacité pour des valeurs de F supérieures à celles testées reste à évaluer.


**Cohérence des données**

Le regroupement conserve la sélection des 20 publications les plus récentes pour un jeu de données fixe car chaque lot retourne ses 20 résultats les plus récents, puis l'application sélectionne les 20 plus récent globalement.

Cependant, les requêtes sont exécutées successivement,sans lecture transactionnelle unique.Si de nouvelles publications apparaissent pendant leur exécution, les différents lots pourraient être consulté à des instants différent.
Je n'ai pas testé ce scénario, puisque mes jeux de données restaient fixes pendant les benchmarks.

le coût de la campagne se trouve dans la section 5. 


### 2.4 Investigations complémentaire


**Hypothèse testée**

Je suppose que la configuration par défaut de Gunicorn constitue une des principales limitations de TinyInsta sous forte concurrence.
Comme vu avant , un worker synchrone ne peut traiter qu'une seule requête à la fois. Or, dans `get_timeline()`, une partie du temps d'exécution est consacrée aux échanges avec Datastore, pendant lesquels le worker reste occupé.

Je suppose donc qu'en augmentant le nombre de workers et de threads, l'instance pourra traiter davantage de requêtes simultanément et mieux exploiter ses ressources, notamment pendant les opérations d'entrée/sortie.

Je m'attends ainsi à une augmentation importante et durable du débit, accompagnée d'une diminution de la latence client, sans avoir à augmenter le nombre d'instance App Engine.


#### 2.4.1 Configurations Gunicorn et concurrence

Après les résultats de la deuxième partie, j'ai voulu comprendre si le nombre limité de workers Gunicorn pouvait expliquer les performances observées sous forte concurrence.

En effet, selon la [documentation officielle de Gunicorn](https://gunicorn.org/design/#how-many-threads), les workers multithreads permettent de traiter plusieurs requêtes simultanément. Cette approche me semblait donc intéressante pour une application effectuant des opérations d'entrée/sortie vers un service distant.

J'ai commencé par tester une configuration avec **1 worker et 4 threads**, en conservant les paramètres suivants:

- **Instance :** un B1
- **Concurrence :** C = 16
- **Données :** U = 1 000,P = 20, F = 20
- **Durée :** 45 secondes

Contrairement à mes attentes, je n'ai pas observé d'amélioration significative des performance.

J'ai alors envisagé que le problème puisse également provenir des opérations d'accès à Datastore,un service partagé entre les requêtes. L'ajout de threads ne garantit pas nécessairement une amélioration si d'autres composants limitent les performances.

J'ai donc poursuivi l'investigation avec différentes configurations de workers, de threads et d'instances, afin de mieux comprendre l'origine de cette limitation.



![Evolution latence ](figures/part-3-second-bottleneck/variation_latency.png)


Pour approfondir cette investigation, j'ai comparé plusieurs configurations Gunicorn en faisant varier le nombre de workers et de threads, avec **C = 16** et des tests de **180 secondes**.

| Configuration | Workers | Threads par worker |
|---|---:|---:|
| `sync_c16_cpu_test` | 1 | 1 |
| `sync_c16_repeat` | 1 | 1 |
| `worker2_c16_cpu_test` | 2 | 1 |
| `worker2thread2_c16` | 2 | 2 |
| `worker4thread4_c16` | 4 | 4 |
| `worker4thread4_c16_repeat` | 4 | 4 |

**Observations**

Avec un seul worker synchrone, je remarque que la latence client se situe généralement autour de **1 000 à 1 200 ms** après le début du test.Le passage à deux workers apporte une amélioration modérée,avec une latence proche de **800 ms**.

Les configurations utilisant plusieurs threads obtiennent de meilleurs résultat, avec des latences généralement comprises entre **550 et 680 ms**.

Cependant, j'ai observé un comportement inattendu avec **4 workers et 4 threads**. Lors du premier test, la latence était initialement très faible, autour de **40 à 60 ms**, avant d'augmenter fortement.

J'ai donc répété l'expérience avec la même configuration. Cette fois, les faibles latences initiales n'ont pas été reproduites  les valeurs sont restées proches de **550 à 670 ms**.

**Interprétation du débit et de la latence**

En comparant les deux graphiques,je remarque qu'augmenter le nombre de workers et de threads permet d'améliorer le débit et de réduire la latence. Cependant, les gains restent inférieurs à ceux auxquels je m'attendais.

Ce qui m'interroge particulièrement,c'est la différence entre les deux essais réalisés avec 4 workers et 4 threads. Lors du premier essai, la chute du débit s'accompagne d'une forte augmentation de la latence, tandis que le second essai ne reproduit pas les bonnes performances initiale.

Une explication possible concerne la gestion des requêtes par App Engine, les requêtes peuvent être placées dans une file d'attente avant leur prise en charge.
De plus, la [documentation concernant les problèmes de latence](https://docs.cloud.google.com/appengine/docs/standard/troubleshooter/latency) indique que des temps d'attente importants peuvent apparaître avec une mise à l'échelle manuelle, meme lorsque plusieurs instances sont disponibles.
Je suppose donc qu'une accumulation de requêtes en attente pourrait contribuer à la dégradation des performances observée.
Cependant, cette hypothèse ne permet pas d'expliquer pourquoi les deux essais réalisés avec une configuration identique ont donné des résultats aussi différents. Mes mesures ne permettent donc pas d'identifier précisément l'origine de cette limitation.


**Retour sur l'hypothèse**

Les résultats obtenus ne réfutent pas entièrement mon hypothèse initiale.En effet, augmenter le nombre de workers et de threads semble améliorer les performances sous concurrence.Cependant, les gains restent inférieurs à ceux auxquels je m'attendais, et les meilleures performances observée n'ont pas pu être reproduites avec une configuration identique.

Je pense donc que mon hypothèse initiale était incomplète. J'avais principalement considéré les limitations liées à Gunicorn, sans suffisamment prendre en compte l'influence des autres composants du système.

Une explication possible concerne la gestion des requêtes par App Engine. Selon la [documentation officielle de Google Cloud](https://docs.cloud.google.com/appengine/docs/standard/how-requests-are-handled), les requêtes peuvent être placées dans une file d'attente lorsqu'aucune instance n'est disponible pour les traiter immédiatement.

Je suppose donc que les très faibles latences observées au début du premier test pourraient correspondre à une période où les requêtes étaient traitées rapidement, avant qu'une accumulation de requêtes en attente n'augmente les temps de réponse. Le second test n'ayant pas reproduit cette phase initiale, il est possible que les conditions d'exécution aient été différentes, notamment au niveau de la gestion des requêtes par App Engine.

Cependant, mes mesures ne permettent pas de vérifier cette explication ni de déterminer précisément pourquoi les deux essais ont donné des résultats aussi différents.

Je considère donc mon hypothèse comme partiellement confirmée: la configuration de Gunicorn semble avoir une influence sur les performances, mais sa modification ne constitue pas à elle seule une solution suffisante au goulot d'étranglement observé.

J'ai donc poursuivi l'investigation en comparant les classes d'instances **B1 et B2**, afin de déterminer si les ressources disponibles sur chaque instance pouvaient également constituer un facteur limitant.



**Hypothèse sur B1 et B2**


À la suite des expériences précédentes, j'ai envisagé que les ressources disponibles sur une instance B1 puissent limiter l'efficacité des configurations utilisant plusieurs workers et threads. D'après la [documentation officielle de Google Cloud sur les classes d'instances App Engine](https://docs.cloud.google.com/appengine/docs/standard/overview#instance_classes), les instances B1 et B2 présentent les caractéristiques suivantes :

| Caractéristique | B1 | B2 |
|---|---:|---:|
| Mémoire disponible | 384 Mo | 768 Mo |
| Puissance CPU relative | 600 MHz | 1,2 GHz |

Google précise que ces valeurs CPU représentent la puissance de calcul relative allouée à chaque instance et non une fréquence d'horloge physique fixe.
Une instance B2 dispose donc de deux fois plus de mémoire et d'une puissance de calcul relative deux fois supérieure à celle d'une instance B1.
Je suppose que l'augmentation du nombre de workers sur une instance B1 pourrait entraîner une contention pour les ressources disponibles, ce qui expliquerait en partie les gains limités observés précédemment. En passant à une instance B2, je m'attends à ce que Gunicorn puisse mieux exploiter ses capacités de traitement concurrent grâce aux ressources supplémentaires.

En conservant une configuration de 4 workers et 4 threads par worker, je m'attends donc à observer une augmentation importante et durable du débit ainsi qu'une diminution de la latence client.

Si cette amélioration n'est pas observée, cela pourrait indiquer que les ressources CPU et mémoire de l'instance ne constituent pas la principale limitation de l'application.

#### 2.4.2 Expérimentation B1 / B2

![Évolution du débit](figures/part-3-second-bottleneck/comparaison_b1_b2.png)

Après avoir testé différentes configurations Gunicorn, j'ai voulu déterminer si les ressources disponibles sur les instances App Engine pouvaient expliquer les limitations observées.

J'ai donc comparé les classes **B1 et B2**, en conservant **4 workers avec 4 threads par worker**, ainsi que les paramètres U =1000, P = 20, F = 20 et C = 16.
J'ai réalisé deux essais de **180 secondes** pour chaque classe, contre 45 secondes lors des benchmarks principaux, afin d'observer l'évolution des performances sur une durée plus longue et de vérifier si les résultats étaient reproductibles, notamment après les premières secondes du test.

**Observations**

Lors du premier essai, j'ai observé des pics de débit particulièrement élevés : environ **124 req/s pour B1** et **210 req/s pour B2**. Cependant, ces performances ont rapidement diminué et n'ont pas été reproduites lors des seconds essais.

Après les premières dizaines de secondes, j'ai obtenu les valeurs approximatives suivante:

| Expérience | Débit après stabilisation | Latence client médiane approximative |
|---|---:|---:|
| B1 Essai 1 | 22–29 req/s | 560–680 ms |
| B1 Essai 2 | 23–29 req/s | 545–665 ms |
| B2 Essai 1 | 34–37 req/s | 420–445 ms |
| B2 Essai 2 | 24–29 req/s | 550–650 ms |

Le premier essai B2 présente donc de meilleures performances que les essais B1.Toutefois, lors de sa répétition, les résultats B2 deviennent très proches de ceux obtenus avec B1.


**Retour sur l'hypothèse**

Les résultats ne confirment pas mon hypothèse initiale.Je m'attendais à une amélioration importante et durable des performances en passant d'une instance B1 à une instance B2, puisque celle-ci dispose de deux fois plus de mémoire et d'une puissance de calcul relative deux fois supérieure.
Bien que le premier essai B2 semble aller dans le sens de cette hypothèse, le second essai donne des résultats très proches de ceux obtenus avec B1. L'amélioration attendue n'est donc pas reproductible.
Je pensais initialement que les ressources limitées des instances B1 empêchaient Gunicorn d'exploiter efficacement ses workers et ses threads. Cependant, j'ai probablement sous-estimé l'influence des autres composants du système, notamment App Engine et Datastore. Ces résultats ne permettent pas d'exclure complètement une limitation liée au CPU ou à la mémoire. En revanche, ils montrent que l'augmentation des ressources de l'instance ne constitue pas, dans les conditions testées, une solution fiable au problème observé.


**Interprétation et investigation des temps d'attente**

Puisque l'augmentation des ressources de l'instance ne semble pas suffire à résoudre le problème, j'ai décidé d'examiner davantage la manière dont App Engine prend en charge les requête.J'ai donc examiné les journaux de requêtes App Engine. Sur un intervalle du test B2, j'ai relevé un **`pendingTime` médian d'environ 389,5 ms**.

D'après la [documentation de Google Cloud sur les journaux App Engine](https://docs.cloud.google.com/python/docs/reference/appenginelogging/latest/google.cloud.appengine_logging_v1.types.RequestLog), `pendingTime` correspond au temps passé par une requête dans la file d'attente avant sa prise en charge.

Et donc cette mesure constitue un indice concret , une partie importante de la latence peut provenir de l'attente avant le traitement applicatif, et non uniquement de l'exécution de `get_timeline()`.Cependant, cette observation concerne un intervalle précis du test B2. Elle ne permet pas d'expliquer à elle seule la chute initiale du débit ni pourquoi les deux essais B2 ont produit des résultats différents.
Je ne peux donc pas conclure que le passage de B1 à B2 constitue une correction fiable du second goulot d'étranglement.

#### Conclusion sur le second goulot d'étranglement

Les différentes expériences suggèrent que la configuration de Gunicorn joue un rôle dans le goulot d'étranglement observé, mais que sa modification ne suffit pas à résoudre le problème.L'augmentation des ressources de l'instance n'a pas non plus apporté d'amélioration reproductible.Les mesures de `pendingTime` suggèrent que la gestion des requêtes par App Engine pourrait également constituer un facteur limitant.Je n'ai donc pas réussi à identifier précisément l'origine de ce second goulot d'étranglement malheureusement.


## 3. Tableau des verdicts

Les expériences précédentes me permet de formuler un verdict sur la scalabilité de TinyInsta, aussi bien concernant le volume de données que les ressources applicatives.

Les conclusions suivantes s'appliquent aux configurations expérimentales étudiées et ne garantissent pas les mêmes performances pour des volumes ou des charges plus importants.

| Paramètre | Passe à l'échelle ? | Jusqu'où ? | Justification | Figure |
|---|---|---|---|---|
| **U — Utilisateurs** | Oui dans la plage étudiée | Jusqu'à U = 10 000 | La latence serveur augmente seulement de 27,55 à 30,85 ms lorsque U est multiplié par 100. | 1a |
| **P — Publications** | Oui avec une légère dégradation | Jusqu'à P = 1 000 | La latence passe de 26,80 à 34,70 ms lorsque P est multiplié par 100. Les requêtes indexées et la limite de 20 publications contribuent à contenir le coût. | 1a |
| **F — Comptes suivis (initial)** | Non au-delà du seuil observé | Jusqu'à F = 25 sans dégradation majeure | À F = 30 la latence passe de 30,00 à 633,30 ms en raison du mécanisme de repli vers des requetes individuelles | 1b |
| **F — Comptes suivis (optimisé)** | Oui dans la plage étudiée | Jusqu'à F = 100 | Le regroupement en lots limite les requêtes Datastore : à F = 100, la latence diminue de 2 154,55 à 80,90 ms. | 3 |
| **N — Instances B1** | Oui, avec une efficacité imparfaite | Jusqu'à N = 4 et C = 64 | Le débit passe de 27,40 à 93,56 req/s entre 1 et 4 instances, soit une accélération de ×3,41. | 2a, 2b |

### 3.1 Scalabilité des données : U, P et F

Les résultats montrent que TinyInsta conserve des performances relativement stables lorsque le nombre d'utilisateurs (U) et de publications (P) augmente,dans les plages étudiées.
En revanche, j'ai identifié une dégradation importante à partir de **F = 30** dans la version initiale, probablement liée à l'activation du mécanisme de repli de `get_timeline()`.
L'optimisation par regroupement des requêtes Datastore a permis de réduire considérablement cette latence, qui reste inférieure à **81 ms jusqu'à F = 100** dans mes expériences.

J'en conclus que **la stratégie d'accès aux données joue un rôle déterminant dans la scalabilité de TinyInsta**, au delà du volume total de données stockées.

### 3.2 Scalabilité des ressources : N

L'ajout d'instances B1 améliore nettement la capacité de traitement de TinyInsta. À **C = 64**, le passage de 1 à 4 instances multiplie le débit par **3,41** et réduit la latence client médiane d'environ **75,4 %**.

Cependant, je constate que les gains de débit diminuent lorsque la concurrence augmente, tandis que les temps de réponse deviennent plus importants. Cela suggère que les différentes configurations approchent certaines limites de traitement.

Je considère donc que **la scalabilité horizontale est efficace dans les conditions testées**, mais que ses gains ne sont pas parfaitement linéaires et qu'elle implique des ressources supplémentaires.

**Verdict général :** TinyInsta bénéficie à la fois de l'ajout d'instances et de l'optimisation algorithmique. Toutefois, augmenter les ressources ne suffit pas à corriger une stratégie de requêtage inefficace.
## 4. Validité expérimentale

### 4.1 Vérification des instances sollicitées

Pour vérifier que les instances configurées avaient réellement traité des requêtes, j'ai analysé les identifiants `X-Instance` enregistrés par Locust.

J'ai ainsi confirmé l'utilisation de **1, 2 et 4 instances distinctes** pour les versions `fixed1`, `fixed2` et `fixed4`, conformément aux configurations attendues. Les parties 1 et 3 ont également été réalisées avec une seule instance par configuration.

### 4.2 Indépendance et ordre des expériences

J'ai exécuté les benchmarks séparément, en faisant varier les paramètres prévus par chaque protocole. Cependant, cela ne garantit pas que les runs soient totalement indépendants.

En effet, ils utilisaient la même infrastructure Cloud et pouvaient être influencés par des effets de cache, des connexions déjà établies ou l'état des instances.

Je n'ai pas non plus randomisé systématiquement l'ordre des expériences. Je ne peux donc pas exclure un effet d'ordre sur les résultats, d'autant que la plupart des benchmarks principaux n'ont pas été répétés.

Les différences observées entre certaines répétitions complémentaires montrent justement que les conditions d'exécution peuvent influencer les performances.

### 4.3 Part de la latence due au réseau

J'ai distingué le temps d'exécution de `get_timeline()`, mesuré côté serveur, de la latence totale observée par Locust.

Cependant, **je ne peux pas déterminer précisément la part de la latence due au réseau**. La différence entre les deux mesures inclut potentiellement les échanges réseau, mais aussi l'attente avant le traitement applicatif, le traitement HTTP et la sérialisation des réponses.

Il serait donc incorrect d'attribuer entièrement cette différence au réseau sans instrumentation supplémentaire.

### 4.4 Définition des échecs et codes HTTP

J'ai considéré comme réussies les requêtes ayant reçu une réponse HTTP `200`. Les autres réponses HTTP et les requêtes sans réponse valide ont été considérées comme des échecs.

Dans les journaux analysés, les parties 1 et 3 n'ont présenté que des réponses HTTP `200`.

En partie 2, j'ai également observé quelques valeurs `STATUS = 0`, qui signalent une absence de réponse HTTP valide et non un code HTTP réellement retourné par le serveur.

Le débit a donc été calculé uniquement à partir du nombre de réponses HTTP `200`.

### 4.5 Vérification du chemin de code exécuté

L'analyse de `get_timeline()` m'a permis d'identifier les requêtes groupées utilisant `IN` et le mécanisme de repli vers des requêtes individuelles.

La rupture de latence à **F = 30** est cohérente avec la limite documentée de Datastore. J'ai également réalisé des mesures complémentaires du coût des requêtes individuelles, qui renforcent cette explication.

Cependant, les exceptions étant interceptées sans journalisation détaillée, **je n'ai pas directement vérifié quelle branche du code était exécutée lors de chaque requête**.

L'activation du mécanisme de repli reste donc une explication fortement étayée par le code et les résultats, mais non confirmée par une trace d'exécution directe.

### 4.6 Portée des conclusions

Mes expériences restent limitées aux paramètres étudiés et à des durées relativement courtes. Le nombre de répétitions ne permet pas d'établir des intervalles de confiance fiables.

Je n'ai pas non plus étudié toutes les interactions possibles entre U, P et F, ni identifié avec certitude l'origine du second goulot d'étranglement observé sous concurrence.

Ces limites m'obligent à rester prudent lorsque je généralise les résultats à d'autres configurations ou charges de travail.

## 5. Coût de la campagne

Cette section présente les dépenses liées à mes expérimentations sur Google Cloud, comprenant les benchmarks obligatoires, les répétitions et les investigations complémentaires.

Les rapports de facturation pour octobre et novembre 2026 sont présentés ci-dessous :

![Coûts Google Cloud — Octobre 2026](cost/october_cost.png)

![Coûts Google Cloud — Novembre 2026](cost/november_cost.png)

### 5.1 Coûts Datastore et App Engine

Les opérations Datastore ont été utilisées pour générer les jeux de données (écritures) et récupérer les timelines (lectures).

J'ai estimé le coût théorique des lectures dans la section 2.1.6, mais le rapport de facturation ne présente aucun coût Datastore distinct. Cela pourrait notamment s'expliquer par les quotas gratuits, sans que je puisse le confirmer à partir de ces seules données.

La consommation provient principalement d'**App Engine**, utilisé pour héberger les différentes versions de TinyInsta.

Les benchmarks principaux duraient généralement **45 secondes**, tandis que certaines investigations complémentaires ont duré **180 secondes**, avec des mesures regroupées par intervalles de 15 secondes pour observer l'évolution des performances.

J'ai également veillé à arrêter les versions à mise à l'échelle manuelle après leur utilisation, afin de limiter les dépenses.

### 5.2 Dépenses réelles et comparaison mensuelle

D'après les rapports Google Cloud, les coûts d'utilisation sont les suivants :

| Service | Coût d'utilisation | Remises | Coût facturé |
|---|---:|---:|---:|
| App Engine | 2,78 USD | −2,78 USD | 0,00 USD |
| Artifact Registry | 0,07 USD | −0,07 USD | 0,00 USD |
| **Total** | **2,85 USD** | **−2,85 USD** | **0,00 USD** |

Pour App Engine, je peux également distinguer les dépenses mensuelles :

| Mois | Coût d'utilisation |
|---|---:|
| Octobre 2026 | 1,29 USD |
| Novembre 2026 | 1,49 USD |
| **Total** | **2,78 USD** |

Je remarque que **novembre a entraîné une consommation légèrement supérieure à octobre**, malgré un nombre de benchmarks inférieur.

Cela pourrait s'expliquer par les investigations complémentaires menées en novembre, j'ai expérimenté différentes configurations Gunicorn, comparé des instances B1 et B2 et exécuté des tests plus longs pour étudier les variations de performance.

Au total, **le coût brut d'utilisation s'élève à 2,85 USD**, entièrement compensé par les remises Google Cloud. Le **montant effectivement facturé est donc de 0,00 USD**.

Cette comparaison montre que le coût d'une campagne dépend non seulement du nombre de tests, mais aussi de leur durée et des ressources mobilisées. Elle souligne également l'intérêt d'arrêter les instances inutilisées après les expérimentations.

## Conclusion générale

Cette étude m'a permis d'évaluer la scalabilité de TinyInsta face à l'augmentation du volume de données et de la charge concurrente.

J'ai constaté que l'application conserve des performances relativement stables lorsque U et P augmentent, mais qu'un important goulot d'étranglement apparaît à partir de F = 30.

L'optimisation des requêtes Datastore a permis de réduire considérablement ce problème, avec une accélération de **×26,63 pour F = 100**, sans ajouter de ressources applicatives. J'ai également observé que l'ajout d'instances améliore la capacité de traitement sous concurrence, même si les gains ne sont pas parfaitement linéaires.

Les investigations complémentaires ont toutefois révélé un second problème de performance dont je n'ai pas encore pu identifier précisément l'origine.

Je retiens surtout que **la scalabilité ne dépend pas uniquement des ressources disponibles, mais aussi de la manière dont une application utilise ces ressources et accède à ses données**. Avant d'augmenter la capacité de l'infrastructure, il est donc essentiel de comprendre les limitations du système et d'évaluer les possibilités d'optimisation.
