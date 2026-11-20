"""
contrat.py - TP 7 : Mixins, Exercice 2

Mixins : Serializable (JSON), Historisable (états passés), Journalisable
(trace console) + extensions : Horodatable, CsvMixin, XmlMixin.
Appliqués à plusieurs classes métiers : Contrat, Commande, Client.

NOTE : dans le code de l'énoncé, to_json() sérialise self.__dict__, qui
contient aussi 'historique' (avec des datetime). json.dumps échoue alors
(TypeError) et la sortie attendue {"id": 1, "description": "Révisé"} ne
peut pas être obtenue. De plus, chaque état sauvegardé contiendrait
l'historique lui-même (copies imbriquées). On range donc l'état interne
dans des attributs préfixés par "_" et on n'exporte que les attributs
publics.
"""

import copy
import csv
import io
import json
import xml.etree.ElementTree as ET
from datetime import datetime


def donnees_publiques(objet):
    """Attributs publics seulement (ceux qui ne commencent pas par _)."""
    return {k: v for k, v in vars(objet).items() if not k.startswith("_")}


# ======================================================================
# MIXINS
# ======================================================================
class Serializable:
    """Export / import JSON."""

    def to_json(self):
        return json.dumps(donnees_publiques(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str):
        donnees = json.loads(json_str)  # JSON invalide -> ValueError
        if not isinstance(donnees, dict):
            raise ValueError("Le JSON doit représenter un objet")
        # cls(**donnees) : les clés du JSON deviennent les arguments du
        # constructeur. Une clé inconnue ou manquante lève un TypeError.
        return cls(**donnees)


class Historisable:
    """Conserve les états successifs de l'objet."""

    def enregistrer_etat(self):
        # deepcopy : copie indépendante, pour que les modifications
        # futures ne changent pas l'état archivé.
        etat = copy.deepcopy(donnees_publiques(self))
        self.__dict__.setdefault("_historique", []).append((datetime.now(), etat))

    @property
    def historique(self):
        return tuple(self.__dict__.get("_historique", ()))


class Journalisable:
    """Trace des actions dans la console."""

    def journaliser(self, message):
        print(f"[Journal] {datetime.now()}: {message}")


class Horodatable:
    """(Extension) Date de création et de dernière modification."""

    def _horodater(self):
        maintenant = datetime.now()
        # La date de création n'est fixée qu'une fois (setdefault)
        self.__dict__.setdefault("_cree_le", maintenant)
        self.__dict__["_modifie_le"] = maintenant

    @property
    def cree_le(self):
        return self.__dict__.get("_cree_le")

    @property
    def modifie_le(self):
        return self.__dict__.get("_modifie_le")


class CsvMixin:
    """(Extension) Export CSV : une ligne d'en-tête + une ligne de données."""

    def to_csv(self):
        donnees = donnees_publiques(self)
        tampon = io.StringIO()  # "fichier" en mémoire
        # lineterminator="\n" : évite les \r\n par défaut du module csv
        writer = csv.DictWriter(tampon, fieldnames=list(donnees), lineterminator="\n")
        writer.writeheader()
        writer.writerow(donnees)
        return tampon.getvalue()


class XmlMixin:
    """(Extension) Export XML : une balise par attribut public."""

    def to_xml(self):
        # La balise racine porte le nom de la classe : <Contrat>...</Contrat>
        racine = ET.Element(type(self).__name__)
        for cle, valeur in donnees_publiques(self).items():
            ET.SubElement(racine, cle).text = str(valeur)
        return ET.tostring(racine, encoding="unicode")


# ======================================================================
# CLASSES MÉTIER (mêmes mixins réutilisés, assemblés différemment)
# ======================================================================
class Contrat(Serializable, Historisable, Journalisable,
              Horodatable, CsvMixin, XmlMixin):
    def __init__(self, id, description):  # 'id' : nom imposé par l'énoncé
        self.id = id
        self.description = description
        self._horodater()

    def modifier(self, nouvelle_desc):
        if not isinstance(nouvelle_desc, str):
            raise TypeError("La description doit être une chaîne")
        self.journaliser(f"Modification du contrat {self.id}")
        self.enregistrer_etat()       # on archive l'état AVANT de changer
        self.description = nouvelle_desc
        self._horodater()


class Commande(Serializable, Historisable, Journalisable, CsvMixin):
    def __init__(self, id, client, montant):
        self.id = id
        self.client = client
        self.montant = montant

    def modifier(self, nouveau_montant):
        if not isinstance(nouveau_montant, (int, float)) or nouveau_montant < 0:
            raise ValueError("Le montant doit être un nombre positif")
        self.journaliser(f"Modification de la commande {self.id}")
        self.enregistrer_etat()
        self.montant = nouveau_montant


class Client(Serializable, Historisable, XmlMixin):
    def __init__(self, id, nom, email):
        self.id = id
        self.nom = nom
        self.email = email

    def modifier(self, nouvel_email):
        if "@" not in str(nouvel_email):
            raise ValueError("Email invalide")
        self.enregistrer_etat()
        self.email = nouvel_email


if __name__ == "__main__":
    c = Contrat(1, "Initial")
    c.modifier("Révisé")
    print(c.to_json())
    print(c.to_csv())
    print(c.to_xml())
    print(c.historique)