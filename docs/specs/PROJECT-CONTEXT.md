# PROJECT-CONTEXT

Statut : validé (phase 0)
Date : 2026-11-17
Lien phase précédente : aucune (c'est le document transverse de phase 0)

## Stack

- **Projet** : Aethera, fork de [rathena/rathena](https://github.com/rathena/rathena) sous `bastiends/aethera`.
- **Langages** : C++ (serveurs login/char/map/web), scripts NPC (langage de script rAthena), données en YAML (`db/`) et texte (`conf/`), SQL (`sql-files/`).
- **Mode** : **Pre-renewal**. Compilé avec `--enable-prere=yes` (voir `deploy/Dockerfile`). `RENEWAL` est défini par défaut dans `src/config/renewal.hpp` mais désactivé par ce flag de configure.
- **PACKETVER** : `20250716` (client kRO patché via WARP0716/WARPGATE), configurable par `.env` (`deploy/.env.example`). Pas de structure de paquet plus récente que `20250402` dans le code actuel (vérifié par grep sur `PACKETVER_MAIN_NUM` dans `src/`) — `20250716` est donc numériquement correct mais le client réel peut envoyer des paquets non encore couverts par rAthena au-delà d'avril 2025.
- **Build** : autotools classique rAthena (`./configure && make server`), pas de CMake utilisé dans ce fork. Compilation faite à l'intérieur d'un multi-stage Dockerfile (`deploy/Dockerfile`), pas en local sur la machine hôte.
- **Déploiement** : Docker Compose (`deploy/docker-compose.yml`), 4 services (db, dbinit, login, char, map), réseau Docker dédié, MariaDB sans port publié sur l'hôte. Lancement : `cd deploy && docker compose build && docker compose up -d`, ou `bash deploy/deploy.sh` (génère `.env` si absent, puis build+up, attend que le map-server soit prêt).
- **Pas de méthode de lancement "nu" (hors Docker) documentée dans ce fork** — seul le chemin Docker est utilisé en pratique à ce jour.

## Conventions du fork (différences avec upstream rathena/rathena)

Point de divergence (merge-base avec `upstream/master`) : commit `d4b8e7b8f`. Tout ce qui suit est spécifique à Aethera, en 7 commits/PR à ce jour :

1. **`deploy/`** — Dockerfile de prod (COPY du code local, pas de `git clone` dans l'image — contrairement à `tools/docker/` côté upstream qui est explicitement marqué "non adapté à la production"), docker-compose.yml, entrypoint.sh, `conf-import/` pour les overrides de conf, `deploy.sh` pour un déploiement en une commande, `.env`/`.env.example` pour les secrets (DB_PASS/GM_PASS générés aléatoirement, jamais committés — `deploy/.env` est dans `.gitignore`).
2. **`src/custom/defines_post.hpp`** — `#undef PACKET_OBFUSCATION` : désactive l'obfuscation des paquets côté serveur (sinon il faut les clés exactes du build client, non publiées pour un client récent). Convention rAthena standard : ce fichier est le point d'extension officiel pour ce genre d'override, inclus juste après `packets.hpp`.
3. **`db/import/mob_db.yml`** — override généré (`tools/aethera/gen_mob_level_scale.py`) qui multiplie le `Level` de chaque monstre par 10, pour compenser le changement de formule de niveau effectif (`level/10`) dans `status_calc_misc`. **Ne pas éditer à la main**, régénérer depuis `db/pre-re/mob_db.yml` si la base vanilla change.
4. **`db/pre-re/job_exp.yml` et `db/pre-re/statpoint.yml`** — tables modifiées directement dans l'arbre `pre-re/` (pas un override dans `import/`) pour le cap de niveau 999 (base) / 80 (job) et la nouvelle courbe d'XP. Générées par `tools/aethera/gen_level_tables.py`, **ne pas éditer à la main**.
5. **`conf/battle/battle.conf`** — ajout direct des clés `hit_ratio_base/exponent/min/max` (nouvelle formule de toucher). C'est un fichier stock rAthena modifié directement (pas un override `conf/import/`), car ce sont de nouvelles clés de config ajoutées en même temps que le code C++ qui les consomme (`src/map/battle.cpp`), pas un changement de valeur par défaut d'une clé existante.
6. **`deploy/conf-import/battle_conf.txt`** — c'est ici (pas dans les fichiers stock `conf/battle/*.conf`) que vivent tous les réglages de rates/caps/valeurs par défaut propres au serveur (rates XP/items, `max_aspd`, `max_lv`, `max_*_parameter`). Convention adoptée : un changement de **valeur par défaut d'une clé existante** passe par `deploy/conf-import/`, un changement de **code + nouvelle(s) clé(s)** passe par le fichier stock correspondant dans `conf/battle/`.
7. **`src/map/battle.cpp` / `battle.hpp`** — formule de toucher ratio-based (`is_attack_hitting`), scoped à cette seule fonction (pas encore étendue à `battle_calc_misc_attack` ni aux résistances/vol, prévus comme étapes séparées de la roadmap gameplay).
8. **`src/map/status.cpp`** — niveau effectif (`level/10`) pour HIT/FLEE dans `status_calc_misc`, partagé par tous les types de bloc (PC, MOB, HOM, MER, ELEM, NPC). **Dette connue** : homonculus/mercenaire/élémental/familier ne sont pas compensés par un scaling x10 comme les mobs (hors scope de la demande initiale, leur niveau effectif sera donc lu bas tant que ce n'est pas traité).
9. **`src/map/map.hpp`** — `MAX_LEVEL` 275 → 999.
10. **`tools/aethera/`** — scripts générateurs Python (`gen_mob_level_scale.py`, `gen_level_tables.py`), committés pour reproductibilité si la base vanilla upstream change.
11. **`CLAUDE.md`** (racine) — ce mode de travail spec-driven, adopté à partir de maintenant. Les 7 PR ci-dessus ont été faites *avant* son adoption, donc sans les documents de phases — elles restent telles quelles, pas de reprise rétroactive prévue sauf décision contraire.

## Conventions de workflow Git

- Branche par sujet, PR systématique contre `bastiends/aethera` (**jamais** `rathena/rathena` — piège vécu : `gh pr create` sans `--repo` cible le dépôt parent par défaut sur un fork, PR fermée immédiatement la fois où c'est arrivé). Toujours passer `--repo bastiends/aethera` explicitement à `gh pr create`/`gh pr merge`/`gh pr view`.
- Merge en squash, branche supprimée après merge.
- Préfixes de branche observés jusqu'ici : `setup/`, `fix/`, `tune/`, `feature/`, `quickfix/`.
- Un changement de conf qui ne touche que `deploy/conf-import/*.txt` ou `deploy/.env.example` ne nécessite pas de rebuild Docker (monté en volume, recopié par `entrypoint.sh` au démarrage du conteneur) — un `docker compose restart login char map` suffit. Un changement de code C++ ou de fichier `db/`/`conf/` stock (copiés dans l'image par `COPY .`) nécessite `docker compose build` puis `up -d`.
- Avant tout merge/déploiement d'un changement de code, vérifier que `docker compose build` passe (pas de simple relecture).

## Zones sensibles

- **`status_calc_misc`** (`src/map/status.cpp`) est partagée par PC/MOB/HOM/MER/ELEM/NPC — toute modif a un rayon d'effet large, bien vérifier l'impact sur chaque type de bloc.
- **`job_exp.yml`** définit 11 groupes (2 pour BaseExp, 9 pour JobExp) avec des listes de jobs qui se chevauchent différemment pour les deux dimensions — un job donné appartient à un groupe BaseExp et un groupe JobExp distincts. Facile de casser la partition en éditant à la main.
- **Obfuscation des paquets désactivée** (`src/custom/defines_post.hpp`) — toute réactivation nécessiterait de retrouver les clés exactes du client 2025-07-16, non trivial.
- **`MAX_LEVEL`** dimensionne plusieurs tableaux statiques (`pc.hpp` : `base_exp[MAX_LEVEL]`, `job_exp[MAX_LEVEL]`, `rate[MAX_LEVEL*2-1]`) — un changement ultérieur doit revérifier qu'aucun champ narrow (uint8...) ne stocke un niveau quelque part (vérifié : `base_level`/`job_level` sont `uint32`, `mob->lv` est `uint16`, pas de risque de troncature à 999).

## Roadmap gameplay (contexte, pas encore en spec-driven)

Discutée en amont de l'adoption de CLAUDE.md, implémentée hors process pour les points 1 et 2 :
1. ✅ Formule de toucher ratio-based (`is_attack_hitting` uniquement)
2. ✅ Niveau effectif (level/10) pour HIT/FLEE, scaling mob x10 — résistances et vol explicitement reportés aux points 3 et 6 (évite du travail jetable, ces formules seront réécrites entièrement)
3. ⬜ Résistance aux statuts ratio-based (`status_get_sc_def`)
4. ⬜ DEF/MDEF dure plafonnée
5. ⬜ Perfect dodge / crit shield ratio-based
6. ⬜ Strip/Divest/Steal ratio-based
7. ⬜ Cap ASPD par classe/buff (actuellement : cap global 193 via conf, pas encore de système par classe)
8. ⬜ Level 999 : tables adaptées (fait), cap de stats client à vérifier

## Éléments non déterminés

- Pas de vérification faite du rendu client au-delà d'ASPD 190 (mentionné comme risque dans la roadmap d'origine, point 7).
- Pas de confirmation que le cap de stats (`max_*_parameter: 250`) s'affiche correctement côté client au-delà de ce que l'UI attend historiquement (certains clients plafonnent l'affichage à 255 ou moins).
- Pas de script de migration SQL pour les changements de cap/XP faits à ce jour — ils n'affectent que des tables de référence (YAML), pas le schéma ou les données de comptes/personnages existants, donc aucune migration n'était nécessaire jusqu'ici. À surveiller pour une future feature qui toucherait réellement le schéma.
- Pas de suite de tests automatisés identifiée dans le dépôt pour le gameplay serveur (CI upstream = builds de compilation uniquement, voir `.github/workflows/`). La stratégie de test en phase 3 devra donc s'appuyer sur build + vérification en jeu/commandes GM, pas sur une suite existante.
