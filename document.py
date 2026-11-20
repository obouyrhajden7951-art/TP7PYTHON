"""
document.py - TP 7 : Mixins, Exercice 1

Un Document reçoit des comportements transversaux grâce à des mixins :
  - Horodatable  : affiche un log horodaté
  - Validable    : valide l'objet (classe ABC avec méthode abstraite)
  - Serializable : export JSON (extension)
  - Historisable : garde la liste des actions effectuées (extension)

Un mixin est une petite classe qu'on N'INSTANCIE PAS seule : on la
mélange à une classe principale pour lui ajouter des méthodes.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime


def donnees_publiques(objet):
    """Retourne les attributs 'publics' (ceux qui ne commencent pas par _)."""
    # vars(objet) = dictionnaire des attributs de l'objet.
    # On exclut ceux qui commencent par "_" (état interne comme l'historique),
    # car ils ne doivent pas être exportés (et peuvent contenir des datetime,
    # que json ne sait pas écrire).
    return {k: v for k, v in vars(objet).items() if not k.startswith("_")}


# ======================================================================
# MIXIN 1 : HORODATAGE
# ======================================================================
class Horodatable:
    def horodatage(self):
        # datetime.now() donne la date et l'heure courantes
        print(f"[LOG] Action à {datetime.now()}")


# ======================================================================
# MIXIN 2 : VALIDATION (avec abc.ABC)
# ======================================================================
# ABC + @abstractmethod : on ne peut pas créer d'objet tant que la classe
# n'a pas implémenté 'erreurs_validation'. Cela FORCE chaque classe qui
# utilise ce mixin à dire ce qu'est "valide" pour elle.
#
# valider() est une "méthode patron" (template method) : l'algorithme est
# fixé ici (récupérer les erreurs, lever une exception, sinon afficher OK),
# et seul le détail (les règles) est délégué à la classe fille.
class Validable(ABC):
    @abstractmethod
    def erreurs_validation(self):
        """Doit retourner la liste des messages d'erreur (vide si tout va bien)."""

    def valider(self):
        erreurs = self.erreurs_validation()
        if erreurs:
            # "; ".join(...) assemble plusieurs messages en un seul texte
            raise ValueError("; ".join(erreurs))
        print("Validation OK")


# ======================================================================
# MIXIN 3 : SÉRIALISATION JSON (extension)
# ======================================================================
class Serializable:
    def to_json(self):
        # ensure_ascii=False garde les accents lisibles
        return json.dumps(donnees_publiques(self), ensure_ascii=False)


# ======================================================================
# MIXIN 4 : HISTORIQUE DES ACTIONS (extension)
# ======================================================================
class Historisable:
    def enregistrer_action(self, action):
        # setdefault crée la liste "_historique" au premier appel seulement :
        # ainsi le mixin n'a PAS besoin de __init__ (donc pas de conflit
        # d'initialisation avec les autres mixins).
        self.__dict__.setdefault("_historique", []).append((datetime.now(), action))

    @property
    def historique(self):
        # Retourne un tuple : lecture seule (impossible de le modifier de l'extérieur)
        return tuple(self.__dict__.get("_historique", ()))


# ======================================================================
# CLASSE PRINCIPALE
# ======================================================================
# Document hérite des 4 mixins "à plat" (pas de hiérarchie profonde).
class Document(Horodatable, Validable, Serializable, Historisable):
    def __init__(self, titre, contenu):
        self.titre = titre
        self.contenu = contenu

    # Implémentation OBLIGATOIRE de la méthode abstraite de Validable
    def erreurs_validation(self):
        erreurs = []
        # Titre absent, non texte, ou fait uniquement d'espaces
        if not isinstance(self.titre, str) or not self.titre.strip():
            erreurs.append("Titre manquant")
        return erreurs

    def sauvegarder(self):
        self.horodatage()                 # méthode de Horodatable
        self.valider()                    # méthode de Validable (peut lever ValueError)
        print(f"Document '{self.titre}' sauvegardé.")
        self.enregistrer_action("sauvegarde")  # méthode de Historisable


if __name__ == "__main__":
    doc = Document("Rapport", "Contenu important")
    doc.sauvegarder()
    print(doc.to_json())
    print(doc.historique)