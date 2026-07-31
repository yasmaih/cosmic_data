# README - Mes notes Pydantic pour Cosmic Data

Ce README est ma fiche de comprehension pour les exercices Pydantic du module
Cosmic Data. Je ne veux pas juste avoir un code qui passe: je veux pouvoir
expliquer en soutenance pourquoi j'ai choisi `BaseModel`, `Field`, les `Enum`,
les validators et les `try/except`.

Le sujet demande Pydantic 2.x, des annotations de type, `flake8`, `mypy`, et une
gestion propre des erreurs de validation.

---

## 1. Ce que Pydantic fait pour moi

En Python normal, les annotations ne valident rien a l'execution:

```python
class Book:
    title: str
    year: int
```

Ca dit ce que je veux, mais Python ne bloque pas automatiquement les mauvaises
donnees.

Avec Pydantic, mon modele herite de `BaseModel`:

```python
from pydantic import BaseModel


class Book(BaseModel):
    title: str
    year: int
```

Quand je fais:

```python
book = Book(title="Dune", year=1965)
```

Pydantic construit l'objet et valide les champs. Si une valeur est invalide,
Pydantic leve une `ValidationError` et l'objet n'est pas cree.

Ce que je dois retenir:

- `BaseModel` transforme ma classe en modele valide automatiquement.
- Un champ sans valeur par defaut est obligatoire.
- Les annotations servent vraiment a Pydantic, pas seulement a `mypy`.
- La validation se fait au moment ou je cree l'objet.

En C, je penserais a une `struct` plus une fonction `validate_struct()`. Avec
Pydantic, les deux sont lies.

---

## 2. Les types et la coercition

Pydantic essaie souvent de convertir les valeurs au bon type. Par exemple:

```python
from datetime import datetime
from pydantic import BaseModel


class Event(BaseModel):
    year: int
    date: datetime


event = Event(year="2024", date="2024-01-01T10:30:00")
```

Ici, Pydantic peut convertir:

- `"2024"` en `int`
- `"2024-01-01T10:30:00"` en `datetime`

Ce mode est pratique parce que les donnees externes arrivent souvent en texte:
JSON, CSV, formulaire, variable d'environnement.

Mais je dois connaitre le risque: si Pydantic convertit trop gentiment, il peut
cacher un bug. Par exemple, une string qui arrive alors que je pensais recevoir
un vrai `int`.

Si je veux refuser les conversions automatiques, il existe le mode strict:

```python
from pydantic import Field

age: int = Field(strict=True)
```

Pour les exercices, je garde le comportement normal de Pydantic, sauf si le
sujet demande explicitement autre chose.

---

## 3. `Field` pour les contraintes

Le type dit la famille de valeur. `Field` ajoute les limites exactes.

```python
from pydantic import BaseModel, Field


class Book(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=1400, le=2100)
    rating: float = Field(ge=0.0, le=10.0)
```

Les options que j'utilise le plus:

| Option | Signification |
| --- | --- |
| `gt=0` | strictement superieur a 0 |
| `ge=0` | superieur ou egal a 0 |
| `lt=10` | strictement inferieur a 10 |
| `le=10` | inferieur ou egal a 10 |
| `min_length=3` | longueur minimale |
| `max_length=50` | longueur maximale |
| `pattern=r"..."` | regex obligatoire |
| `default=...` | valeur par defaut |
| `default_factory=...` | fonction qui cree la valeur par defaut |

Exemples importants:

```python
score: float = Field(ge=0.0, le=10.0)
duration_minutes: int = Field(ge=1, le=1440)
name: str = Field(min_length=3, max_length=100)
```

Je dois faire attention a `ge` et `gt`:

- `ge=1` accepte `1`
- `gt=1` refuse `1`

Pareil pour `le` et `lt`.

---

## 4. Champs requis, optionnels et valeurs par defaut

Ces trois lignes ne veulent pas dire la meme chose:

```python
class User(BaseModel):
    name: str
    active: bool = True
    note: str | None = None
```

Ce que ca signifie:

- `name: str` est obligatoire.
- `active: bool = True` peut etre omis, donc il vaut `True`.
- `note: str | None = None` peut etre omis et peut aussi valoir `None`.

Piege important: `str | None` autorise `None`, mais ne rend pas le champ
optionnel tout seul. Pour que le champ puisse etre absent, il faut une valeur
par defaut:

```python
note: str | None = None
```

---

## 5. `datetime`

Si un champ est declare en `datetime`, je dois fournir une vraie date ou une
string que Pydantic sait parser:

```python
from datetime import UTC, datetime


created_at: datetime
```

Exemples valides:

```python
timestamp=datetime.now(UTC)
timestamp="2024-01-01T10:30:00"
```

Mettre une timezone n'est pas toujours obligatoire, mais c'est plus propre si je
veux eviter les dates ambigues:

```python
datetime.now(UTC)
```

Si j'oublie le champ, Pydantic me dit:

```text
Field required
```

Ca veut dire que le probleme n'est pas mon validator custom: le champ obligatoire
manque deja.

---

## 6. `Enum` pour limiter les valeurs possibles

Une `Enum` sert quand je veux accepter seulement certaines valeurs.

```python
from enum import Enum


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
```

Puis je l'utilise dans un modele:

```python
class Task(BaseModel):
    priority: Priority
```

Ce qui est utile:

- `"high"` est accepte.
- `"urgent"` est refuse.
- Le sujet est plus clair parce que les valeurs autorisees sont regroupees au
  meme endroit.

Dans les exercices, les enums servent surtout a representer des categories
fermees.

---

## 7. `@model_validator(mode="after")`

`Field` valide un seul champ. Mais parfois la regle depend de plusieurs champs.
Dans ce cas, j'utilise un validator de modele.

Exemple simple:

```python
from typing import Self
from pydantic import BaseModel, model_validator


class DateRange(BaseModel):
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def check_order(self) -> Self:
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self
```

Ce que je dois absolument retenir:

- `mode="after"` veut dire que les champs ont deja ete valides.
- Dans le validator, `self.start` et `self.end` sont deja des `datetime`.
- Pour signaler une erreur, je fais `raise ValueError("message")`.
- A la fin, je dois faire `return self`.

Je n'appelle pas le validator moi-meme. Pydantic l'appelle automatiquement quand
je cree l'objet:

```python
date_range = DateRange(start="2024-01-02", end="2024-01-01")
```

Si la regle casse, Pydantic transforme mon `ValueError` en `ValidationError`.

---

## 8. Comment afficher une erreur attendue

Quand je montre volontairement un cas invalide, je ne dois pas laisser le
programme crasher. Je fais un `try/except`.

```python
from pydantic import ValidationError


try:
    Book(title="", year=3000)
except ValidationError as error:
    print("Expected validation error:")
    print(error.errors()[0]["msg"])
```

Si le message vient d'un `ValueError` dans un `model_validator`, Pydantic ajoute
souvent le prefixe `Value error, `. Pour afficher seulement mon message:

```python
print(error.errors()[0]["msg"].replace("Value error, ", ""))
```

Je dois eviter ca:

```python
invalid_book = Book(...)
```

si je n'utilise jamais `invalid_book`, parce que `flake8` peut signaler:

```text
F841 local variable 'invalid_book' is assigned to but never used
```

Dans ce cas, j'appelle juste le modele pour declencher la validation:

```python
try:
    Book(...)
except ValidationError as error:
    print(error.errors()[0]["msg"])
```

---

## 9. Modeles imbriques

Un modele peut contenir un autre modele.

```python
class Author(BaseModel):
    name: str = Field(min_length=2)


class Library(BaseModel):
    name: str
    authors: list[Author] = Field(min_length=1)
```

Pydantic valide aussi les enfants:

```python
library = Library(
    name="42",
    authors=[{"name": "Ada"}, {"name": "Alan"}],
)
```

Si un enfant est invalide, le parent est invalide aussi. L'erreur indique le
chemin du probleme, par exemple `authors -> 0 -> name`.

C'est utile pour l'exercice avec des objets qui contiennent des listes d'autres
objets.

---

## 10. Les methodes Pydantic utiles

Je peux creer un modele directement avec le constructeur:

```python
book = Book(title="Dune", year=1965)
```

Mais Pydantic donne aussi des methodes utiles:

| Methode | Utilite |
| --- | --- |
| `Model.model_validate(dict)` | valider depuis un dictionnaire |
| `Model.model_validate_json(str)` | valider depuis une string JSON |
| `obj.model_dump()` | convertir le modele en dictionnaire |
| `obj.model_dump_json()` | convertir le modele en JSON |
| `Model.model_json_schema()` | voir le schema JSON du modele |

Pour les exercices, `model_validate` est utile si les donnees viennent d'un
fichier deja parse.

---

## 11. Outils a lancer avant de rendre

Je dois verifier le style:

```bash
flake8
```

Je dois verifier les types:

```bash
mypy .
```

Et je dois lancer le programme:

```bash
python alien_contact.py
```

Si j'utilise Fish avec un venv, je dois activer le bon fichier:

```fish
source .venv/bin/activate.fish
```

Pas:

```fish
source .venv/bin/activate
```

parce que `activate` est pour Bash.

---

## 12. Questions que je dois savoir defendre

### Pourquoi heriter de `BaseModel` ?

Parce que sinon mes annotations ne valident rien a l'execution. `BaseModel`
donne la validation automatique, les erreurs structurees et les methodes comme
`model_dump()`.

### Pourquoi utiliser `Field` ?

Parce que le type ne suffit pas. `int` dit seulement que je veux un entier.
`Field(ge=1, le=20)` dit les limites exactes.

### Pourquoi utiliser un `model_validator` ?

Parce que certaines regles dependent de plusieurs champs. Exemple: si un type
vaut une certaine valeur, alors un autre champ doit respecter une condition.

### Pourquoi `mode="after"` ?

Parce que je veux travailler sur un objet deja valide champ par champ. Je peux
donc comparer des vrais `datetime`, des vrais `Enum`, des vrais `int`, etc.

### Pourquoi `return self` ?

Parce qu'un validator `after` doit rendre l'instance validee. Si je l'oublie, le
validator ne respecte pas le contrat attendu par Pydantic.

### Pourquoi attraper `ValidationError` ?

Parce qu'un cas invalide ne doit pas faire planter toute ma demo. Je veux afficher
une erreur claire, puis continuer le programme.

### Est-ce que `flake8` et `mypy` prouvent que mon sujet est bon ?

Non. `flake8` verifie surtout le style. `mypy` verifie les types. Ils peuvent
laisser passer une mauvaise regle metier. Je dois aussi tester les cas limites.

---

## 13. Mini checklist par exercice

Pour chaque exercice, je verifie:

- Les imports sont propres.
- Tous les champs ont une annotation.
- Les contraintes du sujet sont dans `Field`.
- Les categories fermees sont dans une `Enum`.
- Les regles qui dependent de plusieurs champs sont dans un `model_validator`.
- Le validator finit par `return self`.
- Les erreurs attendues sont dans un `try/except ValidationError`.
- Le programme affiche un cas valide et un cas invalide.
- `flake8` passe.
- `mypy` passe.

---

## 14. Liens officiels

- Models: <https://docs.pydantic.dev/latest/concepts/models/>
- Fields: <https://docs.pydantic.dev/latest/concepts/fields/>
- Validators: <https://docs.pydantic.dev/latest/concepts/validators/>
- Strict mode: <https://docs.pydantic.dev/latest/concepts/strict_mode/>
- Conversion table: <https://docs.pydantic.dev/latest/concepts/conversion_table/>

