# README — Comprendre le module *Cosmic Data* (Pydantic)

> Guide de **compréhension**, pas de solution. Les exemples ici utilisent des
> livres, des capteurs, des plages de dates — **jamais** les stations, aliens ou
> équipages des exos. À toi de faire le transfert. Si tu recopies, tu te fais
> démonter en soutenance ; si tu comprends, tu défends chaque ligne.

Testé sur **Pydantic 2.13 / Python 3.12**. Le sujet impose Pydantic **2.x**,
`flake8`, `mypy`, annotations de type partout, et gestion d'exceptions.

---

## 0. Le problème que Pydantic résout (commence par ça)

En C, quand tu reçois des données externes (un fichier, un packet réseau, une
saisie), tu fais quoi ? Tu déclares une `struct`, puis tu écris **à la main** une
fonction de validation que tu dois penser à appeler partout :

```c
typedef struct { char id[11]; int crew_size; double power; } t_station;

int validate_station(t_station *s) {
    if (strlen(s->id) < 3 || strlen(s->id) > 10) return -1;
    if (s->crew_size < 1 || s->crew_size > 20)   return -1;
    if (s->power < 0.0 || s->power > 100.0)      return -1;
    return 0; // et tu pries pour ne jamais oublier l'appel
}
```

Le drame : la `struct` (la **forme**) et le `validate()` (les **règles**) sont
deux choses séparées. Rien ne t'oblige à les garder synchronisées, et un oubli
d'appel = données corrompues silencieusement.

**Pydantic fusionne les deux.** Tu déclares la forme *avec* les règles, et la
validation se déclenche **automatiquement à chaque construction d'objet**.
Impossible de fabriquer un objet invalide : soit il est correct, soit
l'instanciation lève une exception.

> 🦀 *Fait à retenir pour ta soutenance :* le cœur de Pydantic v2
> (`pydantic-core`) est écrit en **Rust**, pas en Python. C'est pour ça que la v2
> est ~5–20× plus rapide que la v1. Quand tu écris `class Book(BaseModel)`,
> Python génère un « core schema » qui est compilé côté Rust. Tu manipules du
> Python, mais la validation tourne en natif — exactement le genre de
> compromis « ergonomie Python / perf natif » qui t'intéresse.

---

## 1. `BaseModel` — la brique de base (ex0)

Un modèle = une classe qui hérite de `BaseModel`. Les champs sont des
**attributs annotés** (les annotations ne sont pas décoratives ici : elles
*sont* les règles de type).

```python
from pydantic import BaseModel


class Book(BaseModel):
    title: str
    year: int
    price: float
```

```python
b = Book(title="Dune", year=1965, price=12.5)
print(b.title)   # Dune
print(b)         # title='Dune' year=1965 price=12.5
```

**Parallèle C :** `class Book(BaseModel)` ≈ `struct Book` **+** un
`validate_book()` fusionné et appelé pour toi dans le « constructeur ».

**Ce qu'il faut comprendre, pas mémoriser :**

- Les `title: str` ne sont pas de simples hints. Pydantic les lit à la
  construction de la classe pour bâtir son schéma de validation.
- Un champ **sans valeur par défaut est requis**. L'oublier lève une erreur.

---

## 2. La coercion de type — le « Think About » du sujet

Le sujet te demande : *« que se passe-t-il quand tu passes une string à un champ
datetime ? »*. Réponse : par défaut, Pydantic **tente de convertir** (coerce)
vers le type déclaré au lieu de refuser bêtement.

```python
from datetime import datetime


class Book(BaseModel):
    year: int
    published_at: datetime


b = Book(year="1965", published_at="1965-08-01T00:00:00")
print(type(b.year).__name__)          # int   -> "1965" converti en 1965
print(type(b.published_at).__name__)  # datetime -> string ISO parsée
```

**Parallèle C :** c'est comme `atoi()` / `strtod()` / `strptime()`… mais
automatique **et** sûr : si la conversion est impossible, tu obtiens une
exception structurée, pas un comportement indéfini.

### Le piège à connaître (et à citer en défense)

La coercion est **pratique mais dangereuse**. Le `bool` en est l'exemple parfait :

```python
Flag(active="yes")   # True
Flag(active=0)       # False
Flag(active="true")  # True
Flag(active="peut-etre")
# -> ValidationError: Input should be a valid boolean, unable to interpret input
```

**Coût de ce design (à nommer toi-même, sans qu'on te le demande) :** la coercion
permissive t'évite du code de parsing, mais elle peut **masquer un bug en amont**
(un `"1"` qui aurait dû être un vrai booléen). Si tu veux zéro conversion
implicite, Pydantic a un `strict=True` — le mentionner en soutenance montre que
tu connais le compromis, pas juste la fonctionnalité.

---

## 3. `Field(...)` — les contraintes (ex0)

`Field` sert à attacher des **contraintes** à un champ (au-delà du type). C'est
littéralement tes `if (x < min || x > max) return -1;` du C, mais déclaratifs.

```python
from pydantic import BaseModel, Field


class Book(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=1400, le=2100)     # ge = >=, le = <=
    price: float = Field(gt=0.0)            # gt = >  (strictement)
    pages: int = Field(default=100, ge=1)  # défaut + contrainte
```

Le mémo des opérateurs (à ne pas confondre) :

| Field       | Signifie | Équivalent C          |
|-------------|----------|-----------------------|
| `gt=0`      | `> 0`    | `if (x <= 0) fail`    |
| `ge=0`      | `>= 0`   | `if (x < 0) fail`     |
| `lt=100`    | `< 100`  | `if (x >= 100) fail`  |
| `le=100`    | `<= 100` | `if (x > 100) fail`   |
| `min_length`/`max_length` | longueur string/list | `strlen()` bornée |

Quand une contrainte casse, le message est **déjà en anglais et lisible** —
c'est exactement ce que le sujet attend dans l'*Expected validation error* :

```python
Book(title="x", year=3000, price=12.5)
# Input should be less than or equal to 2100   <- pour year le=2100
```

> 💡 Le sujet ex0 attend le message `Input should be less than or equal to 20`.
> Tu vois d'où il vient : c'est le message natif d'une contrainte `le=20`. Tu
> n'as **rien à écrire** pour l'obtenir, juste à laisser l'exception remonter.

**`Field` vs `min_length` dans l'annotation :** pour `str`/`list`, préfère les
paramètres de `Field`. Retiens que `Field` est le point central pour : bornes,
valeur par défaut, `description=`, alias.

---

## 4. Optionnel et valeurs par défaut

Trois cas à ne pas mélanger :

```python
from typing import Optional


class Book(BaseModel):
    title: str                              # REQUIS
    in_stock: bool = True                   # optionnel, défaut = True
    notes: Optional[str] = Field(default=None, max_length=200)  # peut être None
```

- **Requis** : pas de `=` → doit être fourni, sinon `ValidationError`.
- **Défaut** : `= valeur` → utilisé si absent.
- **`Optional[str]`** = `str | None` → **autorise `None`** comme valeur.

**Parallèle C :** `Optional[str] = None` ≈ un pointeur qui a le droit d'être
`NULL`. `notes: str` (requis) ≈ une valeur qui **doit** exister.

⚠️ Piège classique : `Optional[str]` ne rend pas le champ optionnel *par magie*.
Il autorise juste `None` comme **type**. Pour qu'il soit vraiment omissible, il
faut **aussi** un défaut (`= None`). Type ≠ obligation.

---

## 5. Les Enums (ex1, ex2)

Une `Enum` = un ensemble **fermé** de valeurs autorisées. En C tu ferais un
`enum { RADIO, VISUAL };` mais tu perds le lien avec une string lisible.
Ici on hérite de `str, Enum` pour avoir les deux : contrainte forte **et**
valeur textuelle.

```python
from enum import Enum


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(BaseModel):
    priority: Priority


Task(priority="high")     # OK -> Priority.HIGH
Task(priority="urgent")   # ValidationError : pas dans l'enum
```

**Pourquoi `str, Enum` et pas juste `Enum` ?** En héritant de `str`, l'objet se
compare et s'affiche comme une string (`"high"`), ce qui simplifie
l'affichage et la sérialisation. Le savoir = un point facile en défense.

**Transfert exos :** ex1 veut `radio / visual / physical / telepathic`, ex2 veut
`cadet / officer / lieutenant / captain / commander`. Même mécanique, à toi de
l'appliquer.

---

## 6. `@model_validator(mode="after")` — les règles métier (ex1, ex2)

`Field` valide **un champ isolé**. Mais certaines règles dépendent de
**plusieurs champs ensemble** (« si le type est X alors le champ Y doit… »).
Ça, `Field` ne sait pas le faire. C'est le rôle du `model_validator`.

**Parallèle C :** c'est ta fonction de cohérence qu'on appelle **à la fin**,
une fois que chaque champ a passé son propre check, pour valider les relations
croisées.

```python
from pydantic import BaseModel, model_validator
from typing import Self


class DateRange(BaseModel):
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def check_order(self) -> Self:
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self          # <-- OBLIGATOIRE en mode="after"
```

```python
DateRange(start="2024-12-31", end="2024-01-01")
# ValidationError -> "Value error, end must be after start"
```

**Les 4 points à ne jamais rater :**

1. `mode="after"` = ça tourne **après** la validation des champs individuels.
   Donc dans le validator, `self.start` est **déjà** un `datetime` propre.
2. Tu **lèves `ValueError`** (ou `raise ValueError(...)`) pour signaler une
   règle violée. Pydantic l'emballe automatiquement dans un `ValidationError`.
   → Parallèle C : `raise ValueError` ≈ ton `return -1` + `errno`, mais typé.
3. Tu **retournes `self`** à la fin. L'oublier est LE bug classique du module.
4. C'est `@model_validator`, **pas** `@validator` (déprécié v1). Le sujet insiste.

**Transfert ex1** (à écrire toi-même, je te donne juste la *forme* du
raisonnement, pas le code) : « si `contact_type == physical` et
`is_verified == False` → lève une erreur ». Même patron que `check_order`
ci-dessus : un `if` sur une combinaison de champs, un `raise ValueError`, un
`return self`.

---

## 7. Modèles imbriqués (ex2)

Un modèle peut contenir… d'autres modèles. Une `list[CrewMember]` dans un
`SpaceMission`, par exemple.

**Parallèle C :** une `struct` qui contient un tableau de `struct`. Sauf qu'ici,
la validation **descend récursivement** toute seule : valider le parent valide
chaque enfant.

```python
class Author(BaseModel):
    name: str = Field(min_length=2)


class Library(BaseModel):
    name: str
    authors: list[Author] = Field(min_length=1)   # au moins 1 auteur
```

```python
# Pydantic construit et valide chaque Author automatiquement :
lib = Library(name="42", authors=[{"name": "Ada"}, {"name": "Alan"}])

# Si UN enfant est invalide, TOUT le parent échoue :
Library(name="42", authors=[{"name": "X"}])   # name trop court -> ValidationError
```

C'est la réponse au 2e « Think About » du sujet : *quand un enfant échoue, le
parent échoue*, et l'erreur te dit **précisément** quel enfant et quel champ
(`authors -> 0 -> name`). La localisation de l'erreur est gratuite — encore un
truc que tu écrirais à la main en C.

---

## 8. Gérer `ValidationError` proprement (exigence du sujet)

Le sujet demande que « la gestion d'exceptions protège les flux de données ».
Concrètement : dans ta `main()`, quand tu **montres volontairement** un cas
invalide, tu dois **attraper** l'erreur, pas laisser le programme crasher.

```python
from pydantic import ValidationError

try:
    Book(title="", year=3000, price=-1)
except ValidationError as e:
    print("Validation failed:")
    print(e)              # message lisible, multi-erreurs
    # ou e.errors() pour une structure exploitable (liste de dicts)
```

Point de compréhension important : Pydantic **collecte toutes les erreurs**
d'un coup, pas seulement la première. En C tu t'arrêtes au premier `return -1` ;
ici tu reçois le rapport complet. Utile, mais ça a un **coût** : Pydantic
continue la validation même après une faute → à mentionner si on te parle de
perf sur de gros volumes.

---

## 9. Le contexte outillage (ne néglige pas, ça tombe en défense)

| Outil | Rôle | Le *pourquoi* |
| ------- | ------ | --------------- |
| **venv** | environnement isolé | tes deps du projet ne polluent pas le système, et inversement. `sys.prefix != sys.base_prefix` quand il est actif. |
| **pip** | installe Pydantic | `pip install pydantic` dans le venv activé |
| **flake8** | style (PEP8) | lisibilité imposée ; lance-le **toi-même** avant de committer |
| **mypy** | vérifie les types | tes annotations doivent être cohérentes ; le sujet l'exige explicitement |
| **type annotations** | `x: int` partout | double emploi : Pydantic s'en sert pour valider, mypy pour vérifier statiquement |

> Rappel de ta config perso : lance `flake8` **et** `mypy` avant de dire
> « c'est fini ». Le `mypy` est celui que tu oublies le plus souvent.

---

## 10. Checklist de soutenance (nomme les *coûts*, pas juste les choix)

Être capable de défendre = pouvoir répondre à ça sans hésiter :

- **« Pourquoi `BaseModel` plutôt qu'une dataclass + validations manuelles ? »**
  → validation automatique et centralisée ; coût : dépendance externe + un peu
  de « magie » qui cache le flux d'exécution.
- **« Que fait Pydantic si je passe `"1965"` à un `int` ? »**
  → coercion vers `1965`. Coût : peut masquer un bug de type en amont
  (mentionne `strict=True` comme parade).
- **« `Field(le=20)` vs un `if` dans un validator, différence ? »**
  → `Field` = contrainte sur un champ isolé, message natif gratuit ;
  `model_validator` = règle inter-champs, à réserver à ce cas.
- **« Pourquoi `mode="after"` et pourquoi `return self` ? »**
  → `after` = les champs sont déjà typés/validés quand ton code tourne ;
  `return self` car le validator doit rendre l'instance (sinon `None`).
- **« Enum : pourquoi `str, Enum` ? »**
  → contrainte fermée **+** valeur textuelle lisible/sérialisable.
- **« Un enfant invalide dans une liste imbriquée, il se passe quoi ? »**
  → tout le parent échoue, avec le chemin exact de l'erreur.

---

## 11. Pièges spécifiques venant de ton réflexe C

- `if x == False:` → écris `if not x:`. Pareil, `!x` n'existe pas → `not x`.
- Pas de `;` en fin de ligne, pas de parenthèses autour du `if`, `:` obligatoire.
- `Optional[str]` **n'implique pas** un défaut — type ≠ champ optionnel (§4).
- Ne réécris pas un parsing « caractère par caractère » façon C : Pydantic fait
  déjà le boulot. Réflexe Python = **EAFP** (tente + `except`), pas LBYL.
- `Self` comme type de retour de validator : `from typing import Self`
  (Python 3.11+) ; sur 3.10, `-> "TonModele"` en string marche aussi.

---

---

# 📚 Référence doc officielle (approfondissement)

> Cette partie va plus loin que le strict nécessaire des exos. C'est là que tu
> gagnes les points « bonus » en soutenance : montrer que tu connais *les
> alternatives* à ce que tu as choisi. Sources : doc officielle Pydantic
> (liens en fin de section).

## 12. Le zoo complet des validators

Le sujet ne te demande que `@model_validator(mode="after")`, mais la doc en
recense **deux familles** et plusieurs modes. Les connaître = pouvoir justifier
*pourquoi tu n'as pas pris les autres*.

| Décorateur | Portée | Modes disponibles |
|------------|--------|-------------------|
| `@field_validator("champ")` | **un** champ | `before`, `after`, `plain`, `wrap` |
| `@model_validator` | **tout** le modèle | `before`, `after`, `wrap` |

Les deux modes qui comptent pour toi :

- **`mode="before"`** : tourne **avant** la validation interne. Reçoit la donnée
  **brute** (souvent un `dict`), donc pas encore typée. C'est une **classmethod**
  qui prend `data: Any` et retourne `data`.
- **`mode="after"`** : tourne **après** que tout le modèle a été validé. C'est une
  **méthode d'instance** — signature `(self) -> Self` — que la doc décrit comme un
  *« post-initialization hook »*. La doc **insiste** : tu dois **retourner
  l'instance validée** (`return self`).

```python
from typing import Self
from pydantic import BaseModel, model_validator


class SignUp(BaseModel):
    password: str
    password_repeat: str

    @model_validator(mode="after")
    def passwords_match(self) -> Self:
        if self.password != self.password_repeat:
            raise ValueError("passwords do not match")
        return self
```

**LA question de soutenance** (elle revient souvent) : *« pourquoi
`model_validator(mode="after")` plutôt qu'un `field_validator` pour une règle
qui touche plusieurs champs ? »*
Réponse doc : un `@field_validator` ne voit **que son propre champ**. Pour lire un
autre champ il faudrait passer par `ValidationInfo.data` (un dict field→valeur),
ce qui est fragile car l'ordre de validation compte. Le `model_validator(after)`,
lui, reçoit l'objet **entier déjà validé** → tous les champs sont accessibles et
déjà typés. C'est exactement le cas des règles inter-champs des exos.

Deux détails doc utiles à lâcher au bon moment :

- Tu peux lever `ValueError` **ou** `AssertionError` (donc un `assert` marche
  aussi) — Pydantic les emballe toutes en `ValidationError`.
- Si un champ échoue à sa validation de base, l'`after` validator de ce champ
  **n'est pas appelé** (pas de perte de temps sur des données déjà invalides).

## 13. Coercion « lax » vs « strict » (le vrai nom du piège du §2)

La doc nomme les deux modes de conversion :

- **lax** (défaut) : Pydantic **tente de convertir** (`"123"` → `123`). Pratique
  pour tout ce qui arrive en texte : variables d'env, paramètres d'URL, saisie
  utilisateur, CSV…
- **strict** : Pydantic **refuse** de convertir et lève une erreur si le type
  n'est pas exact.

On peut activer strict à **trois niveaux** :

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    name: str = Field(strict=True)   # 1) au niveau du champ
    age: int = Field(strict=False)   #    (lax explicite)

# 2) au niveau d'un appel de validation :
User.model_validate({"name": "John", "age": "42"}, strict=True)
# 3) au niveau du modèle entier via model_config (ConfigDict(strict=True))
```

Le message change selon le mode, et c'est un **excellent** point de défense :

| Mode | Entrée `"123"` sur un `int` | Message |
|------|-----------------------------|---------|
| lax | acceptée → `123` | (pas d'erreur) |
| strict | refusée | `Input should be a valid integer` (`type=int_type`) |

> 🔎 Le `bool` lax accepte une **liste fermée et documentée** de valeurs :
> `True/False`, `0/1`, et les strings (après `lower()`) `'0','off','f','false',
> 'n','no'` / `'1','on','t','true','y','yes'`. Tout le reste lève. Ça explique
> pile le comportement qu'on a testé au §2 — ce n'est pas magique, c'est spécifié.

Pour les exos tu restes en **lax** (le sujet veut la coercion string→datetime).
Mais savoir que `strict` existe, et *pourquoi tu ne l'utilises pas ici*, c'est la
différence entre réciter et comprendre.

## 14. Deux pièges de syntaxe que la doc pointe explicitement

**a) `champ: type = Field(...)` ressemble à un défaut, mais ne l'est pas.**
La doc prévient : cette forme peut tromper. Un `Field(...)` avec des contraintes
mais **sans `default=`** laisse le champ **requis**. Ne confonds pas :

```python
a: int = Field(ge=0)                 # REQUIS (le "=" ne donne PAS de défaut)
b: int = Field(default=0, ge=0)      # optionnel, défaut = 0
```

**b) Le pattern `Annotated` — la forme que mypy préfère.**
Tu peux mettre les contraintes *dans* l'annotation. Pour les type-checkers, le
champ reste un `str`/`int` normal, mais Pydantic lit les métadonnées :

```python
from typing import Annotated
from pydantic import Field

class Model(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
```

Les deux formes (`= Field(...)` et `Annotated[..., Field(...)]`) sont valides.
`Annotated` est souvent plus propre côté `mypy` et évite l'ambiguïté du (a).
Choisis-en une et sois cohérente — et sache défendre ton choix.

## 15. Méthodes du modèle utiles (au-delà de la construction)

Ta construction `Book(...)` n'est qu'une porte d'entrée. La doc expose des
méthodes que tu croiseras — et le sujet parle d'**importer du JSON/CSV** depuis
le dossier `tools`, donc `model_validate` est directement pertinent :

| Méthode | Rôle | Quand |
| --------- | ------ | ------- |
| `Model.model_validate(dict)` | construit + valide depuis un `dict` | tu charges des données déjà parsées |
| `Model.model_validate_json(str)` | construit + valide depuis du **JSON brut** | tu lis un `.json` du dossier `tools` |
| `obj.model_dump()` | → `dict` Python | export / affichage structuré |
| `obj.model_dump_json()` | → string JSON | sérialisation |
| `Model.model_fields` | introspection des champs déclarés | comprendre ce que Pydantic a bâti |
| `Model.model_json_schema()` | génère le **JSON Schema** du modèle | doc/API auto |

> 🧠 Lien avec ce que tu lisais dans la doc `BaseModel` : `model_json_schema()`
> et `model_fields` sont la partie *visible* de la « class metadata » que Pydantic
> construit sous le capot (core schema compilé en Rust, cf. §0). Tu n'as pas
> besoin de toucher au `__pydantic_core_schema__` pour ce module — juste de
> savoir qu'il existe et qu'il *est* la raison pour laquelle la validation est
> rapide.

### Liens officiels (à garder sous la main)

- Models : <https://docs.pydantic.dev/latest/concepts/models/>
- Fields (contraintes, `Field`, `strict`) : <https://docs.pydantic.dev/latest/concepts/fields/>
- Validators (`field_validator`, `model_validator`, modes) : <https://docs.pydantic.dev/latest/concepts/validators/>
- Strict Mode : <https://docs.pydantic.dev/latest/concepts/strict_mode/>
- Conversion Table (lax vs strict par type) : <https://docs.pydantic.dev/latest/concepts/conversion_table/>
- Types standard (règles exactes bool, str, datetime…) : <https://docs.pydantic.dev/latest/api/standard_library_types/>

---

## Ordre de travail conseillé

1. **ex0** — fais tourner un `BaseModel` + `Field` + un `datetime` + une `main()`
   qui montre un cas valide puis attrape un cas invalide. Objectif : voir la
   coercion et les messages natifs de tes propres yeux.
2. **ex1** — ajoute l'`Enum` puis **un** `model_validator` avec **une** règle,
   teste-la, puis ajoute les suivantes une par une. N'écris pas les 4 règles
   d'un coup.
3. **ex2** — modèles imbriqués + validator sur la liste. Réutilise tout ce qui
   précède.

À chaque étape : `flake8` ✔ puis `mypy` ✔ avant de passer à la suite. Et surtout,
avant de committer un exo : ferme le fichier et **ré-explique-toi chaque ligne à
voix haute**. Si tu bloques sur une, c'est là qu'on te coincera.

---

## Questions de review — ex0

Les réponses ci-dessous sont volontairement courtes. En review, reformule-les
avec tes propres mots et appuie-toi sur une ligne précise de ton programme.

### Pourquoi `SpaceStation` hérite-t-elle de `BaseModel` ?

`BaseModel` transforme la classe en modèle Pydantic. Lorsqu'une
`SpaceStation` est construite, Pydantic contrôle automatiquement ses types et
ses contraintes. Sans `BaseModel`, les annotations seules ne valident pas les
données à l'exécution.

### À quoi sert `Field` ?

`Field` ajoute des contraintes au type d'un champ :

```python
crew_size: int = Field(ge=1, le=20)
```

`int` définit le type attendu, `ge=1` signifie `>= 1` et `le=20` signifie
`<= 20`.

### Pourquoi la borne basse de `crew_size` est-elle 1 et non 0 ?

Le sujet demande entre 1 et 20 personnes. Avec `ge=0`, une station sans
équipage serait acceptée, même si le code passe `flake8` et `mypy`. Ces outils
ne peuvent pas deviner la règle métier écrite dans le sujet.

Les cas frontières à tester sont :

| Valeur | Résultat attendu |
| -------- | ------------------ |
| `0` | invalide |
| `1` | valide |
| `20` | valide |
| `21` | invalide |

### Quand la validation est-elle exécutée ?

Elle se produit automatiquement à la construction :

```python
station = SpaceStation(...)
```

Il n'y a pas de fonction `validate_station()` séparée à appeler. Si une donnée
est invalide, Pydantic lève une `ValidationError` et l'objet n'est pas créé.

### Pourquoi utiliser `try` et `except ValidationError` ?

Sans `except`, une donnée invalide arrête le programme. Intercepter
`ValidationError` permet d'afficher l'erreur proprement et de protéger la suite
du traitement :

```python
try:
    station = SpaceStation(...)
except ValidationError as error:
    print(error)
```

### Comment afficher uniquement le message natif de Pydantic ?

```python
except ValidationError as error:
    print(error.errors()[0]["msg"])
```

`error.errors()` renvoie une liste de dictionnaires structurés. `[0]`
sélectionne la première erreur et `["msg"]` son message. Pour `crew_size=21`
avec `le=20`, Pydantic produit lui-même :

```text
Input should be less than or equal to 20
```

Il ne faut pas écrire ce texte directement avec `print`, car il ne
représenterait alors pas nécessairement l'erreur réellement rencontrée.

### Comment afficher toutes les erreurs et les champs concernés ?

```python
except ValidationError as error:
    for item in error.errors():
        field = item["loc"][0]
        message = item["msg"]
        print(f"{field}: {message}")
```

Pydantic peut détecter plusieurs champs invalides pendant une même
construction.

### Quelle différence existe-t-il entre le type et les contraintes ?

Dans cet exemple :

```python
station_id: str = Field(min_length=3, max_length=10)
```

`str` impose le type attendu. `min_length` et `max_length` limitent sa
longueur. Une chaîne de deux caractères possède le bon type, mais reste
invalide.

### Pourquoi `last_maintenance` utilise-t-il `datetime` ?

Le modèle doit conserver une date et une heure structurées plutôt qu'un texte
arbitraire :

```python
last_maintenance: datetime
```

En mode non strict, Pydantic peut convertir une chaîne ISO valide comme
`"2026-07-01T12:00:00"` en objet `datetime`. Une chaîne qui ne représente pas
une date valide déclenche une `ValidationError`.

### Qu'est-ce que la coercition automatique ?

Pydantic essaie par défaut de convertir certaines valeurs compatibles vers le
type annoncé. Par exemple, une chaîne ISO peut devenir un `datetime`. C'est
pratique pour traiter des données externes, mais cela peut aussi masquer une
erreur en amont. Le mode strict existe pour désactiver ces conversions, mais
il n'est pas demandé dans l'ex0.

### Pourquoi écrire `str | None` pour `notes` ?

```python
notes: str | None = Field(default=None, max_length=200)
```

`str | None` autorise soit une chaîne, soit `None`. `default=None` permet
d'omettre le champ à la construction. Sans valeur par défaut, le champ
resterait requis même si son type accepte `None`.

Cette syntaxe est disponible depuis Python 3.10 et évite l'import de
`Optional` depuis `typing`.

### Pourquoi `is_operational` peut-il être omis ?

```python
is_operational: bool = True
```

Le champ a une valeur par défaut. Si aucune valeur n'est fournie, Pydantic
utilise `True`.

### Pourquoi transformer le booléen pour l'affichage ?

Le modèle conserve un booléen, tandis que la sortie demandée doit être lisible :

```python
status = "Operational" if station.is_operational else "Offline"
```

La donnée stockée reste adaptée aux traitements logiques, et sa présentation
est adaptée à l'utilisateur.

### Quelle différence avec une validation manuelle en C ?

En C, la structure et la fonction de validation sont séparées, donc on peut
oublier d'appeler la fonction ou désynchroniser ses règles. Avec Pydantic, les
règles sont déclarées avec le modèle et appliquées automatiquement à chaque
construction.

### `flake8` ou `mypy` peuvent-ils garantir le respect du sujet ?

Non. `flake8` contrôle principalement le style et certaines erreurs de code.
`mypy` vérifie les types statiques. Ils peuvent accepter
`crew_size: int = Field(ge=0, le=20)`, alors que la borne `0` contredit le
sujet. La lecture de la spécification et les tests de frontières restent
indispensables.
