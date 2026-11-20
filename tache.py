"""
tache.py - TP 7 : Mixins, Exercice 3

Une Tache est composée de trois mixins, chacun avec UNE seule responsabilité :
  - ValidationMixin     : le titre est toujours renseigné et non vide
  - HistoriqueMixin     : conserve les anciennes versions de la description
  - JournalisationMixin : affiche une trace des actions dans la console

Pas de hiérarchie profonde : Tache hérite directement des trois mixins,
qui sont indépendants entre eux (aucun ne connaît les autres).
"""

# copy   : pour cloner proprement une valeur (deepcopy = copie complète)
# datetime : pour horodater l'historique et le journal
import copy
from datetime import datetime


# ======================================================================
# MIXIN 1 : VALIDATION
# ======================================================================
class ValidationMixin:
    """Garantit que l'attribut 'titre' est toujours valide."""

    def __setattr__(self, nom, valeur):
        # __setattr__ est appelée À CHAQUE affectation  self.xxx = ...
        # On intercepte donc toute écriture du titre, à la création comme
        # plus tard (tache.titre = "") : le titre est "toujours" validé.
        if nom == "titre":
            self._verifier_titre(valeur)
        # On délègue ensuite l'affectation réelle à la classe suivante
        # dans le MRO (en dernier recours : object).
        super().__setattr__(nom, valeur)

    @staticmethod
    def _verifier_titre(titre):
        """Lève une exception si le titre est absent, non texte ou vide."""
        if titre is None:
            raise ValueError("Le titre est obligatoire")
        if not isinstance(titre, str):
            raise TypeError(f"Le titre doit être une chaîne (reçu : {type(titre).__name__})")
        # strip() enlève les espaces : "   " est donc considéré comme vide
        if not titre.strip():
            raise ValueError("Le titre ne peut pas être vide")

    def valider(self):
        """Valide l'état courant de l'objet (utile avant une opération)."""
        # getattr(..., None) évite une AttributeError si 'titre' n'existe pas
        self._verifier_titre(getattr(self, "titre", None))


# ======================================================================
# MIXIN 2 : HISTORIQUE
# ======================================================================
class HistoriqueMixin:
    """Conserve chaque version antérieure de la description."""

    def _init_historique(self):
        # Doit être appelée une fois par la classe finale (dans son __init__).
        # On n'utilise pas __init__ ici pour éviter les conflits entre mixins.
        self._historique = []

    def enregistrer_version(self, description):
        """Ajoute (date, description) à l'historique."""
        # deepcopy : on stocke un CLONE, pour qu'une modification ultérieure
        # de l'original (si ce n'était pas un str, mais une liste par ex.)
        # ne change pas l'historique.
        self._historique.append((datetime.now(), copy.deepcopy(description)))

    @property
    def historique(self):
        """Lecture seule : retourne un tuple (immuable) des versions."""
        # Un tuple empêche de modifier l'historique depuis l'extérieur
        # avec  tache.historique.append(...)
        return tuple(self._historique)


# ======================================================================
# MIXIN 3 : JOURNALISATION
# ======================================================================
class JournalisationMixin:
    """Affiche une trace horodatée des actions."""

    def journaliser(self, message):
        print(f"[Journal] {datetime.now()}: {message}")


# ======================================================================
# CLASSE PRINCIPALE : TACHE
# ======================================================================
# Ordre des mixins = ordre du MRO (Method Resolution Order) : Python cherche
# une méthode d'abord dans Tache, puis ValidationMixin, HistoriqueMixin,
# JournalisationMixin, puis object. Ici aucun conflit de noms.
class Tache(ValidationMixin, HistoriqueMixin, JournalisationMixin):
    """Une tâche professionnelle avec validation, historique et journal."""

    def __init__(self, titre, description=""):
        # Grâce à ValidationMixin.__setattr__, cette ligne valide le titre :
        # si invalide, une exception est levée et l'objet n'est pas créé.
        self.titre = titre

        self._verifier_description(description)
        self.description = description

        # Date de création, fixée une seule fois
        self.date_creation = datetime.now()

        # Prépare la liste vide de l'historique
        self._init_historique()

        self.journaliser(f"Création de la tâche '{self.titre}'")

    @staticmethod
    def _verifier_description(description):
        if not isinstance(description, str):
            raise TypeError(
                f"La description doit être une chaîne (reçu : {type(description).__name__})"
            )

    def mettre_a_jour(self, description):
        """Met à jour la description en conservant l'ancienne version."""
        # 1) On valide TOUT avant de modifier quoi que ce soit : si une
        #    erreur survient, l'objet et l'historique restent inchangés.
        self.valider()
        self._verifier_description(description)

        # 2) On sauvegarde l'ANCIENNE description dans l'historique
        self.enregistrer_version(self.description)

        # 3) On applique la nouvelle valeur
        self.description = description

        # 4) On trace l'opération
        self.journaliser(f"Mise à jour de la tâche '{self.titre}'")

    def afficher_historique(self):
        """Affiche les anciennes versions de la description."""
        if not self.historique:
            print(f"Aucun historique pour '{self.titre}'.")
            return
        print(f"Historique de '{self.titre}' :")
        # enumerate(..., start=1) numérote les versions à partir de 1
        for numero, (date, ancienne) in enumerate(self.historique, start=1):
            print(f"  v{numero} ({date:%Y-%m-%d %H:%M:%S}) : {ancienne}")


if __name__ == "__main__":
    t = Tache("Préparer la réunion", "Version 1")
    t.mettre_a_jour("Version 2")
    t.mettre_a_jour("Version 3")
    t.afficher_historique()
    print("MRO :", [c.__name__ for c in Tache.__mro__])