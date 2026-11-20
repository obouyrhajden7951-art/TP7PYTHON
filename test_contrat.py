"""
test_contrat.py - Tests de contrat.py
Lancer avec :  python -m unittest test_contrat -v
"""

import io
import json
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout
from datetime import datetime

from contrat import (
    Contrat, Commande, Client,
    Serializable, Historisable, Journalisable, Horodatable, CsvMixin, XmlMixin,
)


def capturer(fonction, *args):
    tampon = io.StringIO()
    with redirect_stdout(tampon):
        fonction(*args)
    return tampon.getvalue()


class TestContrat(unittest.TestCase):
    def setUp(self):
        self.c = Contrat(1, "Initial")

    def test_exemple_de_l_enonce(self):
        sortie = capturer(self.c.modifier, "Révisé")
        self.assertRegex(sortie, r"^\[Journal\] .*: Modification du contrat 1\n$")
        self.assertEqual(self.c.to_json(), '{"id": 1, "description": "Révisé"}')

    def test_modifier_change_la_description(self):
        with redirect_stdout(io.StringIO()):
            self.c.modifier("Nouveau")
        self.assertEqual(self.c.description, "Nouveau")

    def test_modifier_type_invalide(self):
        with self.assertRaises(TypeError):
            self.c.modifier(123)
        self.assertEqual(self.c.description, "Initial")
        self.assertEqual(self.c.historique, ())  # rien d'archivé

    def test_to_json_fonctionne_apres_modification(self):
        # Régression : l'historique (datetime) ne doit pas casser to_json
        with redirect_stdout(io.StringIO()):
            self.c.modifier("A")
            self.c.modifier("B")
        data = json.loads(self.c.to_json())
        self.assertEqual(set(data), {"id", "description"})


class TestHistorique(unittest.TestCase):
    def test_etat_archive_avant_modification(self):
        c = Contrat(1, "Initial")
        with redirect_stdout(io.StringIO()):
            c.modifier("Révisé")
        self.assertEqual(len(c.historique), 1)
        date, etat = c.historique[0]
        self.assertIsInstance(date, datetime)
        self.assertEqual(etat, {"id": 1, "description": "Initial"})

    def test_pas_d_historique_imbrique(self):
        c = Contrat(1, "v1")
        with redirect_stdout(io.StringIO()):
            c.modifier("v2")
            c.modifier("v3")
        for _, etat in c.historique:
            self.assertNotIn("historique", etat)
            self.assertNotIn("_historique", etat)

    def test_ordre_des_etats(self):
        c = Contrat(1, "v1")
        with redirect_stdout(io.StringIO()):
            c.modifier("v2")
            c.modifier("v3")
        self.assertEqual([e["description"] for _, e in c.historique], ["v1", "v2"])

    def test_etat_archive_independant(self):
        # Une valeur modifiable (liste) doit être clonée dans l'archive
        class Panier(Historisable):
            def __init__(self):
                self.articles = ["a"]
        p = Panier()
        p.enregistrer_etat()
        p.articles.append("b")
        self.assertEqual(p.historique[0][1]["articles"], ["a"])

    def test_historiques_separes_entre_instances(self):
        c1, c2 = Contrat(1, "a"), Contrat(2, "b")
        with redirect_stdout(io.StringIO()):
            c1.modifier("x")
        self.assertEqual(c2.historique, ())

    def test_lecture_seule(self):
        c = Contrat(1, "a")
        with self.assertRaises(AttributeError):
            c.historique.append(1)


class TestFromJson(unittest.TestCase):
    def test_aller_retour(self):
        c = Contrat(7, "Texte")
        c2 = Contrat.from_json(c.to_json())
        self.assertEqual((c2.id, c2.description), (7, "Texte"))

    def test_json_invalide(self):
        with self.assertRaises(ValueError):
            Contrat.from_json("pas du json")

    def test_json_pas_un_objet(self):
        with self.assertRaises(ValueError):
            Contrat.from_json("[1, 2]")

    def test_champ_manquant(self):
        with self.assertRaises(TypeError):
            Contrat.from_json('{"id": 1}')

    def test_champ_inconnu(self):
        with self.assertRaises(TypeError):
            Contrat.from_json('{"id": 1, "description": "a", "x": 2}')


class TestHorodatable(unittest.TestCase):
    def test_dates_a_la_creation(self):
        c = Contrat(1, "a")
        self.assertIsInstance(c.cree_le, datetime)
        self.assertEqual(c.cree_le, c.modifie_le)

    def test_modification_met_a_jour_modifie_le_seulement(self):
        c = Contrat(1, "a")
        creation = c.cree_le
        with redirect_stdout(io.StringIO()):
            c.modifier("b")
        self.assertEqual(c.cree_le, creation)       # inchangée
        self.assertGreaterEqual(c.modifie_le, creation)

    def test_dates_non_exportees(self):
        self.assertNotIn("cree_le", Contrat(1, "a").to_json())


class TestExports(unittest.TestCase):
    def test_csv(self):
        self.assertEqual(Contrat(1, "Texte").to_csv(), "id,description\n1,Texte\n")

    def test_csv_echappe_les_virgules(self):
        # Le module csv met automatiquement des guillemets si besoin
        self.assertEqual(Contrat(1, "a, b").to_csv(), 'id,description\n1,"a, b"\n')

    def test_xml(self):
        self.assertEqual(
            Contrat(1, "Révisé").to_xml(),
            "<Contrat><id>1</id><description>Révisé</description></Contrat>",
        )

    def test_xml_echappe_les_caracteres_speciaux(self):
        xml = Contrat(1, "a < b & c").to_xml()
        racine = ET.fromstring(xml)  # doit rester du XML valide
        self.assertEqual(racine.find("description").text, "a < b & c")


class TestAutresClasses(unittest.TestCase):
    def test_commande(self):
        cmd = Commande(10, "Alice", 50.0)
        with redirect_stdout(io.StringIO()):
            cmd.modifier(75.5)
        self.assertEqual(cmd.montant, 75.5)
        self.assertEqual(cmd.historique[0][1]["montant"], 50.0)
        self.assertEqual(cmd.to_csv(), "id,client,montant\n10,Alice,75.5\n")

    def test_commande_montant_invalide(self):
        cmd = Commande(10, "Alice", 50)
        for valeur in (-1, "10", None):
            with self.subTest(valeur=valeur):
                with self.assertRaises(ValueError):
                    cmd.modifier(valeur)
        self.assertEqual(cmd.montant, 50)

    def test_client(self):
        cl = Client(1, "Bob", "bob@mail.com")
        cl.modifier("bob@new.com")
        self.assertEqual(cl.email, "bob@new.com")
        self.assertEqual(cl.historique[0][1]["email"], "bob@mail.com")
        self.assertIn("<Client>", cl.to_xml())

    def test_client_email_invalide(self):
        with self.assertRaises(ValueError):
            Client(1, "Bob", "bob@mail.com").modifier("sans-arobase")

    def test_chaque_classe_a_ses_mixins_seulement(self):
        self.assertFalse(hasattr(Commande, "to_xml"))   # pas de XmlMixin
        self.assertFalse(hasattr(Client, "to_csv"))     # pas de CsvMixin
        self.assertFalse(hasattr(Client, "journaliser"))


class TestStructure(unittest.TestCase):
    def test_journalisable_seul(self):
        class S(Journalisable):
            pass
        self.assertIn("hello", capturer(S().journaliser, "hello"))

    def test_serializable_seul(self):
        class P(Serializable):
            def __init__(self, x):
                self.x = x
        self.assertEqual(P(3).to_json(), '{"x": 3}')

    def test_contrat_instance_des_mixins(self):
        c = Contrat(1, "a")
        for m in (Serializable, Historisable, Journalisable, Horodatable, CsvMixin, XmlMixin):
            self.assertIsInstance(c, m)


if __name__ == "__main__":
    unittest.main()